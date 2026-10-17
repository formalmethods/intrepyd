"""
fetch_intrepid.py uses a release package of intrepid only if its SHA-256 is
the one pinned in INTREPID_SHA256: downloaded or cached, and as GitHub gives
it. GitHub is stood in for here, with made-up packages and releases: nothing
is downloaded.
"""

import contextlib
import hashlib
import io
import importlib.util
import os
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SPEC = importlib.util.spec_from_file_location('fetch_intrepid',
                                               os.path.join(ROOT, 'fetch_intrepid.py'))
fetch = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(fetch)

PACKAGE = b'a made-up package'
NAME = 'intrepid-9.9.9-linux-x86_64.tar.gz'
DIGEST = hashlib.sha256(PACKAGE).hexdigest()
OTHER = hashlib.sha256(b'another package').hexdigest()


def _release(digest=DIGEST, immutable=True):
    return {'immutable': immutable,
            'assets': [{'name': NAME, 'url': 'https://example.invalid/asset',
                        'digest': 'sha256:' + digest}]}


class TestFetchIntrepid(unittest.TestCase):
    """The pinned digests of intrepid's release packages"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self.cache = os.path.join(self.tmp.name, 'cache')
        self.pin_file = os.path.join(self.tmp.name, 'INTREPID_SHA256')
        patches = [mock.patch.object(fetch, 'PIN_FILE', self.pin_file),
                   mock.patch.object(fetch, 'github_token', return_value='a made-up token'),
                   contextlib.redirect_stdout(io.StringIO())]
        for patch in patches[:2]:
            patch.start()
            self.addCleanup(patch.stop)
        # what the script prints, out of the tests' output
        self.enterContext(patches[2])

    def tearDown(self):
        self.tmp.cleanup()

    def _download(self, pins, release=None, data=PACKAGE):
        with mock.patch.object(fetch, 'release_json', return_value=release or _release()), \
                mock.patch.object(fetch, 'github_get', return_value=data) as get:
            path = fetch.download('9.9.9', 'linux-x86_64', self.cache, pins)
        return path, get

    def test_the_pins_file(self):
        """Written and read as sha256sum does; a line that is not a pin is said"""
        fetch.write_pins({NAME: DIGEST})
        with open(self.pin_file, encoding='ascii') as pins:
            self.assertEqual(pins.read(), f'{DIGEST}  {NAME}\n')
        self.assertEqual(fetch.read_pins(), {NAME: DIGEST})
        with open(self.pin_file, 'w', encoding='ascii') as pins:
            pins.write(f'not a digest  {NAME}\n')
        with self.assertRaisesRegex(SystemExit, 'INTREPID_SHA256:1 is not'):
            fetch.read_pins()
        os.remove(self.pin_file)
        self.assertEqual(fetch.read_pins(), {})

    def test_the_pinned_package_is_downloaded(self):
        """A package whose digest is the pinned one, here and on GitHub"""
        path, get = self._download({NAME: DIGEST})
        self.assertEqual(get.call_count, 1)
        with open(path, 'rb') as package:
            self.assertEqual(package.read(), PACKAGE)
        # then taken from the cache, checked again
        path, get = self._download({NAME: DIGEST})
        self.assertEqual(get.call_count, 0)

    def test_a_package_not_pinned_is_refused(self):
        """No pin: nothing downloaded, and how to pin it is said"""
        with self.assertRaisesRegex(SystemExit, 'no digest pinned.*make pin_intrepid'):
            self._download({})

    def test_another_digest_on_github_is_refused(self):
        """GitHub gives another digest: refused before downloading"""
        with self.assertRaisesRegex(SystemExit, f'SHA-256 {OTHER}, not the pinned {DIGEST}'):
            self._download({NAME: DIGEST}, release=_release(digest=OTHER))

    def test_another_package_downloaded_is_refused(self):
        """What arrives is not the pinned package: refused, and not kept"""
        with self.assertRaisesRegex(SystemExit, 'is not the package pinned'):
            self._download({NAME: DIGEST}, data=b'changed on the way')
        self.assertEqual(os.listdir(self.cache), [])

    def test_a_cached_package_changed_is_refused(self):
        """A package changed in the cache: refused, saying how to download it again"""
        self._download({NAME: DIGEST})
        with open(os.path.join(self.cache, NAME), 'ab') as package:
            package.write(b'!')
        with self.assertRaisesRegex(SystemExit, 'not the package pinned(.|\n)*delete the cached'):
            self._download({NAME: DIGEST})

    def test_pin_and_check(self):
        """Pinned from an immutable release only; checked against the published digest"""
        with mock.patch.object(fetch, 'release_json', return_value=_release(immutable=False)):
            with self.assertRaisesRegex(SystemExit, 'is not immutable'):
                fetch.pin('9.9.9', ['linux-x86_64'])
            with self.assertRaisesRegex(SystemExit, 'is not immutable'):
                fetch.check_available('9.9.9', 'linux-x86_64', {NAME: DIGEST})
        self.assertFalse(os.path.exists(self.pin_file))
        with mock.patch.object(fetch, 'release_json', return_value=_release()):
            fetch.pin('9.9.9', ['linux-x86_64'])
            self.assertEqual(fetch.read_pins(), {NAME: DIGEST})
            fetch.check_available('9.9.9', 'linux-x86_64', {NAME: DIGEST})
            with self.assertRaisesRegex(SystemExit, 'not the pinned'):
                fetch.check_available('9.9.9', 'linux-x86_64', {NAME: OTHER})
            with self.assertRaisesRegex(SystemExit, 'has no intrepid-9.9.9-windows'):
                fetch.pin('9.9.9', ['windows-x86_64'])


if __name__ == '__main__':
    unittest.main()
