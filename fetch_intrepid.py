#!/usr/bin/env python3
"""
Puts the intrepid shared library where intrepyd/api.py loads it from.

intrepid is built and released from its own repository. This script takes one
of its release packages and copies, into intrepyd/,

    libintrepid.so / intrepid.dll   the library
    LICENSE.intrepid                its license

and keeps the header in .intrepid/Intrepid.h, where intrepyd/tests/test_api.py
checks the binding against it.

Usage:

    fetch_intrepid.py                     # the release named in INTREPID_VERSION
    fetch_intrepid.py --platform windows-x86_64
    fetch_intrepid.py --from ../intrepid  # a local checkout, after 'make build'
    fetch_intrepid.py --from intrepid-1.0.0-linux-x86_64.tar.gz
    fetch_intrepid.py --pin linux-x86_64 windows-x86_64

A release package is used only if its SHA-256 is the one pinned in
INTREPID_SHA256 (as sha256sum writes it: '<digest>  <package>'), downloaded or
found in the cache, so that the wheels carry the library intrepid released and
nothing else. --pin writes that file from the digests GitHub gives of the
release's packages, for an immutable release only (its packages can no longer
be replaced); it is committed with INTREPID_VERSION. --from is not checked:
it is for development, never what a release uses.

Downloading needs read access to the intrepid repository, which is private:
the token is taken from GITHUB_TOKEN, or else from 'gh auth token'.
"""

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.error
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPOSITORY = 'formalmethods/intrepid'
PIN_FILE = os.path.join(HERE, 'INTREPID_SHA256')
LIBRARY_NAMES = {
    'linux': 'libintrepid.so',
    'windows': 'intrepid.dll',
}


def current_platform():
    system = platform.system().lower()
    machine = platform.machine().lower()
    machine = {'amd64': 'x86_64', 'aarch64': 'arm64'}.get(machine, machine)
    return '%s-%s' % (system, machine)


def github_token():
    token = os.environ.get('GITHUB_TOKEN')
    if token:
        return token
    try:
        return subprocess.check_output(['gh', 'auth', 'token'], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        sys.exit('Error: set GITHUB_TOKEN, or log in with "gh auth login", to download '
                 'from %s' % REPOSITORY)


def github_get(url, token, accept):
    request = urllib.request.Request(url, headers={
        'Authorization': 'Bearer ' + token,
        'Accept': accept,
        'X-GitHub-Api-Version': '2022-11-28',
    })
    with urllib.request.urlopen(request) as response:
        return response.read()


def asset_name(version, plat):
    extension = '.zip' if plat.startswith('windows') else '.tar.gz'
    return 'intrepid-%s-%s%s' % (version, plat, extension)


def release_json(version, token):
    """The release v<version> of intrepid, or exit with a clear error."""
    release_url = 'https://api.github.com/repos/%s/releases/tags/v%s' % (REPOSITORY, version)
    try:
        return json.loads(github_get(release_url, token, 'application/vnd.github+json'))
    except urllib.error.HTTPError as error:
        if error.code == 404:
            sys.exit('Error: %s has no release v%s' % (REPOSITORY, version))
        raise


def read_pins(pin_file=None):
    """{package: sha256} of INTREPID_SHA256 ({} if there is none)"""
    pin_file = pin_file or PIN_FILE
    pins = {}
    if not os.path.isfile(pin_file):
        return pins
    with open(pin_file, encoding='ascii') as pins_file:
        for number, line in enumerate(pins_file, 1):
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) != 2 or len(parts[0]) != 64 or \
                    any(c not in '0123456789abcdef' for c in parts[0]):
                sys.exit('Error: %s:%d is not "<sha256>  <package>"' % (pin_file, number))
            pins[parts[1].lstrip('*')] = parts[0]
    return pins


def write_pins(pins, pin_file=None):
    with open(pin_file or PIN_FILE, 'w', encoding='ascii') as pins_file:
        for name in sorted(pins):
            pins_file.write('%s  %s\n' % (pins[name], name))


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as data:
        for block in iter(lambda: data.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def pinned(name, pins):
    """The digest pinned for package <name>, or exit saying how to pin it"""
    if name not in pins:
        sys.exit('Error: %s has no digest pinned in %s: pin the release with '
                 '"make pin_intrepid" (and commit it)' % (name, os.path.basename(PIN_FILE)))
    return pins[name]


def check_pinned(path, name, pins, hint=''):
    """Exit unless the package at <path> is the one pinned for <name>"""
    expected = pinned(name, pins)
    actual = sha256_of(path)
    if actual != expected:
        sys.exit('Error: %s is not the package pinned in %s: its SHA-256 is %s, the pinned one %s%s'
                 % (path, os.path.basename(PIN_FILE), actual, expected, hint))


def release_asset(release, version, plat):
    """The asset of <plat>'s package in <release>, or exit saying what it has"""
    name = asset_name(version, plat)
    assets = [asset for asset in release.get('assets', []) if asset['name'] == name]
    if not assets:
        sys.exit('Error: release v%s of %s has no %s; it has: %s'
                 % (version, REPOSITORY, name,
                    ', '.join(asset['name'] for asset in release.get('assets', []))
                    or 'no assets'))
    return assets[0]


def published_digest(asset):
    """The SHA-256 GitHub gives of a release asset, or None if it gives none"""
    digest = asset.get('digest') or ''
    return digest[len('sha256:'):] if digest.startswith('sha256:') else None


def require_immutable(release, version):
    if not release.get('immutable'):
        sys.exit('Error: release v%s of %s is not immutable: its packages could still be '
                 'replaced (turn on immutable releases in its settings, and release again)'
                 % (version, REPOSITORY))


def check_available(version, plat, pins):
    """Exit non-zero unless intrepid v<version> is published, immutable, with
    the package for <plat>, whose digest is the pinned one. Checks the
    metadata only, nothing is downloaded."""
    token = github_token()
    release = release_json(version, token)
    asset = release_asset(release, version, plat)
    require_immutable(release, version)
    expected = pinned(asset['name'], pins)
    if published_digest(asset) != expected:
        sys.exit('Error: %s of %s v%s has SHA-256 %s, not the pinned %s'
                 % (asset['name'], REPOSITORY, version, published_digest(asset), expected))
    print('# %s is available in %s v%s, as pinned' % (asset['name'], REPOSITORY, version))


def pin(version, platforms):
    """Writes the digests of the packages of <platforms> of intrepid
    v<version> into INTREPID_SHA256, in place of the ones it had"""
    token = github_token()
    release = release_json(version, token)
    require_immutable(release, version)
    pins = {}
    for plat in platforms:
        asset = release_asset(release, version, plat)
        digest = published_digest(asset)
        if digest is None:
            sys.exit('Error: GitHub gives no digest of %s' % asset['name'])
        pins[asset['name']] = digest
        print('# %s  %s' % (digest, asset['name']))
    write_pins(pins)
    print('# Pinned in %s: commit it with INTREPID_VERSION' % os.path.basename(PIN_FILE))


def download(version, plat, cache_dir, pins):
    """Downloads the release package, or takes it from the cache, and returns
    the path of the archive: in both cases, the pinned one"""
    name = asset_name(version, plat)
    path = os.path.join(cache_dir, name)
    if os.path.isfile(path):
        print('# Using cached %s' % path)
        check_pinned(path, name, pins, hint='\n(delete the cached package to download it again)')
        return path
    expected = pinned(name, pins)
    token = github_token()
    print('# Downloading %s from %s v%s' % (name, REPOSITORY, version))
    release = release_json(version, token)
    asset = release_asset(release, version, plat)
    published = published_digest(asset)
    if published is not None and published != expected:
        sys.exit('Error: %s of %s v%s has SHA-256 %s, not the pinned %s'
                 % (name, REPOSITORY, version, published, expected))
    data = github_get(asset['url'], token, 'application/octet-stream')
    os.makedirs(cache_dir, exist_ok=True)
    with open(path + '.part', 'wb') as part:
        part.write(data)
    try:
        check_pinned(path + '.part', name, pins)
    except SystemExit:
        os.remove(path + '.part')
        raise
    os.replace(path + '.part', path)
    return path


def extract(archive, cache_dir):
    """Extracts a package, returns the directory it contains"""
    if archive.endswith('.zip'):
        with zipfile.ZipFile(archive) as package:
            top = package.namelist()[0].split('/')[0]
            package.extractall(cache_dir)
    else:
        with tarfile.open(archive) as package:
            top = package.getnames()[0].split('/')[0]
            try:
                package.extractall(cache_dir, filter='data')
            except TypeError:   # python older than 3.11.4
                package.extractall(cache_dir)
    return os.path.join(cache_dir, top)


def locate(source, plat):
    """Returns (library, header, license) inside a package or a checkout"""
    system = plat.split('-')[0]
    library_name = LIBRARY_NAMES[system]
    if os.path.isfile(os.path.join(source, 'src', 'api', 'Intrepid.h')):
        # A source checkout of intrepid, built with 'make build'
        candidates = [os.path.join(source, 'build', library_name),
                      os.path.join(source, 'build', 'bin', library_name)]
        header = os.path.join(source, 'src', 'api', 'Intrepid.h')
        license_file = os.path.join(source, 'LICENSE')
    else:
        # An installed tree, or an extracted release package
        candidates = [os.path.join(source, 'lib', library_name),
                      os.path.join(source, 'bin', library_name)]
        header = os.path.join(source, 'include', 'intrepid', 'Intrepid.h')
        license_file = os.path.join(source, 'share', 'intrepid', 'LICENSE')
    libraries = [path for path in candidates if os.path.exists(path)]
    for path in [libraries[0] if libraries else None, header, license_file]:
        if path is None or not os.path.isfile(path):
            sys.exit('Error: cannot find %s in %s' % (path or library_name, source))
    return libraries[0], header, license_file


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[1],
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--from', dest='source',
                        help='a release package, an extracted one, or an intrepid checkout')
    parser.add_argument('--platform', default=current_platform(),
                        help='the platform to download for (default: %(default)s)')
    parser.add_argument('--version', help='the release to download (default: INTREPID_VERSION)')
    parser.add_argument('--check', action='store_true',
                        help='only check that the release and its package for the '
                             'platform are published, immutable and pinned, without '
                             'downloading anything')
    parser.add_argument('--pin', nargs='+', metavar='PLATFORM',
                        help='write the digests of these platforms\' packages into '
                             'INTREPID_SHA256, and nothing else')
    args = parser.parse_args()

    if args.platform.split('-')[0] not in LIBRARY_NAMES:
        sys.exit('Error: unsupported platform %s' % args.platform)
    cache_dir = os.path.join(HERE, '.intrepid')

    def resolve_version():
        if args.version:
            return args.version
        with open(os.path.join(HERE, 'INTREPID_VERSION')) as version_file:
            return version_file.read().strip()

    if args.pin:
        pin(resolve_version(), args.pin)
        return

    if args.check:
        check_available(resolve_version(), args.platform, read_pins())
        return

    if args.source is None:
        source = extract(download(resolve_version(), args.platform, cache_dir, read_pins()),
                         cache_dir)
    elif os.path.isfile(args.source):
        source = extract(args.source, cache_dir)
    else:
        source = args.source

    library, header, license_file = locate(source, args.platform)
    package_dir = os.path.join(HERE, 'intrepyd')
    # Libraries for the other platforms would otherwise end up in the wheel
    for name in LIBRARY_NAMES.values():
        stale = os.path.join(package_dir, name)
        if os.path.lexists(stale):
            os.remove(stale)
    # copyfile follows symlinks: libintrepid.so -> .so.1 -> .so.1.0.0 becomes
    # one file, as wheels cannot hold symlinks
    destination = os.path.join(package_dir, os.path.basename(library))
    shutil.copyfile(library, destination)
    shutil.copymode(library, destination)
    shutil.copyfile(license_file, os.path.join(package_dir, 'LICENSE.intrepid'))
    os.makedirs(cache_dir, exist_ok=True)
    shutil.copyfile(header, os.path.join(cache_dir, 'Intrepid.h'))
    with open(os.path.join(cache_dir, 'PLATFORM'), 'w') as platform_file:
        platform_file.write(args.platform + '\n')
    print('# Installed %s from %s' % (os.path.relpath(destination, HERE), source))


if __name__ == '__main__':
    main()
