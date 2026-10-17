"""
The license intrepid's engines run under.

The engines (BMC and k-induction, backward reachability, PDR) need a valid
license; building circuits, simulating them, exporting them do not. intrepid
looks for the license in this order:

1. the one given with :func:`set_license` or :func:`set_license_file`;
2. the ``INTREPID_LICENSE`` environment variable: the path of the license's
   file, or its JSON itself;
3. ``~/.intrepid/license.json`` (``%APPDATA%\\intrepid\\license.json`` on
   Windows);
4. ``license.json`` next to the intrepid library: the wheels of intrepyd on
   PyPI carry there a noncommercial license, valid for a year from the
   release, for the noncommercial use the license of intrepyd allows (see
   LICENSE.md). A commercial use needs a commercial license, given in one of
   the ways above.

One given with :func:`set_license` or :func:`set_license_file` is the one
used. Otherwise the first valid one is, and those before it are passed over
(``skipped`` in :func:`license_info`): a license for another build of
intrepid, or one expired, does not hide the wheel's.

Without a valid license, making an engine raises RuntimeError saying why: no
license found (and where it was looked for), a signature that is not valid, a
license that expired, or one that does not cover this release of intrepid.
"""

import json
import os
from typing import Any, Dict, Optional

from intrepyd import api

__all__ = ['set_license', 'set_license_file', 'license_info', 'require_license']


def _require():
    if not api.HAS_LICENSE:
        raise RuntimeError(f'this intrepid library ({api.LIBRARY_PATH}) has no licenses: '
                           'it needs none')


def set_license(text: str) -> None:
    """Run the engines under this license, given as its JSON text. It is also
    put in ``INTREPID_LICENSE``, so that the processes the portfolio starts
    run under it too. Raises RuntimeError if it is not valid."""
    _require()
    os.environ['INTREPID_LICENSE'] = text
    api.set_license(text)


def set_license_file(path: str) -> None:
    """As :func:`set_license`, with the license read from a file."""
    _require()
    path = os.path.abspath(path)
    os.environ['INTREPID_LICENSE'] = path
    api.set_license_file(path)


def require_license() -> None:
    """Raises RuntimeError, saying why, if the engines have no valid license
    (nothing for an intrepid library that needs none)."""
    info = license_info()
    if info is not None and not info.get('valid'):
        raise RuntimeError(info.get('error') or 'no valid license')


def license_info() -> Optional[Dict[str, Any]]:
    """The license the engines run under: its fields (but its signature),
    ``valid``, ``error`` when it is not valid or none was found, ``source``
    (where it was found), ``skipped`` (those passed over before it, each with
    its ``source`` and ``error``, when there are any), ``key`` and ``release``
    (the key this intrepid checks licenses with, and its release date). None
    for an intrepid library older than 1.7, which needs no license."""
    if not api.HAS_LICENSE:
        return None
    return json.loads(api.license_info())
