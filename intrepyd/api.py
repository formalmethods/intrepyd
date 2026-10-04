"""
Python binding of the intrepid backend.

intrepid is a C library (libintrepid.so on Linux, intrepid.dll on Windows),
built and released from its own repository. This module loads it with ctypes
and exposes each function of its C API, src/api/Intrepid.h, under the same
name, so that

    from intrepyd.api import mk_ctx, mk_boolean_type

behaves as it did with the SWIG extension this module replaces:

- strings are passed and returned as str;
- handles (contexts, types, engines, traces, simulators) are opaque values,
  None when the library returns NULL; nets are ints;
- an error reported by the library raises RuntimeError with its message.

The library is looked up first in the INTREPID_LIBRARY environment variable,
which must be the path of the library file, and then next to this module,
which is where the packaged intrepyd ships it.
"""

import ctypes
import os
import sys

__all__ = ['INT_ENGINE_RESULT_UNKNOWN', 'INT_ENGINE_RESULT_REACHABLE',
           'INT_ENGINE_RESULT_UNREACHABLE', 'FUNCTIONS', 'LIBRARY_PATH']

# intrepid is built for Linux and Windows only
if sys.platform == 'win32':
    _LIBRARY_NAME = 'intrepid.dll'
else:
    _LIBRARY_NAME = 'libintrepid.so'


def _find_library():
    path = os.environ.get('INTREPID_LIBRARY')
    if path:
        if not os.path.isfile(path):
            raise ImportError('INTREPID_LIBRARY is set to %s, which is not a file' % path)
        return path
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), _LIBRARY_NAME)
    if not os.path.isfile(path):
        raise ImportError(
            'Cannot find the intrepid library %s. In a source checkout, run '
            '"make fetch_intrepid", or point INTREPID_LIBRARY at a local build '
            'of intrepid.' % path)
    return path


LIBRARY_PATH = _find_library()
_lib = ctypes.CDLL(LIBRARY_PATH)

# Values of the Int_engine_result enum
INT_ENGINE_RESULT_UNKNOWN = 0
INT_ENGINE_RESULT_REACHABLE = 1
INT_ENGINE_RESULT_UNREACHABLE = 2

# The C types used by the API
HANDLE = ctypes.c_void_p    # Int_ctx, Int_type, Int_engine_*, Int_trace, ...
UINT = ctypes.c_uint        # Int_net, unsigned
INT = ctypes.c_int          # Int_engine_result
STR = ctypes.c_char_p       # const char* argument, char* result
CHAR = ctypes.c_char        # char result
VOID = None

# Every function of Intrepid.h, as name: (result type, argument types). It is
# filled in by _bind, below, and checked against the header by
# intrepyd/tests/test_api.py.
FUNCTIONS = {}

_check_exception = _lib.check_exception
_check_exception.restype = STR
_check_exception.argtypes = ()
_clear_exception = _lib.clear_exception
_clear_exception.restype = VOID
_clear_exception.argtypes = ()
FUNCTIONS['check_exception'] = (STR, ())
FUNCTIONS['clear_exception'] = (VOID, ())
__all__ += ['check_exception', 'clear_exception']


def _encode(value):
    return value.encode() if isinstance(value, str) else value


def _bind(name, restype, argtypes):
    FUNCTIONS[name] = (restype, argtypes)
    __all__.append(name)
    function = getattr(_lib, name)
    function.restype = restype
    function.argtypes = argtypes
    string_args = [i for i, argtype in enumerate(argtypes) if argtype is STR]
    decode = restype in (STR, CHAR)

    # The library records an error rather than throwing, and the record stays
    # until cleared: it is checked after each call, and cleared before raising
    # so that the next call starts afresh.
    def wrapper(*args):
        if string_args:
            args = list(args)
            for i in string_args:
                if i < len(args):
                    args[i] = _encode(args[i])
        result = function(*args)
        error = _check_exception()
        if error is not None:
            _clear_exception()
            raise RuntimeError(error.decode(errors='replace'))
        if decode and result is not None:
            return result.decode(errors='replace')
        return result

    wrapper.__name__ = name
    wrapper.__qualname__ = name
    return wrapper


# check_exception and clear_exception are exposed as they are: wrapping them
# would clear the very error they are asked about.
def check_exception():
    """Returns the message of the last error, or None if there was none"""
    error = _check_exception()
    return None if error is None else error.decode(errors='replace')


def clear_exception():
    """Forgets the last error"""
    _clear_exception()


mk_ctx = _bind('mk_ctx', HANDLE, ())
del_ctx = _bind('del_ctx', VOID, (HANDLE,))
throw_exception = _bind('throw_exception', VOID, (STR,))
push_namespace = _bind('push_namespace', VOID, (HANDLE, STR))
pop_namespace = _bind('pop_namespace', VOID, (HANDLE,))
mk_engine_bmc = _bind('mk_engine_bmc', HANDLE, (HANDLE,))
set_bmc_current_depth = _bind('set_bmc_current_depth', VOID, (HANDLE, UINT))
set_bmc_optimize = _bind('set_bmc_optimize', VOID, (HANDLE,))
set_bmc_allow_targets_at_any_depth = _bind('set_bmc_allow_targets_at_any_depth', VOID, (HANDLE,))
set_bmc_use_induction = _bind('set_bmc_use_induction', VOID, (HANDLE,))
set_bmc_use_attack_path_axioms = _bind('set_bmc_use_attack_path_axioms', VOID, (HANDLE, HANDLE, UINT, UINT))
bmc_add_target = _bind('bmc_add_target', VOID, (HANDLE, HANDLE, UINT))
bmc_add_watch = _bind('bmc_add_watch', VOID, (HANDLE, HANDLE, UINT))
bmc_reach_targets = _bind('bmc_reach_targets', INT, (HANDLE,))
bmc_remove_last_reached_targets = _bind('bmc_remove_last_reached_targets', VOID, (HANDLE,))
bmc_last_reached_targets_number = _bind('bmc_last_reached_targets_number', UINT, (HANDLE,))
bmc_last_reached_target = _bind('bmc_last_reached_target', UINT, (HANDLE, UINT))
bmc_get_trace = _bind('bmc_get_trace', HANDLE, (HANDLE, HANDLE, UINT))
mk_engine_br = _bind('mk_engine_br', HANDLE, (HANDLE,))
br_add_target = _bind('br_add_target', VOID, (HANDLE, HANDLE, UINT))
br_add_watch = _bind('br_add_watch', VOID, (HANDLE, HANDLE, UINT))
br_reach_targets = _bind('br_reach_targets', INT, (HANDLE,))
br_remove_last_reached_targets = _bind('br_remove_last_reached_targets', VOID, (HANDLE,))
br_last_reached_targets_number = _bind('br_last_reached_targets_number', UINT, (HANDLE,))
br_last_reached_target = _bind('br_last_reached_target', UINT, (HANDLE, UINT))
br_get_trace = _bind('br_get_trace', HANDLE, (HANDLE, HANDLE, UINT))
mk_engine_pdr = _bind('mk_engine_pdr', HANDLE, (HANDLE,))
pdr_add_target = _bind('pdr_add_target', VOID, (HANDLE, HANDLE, UINT))
pdr_add_watch = _bind('pdr_add_watch', VOID, (HANDLE, HANDLE, UINT))
pdr_reach_targets = _bind('pdr_reach_targets', INT, (HANDLE,))
pdr_remove_last_reached_targets = _bind('pdr_remove_last_reached_targets', VOID, (HANDLE,))
pdr_last_reached_targets_number = _bind('pdr_last_reached_targets_number', UINT, (HANDLE,))
pdr_last_reached_target = _bind('pdr_last_reached_target', UINT, (HANDLE, UINT))
pdr_get_trace = _bind('pdr_get_trace', HANDLE, (HANDLE, HANDLE, UINT))
trace_prepare_value_for_net = _bind('trace_prepare_value_for_net', UINT, (HANDLE, HANDLE, UINT, UINT))
prepare_value_for_net = _bind('prepare_value_for_net', UINT, (HANDLE, UINT))
value_at = _bind('value_at', CHAR, (UINT,))
trace_get_max_depth = _bind('trace_get_max_depth', UINT, (HANDLE,))
mk_trace = _bind('mk_trace', HANDLE, (HANDLE,))
trace_set_value = _bind('trace_set_value', VOID, (HANDLE, HANDLE, UINT, UINT, STR))
trace_get_watched_nets_number = _bind('trace_get_watched_nets_number', UINT, (HANDLE,))
trace_get_watched_net = _bind('trace_get_watched_net', UINT, (HANDLE, UINT))
mk_simulator = _bind('mk_simulator', HANDLE, (HANDLE,))
simulator_add_watch = _bind('simulator_add_watch', VOID, (HANDLE, HANDLE, UINT))
simulator_simulate = _bind('simulator_simulate', VOID, (HANDLE, HANDLE, UINT))
mk_boolean_type = _bind('mk_boolean_type', HANDLE, (HANDLE,))
mk_int8_type = _bind('mk_int8_type', HANDLE, (HANDLE,))
mk_int16_type = _bind('mk_int16_type', HANDLE, (HANDLE,))
mk_int32_type = _bind('mk_int32_type', HANDLE, (HANDLE,))
mk_int64_type = _bind('mk_int64_type', HANDLE, (HANDLE,))
mk_uint8_type = _bind('mk_uint8_type', HANDLE, (HANDLE,))
mk_uint16_type = _bind('mk_uint16_type', HANDLE, (HANDLE,))
mk_uint32_type = _bind('mk_uint32_type', HANDLE, (HANDLE,))
mk_uint64_type = _bind('mk_uint64_type', HANDLE, (HANDLE,))
mk_int_type = _bind('mk_int_type', HANDLE, (HANDLE,))
mk_real_type = _bind('mk_real_type', HANDLE, (HANDLE,))
mk_float16_type = _bind('mk_float16_type', HANDLE, (HANDLE,))
mk_float32_type = _bind('mk_float32_type', HANDLE, (HANDLE,))
mk_float64_type = _bind('mk_float64_type', HANDLE, (HANDLE,))
mk_undef = _bind('mk_undef', UINT, (HANDLE,))
mk_true = _bind('mk_true', UINT, (HANDLE,))
mk_false = _bind('mk_false', UINT, (HANDLE,))
mk_number = _bind('mk_number', UINT, (HANDLE, STR, HANDLE))
mk_not = _bind('mk_not', UINT, (HANDLE, UINT))
mk_and = _bind('mk_and', UINT, (HANDLE, UINT, UINT))
mk_or = _bind('mk_or', UINT, (HANDLE, UINT, UINT))
mk_xor = _bind('mk_xor', UINT, (HANDLE, UINT, UINT))
mk_ite = _bind('mk_ite', UINT, (HANDLE, UINT, UINT, UINT))
mk_iff = _bind('mk_iff', UINT, (HANDLE, UINT, UINT))
mk_minus = _bind('mk_minus', UINT, (HANDLE, UINT))
mk_add = _bind('mk_add', UINT, (HANDLE, UINT, UINT))
mk_sub = _bind('mk_sub', UINT, (HANDLE, UINT, UINT))
mk_mul = _bind('mk_mul', UINT, (HANDLE, UINT, UINT))
mk_div = _bind('mk_div', UINT, (HANDLE, UINT, UINT))
mk_mod = _bind('mk_mod', UINT, (HANDLE, UINT, UINT))
mk_eq = _bind('mk_eq', UINT, (HANDLE, UINT, UINT))
mk_leq = _bind('mk_leq', UINT, (HANDLE, UINT, UINT))
mk_lt = _bind('mk_lt', UINT, (HANDLE, UINT, UINT))
mk_geq = _bind('mk_geq', UINT, (HANDLE, UINT, UINT))
mk_gt = _bind('mk_gt', UINT, (HANDLE, UINT, UINT))
mk_neq = _bind('mk_neq', UINT, (HANDLE, UINT, UINT))
mk_input = _bind('mk_input', UINT, (HANDLE, STR, HANDLE))
mk_output = _bind('mk_output', VOID, (HANDLE, UINT))
get_bit = _bind('get_bit', UINT, (HANDLE, UINT, UINT))
set_bit = _bind('set_bit', UINT, (HANDLE, UINT, UINT, UINT))
mk_assumption = _bind('mk_assumption', VOID, (HANDLE, UINT))
push_assumption = _bind('push_assumption', VOID, (HANDLE, UINT))
pop_assumption = _bind('pop_assumption', VOID, (HANDLE,))
mk_latch = _bind('mk_latch', UINT, (HANDLE, STR, HANDLE))
set_latch_init_next = _bind('set_latch_init_next', VOID, (HANDLE, UINT, UINT, UINT))
mk_substitute = _bind('mk_substitute', UINT, (HANDLE, UINT, UINT, UINT))
mk_cast_to_int8 = _bind('mk_cast_to_int8', UINT, (HANDLE, UINT))
mk_cast_to_int16 = _bind('mk_cast_to_int16', UINT, (HANDLE, UINT))
mk_cast_to_int32 = _bind('mk_cast_to_int32', UINT, (HANDLE, UINT))
mk_cast_to_int64 = _bind('mk_cast_to_int64', UINT, (HANDLE, UINT))
mk_cast_to_uint8 = _bind('mk_cast_to_uint8', UINT, (HANDLE, UINT))
mk_cast_to_uint16 = _bind('mk_cast_to_uint16', UINT, (HANDLE, UINT))
mk_cast_to_uint32 = _bind('mk_cast_to_uint32', UINT, (HANDLE, UINT))
mk_cast_to_uint64 = _bind('mk_cast_to_uint64', UINT, (HANDLE, UINT))
apitrace_dump_to_file = _bind('apitrace_dump_to_file', VOID, (STR,))
apitrace_print_to_stdout = _bind('apitrace_print_to_stdout', VOID, ())
apitrace_print_to_stderr = _bind('apitrace_print_to_stderr', VOID, ())

_clear_exception()
