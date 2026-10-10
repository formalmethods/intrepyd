"""
The context module exposes the class Context, which
can be used to construct terms, formulas, simulators,
engines, and traces

Example:

from intrepyd.context import Context

ctx = Context()
bt = ctx.mk_boolean_type()
a = ctx.mk_input('a', bt)
"""

from __future__ import annotations

import functools
from collections.abc import Sequence
from typing import Callable, Concatenate, ParamSpec, Protocol, TypeVar

from intrepyd.api import Net, Type,\
                         mk_assumption, mk_undef, mk_true, mk_false, pop_assumption,\
                         push_assumption, push_namespace, pop_namespace,\
                         mk_boolean_type, mk_real_type,\
                         mk_int8_type, mk_int16_type, mk_int32_type, mk_int64_type,\
                         mk_uint8_type, mk_uint16_type, mk_uint32_type, mk_uint64_type,\
                         mk_float16_type, mk_float32_type, mk_float64_type, mk_int_type,\
                         mk_cast_to_int8, mk_cast_to_int16, mk_cast_to_int32, mk_cast_to_int64,\
                         mk_cast_to_uint8, mk_cast_to_uint16, mk_cast_to_uint32, mk_cast_to_uint64,\
                         mk_ctx, del_ctx,\
                         mk_number, mk_and, mk_or, mk_xor, mk_iff, mk_not,\
                         mk_leq, mk_lt, mk_geq, mk_gt, mk_eq, mk_neq,\
                         mk_add, mk_mul, mk_minus, mk_div, mk_sub,\
                         mk_input, mk_mod, mk_ite, mk_output,\
                         mk_latch, mk_substitute, set_latch_init_next,\
                         prepare_value_for_net, value_at

from intrepyd import engine, trace, simulator, portfolio, remote
from intrepyd.recipe import Recipe

_P = ParamSpec('_P')
_R = TypeVar('_R')

# Type attribute of a Context -> its readable name, for type-error messages.
_TYPE_NAMES = {
    'booleantype': 'bool',
    'int8type': 'int8', 'int16type': 'int16', 'int32type': 'int32', 'int64type': 'int64',
    'uint8type': 'uint8', 'uint16type': 'uint16', 'uint32type': 'uint32', 'uint64type': 'uint64',
    'realtype': 'real',
    'float16type': 'float16', 'float32type': 'float32', 'float64type': 'float64',
    'inttype': 'int',
}


class IntrepydTypeError(TypeError):
    """
    Raised by a Context's mk_* builder when it can see, from the types it
    tracks, that an operand has the wrong type (e.g. a boolean operator applied
    to an integer): a readable diagnosis in place of an internal solver error.
    The check is conservative — it fires only when the operand types are known
    and clearly incompatible, never rejecting a circuit the tracker is unsure of.
    """


class _Recordable(Protocol):  # pylint: disable=too-few-public-methods
    """What ``_recorded`` needs of the object it wraps a method of: a recipe to
    record the call in. ``Context`` satisfies it structurally."""
    recipe: Recipe


_S = TypeVar('_S', bound=_Recordable)


def _recorded(method: Callable[Concatenate[_S, _P], _R]) -> Callable[Concatenate[_S, _P], _R]:
    """
    Records each call of a method that builds the circuit in the recipe of
    the context (see intrepyd.recipe). The signature is preserved, so the
    wrapped ``mk_*`` keep their types for editors and type checkers.
    """
    @functools.wraps(method)
    def wrapper(self: _S, *args: _P.args, **kwargs: _P.kwargs) -> _R:
        result = method(self, *args, **kwargs)
        self.recipe.record(method.__name__, args, kwargs, result)
        return result
    return wrapper

class Context:
    """
    An intrepyd context

    After intrepyd.use_remote(url), Context() makes a RemoteContext on the
    service at url instead (see intrepyd.remote)
    """
    def __new__(cls, *args: object, **kwargs: object) -> "Context":
        if cls is Context and remote.get_remote() is not None:
            return remote.RemoteContext(remote.get_remote())  # type: ignore[return-value]
        return super().__new__(cls)

    def __init__(self) -> None:
        self.ctx = mk_ctx()
        self.inputs: dict[str, Net] = {}
        self.outputs: dict[str, Net] = {}
        self.latches: dict[str, Net] = {}
        self.nets: dict[str, Net] = {}
        self.net2name: dict[Net, str] = {}
        self.input2type: dict[Net, Type] = {}
        self.booleantype: Type = mk_boolean_type(self.ctx)
        self.int8type: Type = mk_int8_type(self.ctx)
        self.int16type: Type = mk_int16_type(self.ctx)
        self.int32type: Type = mk_int32_type(self.ctx)
        self.int64type: Type = mk_int64_type(self.ctx)
        self.uint8type: Type = mk_uint8_type(self.ctx)
        self.uint16type: Type = mk_uint16_type(self.ctx)
        self.uint32type: Type = mk_uint32_type(self.ctx)
        self.uint64type: Type = mk_uint64_type(self.ctx)
        self.realtype: Type = mk_real_type(self.ctx)
        self.float16type: Type = mk_float16_type(self.ctx)
        self.float32type: Type = mk_float32_type(self.ctx)
        self.float64type: Type = mk_float64_type(self.ctx)
        self.inttype: Type = mk_int_type(self.ctx)
        self.undef: Net = mk_undef(self.ctx)
        self.true: Net = mk_true(self.ctx)
        self.false: Net = mk_false(self.ctx)
        self.namespaces: list[str] = []
        self.recipe = Recipe(self)
        # The type of each net, as far as it can be tracked on the python side,
        # for the sanity checks in the mk_* builders. Populated for inputs,
        # latches, numbers, the predefined booleans, and the results whose type
        # is certain; a net stays absent when its type is not known, and the
        # checks skip it.
        self._type_name_by_value: dict[Type, str] = {
            getattr(self, attr): name for attr, name in _TYPE_NAMES.items()
        }
        self._net2type: dict[Net, Type] = {self.true: self.booleantype,
                                          self.false: self.booleantype}

    def __del__(self) -> None:
        del_ctx(self.ctx)

    @_recorded
    def push_namespace(self, name: str) -> None:
        """
        Pushes a namespace
        """
        push_namespace(self.ctx, name)
        self.namespaces.append(name)

    @_recorded
    def pop_namespace(self) -> str:
        """
        Pops a namespace
        """
        if len(self.namespaces) == 0:
            raise Exception('Cannot pop namespace, empty list')
        pop_namespace(self.ctx)
        return self.namespaces.pop()

    def mk_boolean_type(self) -> Type:
        """
        Creates boolean type
        """
        return self.booleantype

    def mk_int8_type(self) -> Type:
        """
        Creates int8 type
        """
        return self.int8type

    def mk_int16_type(self) -> Type:
        """
        Creates int16 type
        """
        return self.int16type

    def mk_int32_type(self) -> Type:
        """
        Creates int32 type
        """
        return self.int32type

    def mk_int64_type(self) -> Type:
        """
        Creates int64 type
        """
        return self.int64type

    def mk_uint8_type(self) -> Type:
        """
        Creates uint8 type
        """
        return self.uint8type

    def mk_uint16_type(self) -> Type:
        """
        Creates uint16 type
        """
        return self.uint16type

    def mk_uint32_type(self) -> Type:
        """
        Creates uint32 type
        """
        return self.uint32type

    def mk_uint64_type(self) -> Type:
        """
        Creates uint64 type
        """
        return self.uint64type

    def mk_real_type(self) -> Type:
        """
        Creates real type
        """
        return self.realtype

    def mk_float16_type(self) -> Type:
        """
        Creates float16 type
        """
        return self.float16type

    def mk_float32_type(self) -> Type:
        """
        Creates float32 type
        """
        return self.float32type

    def mk_float64_type(self) -> Type:
        """
        Creates float64 type
        """
        return self.float64type

    def mk_int_type(self) -> Type:
        """
        Creates infinite precision int type
        """
        return self.inttype

    def mk_undef(self) -> Net:
        """
        Creates undef net
        """
        return self.undef

    @_recorded
    def mk_true(self, name: str | None = None) -> Net:
        """
        Creates net true
        """
        return self._register(self.true, name)

    @_recorded
    def mk_false(self, name: str | None = None) -> Net:
        """
        Creates net false
        """
        return self._register(self.false, name)

    @_recorded
    def mk_number(self, value: str, type_: Type, name: str | None = None) -> Net:
        """
        Creates a number from a value and a type
        """
        net = self._register(mk_number(self.ctx, value, type_), name)
        self._net2type[net] = type_
        return net

    @_recorded
    def mk_not(self, x: Net, name: str | None = None) -> Net:
        """
        Creates the net !x
        """
        self._require_boolean('mk_not', x)
        net = self._register(mk_not(self.ctx, x), name=name)
        self._net2type[net] = self.booleantype
        return net

    @_recorded
    def mk_and(self, x: Net, y: Net, name: str | None = None) -> Net:
        """
        Creates the net x && y
        """
        self._require_boolean('mk_and', x, y)
        net = self._register(mk_and(self.ctx, x, y), name=name)
        self._net2type[net] = self.booleantype
        return net

    @_recorded
    def mk_or(self, x: Net, y: Net, name: str | None = None) -> Net:
        """
        Creates the net x || y
        """
        self._require_boolean('mk_or', x, y)
        net = self._register(mk_or(self.ctx, x, y), name=name)
        self._net2type[net] = self.booleantype
        return net

    @_recorded
    def mk_xor(self, x: Net, y: Net, name: str | None = None) -> Net:
        """
        Creates the net x ^ y
        """
        self._require_boolean('mk_xor', x, y)
        net = self._register(mk_xor(self.ctx, x, y), name=name)
        self._net2type[net] = self.booleantype
        return net

    @_recorded
    def mk_implies(self, x: Net, y: Net, name: str | None = None) -> Net:
        """
        Creates the net x -> y
        """
        self._require_boolean('mk_implies', x, y)
        net = self._register(mk_or(self.ctx, mk_not(self.ctx, x), y), name=name)
        self._net2type[net] = self.booleantype
        return net

    @_recorded
    def mk_iff(self, x: Net, y: Net, name: str | None = None) -> Net:
        """
        Creates the net x <-> y
        """
        self._require_boolean('mk_iff', x, y)
        net = self._register(mk_iff(self.ctx, x, y), name=name)
        self._net2type[net] = self.booleantype
        return net

    @_recorded
    def mk_eq(self, x: Net, y: Net, name: str | None = None) -> Net:
        """
        Creates the predicate x = y
        """
        self._require_same('mk_eq', x, y)
        net = self._register(mk_eq(self.ctx, x, y), name=name)
        self._net2type[net] = self.booleantype
        return net

    @_recorded
    def mk_leq(self, x: Net, y: Net, name: str | None = None) -> Net:
        """
        Creates the predicate x <= y
        """
        self._require_numeric('mk_leq', x, y)
        self._require_same('mk_leq', x, y)
        net = self._register(mk_leq(self.ctx, x, y), name=name)
        self._net2type[net] = self.booleantype
        return net

    @_recorded
    def mk_lt(self, x: Net, y: Net, name: str | None = None) -> Net:
        """
        Creates the predicate x < y
        """
        self._require_numeric('mk_lt', x, y)
        self._require_same('mk_lt', x, y)
        net = self._register(mk_lt(self.ctx, x, y), name=name)
        self._net2type[net] = self.booleantype
        return net

    @_recorded
    def mk_geq(self, x: Net, y: Net, name: str | None = None) -> Net:
        """
        Creates the predicate x >= y
        """
        self._require_numeric('mk_geq', x, y)
        self._require_same('mk_geq', x, y)
        net = self._register(mk_geq(self.ctx, x, y), name=name)
        self._net2type[net] = self.booleantype
        return net

    @_recorded
    def mk_gt(self, x: Net, y: Net, name: str | None = None) -> Net:
        """
        Creates the predicate x > y
        """
        self._require_numeric('mk_gt', x, y)
        self._require_same('mk_gt', x, y)
        net = self._register(mk_gt(self.ctx, x, y), name=name)
        self._net2type[net] = self.booleantype
        return net

    @_recorded
    def mk_neq(self, x: Net, y: Net, name: str | None = None) -> Net:
        """
        Creates the predicate x != y
        """
        self._require_same('mk_neq', x, y)
        net = self._register(mk_neq(self.ctx, x, y), name=name)
        self._net2type[net] = self.booleantype
        return net

    @_recorded
    def mk_add(self, x: Net, y: Net, name: str | None = None) -> Net:
        """
        Creates the term x + y
        """
        self._require_numeric('mk_add', x, y)
        self._require_same('mk_add', x, y)
        net = self._register(mk_add(self.ctx, x, y), name=name)
        self._record_type(net, self._common_type(x, y))
        return net

    @_recorded
    def mk_mul(self, x: Net, y: Net, name: str | None = None) -> Net:
        """
        Creates the term x * y
        """
        self._require_numeric('mk_mul', x, y)
        self._require_same('mk_mul', x, y)
        net = self._register(mk_mul(self.ctx, x, y), name=name)
        self._record_type(net, self._common_type(x, y))
        return net

    @_recorded
    def mk_div(self, x: Net, y: Net, name: str | None = None) -> Net:
        """
        Creates the term x / y
        """
        self._require_numeric('mk_div', x, y)
        self._require_same('mk_div', x, y)
        net = self._register(mk_div(self.ctx, x, y), name=name)
        self._record_type(net, self._common_type(x, y))
        return net

    @_recorded
    def mk_mod(self, x: Net, y: Net, name: str | None = None) -> Net:
        """
        Creates the term x % y
        """
        self._require_numeric('mk_mod', x, y)
        self._require_same('mk_mod', x, y)
        net = self._register(mk_mod(self.ctx, x, y), name=name)
        self._record_type(net, self._common_type(x, y))
        return net

    @_recorded
    def mk_sub(self, x: Net, y: Net, name: str | None = None) -> Net:
        """
        Creates the term x - y
        """
        self._require_numeric('mk_sub', x, y)
        self._require_same('mk_sub', x, y)
        net = self._register(mk_sub(self.ctx, x, y), name=name)
        self._record_type(net, self._common_type(x, y))
        return net

    @_recorded
    def mk_minus(self, x: Net, name: str | None = None) -> Net:
        """
        Creates the term -x
        """
        self._require_numeric('mk_minus', x)
        net = self._register(mk_minus(self.ctx, x), name=name)
        self._record_type(net, self._net2type.get(x))
        return net

    @_recorded
    def mk_ite(self, i: Net, t: Net, e: Net, name: str | None = None) -> Net:
        """
        Creates the term ite(i, t, e)
        """
        self._require_boolean('mk_ite', i)
        self._require_same('mk_ite', t, e)
        net = self._register(mk_ite(self.ctx, i, t, e), name=name)
        self._record_type(net, self._common_type(t, e))
        return net

    @_recorded
    def mk_input(self, name: str, type_: Type) -> Net:
        """
        Creates a primary input
        """
        return self._register_input(mk_input(self.ctx, name, type_), type_, name=name)

    @_recorded
    def mk_output(self, x: Net, name: str | None = None) -> None:
        """
        Tag a net as output
        """
        mk_output(self.ctx, x)
        self._register_output(x, name=name)

    @_recorded
    def mk_latch(self, name: str, type_: Type) -> Net:
        """
        Creates a latch
        """
        latch = self._register_latch(mk_latch(self.ctx, name, type_), name=name)
        self._net2type[latch] = type_
        return latch

    @_recorded
    def set_latch_init_next(self, latch: Net, init: Net, nex: Net) -> None:
        """
        Sets the initial and next value of a latch
        """
        set_latch_init_next(self.ctx, latch, init, nex)

    @_recorded
    def mk_substitute(self, term: Net, new_term: Net, old_term: Net) -> Net:
        """
        Replaces the occurrences of oldTerm, that are found in term, with newTerm
        """
        return mk_substitute(self.ctx, term, new_term, old_term)

    @_recorded
    def mk_assumption(self, net: Net) -> None:
        """
        Creates an assumption
        @deprecated
        """
        mk_assumption(self.ctx, net)

    @_recorded
    def push_assumption(self, net: Net) -> None:
        """
        Pushes an assumption
        """
        push_assumption(self.ctx, net)

    @_recorded
    def pop_assumption(self) -> None:
        """
        Pops an assumption
        """
        pop_assumption(self.ctx)

    @_recorded
    def mk_cast_to_int8(self, net: Net, name: str | None = None) -> Net:
        """
        Casts a net to an int8
        """
        return self._register(mk_cast_to_int8(self.ctx, net), name)

    @_recorded
    def mk_cast_to_int16(self, net: Net, name: str | None = None) -> Net:
        """
        Casts a net to an int16
        """
        return self._register(mk_cast_to_int16(self.ctx, net), name)

    @_recorded
    def mk_cast_to_int32(self, net: Net, name: str | None = None) -> Net:
        """
        Casts a net to an int32
        """
        return self._register(mk_cast_to_int32(self.ctx, net), name)

    @_recorded
    def mk_cast_to_int64(self, net: Net, name: str | None = None) -> Net:
        """
        Casts a net to an int64
        """
        return self._register(mk_cast_to_int64(self.ctx, net), name)

    @_recorded
    def mk_cast_to_uint8(self, net: Net, name: str | None = None) -> Net:
        """
        Casts a net to an uint8
        """
        return self._register(mk_cast_to_uint8(self.ctx, net), name)

    @_recorded
    def mk_cast_to_uint16(self, net: Net, name: str | None = None) -> Net:
        """
        Casts a net to an uint16
        """
        return self._register(mk_cast_to_uint16(self.ctx, net), name)

    @_recorded
    def mk_cast_to_uint32(self, net: Net, name: str | None = None) -> Net:
        """
        Casts a net to an uint32
        """
        return self._register(mk_cast_to_uint32(self.ctx, net), name)

    @_recorded
    def mk_cast_to_uint64(self, net: Net, name: str | None = None) -> Net:
        """
        Casts a net to an uint64
        """
        return self._register(mk_cast_to_uint64(self.ctx, net), name)

    def mk_bmc(self) -> engine.Bmc:
        """
        Creates a BMC engine
        """
        return engine.Bmc(self.ctx)

    def mk_optimizing_bmc(self) -> engine.OptimizingBmc:
        """
        Creates an optimizing BMC engine
        """
        return engine.OptimizingBmc(self.ctx)

    def mk_backward_reach(self) -> engine.BackwardReach:
        """
        Creates a backward reachability engine
        """
        return engine.BackwardReach(self.ctx)

    def mk_pdr(self) -> engine.Pdr:
        """
        Creates an IC3/PDR engine
        """
        return engine.Pdr(self.ctx)

    def mk_portfolio(self, engines: Sequence[str] | None = None,
                     max_depth: int | None = None) -> portfolio.Portfolio:
        """
        Creates a portfolio: an engine that runs several engines in parallel,
        each in a process of its own, and stops them all at the first
        conclusive answer (see intrepyd.portfolio). ``engines`` defaults to all
        of ``portfolio.ENGINES``.
        """
        if engines is None:
            engines = portfolio.ENGINES
        return portfolio.Portfolio(self, engines, max_depth)

    def mk_simulator(self) -> simulator.Simulator:
        """
        Creates a simulator
        """
        return simulator.Simulator(self.ctx)

    def mk_trace(self) -> trace.Trace:
        """
        Creates an empty trace
        """
        return trace.Trace(self.ctx)

    def to_string(self, net: Net) -> str:
        """
        Returns the given net as a string, as given from the underlying smt-solver.
        """
        size = prepare_value_for_net(self.ctx, net)
        value = ''
        for i in range(size):
            value += value_at(i)
        return value

    def get_default_value(self, type_: Type) -> str:
        """
        Returns a default value for the given type
        """
        if type_ == self.booleantype:
            return 'F'
        if type_ in [self.float16type, self.float32type, self.float64type, self.realtype]:
            return '0.0'
        assert type_ in [self.int8type, \
                         self.int16type, \
                         self.int32type, \
                         self.uint8type, \
                         self.uint16type, \
                         self.uint32type]
        return '0'

    def _current_namespace_prefix(self) -> str:
        result = ''
        for namespace in self.namespaces:
            result += namespace + '.'
        return result

    def _register(self, rawnet: Net, name: str | None) -> Net:
        if name is None:
            name = '__n' + str(rawnet)
        name = self._current_namespace_prefix() + name
        # Potentially overrides previous
        self.nets[name] = rawnet
        if rawnet not in self.net2name:
            self.net2name[rawnet] = name
        return rawnet

    def _register_input(self, rawnet: Net, type_: Type, name: str) -> Net:
        rawnet = self._register(rawnet, name)
        self.inputs[name] = rawnet
        self.input2type[rawnet] = type_
        self._net2type[rawnet] = type_
        return rawnet

    # --- sanity checks of the mk_* builders (see IntrepydTypeError) -----------
    # Each fires only when the operand types are known; the result type is
    # recorded only when certain, so the tracker never holds a wrong type.

    def _type_name(self, type_: Type) -> str:
        return self._type_name_by_value.get(type_, 'an unknown type')

    def _describe(self, net: Net) -> str:
        name = self.net2name.get(net)
        return f"'{name}'" if name is not None and not name.startswith('__') else f"net {net}"

    def _require_boolean(self, op: str, *nets: Net) -> None:
        for net in nets:
            type_ = self._net2type.get(net)
            if type_ is not None and type_ != self.booleantype:
                raise IntrepydTypeError(
                    f"{op} expects boolean operands, but {self._describe(net)} has type "
                    f"{self._type_name(type_)}")

    def _require_numeric(self, op: str, *nets: Net) -> None:
        for net in nets:
            if self._net2type.get(net) == self.booleantype:
                raise IntrepydTypeError(
                    f"{op} expects numeric operands, but {self._describe(net)} is boolean")

    def _require_same(self, op: str, x: Net, y: Net) -> None:
        tx, ty = self._net2type.get(x), self._net2type.get(y)
        if tx is not None and ty is not None and tx != ty:
            raise IntrepydTypeError(
                f"{op} expects operands of the same type, but {self._describe(x)} has type "
                f"{self._type_name(tx)} and {self._describe(y)} has type {self._type_name(ty)}")

    def _common_type(self, *nets: Net) -> Type | None:
        """The operands' type when they all share one known type, else None."""
        types = {self._net2type.get(net) for net in nets}
        types.discard(None)
        return next(iter(types)) if len(types) == 1 else None

    def _record_type(self, net: Net, type_: Type | None) -> None:
        """Remember a result's type, but only when it is certain."""
        if type_ is not None:
            self._net2type[net] = type_

    def _register_latch(self, rawnet: Net, name: str) -> Net:
        rawnet = self._register(rawnet, name)
        self.latches[name] = rawnet
        return rawnet

    def _register_output(self, rawnet: Net, name: str | None) -> None:
        if name is None:
            name = '__o' + str(rawnet)
        rawnet = self._register(rawnet, name)
        self.outputs[name] = rawnet
