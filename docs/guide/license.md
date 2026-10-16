# The engines' license

From intrepid 1.7, the library inside intrepyd, the engines (BMC and
k-induction, backward reachability, PDR, and the portfolio that runs them)
run under a license only. Building circuits, simulating them, exporting them
and generating code need none.

## Noncommercial use

Each wheel of intrepyd on PyPI carries a noncommercial license, next to the
library, valid for a year from the day of its release: `pip install intrepyd`
is all the noncommercial use that [the license of intrepyd](https://github.com/formalmethods/intrepyd/blob/main/LICENSE.md)
allows needs. When it expires, a newer release of intrepyd carries a new
one.

## Commercial use

A company uses the commercial license it was given, a JSON file, in one of
these ways. intrepid looks for a license in this order, and uses the first it
finds:

1. given by the program:

    ```python
    import intrepyd.license

    intrepyd.license.set_license_file("/path/to/license.json")
    # or intrepyd.license.set_license(text), with the license's JSON itself
    ```

2. the `INTREPID_LICENSE` environment variable: the path of the license's
   file, or its JSON itself (convenient for a CI secret, or a container);
3. the file `~/.intrepid/license.json` (`%APPDATA%\intrepid\license.json` on
   Windows);
4. the noncommercial license the wheel carries.

A commercial license keeps working, after it expires, for the releases of
intrepid made before then: a later release needs it renewed.

## What intrepyd says

```python
import intrepyd.license

print(intrepyd.license.license_info())
```

gives the license the engines run under: its id, licensee, kind, issue and
expiry dates, whether it is `valid` (and, if not, the `error`), where it was
found (`source`), and the release date of the library. Without a valid
license, making an engine raises `RuntimeError` saying why: no license found
(and where it was looked for), a signature that is not valid, a license that
expired, or one that does not cover this release.

The processes the portfolio starts run under the same license:
`set_license` and `set_license_file` put it in `INTREPID_LICENSE`, which they
inherit.
