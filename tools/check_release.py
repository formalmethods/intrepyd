#!/usr/bin/env python3
"""
Checks that the version in VERSION can be released, for 'make release' and the
release workflow.

    check_release.py check [--tag TAG]   checks VERSION, INTREPID_VERSION and
                                         CHANGELOG.md, and that PyPI has no
                                         VERSION or later yet (and that TAG
                                         is v<VERSION>)
    check_release.py notes FILE          writes the CHANGELOG.md section of
                                         VERSION, the release notes, to FILE
    check_release.py published           succeeds if PyPI has VERSION, fails
                                         with status 1 if it has not, 2 if
                                         PyPI cannot be reached

PyPI never accepts a version twice, even after it is deleted: a version that
has been published, or has gone to PyPI with a failed release, is spent.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request

from packaging.version import InvalidVersion, Version

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYPI_URL = 'https://pypi.org/pypi/intrepyd/json'


def read(name):
    with open(os.path.join(HERE, name), encoding='utf-8') as file:
        return file.read()


def version():
    text = read('VERSION').strip()
    try:
        parsed = Version(text)
    except InvalidVersion:
        sys.exit('Error: VERSION is "%s", which is not a PEP 440 version' % text)
    if str(parsed) != text:
        sys.exit('Error: VERSION is "%s", write it as "%s"' % (text, parsed))
    return parsed


def cannot_read(error):
    # Status 2, so that 'published' tells it apart from "not published"
    print('Error: cannot read %s: %s' % (PYPI_URL, error), file=sys.stderr)
    sys.exit(2)


def published_versions():
    try:
        with urllib.request.urlopen(PYPI_URL, timeout=30) as response:
            releases = json.load(response)['releases']
    except urllib.error.HTTPError as error:
        if error.code == 404:   # not on PyPI at all
            return []
        cannot_read(error)
    except OSError as error:
        cannot_read(error)
    versions = []
    for text in releases:
        try:
            versions.append(Version(text))
        except InvalidVersion:
            pass
    return versions


def changelog_section(current):
    """The text under the '## <version>' heading of CHANGELOG.md"""
    lines = read('CHANGELOG.md').splitlines()
    heading = re.compile(r'^## +(\S+)')
    section = None
    for line in lines:
        match = heading.match(line)
        if match:
            if section is not None:
                break
            if match.group(1) == str(current):
                section = []
            continue
        if section is not None:
            section.append(line)
    if section is None:
        sys.exit('Error: CHANGELOG.md has no "## %s" section' % current)
    text = '\n'.join(section).strip()
    if not text:
        sys.exit('Error: the "## %s" section of CHANGELOG.md is empty' % current)
    return text + '\n'


def check(tag):
    current = version()
    if tag is not None and tag != 'v%s' % current:
        sys.exit('Error: the tag is %s, but VERSION is %s' % (tag, current))
    intrepid = read('INTREPID_VERSION').strip()
    if not re.fullmatch(r'\d+\.\d+\.\d+', intrepid):
        sys.exit('Error: INTREPID_VERSION is "%s", not a release of intrepid' % intrepid)
    changelog_section(current)
    published = published_versions()
    if current in published:
        sys.exit('Error: intrepyd %s is already on PyPI: bump VERSION' % current)
    later = [str(v) for v in published if v > current]
    if later:
        sys.exit('Error: PyPI already has later versions than %s: %s'
                 % (current, ', '.join(sorted(later, key=Version))))
    print('# intrepyd %s, on intrepid %s, can be released' % (current, intrepid))


def main():
    args = sys.argv[1:]
    if args[:1] == ['check'] and len(args) in (1, 3) and args[1:2] in ([], ['--tag']):
        check(args[2] if len(args) == 3 else None)
    elif args[:1] == ['notes'] and len(args) == 2:
        with open(args[1], 'w', encoding='utf-8') as notes:
            notes.write(changelog_section(version()))
    elif args == ['published']:
        sys.exit(0 if version() in published_versions() else 1)
    else:
        sys.exit(__doc__.strip().split('\n\n')[1])


if __name__ == '__main__':
    main()
