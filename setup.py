"""
Setup script for Intrepyd

The metadata is in pyproject.toml. This only says what cannot be said there:
the intrepid backend is a prebuilt shared library, put next to
intrepyd/__init__.py by fetch_intrepid.py, which also records the platform it
is for in .intrepid/PLATFORM. Each wheel carries the library of one platform.
intrepyd/api.py loads it through ctypes, so the wheel does not depend on the
python version: its tag is py3-none-<platform>.
"""

import os
import sys
from setuptools import setup, Distribution
from setuptools.command.bdist_wheel import bdist_wheel

HERE = os.path.abspath(os.path.dirname(__file__))

LIBRARIES = ['libintrepid.so', 'intrepid.dll']
WHEEL_PLATFORMS = {
    'linux-x86_64': 'manylinux_2_28_x86_64',
    'windows-x86_64': 'win_amd64',
}


def fetched_platform():
    path = os.path.join(HERE, '.intrepid', 'PLATFORM')
    if not os.path.isfile(path):
        return None
    with open(path, encoding='utf-8') as platform_file:
        return platform_file.read().strip()


class BinaryDistribution(Distribution):
    """Has a native library, so the package goes in platlib, not purelib"""

    def has_ext_modules(self):
        return True


class PlatformWheel(bdist_wheel):
    """A wheel tagged for the platform of the bundled library"""

    def run(self):
        bundled = [name for name in LIBRARIES
                   if os.path.isfile(os.path.join(HERE, 'intrepyd', name))]
        if len(bundled) != 1 or fetched_platform() not in WHEEL_PLATFORMS:
            sys.exit('Error: run "make fetch_intrepid" first, to put the intrepid '
                     'library of exactly one platform into intrepyd/')
        super().run()

    def get_tag(self):
        platform = fetched_platform()
        if platform not in WHEEL_PLATFORMS:
            # An editable install, made before the library is fetched: it
            # uses whatever library intrepyd/ holds at run time
            return 'py3', 'none', 'any'
        return 'py3', 'none', WHEEL_PLATFORMS[platform]


setup(cmdclass={'bdist_wheel': PlatformWheel},
      distclass=BinaryDistribution,
      zip_safe=False)
