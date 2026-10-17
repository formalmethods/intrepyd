"""
tools/check_wheel.py refuses a wheel whose noncommercial license would not
last a year from the release. The licenses here are made up (their fields as
license_info gives them).
"""

import datetime
import importlib.util
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SPEC = importlib.util.spec_from_file_location('check_wheel',
                                               os.path.join(ROOT, 'tools', 'check_wheel.py'))
check_wheel = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(check_wheel)

TODAY = datetime.date(2027, 9, 1)


def _info(**changes):
    info = {'valid': True, 'kind': 'noncommercial', 'id': 'PYPI-0.0.0', 'expires': '2028-09-01'}
    info.update(changes)
    return info


class TestCheckWheel(unittest.TestCase):
    """The license the wheels carry"""

    def test_a_year_left_will_do(self):
        """A year from the release, give or take a few days"""
        self.assertIsNone(check_wheel.wheel_license_problem(_info(), TODAY))
        self.assertIsNone(check_wheel.wheel_license_problem(_info(expires='2028-08-26'), TODAY))

    def test_a_license_left_from_an_earlier_release(self):
        """Valid today, but for a few weeks only: refused, saying what to renew"""
        problem = check_wheel.wheel_license_problem(_info(expires='2027-10-16'), TODAY)
        self.assertIn('expires on 2027-10-16, in 45 days', problem)
        self.assertIn('renew INTREPYD_WHEEL_LICENSE', problem)

    def test_not_a_valid_noncommercial_one(self):
        """Not valid, or of another kind"""
        self.assertIn('not a valid noncommercial',
                      check_wheel.wheel_license_problem(_info(valid=False), TODAY))
        self.assertIn('not a valid noncommercial',
                      check_wheel.wheel_license_problem(_info(kind='commercial'), TODAY))


if __name__ == '__main__':
    unittest.main()
