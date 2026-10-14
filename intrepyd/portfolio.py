"""
This module implements the portfolio: an engine that runs several engines in
parallel on the same targets, and stops them all as soon as one of them gives
a conclusive answer, a counterexample or a proof.

The engines are complementary: BMC finds counterexamples fastest, while
k-induction, backward reachability and PDR each prove properties that the
others cannot. The portfolio answers as soon as the best of them does.

Each engine runs in a process of its own, with a context of its own: intrepid
contexts cannot be shared between threads, and a process can be stopped at
any moment. The process builds the circuit again from the recipe of the
context (see intrepyd.recipe), runs its engine, and sends back its answer.
The counterexample of a REACHABLE answer is rebuilt in the caller's context,
by BMC at the depth the engine found, when get_last_trace() first asks for it.
With certificates=True, an UNREACHABLE answer comes with the proof certificate
of the engine that gave it (get_last_certificate(), see
Engine.set_produce_certificates); an engine whose certificate does not hold
answers UNKNOWN, and the others go on.

The processes are started with multiprocessing (forkserver on Linux, spawn on
Windows), which imports the main module of the program in each of them: as
for any use of multiprocessing, a script that uses a portfolio must keep its
top level code under 'if __name__ == "__main__":'.

Example:

    portfolio = ctx.mk_portfolio()
    portfolio.add_target(bad)
    result = portfolio.reach_targets(timeout=60)
    print(result, portfolio.get_last_engine(), portfolio.get_last_time())
"""

from __future__ import annotations

from collections.abc import Iterable
import multiprocessing
import sys
import threading
import time
import os
from multiprocessing import connection
from typing import TYPE_CHECKING, cast
from intrepyd.api import Net
from intrepyd.engine import Bmc, Engine, EngineResult
from intrepyd.recipe import replay

if TYPE_CHECKING:
    from intrepyd.context import Context
    from intrepyd.trace import Trace

# The engines a portfolio can run:
#   bmc     bounded model checking, at depth 0, 1, 2, ...: counterexamples
#   kind    k-induction (BMC with induction): counterexamples and proofs
#   br      backward reachability: counterexamples and proofs
#   pdr     IC3/PDR: counterexamples and proofs
ENGINES = ('bmc', 'kind', 'br', 'pdr')


class Portfolio(Engine):  # pylint: disable=abstract-method,too-many-instance-attributes
    """
    Runs several engines in parallel, and answers with the first conclusive
    answer of any of them

    The _*_impl methods of Engine wrap the C API of one engine: a portfolio
    has none, and implements the public methods instead.
    """

    def __init__(self, context: Context, engines: Iterable[str] = ENGINES,
                 max_depth: int | None = None, certificates: bool = False) -> None:
        """
        Args:
            context (Context): the context of the circuit
            engines (iterable): which of ENGINES to run, all by default
            max_depth (int=None): the deepest depth that bmc and kind try;
                None for no limit
            certificates (bool=False): whether an UNREACHABLE answer comes
                with a proof certificate (get_last_certificate)
        """
        Engine.__init__(self, context.ctx)
        engines = tuple(engines)
        unknown = [name for name in engines if name not in ENGINES]
        if unknown or not engines:
            raise ValueError('Unknown engines %s: a portfolio runs some of %s'
                             % (', '.join(unknown) or '(none)', ', '.join(ENGINES)))
        self.context = context
        self.engines = engines
        self.max_depth = max_depth
        self.certificates = certificates
        self.targets: list[Net] = []
        self.watches: list[Net] = []
        self._last_engine: str | None = None
        self._last_time: float | None = None
        self._last_errors: dict[str, str] = {}
        self._last_reached: tuple[Net, ...] = ()
        self._last_depth: int | None = None
        self._last_trace: Trace | None = None
        self._last_certificate: str | None = None

    def add_target(self, net: Net) -> None:
        self.context.recipe.ref(net)    # raises if it cannot be rebuilt
        self.targets.append(net)

    def add_watch(self, net: Net) -> None:
        self.watches.append(net)

    def reach_targets(self, timeout: float | None = None) -> EngineResult:
        """
        Runs the engines until one of them answers REACHABLE or UNREACHABLE,
        and returns that answer; returns UNKNOWN if none of them does, or
        none does within timeout seconds
        """
        if not self.targets:
            raise ValueError('The portfolio has no targets')
        recipe = self.context.recipe
        recipe.check()
        targets = [recipe.ref(target) for target in self.targets]
        self._last_engine = None
        self._last_errors = {}
        self._last_reached = ()
        self._last_depth = None
        self._last_trace = None
        self._last_certificate = None
        start = time.monotonic()
        # The class of the context goes to the processes, which make their
        # own context of the same class
        winner = _run(self.engines, (type(self.context), recipe.calls), targets,
                      (self.max_depth, self.certificates), timeout, self._last_errors)
        self._last_time = time.monotonic() - start
        self.last_result = EngineResult.UNKNOWN
        if winner is not None:
            engine, result, reached, depth, certificate = winner
            self._last_engine = engine
            self.last_result = result
            self._last_certificate = certificate
            self._last_reached = tuple(self.targets[index] for index in reached)
            self._last_depth = depth
        return self.last_result

    def get_last_engine(self) -> str | None:
        """
        Returns the name of the engine that gave the last answer, or None if
        the last answer was UNKNOWN
        """
        return self._last_engine

    def get_last_time(self) -> float | None:
        """
        Returns how long the last reach_targets() took, in seconds
        """
        return self._last_time

    def get_last_errors(self) -> dict[str, str]:
        """
        Returns the errors of the engines that failed in the last
        reach_targets(), as a dictionary engine -> message
        """
        return dict(self._last_errors)

    def get_last_reached_targets(self) -> tuple[Net, ...]:
        if self.last_result != EngineResult.REACHABLE:
            return ()
        return self._last_reached

    def get_last_certificate(self) -> str | None:
        if self.last_result != EngineResult.UNREACHABLE:
            return None
        return self._last_certificate

    def get_last_trace(self) -> Trace:
        if self.last_result != EngineResult.REACHABLE:
            raise Exception('Cannot get a trace as last result was not REACHABLE')
        if self._last_trace is None:
            bmc = self.context.mk_bmc()
            for target in self._last_reached:
                bmc.add_target(target)
            for net in self.watches:
                bmc.add_watch(net)
            depth = cast(int, self._last_depth)  # a REACHABLE answer carries a depth
            bmc.set_current_depth(depth)
            if bmc.reach_targets() != EngineResult.REACHABLE:
                raise RuntimeError('Cannot rebuild the counterexample that %s found at depth %d'
                                   % (self._last_engine, depth))
            self._last_trace = bmc.get_last_trace()
        return self._last_trace

    def remove_last_reached_targets(self) -> None:
        for target in self.get_last_reached_targets():
            self.targets.remove(target)

    def can_reach(self) -> bool:
        return True

    def can_prove(self) -> bool:
        return any(name != 'bmc' for name in self.engines)

    def can_optimize(self) -> bool:
        return False


def _multiprocessing_context():
    if sys.platform == 'win32':
        return multiprocessing.get_context('spawn')
    context = multiprocessing.get_context('forkserver')
    # The processes fork from a server that has already imported intrepyd
    context.set_forkserver_preload(['intrepyd.portfolio'])
    return context


def _run(engines, circuit, targets, how, timeout, errors):  # pylint: disable=too-many-locals
    """
    Runs each engine in a process, on circuit, (context class, recipe calls),
    how being (max depth, certificates); returns (engine, result, indices of
    the reached targets, depth, certificate) for the first conclusive answer,
    or None
    """
    context = _multiprocessing_context()
    deadline = None if timeout is None else time.monotonic() + timeout
    processes = []
    running = {}
    try:
        for engine in engines:
            receiver, sender = context.Pipe(duplex=False)
            process = context.Process(target=_work, name='intrepyd-portfolio-' + engine,
                                      args=(engine, circuit, targets, how, sender),
                                      daemon=True)
            process.start()
            sender.close()
            processes.append(process)
            running[receiver] = (engine, process)
        while running:
            remaining = None if deadline is None else deadline - time.monotonic()
            if remaining is not None and remaining <= 0:
                return None
            for ready in connection.wait(list(running), remaining):
                # wait() also accepts sockets and integer handles; this call
                # only passes the receiving ends of our pipes.
                receiver = cast(connection.Connection, ready)
                engine, process = running.pop(receiver)
                try:
                    message = receiver.recv()
                except EOFError:
                    process.join()
                    message = ('error', 'its process ended with exit code %s'
                               % process.exitcode)
                receiver.close()
                if message[0] == 'error':
                    errors[engine] = message[1]
                    continue
                _, result, reached, depth, certificate = message
                if result != EngineResult.UNKNOWN.name:
                    return engine, EngineResult[result], reached, depth, certificate
        return None
    finally:
        for receiver in running:
            receiver.close()
        for process in processes:
            if process.is_alive():
                process.terminate()
        for process in processes:
            process.join()


def _work(engine, circuit, targets, how, sender):
    """
    The process of one engine: builds the circuit, runs the engine, and
    sends ('done', result name, indices of the reached targets, depth,
    certificate), or ('error', message)
    """
    _exit_with_parent()
    # The engines run here, even if the process that started them imported a
    # script that called use_remote()
    from intrepyd.remote import use_local  # pylint: disable=import-outside-toplevel
    use_local()
    try:
        sender.send(_answer(engine, circuit, targets, how))
    except Exception as error:  # pylint: disable=broad-except
        sender.send(('error', '%s: %s' % (type(error).__name__, error)))
    finally:
        sender.close()


def _answer(engine, circuit, targets, how):
    """What _work sends for one engine, once it has run"""
    context_class, calls = circuit
    context = context_class()
    resolve = replay(calls, context)
    nets = [resolve(target) for target in targets]
    max_depth, certificates = how
    runner = _RUNNERS[engine](context, max_depth)
    if certificates and engine != 'bmc':
        runner.set_produce_certificates()
    result, reached, depth = _solve(runner, nets, max_depth)
    return ('done', result.name, [nets.index(net) for net in reached], depth,
            runner.get_last_certificate() if certificates else None)


def _exit_with_parent():
    """
    Ends this process when the one that started it ends, even if that one
    is killed and cannot stop it
    """
    parent = multiprocessing.parent_process()
    if parent is None:
        return

    def watch():
        connection.wait([parent.sentinel])
        os._exit(1)  # pylint: disable=protected-access

    threading.Thread(target=watch, daemon=True).start()


def _mk_bmc(context, induction):
    bmc = context.mk_bmc()
    if induction:
        bmc.set_use_induction()
    return bmc


def _solve(engine, targets, max_depth):
    """Runs an engine on the targets: (result, the targets reached, depth)"""
    for target in targets:
        engine.add_target(target)
    if isinstance(engine, Bmc):
        depth = 0
        while max_depth is None or depth <= max_depth:
            engine.set_current_depth(depth)
            result = engine.reach_targets()
            if result == EngineResult.REACHABLE:
                return result, list(engine.get_last_reached_targets()), depth
            if result == EngineResult.UNREACHABLE:
                return result, [], None
            depth += 1
        return EngineResult.UNKNOWN, [], None
    # The depth of a trace is the last at which it has a value: with no
    # input and no watch, the trace of a counterexample has none after
    # depth 0. The targets have one at every depth.
    for target in targets:
        engine.add_watch(target)
    result = engine.reach_targets()
    if result == EngineResult.REACHABLE:
        reached = list(engine.get_last_reached_targets())
        return result, reached, engine.get_last_trace().get_max_depth()
    return result, [], None


# The engine each name runs, made in a context
_RUNNERS = {
    'bmc': lambda context, _: _mk_bmc(context, False),
    'kind': lambda context, _: _mk_bmc(context, True),
    'br': lambda context, _: context.mk_backward_reach(),
    'pdr': lambda context, _: context.mk_pdr(),
}
