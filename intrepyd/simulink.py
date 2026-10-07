"""
Python binding of the Simulink front-end.

The translator from Simulink models to intrepyd circuits is a C library
(libintrepid_simulink.so on Linux, intrepid_simulink.dll on Windows), built
and released from its own repository, as intrepid is. This module loads it
with ctypes, when it is first needed: intrepyd works without it, and only
translate_simulink() requires it.

The library is looked up first in the INTREPID_SIMULINK_LIBRARY environment
variable, which must be the path of the library file, and then next to this
module, which is where the packaged intrepyd ships it.
"""

import ctypes
import os
import sys

__all__ = ['SimulinkError', 'translate_file', 'library_path']

if sys.platform == 'win32':
    _LIBRARY_NAME = 'intrepid_simulink.dll'
else:
    _LIBRARY_NAME = 'libintrepid_simulink.so'

_lib = None


class SimulinkError(Exception):
    """A model that cannot be translated: the message lists the reasons"""


def library_path():
    """The path of the library, or None if it is not available"""
    path = os.environ.get('INTREPID_SIMULINK_LIBRARY')
    if path:
        if not os.path.isfile(path):
            raise ImportError(f'INTREPID_SIMULINK_LIBRARY is set to {path}, which is not a file')
        return path
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), _LIBRARY_NAME)
    return path if os.path.isfile(path) else None


def _load():
    global _lib  # pylint: disable=global-statement
    if _lib is not None:
        return _lib
    path = library_path()
    if path is None:
        raise ImportError(
            f'The Simulink front-end is not available: cannot find {_LIBRARY_NAME} next to '
            'intrepyd, nor in INTREPID_SIMULINK_LIBRARY.')
    lib = ctypes.CDLL(path)
    handle = ctypes.c_void_p
    lib.ims_version.restype = ctypes.c_char_p
    lib.ims_mk_options.restype = handle
    lib.ims_del_options.argtypes = [handle]
    lib.ims_set_option.argtypes = [handle, ctypes.c_char_p, ctypes.c_char_p]
    lib.ims_set_option.restype = ctypes.c_int
    lib.ims_options_error.argtypes = [handle]
    lib.ims_options_error.restype = ctypes.c_char_p
    lib.ims_translate_file.argtypes = [ctypes.c_char_p, handle]
    lib.ims_translate_file.restype = handle
    lib.ims_result_ok.argtypes = [handle]
    lib.ims_result_ok.restype = ctypes.c_int
    lib.ims_result_python.argtypes = [handle]
    lib.ims_result_python.restype = ctypes.c_char_p
    lib.ims_result_errors.argtypes = [handle]
    lib.ims_result_errors.restype = ctypes.c_char_p
    lib.ims_del_result.argtypes = [handle]
    _lib = lib
    return lib


def version():
    """The version of the library"""
    return _load().ims_version().decode()


def translate_file(infilename, realtype='float', variables=None, scripts=None, mats=None,
                   callbacks=True):
    """
    Translates a Simulink model, a .mdl or a .slx file, and returns the
    python module of its circuit, as a string. Raises SimulinkError, listing
    the blocks that cannot be translated, if the model cannot be.

    realtype is 'float', to translate single and double as floats, exactly,
    or 'real', as reals, which is not exact but much easier for the engines.
    The workspace of MATLAB the model refers to is filled, in order, by the
    callbacks of the model (PreLoadFcn, PostLoadFcn, InitFcn: their loads of
    MAT files and their scripts), unless callbacks is False; then by the MAT
    files in mats (their Simulink.Bus objects and numeric variables); then by
    the MATLAB scripts of assignments in scripts; then by variables, which
    maps names to MATLAB expressions.
    """
    lib = _load()
    options = lib.ims_mk_options()
    try:
        settings = [('real_type', realtype), ('callbacks', 'on' if callbacks else 'off')]
        settings += [('mat', mat) for mat in mats or []]
        settings += [('script', script) for script in scripts or []]
        settings += [('variable', f'{name}={value}') for name, value in (variables or {}).items()]
        for key, value in settings:
            if lib.ims_set_option(options, key.encode(), str(value).encode()) != 0:
                raise SimulinkError(lib.ims_options_error(options).decode())
        result = lib.ims_translate_file(os.fsencode(infilename), options)
        try:
            if not lib.ims_result_ok(result):
                raise SimulinkError(lib.ims_result_errors(result).decode().rstrip('\n'))
            return lib.ims_result_python(result).decode()
        finally:
            lib.ims_del_result(result)
    finally:
        lib.ims_del_options(options)
