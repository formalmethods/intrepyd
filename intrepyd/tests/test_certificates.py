"""
Tests for proof certificates: an engine that proves a target unreachable gives
an SMT-LIB 2 script whose every check-sat must answer unsat. When an SMT solver
is installed (the z3 or cvc5 command, or the cvc5 python module), it checks
them independently of the library, and a tampered certificate is refused.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import intrepyd as ip
from intrepyd import api, diagram
from intrepyd.engine import EngineResult

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir)

_CVC5_RUNNER = """
import sys
import cvc5
tm = cvc5.TermManager()
solver = cvc5.Solver(tm)
solver.setOption("incremental", "true")
symbols = cvc5.SymbolManager(tm)
parser = cvc5.InputParser(solver, symbols)
parser.setFileInput(cvc5.InputLanguage.SMT_LIB_2_6, sys.argv[1])
while True:
    command = parser.nextCommand()
    if command.isNull():
        break
    out = command.invoke(solver, symbols)
    if out.strip():
        print(out.strip())
"""


def _solvers():
    """The SMT solvers of the machine, as commands that run a script file"""
    found = {}
    for name in ('z3', 'cvc5'):
        path = shutil.which(name)
        if path:
            found[name] = [path]
    if 'cvc5' not in found:
        try:
            import cvc5  # pylint: disable=import-outside-toplevel,unused-import
            found['cvc5 (python)'] = [sys.executable, '-c', _CVC5_RUNNER]
        except ImportError:
            pass
    return found


def _answers(command, script):
    """What a solver answers to a script, one word per check-sat"""
    with tempfile.NamedTemporaryFile('w', suffix='.smt2', delete=False) as handle:
        handle.write(script)
        path = handle.name
    try:
        run = subprocess.run([*command, path], capture_output=True, text=True, check=False,
                             timeout=120)
        return run.stdout.split()
    finally:
        os.unlink(path)


def _swap(ctx):
    """Two int8 latches that swap, from 0; the target that they differ"""
    int8 = ctx.mk_int8_type()
    x = ctx.mk_latch('x', int8)
    y = ctx.mk_latch('y', int8)
    zero = ctx.mk_number('0', int8)
    ctx.set_latch_init_next(x, zero, y)
    ctx.set_latch_init_next(y, zero, x)
    return ctx.mk_not(ctx.mk_eq(x, y))


def _counter(ctx):
    """c counts 0..3 then 0 again, or jumps 5 -> 7 on an input that never
    gets there: c = 7 is unreachable, which k-induction proves at depth 2
    with its simple paths"""
    int8 = ctx.mk_int8_type()
    go = ctx.mk_input('go', ctx.mk_boolean_type())
    c = ctx.mk_latch('c', int8)
    n = lambda v: ctx.mk_number(v, int8)  # pylint: disable=unnecessary-lambda-assignment
    nxt = ctx.mk_ite(ctx.mk_eq(c, n('5')), ctx.mk_ite(go, n('7'), n('5')),
                     ctx.mk_ite(ctx.mk_eq(c, n('3')), n('0'),
                                ctx.mk_ite(ctx.mk_lt(c, n('3')), ctx.mk_add(c, n('1')), c)))
    ctx.set_latch_init_next(c, n('0'), nxt)
    return ctx.mk_eq(c, n('7'))


def _prove(engine, target):
    engine.add_target(target)
    engine.set_produce_certificates()
    if isinstance(engine, ip.engine.Bmc):
        engine.set_use_induction()
        for depth in range(20):
            engine.set_current_depth(depth)
            if engine.reach_targets() != EngineResult.UNKNOWN:
                break
    else:
        engine.reach_targets()
    return engine


@unittest.skipUnless(api.HAS_CERTIFICATES, 'the intrepid library has no proof certificates (1.4+)')
class CertificateTest(unittest.TestCase):

    def assert_checked(self, script, conditions):
        self.assertEqual(script.count('(check-sat)'), conditions)
        for name, command in _solvers().items():
            with self.subTest(solver=name):
                self.assertEqual(_answers(command, script), ['unsat'] * conditions)

    def test_each_engine_gives_a_certificate_other_solvers_accept(self):
        for make in ('mk_pdr', 'mk_backward_reach', 'mk_bmc'):
            with self.subTest(engine=make):
                ctx = ip.Context()
                target = _counter(ctx)
                engine = _prove(getattr(ctx, make)(), target)
                self.assertEqual(engine.last_result, EngineResult.UNREACHABLE)
                script = engine.get_last_certificate()
                self.assertIsNotNone(script)
                self.assertIn('(set-logic QF_BV)', script)
                kind = make == 'mk_bmc'
                self.assertIn('k-induction' if kind else 'inductive invariant', script)
                self.assert_checked(script, 4 if kind else 3)

    def test_a_tampered_certificate_is_refused_by_the_other_solvers(self):
        ctx = ip.Context()
        engine = _prove(ctx.mk_pdr(), _swap(ctx))
        script = engine.get_last_certificate()
        # the invariant becomes true: it holds initially and is kept, but it
        # no longer excludes the target
        head, rest = script.split('(define-fun Inv ', 1)
        params, body = rest.split(') Bool\n', 1)
        body = body.split('\n\n', 1)[1]
        tampered = f'{head}(define-fun Inv {params}) Bool\n  true)\n\n{body}'
        for name, command in _solvers().items():
            with self.subTest(solver=name):
                self.assertEqual(_answers(command, tampered), ['unsat', 'unsat', 'sat'])

    def test_none_without_asking_nor_for_a_reachable_target(self):
        ctx = ip.Context()
        target = _swap(ctx)
        pdr = ctx.mk_pdr()
        pdr.add_target(target)
        self.assertEqual(pdr.reach_targets(), EngineResult.UNREACHABLE)
        self.assertIsNone(pdr.get_last_certificate())
        ctx = ip.Context()
        reachable = ctx.mk_not(_swap(ctx))
        pdr = _prove(ctx.mk_pdr(), reachable)
        self.assertEqual(pdr.last_result, EngineResult.REACHABLE)
        self.assertIsNone(pdr.get_last_certificate())

    def test_the_portfolio_gives_the_certificate_of_the_engine_that_proved(self):
        ctx = ip.Context()
        target = _counter(ctx)
        portfolio = ctx.mk_portfolio(engines=['kind', 'br', 'pdr'], certificates=True)
        portfolio.add_target(target)
        self.assertEqual(portfolio.reach_targets(timeout=60), EngineResult.UNREACHABLE)
        script = portfolio.get_last_certificate()
        self.assertIn(f'Engine: {portfolio.get_last_engine()}.', script)
        self.assert_checked(script, script.count('(check-sat)'))
        # and none unless asked for
        plain = ctx.mk_portfolio(engines=['pdr'])
        plain.add_target(target)
        self.assertEqual(plain.reach_targets(timeout=60), EngineResult.UNREACHABLE)
        self.assertIsNone(plain.get_last_certificate())

    def test_a_diagram_property_that_holds_comes_with_its_certificate(self):
        doc = {"format": diagram.FORMAT, "version": diagram.VERSION, "layout": {"blocks": {}},
               "circuit": {"nodes": [
                   {"id": 1, "kind": "latch", "name": "stuck", "type": "bool"},
                   {"id": 2, "kind": "const", "name": None, "op": "false", "value": "false"},
                   {"id": 3, "kind": "gate", "name": None, "op": "not"},
                   {"id": 4, "kind": "assertion", "name": "never"}],
                   "edges": [{"from": 2, "to": 1, "port": "init"},
                             {"from": 1, "to": 1, "port": "next"},
                             {"from": 1, "to": 3, "port": "in"},
                             {"from": 3, "to": 4, "port": "in"}]}}
        [result] = diagram.verify(doc, engine="pdr", timeout=30, certificates=True)["results"]
        self.assertEqual(result["verdict"], "holds")
        self.assert_checked(result["certificate"], 3)
        [plain] = diagram.verify(doc, engine="pdr", timeout=30)["results"]
        self.assertNotIn("certificate", plain)
        run = subprocess.run([sys.executable, "-m", "intrepyd.diagram", "verify", "-",
                              "--engine", "br", "--certificates"], input=json.dumps(doc),
                             capture_output=True, text=True, cwd=ROOT, check=False)
        self.assertEqual(run.returncode, 0, run.stderr)
        [cli] = json.loads(run.stdout)["results"]
        self.assertIn("Engine: br.", cli["certificate"])


if __name__ == "__main__":
    unittest.main()
