"""
The license intrepid's engines run under (intrepyd.license): what is said
without one, of one that is not a license, and that the processes intrepyd
starts get the one given. Needs an intrepid library that has licenses (1.7 or
newer) and, for the engines, a valid license in INTREPID_LICENSE; skipped
otherwise.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

from intrepyd import api
from intrepyd import license as lic

ENGINE = """
import intrepyd as ip
ctx = ip.Context()
a = ctx.mk_input('a', ctx.mk_boolean_type())
bmc = ctx.mk_bmc()
bmc.add_target(a)
print(bmc.reach_targets())
"""


def _run(script, env):
    return subprocess.run([sys.executable, '-c', script], env=env, capture_output=True, text=True,
                          check=False)


@unittest.skipUnless(api.HAS_LICENSE, 'this intrepid library has no licenses (older than 1.7)')
class TestLicense(unittest.TestCase):
    """The license, through intrepyd.license and the engines"""

    def test_no_license_no_engine(self):
        """Without a license an engine says so; circuits and the simulator need none"""
        with tempfile.TemporaryDirectory() as home:
            env = {k: v for k, v in os.environ.items() if k != 'INTREPID_LICENSE'}
            env.update(HOME=home, APPDATA=home)
            run = _run(ENGINE, env)
            if 'REACHABLE' in run.stdout:
                self.skipTest('a license next to the library (a wheel\'s): '
                              'engines run without one of the user')
            self.assertNotEqual(run.returncode, 0)
            self.assertIn('no license found', run.stderr)
            # building and simulating need none
            run = _run('import intrepyd as ip\nctx = ip.Context()\n'
                       'ctx.mk_input("a", ctx.mk_boolean_type())\n'
                       'ctx.mk_simulator()\nprint("ok")', env)
            self.assertEqual(run.stdout.strip(), 'ok', run.stderr)

    def test_the_portfolio_says_it_too(self):
        """Without a license the portfolio says why, rather than each engine failing"""
        script = ENGINE.replace('bmc = ctx.mk_bmc()', 'bmc = ctx.mk_portfolio()')
        with tempfile.TemporaryDirectory() as home:
            env = {k: v for k, v in os.environ.items() if k != 'INTREPID_LICENSE'}
            env.update(HOME=home, APPDATA=home)
            run = _run(script, env)
            if 'REACHABLE' in run.stdout:
                self.skipTest('a license next to the library (a wheel\'s)')
            self.assertIn('no license found', run.stderr)

    def test_a_text_that_is_not_a_license(self):
        """A text that is not a license is said so, and given to the processes"""
        script = ('import intrepyd.license as lic\n'
                  'try:\n    lic.set_license("not a license")\n'
                  'except RuntimeError as e:\n    print(e)\n'
                  'import os\nprint(os.environ["INTREPID_LICENSE"])\n'
                  'import json\nprint(json.dumps(lic.license_info()))')
        run = _run(script, dict(os.environ))
        lines = run.stdout.splitlines()
        self.assertEqual(lines[0], 'the license is not JSON', run.stderr)
        self.assertEqual(lines[1], 'not a license',
                         'put in INTREPID_LICENSE, for the processes started')
        info = json.loads(lines[2])
        self.assertEqual((info['valid'], info['error'], info['source']),
                         (False, 'the license is not JSON', 'set_license'))

    @unittest.skipUnless(os.environ.get('INTREPID_LICENSE'),
                         'set INTREPID_LICENSE to a valid license')
    def test_a_valid_license(self):
        """A valid license is told, but its signature, and the engines run"""
        info = lic.license_info()
        self.assertTrue(info['valid'], info)
        self.assertNotIn('signature', info)
        self.assertIn(info['key'], ('development', 'production', 'custom'))
        self.assertEqual(_run(ENGINE, dict(os.environ)).stdout.strip(), 'EngineResult.REACHABLE')

    @unittest.skipUnless(os.environ.get('INTREPID_LICENSE'),
                         'set INTREPID_LICENSE to a valid license')
    def test_one_not_valid_does_not_hide_a_valid_one(self):
        """The first valid license is used: those before it are passed over, and told"""
        given = os.environ['INTREPID_LICENSE']
        if given.lstrip().startswith('{'):
            text = given
        else:
            with open(given, encoding='utf-8') as f:
                text = f.read()
        with tempfile.TemporaryDirectory() as home:
            os.makedirs(os.path.join(home, '.intrepid'))
            os.makedirs(os.path.join(home, 'intrepid'))
            for folder in ('.intrepid', 'intrepid'):  # HOME's, and APPDATA's on Windows
                with open(os.path.join(home, folder, 'license.json'), 'w', encoding='utf-8') as f:
                    f.write(text)
            missing = os.path.join(home, 'none.json')
            env = dict(os.environ, INTREPID_LICENSE=missing, HOME=home, APPDATA=home)
            run = _run('import json, intrepyd.license as lic\n'
                       'print(json.dumps(lic.license_info()))\n' + ENGINE, env)
            lines = run.stdout.splitlines()
            info = json.loads(lines[0]) if lines else {}
            if not info.get('valid') and 'skipped' not in info and \
                    'cannot be read' in info.get('error', ''):
                self.skipTest('this intrepid uses the first license found, valid or not '
                              '(older than 1.7.1)')
            self.assertEqual(len(lines), 2, run.stderr)
            self.assertTrue(info['valid'], info)
            self.assertIn(info['source'], (os.path.join(home, '.intrepid', 'license.json'),
                                           os.path.join(home, 'intrepid', 'license.json')))
            self.assertEqual(info['skipped'][0]['source'], missing + ' (INTREPID_LICENSE)')
            self.assertIn('cannot be read', info['skipped'][0]['error'])
            self.assertEqual(lines[1], 'EngineResult.REACHABLE')


if __name__ == '__main__':
    unittest.main()
