"""
The benchmark harness: runs intrepyd's engines, and Kind2, on the Lustre
benchmarks listed in kind2-benchmarks.txt, and reports and compares the runs.

    python benchmarks/harness.py run OUT.jsonl [--tools bmc,kind,br,pdr,portfolio]
        [--timeout 10] [--memory 4096] [--int-type int32|int] [--library PATH]
        [--cpus 0-15] [--portfolio-cpus 4] [--filter REGEX] [--kind2 PATH]
        [--z3 PATH]
    python benchmarks/harness.py report OUT.jsonl... [--expected kind2-benchmarks.txt]
    python benchmarks/harness.py compare A.jsonl B.jsonl

run executes each file x tool pair in a process of its own, as many at a
time as the cpus allow: each single engine gets one cpu, a portfolio (ours,
or Kind2's) gets --portfolio-cpus of them, bound to it, so that every tool
works with the same number of cores; by default, the cpus are one thread per
physical core. A run that passes the timeout is killed, as is one whose
processes together use more than --memory MB. Each result is appended to OUT
as a line of JSON as soon as it is known, and a run started again with the
same OUT skips the pairs it already has, so a long run can be interrupted.

The tools:

    bmc, kind, br, pdr  one engine of intrepyd, as the portfolio runs it
                        (kind is BMC with k-induction)
    portfolio           intrepyd's portfolio, all four engines in parallel
    kind2               Kind2 as it runs by default, all its engines in
                        parallel
    kind2_bmc           Kind2's BMC alone
    kind2_kind          Kind2's k-induction, BMC with IND
    kind2_ic3           Kind2's IC3 alone (IC3QE, on z3)
    kind2_ic3ia         Kind2's IC3 with implicit abstraction (IC3IA)

Each .lus file is translated once per --int-type, and the encoding is kept in
benchmarks/cache, until the file or the translator changes. Kind2 reads Lustre
int as unbounded integers: compare it with --int-type int. It uses the z3
executable given by --z3 (by default, z3 on the PATH), which should be the
z3 that intrepid is built with.

report gives, per tool, the solved models, their verdicts and times; the
models where tools disagree (a bug in one of them); the verdicts that
contradict --expected (which follow 32 bit semantics); and, for each of
intrepyd's tools against its Kind2 counterpart, the models solved by one only
and those solved much faster by one. compare does the same for the same tool
in two runs, for instance two versions of libintrepid.
"""

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BENCHMARKS = os.path.join(HERE, 'kind2-benchmarks')
LIST = os.path.join(HERE, 'kind2-benchmarks.txt')
CACHE = os.path.join(HERE, 'cache')

INTREPYD_TOOLS = ('bmc', 'kind', 'br', 'pdr', 'portfolio')
KIND2_TOOLS = {
    'kind2': [],
    'kind2_bmc': ['--enable', 'BMC'],
    'kind2_kind': ['--enable', 'BMC', '--enable', 'IND'],
    'kind2_ic3': ['--enable', 'IC3QE'],
    'kind2_ic3ia': ['--enable', 'IC3IA'],
}
TOOLS = INTREPYD_TOOLS + tuple(KIND2_TOOLS)
PORTFOLIOS = ('portfolio', 'kind2')
# Each of intrepyd's tools, and the Kind2 tool it is measured against
COUNTERPARTS = [('portfolio', 'kind2'), ('bmc', 'kind2_bmc'), ('kind', 'kind2_kind'),
                ('pdr', 'kind2_ic3'), ('pdr', 'kind2_ic3ia')]
SOLVED = ('Valid', 'Invalid')
# Kind2 and the portfolio stop at their timeout: kill them this long after
# it, if they are still there; the single engines have no timeout of their
# own, and are killed at it
GRACE = 2.0


# Translation

def translator_digest():
    """A digest of the sources of the translator, to know when a cache is stale"""
    import intrepyd.lustre2py  # pylint: disable=import-outside-toplevel
    folder = os.path.dirname(intrepyd.lustre2py.__file__)
    digest = hashlib.sha256()
    for name in sorted(os.listdir(folder)):
        if name.endswith('.py'):
            with open(os.path.join(folder, name), 'rb') as stream:
                digest.update(name.encode() + stream.read())
    return digest.hexdigest()


def encoding_path(name, int_type):
    return os.path.join(CACHE, int_type, name[:-len('.lus')] + '.py')


def translate(name, int_type, translator):
    """
    Translates benchmark name (relative to BENCHMARKS) unless the cache has
    it already; returns None, or the error
    """
    from intrepyd.lustre2py import translator as lustre  # pylint: disable=import-outside-toplevel
    source = os.path.join(BENCHMARKS, name)
    out = encoding_path(name, int_type)
    with open(source, 'rb') as stream:
        key = hashlib.sha256(stream.read() + translator.encode()).hexdigest()
    stamp = out + '.key'
    if os.path.exists(out) and os.path.exists(stamp):
        with open(stamp) as stream:
            if stream.read() == key:
                return None
    os.makedirs(os.path.dirname(out), exist_ok=True)
    try:
        lustre.translate(source, 'top', out, 'real', int_type)
    except Exception as error:  # pylint: disable=broad-except
        return '%s: %s' % (type(error).__name__, error)
    with open(stamp, 'w') as stream:
        stream.write(key)
    return None


# The worker, a process that runs one of intrepyd's tools on one encoding

def worker(arguments):
    """Prints one line of JSON: the verdict, and the engine that gave it"""
    from intrepyd.context import Context  # pylint: disable=import-outside-toplevel
    from intrepyd.engine import EngineResult  # pylint: disable=import-outside-toplevel
    from intrepyd import portfolio  # pylint: disable=import-outside-toplevel
    spec = importlib.util.spec_from_file_location('encoding', arguments.encoding)
    encoding = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(encoding)
    context = Context()
    circuit = encoding.mk_instance(context, arguments.tool)
    circuit.mk_circuit()
    target = context.mk_not(circuit.outputs['OK'])
    engine = arguments.tool
    depth = None
    if arguments.tool == 'portfolio':
        engines = context.mk_portfolio()
        engines.add_target(target)
        result = engines.reach_targets(timeout=arguments.timeout)
        engine = engines.get_last_engine()
        errors = engines.get_last_errors()
        if result == EngineResult.UNKNOWN and errors and len(errors) == len(portfolio.ENGINES):
            raise RuntimeError('; '.join('%s: %s' % item for item in sorted(errors.items())))
    else:
        result, _, depth = portfolio._RUNNERS[arguments.tool](  # pylint: disable=protected-access
            context, [target], None)
    verdict = {EngineResult.REACHABLE: 'Invalid', EngineResult.UNREACHABLE: 'Valid'}.get(result, 'Unknown')
    print(json.dumps({'verdict': verdict, 'engine': engine, 'depth': depth}))


# Running

class Job:  # pylint: disable=too-few-public-methods
    """One file x tool pair"""

    def __init__(self, name, tool):
        self.name = name
        self.tool = tool
        self.cpus = []
        self.process = None
        self.start = None
        self.output = None
        self.errors = None
        self.scratch = None
        self.memout = False


def kind2_command(arguments, job):
    job.scratch = tempfile.mkdtemp(prefix='kind2-')
    return [arguments.kind2, '-json', '--color', 'false', '--timeout', str(arguments.timeout),
            '--lus_main', 'top', '--check_subproperties', 'false', '--output_dir', job.scratch,
            '--smt_solver', 'Z3', '--z3_bin', arguments.z3] + KIND2_TOOLS[job.tool] + \
           [os.path.join(BENCHMARKS, job.name)]


def intrepyd_command(arguments, job):
    return [sys.executable, os.path.abspath(__file__), 'worker', job.tool,
            encoding_path(job.name, arguments.int_type), '--timeout', str(arguments.timeout)]


def parse_kind2(output):
    """The verdict of Kind2 on property OK of top, and the engine that gave it"""
    try:
        # Kind2 writes the newlines of long expressions raw, inside strings
        objects = json.loads(output, strict=False)
    except ValueError:
        return 'Exception', None, 'Kind2 printed no JSON'
    errors = [o.get('value', '') for o in objects if o.get('objectType') == 'log' and o.get('level') in
              ('error', 'fatal')]
    properties = [o for o in objects if o.get('objectType') == 'property']
    chosen = [p for p in properties if p.get('expr') == 'OK'] or properties
    if not chosen:
        return 'Exception', None, '; '.join(errors) or 'Kind2 checked no property'
    answers = [p.get('answer', {}) for p in chosen]
    for answer in answers:
        if answer.get('value') == 'falsifiable':
            return 'Invalid', answer.get('source'), None
    if all(answer.get('value') == 'valid' for answer in answers):
        return 'Valid', answers[0].get('source'), None
    return 'Unknown', None, '; '.join(errors) or None


def finish(arguments, job, killed):
    """The result of a job, as a dictionary"""
    elapsed = time.monotonic() - job.start
    with open(job.output.name, errors='replace') as stream:
        output = stream.read()
    with open(job.errors.name, errors='replace') as stream:
        errors = stream.read().strip()
    os.unlink(job.output.name)
    os.unlink(job.errors.name)
    if job.scratch:
        shutil.rmtree(job.scratch, ignore_errors=True)
    result = {'file': job.name, 'tool': job.tool, 'time': round(elapsed, 3), 'timeout': arguments.timeout,
              'int_type': arguments.int_type, 'engine': None}
    if job.memout:
        result['verdict'] = 'Memout'
    elif killed:
        result['verdict'] = 'Timeout'
    elif job.tool in KIND2_TOOLS:
        verdict, engine, error = parse_kind2(output)
        result.update(verdict=verdict, engine=engine)
        if verdict not in SOLVED and (error or errors):
            result['error'] = '\n'.join(text for text in (error, errors) if text)[-500:]
    else:
        lines = [line for line in output.splitlines() if line.startswith('{')]
        if job.process.returncode == 0 and lines:
            result.update(json.loads(lines[-1]))
        else:
            result.update(verdict='Exception', error=(output + errors).strip()[-500:])
    if result['verdict'] == 'Unknown' and elapsed >= arguments.timeout:
        result['verdict'] = 'Timeout'
    if result['verdict'] == 'Timeout':
        result['time'] = arguments.timeout
    return result


def session_memory():
    """The resident memory, in MB, of every session of processes"""
    pagesize = os.sysconf('SC_PAGE_SIZE')
    used = {}
    for pid in os.listdir('/proc'):
        if not pid.isdigit():
            continue
        try:
            with open('/proc/%s/stat' % pid) as stream:
                fields = stream.read().rsplit(')', 1)[1].split()
        except OSError:
            continue
        # fields[0] is the state, the third field of stat; session is the 6th, rss the 24th
        session, rss = int(fields[3]), int(fields[21])
        used[session] = used.get(session, 0) + rss * pagesize / 2 ** 20
    return used


def default_cpus():
    """One logical cpu per physical core"""
    cpus = []
    for cpu in sorted(os.sched_getaffinity(0)):
        try:
            with open('/sys/devices/system/cpu/cpu%d/topology/thread_siblings_list' % cpu) as stream:
                first = int(re.split('[,-]', stream.read().strip())[0])
        except OSError:
            first = cpu
        if first == cpu:
            cpus.append(cpu)
    return cpus


def parse_cpus(text):
    cpus = []
    for part in text.split(','):
        low, _, high = part.partition('-')
        cpus += range(int(low), int(high or low) + 1)
    return cpus


def benchmarks(arguments):
    with open(arguments.list) as stream:
        names = [line.split()[0] for line in stream if line.strip()]
    if arguments.filter:
        names = [name for name in names if re.search(arguments.filter, name)]
    return names


def done_pairs(path):
    pairs = set()
    if os.path.exists(path):
        with open(path) as stream:
            for line in stream:
                if line.strip():
                    result = json.loads(line)
                    pairs.add((result['file'], result['tool']))
    return pairs


def translate_all(arguments, names):
    """Translates what the intrepyd tools need, in parallel; returns {name: error}"""
    from concurrent.futures import ProcessPoolExecutor  # pylint: disable=import-outside-toplevel
    digest = translator_digest()
    with ProcessPoolExecutor(max_workers=len(arguments.cpus)) as pool:
        errors = list(pool.map(translate, names, [arguments.int_type] * len(names), [digest] * len(names)))
    return {name: error for name, error in zip(names, errors) if error}


def run(arguments):  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    arguments.cpus = parse_cpus(arguments.cpus) if arguments.cpus else default_cpus()
    if arguments.library:
        os.environ['INTREPID_LIBRARY'] = os.path.abspath(arguments.library)
    tools = arguments.tools.split(',')
    for tool in tools:
        if tool not in TOOLS:
            sys.exit('unknown tool %s, not one of %s' % (tool, ', '.join(TOOLS)))
    if not shutil.which('taskset'):
        sys.exit('no taskset, which binds each run to its cpus (util-linux)')
    if any(tool in KIND2_TOOLS for tool in tools) and not shutil.which(arguments.kind2):
        sys.exit('no Kind2 at %s (--kind2)' % arguments.kind2)
    arguments.z3 = shutil.which(arguments.z3) or arguments.z3
    names = benchmarks(arguments)
    done = done_pairs(arguments.out)
    jobs = [Job(name, tool) for name in names for tool in tools if (name, tool) not in done]
    out = open(arguments.out, 'a')  # pylint: disable=consider-using-with
    if any(tool in INTREPYD_TOOLS for tool in tools):
        print('translating %d files' % len(names), flush=True)
        failed = translate_all(arguments, sorted({job.name for job in jobs if job.tool in INTREPYD_TOOLS}))
        for job in [job for job in jobs if job.tool in INTREPYD_TOOLS and job.name in failed]:
            out.write(json.dumps({'file': job.name, 'tool': job.tool, 'time': 0, 'timeout': arguments.timeout,
                                  'int_type': arguments.int_type, 'engine': None,
                                  'verdict': 'Exception', 'error': failed[job.name]}) + '\n')
        jobs = [job for job in jobs if not (job.tool in INTREPYD_TOOLS and job.name in failed)]
    # The portfolios first, as they need the most cpus at once
    jobs.sort(key=lambda job: job.tool not in PORTFOLIOS)
    free = list(arguments.cpus)
    running = []
    total = len(jobs)
    finished = 0
    lock = threading.Lock()
    stop = threading.Event()

    def watch_memory():
        while not stop.wait(0.5):
            used = session_memory()
            with lock:
                for job in running:
                    if used.get(job.process.pid, 0) > arguments.memory:
                        job.memout = True
                        kill(job)

    threading.Thread(target=watch_memory, daemon=True).start()
    try:
        while jobs or running:
            with lock:
                for job in list(running):
                    elapsed = time.monotonic() - job.start
                    killed = False
                    if job.process.poll() is None:
                        if elapsed < arguments.timeout + (GRACE if job.tool in KIND2_TOOLS or
                                                          job.tool == 'portfolio' else 0):
                            continue
                        kill(job)
                        killed = True
                    job.process.wait()
                    running.remove(job)
                    free += job.cpus
                    result = finish(arguments, job, killed)
                    out.write(json.dumps(result) + '\n')
                    out.flush()
                    finished += 1
                    print('[%d/%d] %s %s %s %.2f' % (finished, total, job.name, job.tool, result['verdict'],
                                                     result['time']), flush=True)
                while jobs:
                    need = arguments.portfolio_cpus if jobs[0].tool in PORTFOLIOS else 1
                    if len(free) < min(need, len(arguments.cpus)):
                        break
                    job = jobs.pop(0)
                    job.cpus, free = free[:need], free[need:]
                    launch(arguments, job)
                    running.append(job)
            time.sleep(0.02)
    finally:
        stop.set()
        for job in running:
            kill(job)
        out.close()
    return 0


def launch(arguments, job):
    command = kind2_command(arguments, job) if job.tool in KIND2_TOOLS else intrepyd_command(arguments, job)
    job.output = tempfile.NamedTemporaryFile('w', delete=False, prefix='harness-')  # pylint: disable=consider-using-with
    job.errors = tempfile.NamedTemporaryFile('w', delete=False, prefix='harness-')  # pylint: disable=consider-using-with
    # Bound to its cpus by taskset, which its processes inherit
    command = ['taskset', '-c', ','.join(str(cpu) for cpu in job.cpus)] + command
    job.start = time.monotonic()
    job.process = subprocess.Popen(command, stdout=job.output, stderr=job.errors,  # pylint: disable=consider-using-with
                                   stdin=subprocess.DEVNULL, start_new_session=True)
    job.output.close()
    job.errors.close()


def kill(job):
    try:
        os.killpg(job.process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


# Reports

def load(*paths):
    """{(file, tool): result}, the last result of each pair in paths"""
    results = {}
    for path in paths:
        with open(path) as stream:
            for line in stream:
                if line.strip():
                    result = json.loads(line)
                    results[(result['file'], result['tool'])] = result
    return results


def expected_verdicts(path):
    verdicts = {}
    with open(path) as stream:
        for line in stream:
            fields = line.split()
            if len(fields) >= 2:
                verdicts[fields[0]] = fields[1]
    return verdicts


def solved(result):
    return result is not None and result['verdict'] in SOLVED


def summary(results, tools):
    lines = ['%-12s %6s %6s %6s %8s %8s %6s %6s %6s' % ('tool', 'solved', 'valid', 'invalid', 'time',
                                                       'par2', 'unkn', 'tmout', 'error')]
    for tool in tools:
        mine = [r for (_, t), r in results.items() if t == tool]
        good = [r for r in mine if solved(r)]
        par2 = sum(r['time'] if solved(r) else 2 * r['timeout'] for r in mine)
        lines.append('%-12s %6d %6d %6d %8.1f %8.1f %6d %6d %6d' % (
            tool, len(good), sum(r['verdict'] == 'Valid' for r in good),
            sum(r['verdict'] == 'Invalid' for r in good), sum(r['time'] for r in good), par2,
            sum(r['verdict'] == 'Unknown' for r in mine), sum(r['verdict'] == 'Timeout' for r in mine),
            sum(r['verdict'] in ('Exception', 'Memout') for r in mine)))
    return lines


def head_to_head(first, second, label_first, label_second, files, factor=2.0, floor=1.0):
    """Lines that compare two results per file: solved by one only, much faster"""
    only_first, only_second, faster_first, faster_second = [], [], [], []
    for name in files:
        one, two = first.get(name), second.get(name)
        if solved(one) and not solved(two):
            only_first.append('  %s: %s %.2f, %s %s' % (name, one['verdict'], one['time'], label_second,
                                                        two['verdict'] if two else 'missing'))
        elif solved(two) and not solved(one):
            only_second.append('  %s: %s %.2f, %s %s' % (name, two['verdict'], two['time'], label_first,
                                                         one['verdict'] if one else 'missing'))
        elif solved(one) and solved(two):
            if two['time'] > max(floor, factor * one['time']):
                faster_first.append('  %s: %.2f against %.2f' % (name, one['time'], two['time']))
            elif one['time'] > max(floor, factor * two['time']):
                faster_second.append('  %s: %.2f against %.2f' % (name, two['time'], one['time']))
    both = sum(1 for name in files if solved(first.get(name)) and solved(second.get(name)))
    lines = ['%s against %s: %d solved by both' % (label_first, label_second, both)]
    for title, items in [('solved by %s only' % label_first, only_first),
                         ('solved by %s only' % label_second, only_second),
                         ('%gx faster with %s (and over %gs)' % (factor, label_first, floor), faster_first),
                         ('%gx faster with %s (and over %gs)' % (factor, label_second, floor), faster_second)]:
        lines.append(' %d %s' % (len(items), title))
        lines += sorted(items)
    return lines


def by_file(results, tool):
    return {name: result for (name, t), result in results.items() if t == tool}


def report(arguments):
    results = load(*arguments.results)
    tools = [tool for tool in TOOLS if any(t == tool for _, t in results)]
    files = sorted({name for name, _ in results})
    lines = summary(results, tools)
    lines.append('')
    # Disagreements between tools
    disagreements = []
    for name in files:
        verdicts = {tool: results[(name, tool)]['verdict'] for tool in tools
                    if solved(results.get((name, tool)))}
        if len(set(verdicts.values())) > 1:
            disagreements.append('  %s: %s' % (name, ', '.join('%s %s' % item for item in sorted(verdicts.items()))))
    lines.append('%d models where tools disagree' % len(disagreements))
    lines += disagreements
    if arguments.expected:
        expected = expected_verdicts(arguments.expected)
        contradictions = []
        for (name, tool), result in sorted(results.items()):
            want = expected.get(name)
            if solved(result) and want in SOLVED and result['verdict'] != want:
                contradictions.append('  %s %s: %s, expected %s' % (name, tool, result['verdict'], want))
        lines.append('%d verdicts contradict %s' % (len(contradictions), arguments.expected))
        lines += contradictions
    # Engines of the portfolios
    for tool in PORTFOLIOS:
        engines = {}
        for result in by_file(results, tool).values():
            if solved(result):
                engines[result['engine']] = engines.get(result['engine'], 0) + 1
        if engines:
            lines.append('%s answers by engine: %s' % (tool, ', '.join('%s %d' % item for item in
                                                                         sorted(engines.items(), key=lambda i: -i[1]))))
    for mine, theirs in COUNTERPARTS:
        if mine in tools and theirs in tools:
            lines.append('')
            lines += head_to_head(by_file(results, mine), by_file(results, theirs), mine, theirs, files)
    print('\n'.join(lines))
    return 0


def compare(arguments):
    first, second = load(arguments.first), load(arguments.second)
    tools = [tool for tool in TOOLS if any(t == tool for _, t in first) and any(t == tool for _, t in second)]
    lines = [summary({}, [])[0]]
    for tool in tools:
        files = sorted({name for name, t in first if t == tool} & {name for name, t in second if t == tool})
        for label, results in (('A', first), ('B', second)):
            row = summary({key: value for key, value in results.items() if key[0] in files}, [tool])[1]
            lines.append(('%s %s' % (tool, label)).ljust(12) + row[12:])
        lines += head_to_head(by_file(first, tool), by_file(second, tool), 'A', 'B', files)
        changed = ['  %s: %s, %s' % (name, first[(name, tool)]['verdict'], second[(name, tool)]['verdict'])
                   for name in files if solved(first[(name, tool)]) and solved(second[(name, tool)])
                   and first[(name, tool)]['verdict'] != second[(name, tool)]['verdict']]
        lines.append(' %d different verdicts' % len(changed))
        lines += changed
        lines.append('')
    print('\n'.join(['%s is A, %s is B' % (arguments.first, arguments.second), ''] + lines))
    return 0


def _solved_times(results, tool):
    """The solved times of a tool, ascending."""
    return sorted(r['time'] for r in by_file(results, tool).values() if solved(r))


def plot_cactus(results, tools, path):
    """Benchmarks solved (y) against cumulative time (x), one curve per tool."""
    import matplotlib  # pylint: disable=import-outside-toplevel
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt  # pylint: disable=import-outside-toplevel
    fig, axes = plt.subplots(figsize=(7, 5))
    for tool in tools:
        times = _solved_times(results, tool)
        cumulative, xs, ys = 0.0, [], []
        for index, value in enumerate(times, start=1):
            cumulative += value
            xs.append(cumulative)
            ys.append(index)
        if xs:
            axes.plot(xs, ys, marker='.', markersize=4, label='%s (%d)' % (tool, len(times)))
    axes.set_xlabel('cumulative time (s)')
    axes.set_ylabel('benchmarks solved')
    axes.set_title('Benchmarks solved over time')
    axes.legend()
    axes.grid(True, alpha=0.3)
    fig.savefig(path, dpi=120, bbox_inches='tight')
    plt.close(fig)


def plot_scatter(results, tool_a, tool_b, timeout, path):
    """Per-benchmark runtime of tool_a (y) against tool_b (x), log-log, with the
    timeout as the border; unsolved benchmarks sit on the timeout lines."""
    import matplotlib  # pylint: disable=import-outside-toplevel
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt  # pylint: disable=import-outside-toplevel
    first, second = by_file(results, tool_a), by_file(results, tool_b)
    floor = 0.01
    cap = timeout
    both_x, both_y, one_x, one_y = [], [], [], []
    for name in sorted(set(first) | set(second)):
        one, two = first.get(name), second.get(name)
        if not solved(one) and not solved(two):
            continue
        ya = min(max(one['time'], floor), cap) if solved(one) else cap
        xb = min(max(two['time'], floor), cap) if solved(two) else cap
        if solved(one) and solved(two):
            both_x.append(xb)
            both_y.append(ya)
        else:
            one_x.append(xb)
            one_y.append(ya)
    fig, axes = plt.subplots(figsize=(6, 6))
    axes.plot([floor, cap], [floor, cap], color='gray', linewidth=0.8)  # diagonal
    axes.axvline(cap, color='gray', linewidth=0.6, linestyle='--')
    axes.axhline(cap, color='gray', linewidth=0.6, linestyle='--')
    axes.scatter(both_x, both_y, s=14, label='solved by both')
    axes.scatter(one_x, one_y, s=14, marker='x', label='solved by one only')
    axes.set_xscale('log')
    axes.set_yscale('log')
    axes.set_xlim(floor, cap * 1.3)
    axes.set_ylim(floor, cap * 1.3)
    axes.set_xlabel('%s time (s)' % tool_b)
    axes.set_ylabel('%s time (s)' % tool_a)
    axes.set_title('%s vs %s (timeout %gs)' % (tool_a, tool_b, timeout))
    axes.legend()
    axes.grid(True, which='both', alpha=0.3)
    fig.savefig(path, dpi=120, bbox_inches='tight')
    plt.close(fig)


def plot(arguments):
    """Writes the scatter and cactus plots of a run as PNGs."""
    results = load(*arguments.results)
    if not results:
        print('No results in %s' % ', '.join(arguments.results), file=sys.stderr)
        return 1
    timeout = max(r.get('timeout') or 0 for r in results.values()) or 30.0
    present = [tool for tool in TOOLS if any(t == tool for _, t in results)]
    cactus_tools = arguments.tools.split(',') if arguments.tools else present
    os.makedirs(arguments.out_dir, exist_ok=True)
    cactus_path = os.path.join(arguments.out_dir, 'cactus.png')
    plot_cactus(results, cactus_tools, cactus_path)
    tool_a, tool_b = arguments.pair.split(',')
    scatter_path = os.path.join(arguments.out_dir, 'scatter.png')
    plot_scatter(results, tool_a, tool_b, timeout, scatter_path)
    print('Wrote %s and %s' % (scatter_path, cactus_path))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n', maxsplit=1)[0])
    commands = parser.add_subparsers(dest='command', required=True)
    command = commands.add_parser('run', help='runs tools on the benchmarks')
    command.add_argument('out', help='the results, a line of JSON each, appended to')
    command.add_argument('--tools', default=','.join(INTREPYD_TOOLS), help='comma separated, among: ' +
                         ', '.join(TOOLS))
    command.add_argument('--timeout', type=float, default=10, help='seconds per run (10)')
    command.add_argument('--memory', type=float, default=4096, help='MB per run (4096)')
    command.add_argument('--int-type', default='int32', choices=['int32', 'int'],
                         help='how Lustre int is encoded for intrepyd (int32)')
    command.add_argument('--library', help='the libintrepid to load (INTREPID_LIBRARY)')
    command.add_argument('--cpus', help='the cpus to use, as 0-7,16 (one thread per physical core)')
    command.add_argument('--portfolio-cpus', type=int, default=4, help='cpus per portfolio run (4)')
    command.add_argument('--filter', help='only the benchmarks whose path matches this regex')
    command.add_argument('--list', default=LIST, help='the list of benchmarks (kind2-benchmarks.txt)')
    command.add_argument('--kind2', default=os.environ.get('KIND2', 'kind2'), help='the Kind2 executable ($KIND2)')
    command.add_argument('--z3', default=os.environ.get('KIND2_Z3', 'z3'),
                         help='the z3 executable for Kind2 ($KIND2_Z3)')
    command.set_defaults(function=run)
    command = commands.add_parser('report', help='reports on one run')
    command.add_argument('results', nargs='+', help='one run, or several, whose results are merged; '
                         'a later file wins for a file x tool pair that both have')
    command.add_argument('--expected', help='verdicts to check against, as kind2-benchmarks.txt')
    command.set_defaults(function=report)
    command = commands.add_parser('compare', help='compares two runs, tool by tool')
    command.add_argument('first')
    command.add_argument('second')
    command.set_defaults(function=compare)
    command = commands.add_parser('plot', help='writes the scatter and cactus plots of a run')
    command.add_argument('results', nargs='+', help='one run, or several merged (as report)')
    command.add_argument('--pair', default='portfolio,kind2',
                         help='the two tools of the scatter plot (portfolio,kind2)')
    command.add_argument('--tools', help='comma separated tools for the cactus plot (default: all present)')
    command.add_argument('--out-dir', default='.', help='where to write scatter.png and cactus.png (.)')
    command.set_defaults(function=plot)
    command = commands.add_parser('worker')
    command.add_argument('tool', choices=INTREPYD_TOOLS)
    command.add_argument('encoding')
    command.add_argument('--timeout', type=float)
    command.set_defaults(function=worker)
    arguments = parser.parse_args()
    return arguments.function(arguments)


if __name__ == '__main__':
    sys.exit(main())
