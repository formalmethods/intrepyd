#!/usr/bin/env python3
"""
Checks an installed intrepyd wheel, for the release workflow: that it has the
version of VERSION, holds its license files and nothing but the intrepyd
package, and that its intrepid library loads and works, with every engine.

Run it as a script, after installing the wheel:

    python tools/check_wheel.py

'import intrepyd' then finds the installed package, since python puts tools/,
not the current directory, first on the path; it fails if it finds the
sources instead.
"""

import os
import sys
from importlib import metadata

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def check_installation():
    import intrepyd
    location = os.path.dirname(os.path.abspath(intrepyd.__file__))
    if os.path.commonpath([location, HERE]) == HERE:
        sys.exit('Error: intrepyd is imported from the sources, %s, not from '
                 'the installed wheel' % location)
    with open(os.path.join(HERE, 'VERSION'), encoding='utf-8') as version_file:
        expected = version_file.read().strip()
    installed = metadata.version('intrepyd')
    if installed != expected:
        sys.exit('Error: the installed intrepyd is %s, VERSION is %s' % (installed, expected))
    distribution = metadata.distribution('intrepyd')
    files = [str(path) for path in distribution.files]
    top_level = {path.split('/')[0] for path in files if '.dist-info' not in path}
    if top_level != {'intrepyd'}:
        sys.exit('Error: the wheel installs more than intrepyd: %s' % sorted(top_level))
    for name in ['LICENSE.md', 'CREDITS.md', 'LICENSE.intrepid']:
        # PEP 639 keeps the path of each license file under licenses/
        if not any('.dist-info/licenses/' in path and path.endswith('/' + name)
                   for path in files):
            sys.exit('Error: the wheel has no license file %s' % name)
    if any('/tests/' in path for path in files):
        sys.exit('Error: the wheel contains the tests')
    print('# intrepyd %s installed in %s' % (installed, location))


def check_engines():
    import intrepyd as ip
    from intrepyd.engine import EngineResult

    def counter(ctx, limit):
        # c counts 0, 1, 2, ... up to limit, then stays there
        int_t = ctx.mk_int8_type()
        c = ctx.mk_latch('c', int_t)
        top = ctx.mk_number(str(limit), int_t)
        ctx.set_latch_init_next(
            c, ctx.mk_number('0', int_t),
            ctx.mk_ite(ctx.mk_lt(c, top), ctx.mk_add(c, ctx.mk_number('1', int_t)), c))
        return c, int_t

    ctx = ip.Context()
    c, int_t = counter(ctx, 5)
    reachable = ctx.mk_eq(c, ctx.mk_number('5', int_t))
    unreachable = ctx.mk_gt(c, ctx.mk_number('5', int_t))

    bmc = ctx.mk_bmc()
    bmc.add_target(reachable)
    bmc.set_current_depth(5)
    assert bmc.reach_targets() == EngineResult.REACHABLE, 'bmc'

    for name, make in [('backward reachability', ctx.mk_backward_reach),
                       ('pdr', ctx.mk_pdr)]:
        engine = make()
        engine.add_target(unreachable)
        assert engine.reach_targets() == EngineResult.UNREACHABLE, name
        engine = make()
        engine.add_target(reachable)
        assert engine.reach_targets() == EngineResult.REACHABLE, name

    kind = ctx.mk_bmc()
    kind.set_use_induction()
    kind.add_target(unreachable)
    result = EngineResult.UNKNOWN
    for depth in range(10):
        kind.set_current_depth(depth)
        result = kind.reach_targets()
        if result != EngineResult.UNKNOWN:
            break
    assert result == EngineResult.UNREACHABLE, 'k-induction'
    print('# The intrepid library works')


def main():
    check_installation()
    check_engines()


if __name__ == '__main__':
    main()
