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

Downloading needs read access to the intrepid repository, which is private:
the token is taken from GITHUB_TOKEN, or else from 'gh auth token'.
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPOSITORY = 'formalmethods/intrepid'
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


def download(version, plat, cache_dir):
    """Downloads the release package, returns the path of the archive"""
    extension = '.zip' if plat.startswith('windows') else '.tar.gz'
    name = 'intrepid-%s-%s%s' % (version, plat, extension)
    path = os.path.join(cache_dir, name)
    if os.path.isfile(path):
        print('# Using cached %s' % path)
        return path
    token = github_token()
    release_url = 'https://api.github.com/repos/%s/releases/tags/v%s' % (REPOSITORY, version)
    print('# Downloading %s from %s v%s' % (name, REPOSITORY, version))
    release = json.loads(github_get(release_url, token, 'application/vnd.github+json'))
    assets = [asset for asset in release['assets'] if asset['name'] == name]
    if not assets:
        sys.exit('Error: release v%s of %s has no %s; it has: %s'
                 % (version, REPOSITORY, name,
                    ', '.join(asset['name'] for asset in release['assets'])))
    data = github_get(assets[0]['url'], token, 'application/octet-stream')
    os.makedirs(cache_dir, exist_ok=True)
    with open(path + '.part', 'wb') as part:
        part.write(data)
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
            except TypeError:   # python older than 3.9.17, 3.10.12 or 3.11.4
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
    args = parser.parse_args()

    if args.platform.split('-')[0] not in LIBRARY_NAMES:
        sys.exit('Error: unsupported platform %s' % args.platform)
    cache_dir = os.path.join(HERE, '.intrepid')

    if args.source is None:
        version = args.version
        if version is None:
            with open(os.path.join(HERE, 'INTREPID_VERSION')) as version_file:
                version = version_file.read().strip()
        source = extract(download(version, args.platform, cache_dir), cache_dir)
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
