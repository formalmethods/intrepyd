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

import functools
from intrepyd.api import mk_assumption, mk_undef, mk_true, mk_false, pop_assumption, push_assumption,\
                         push_namespace, pop_namespace,\
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

def _recorded(method):
    """
    Records each call of a method that builds the circuit in the recipe of
    the context (see intrepyd.recipe)
    """
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
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
    def __new__(cls, *args, **kwargs):
        if cls is Context and remote.get_remote() is not None:
            return remote.RemoteContext(remote.get_remote())
        return super().__new__(cls)

    def __init__(self):
        self.ctx = mk_ctx()
        self.inputs = {}
        self.outputs = {}
        self.latches = {}
        self.nets = {}
        self.net2name = {}
        self.input2type = {}
        self.booleantype = mk_boolean_type(self.ctx)
        self.int8type = mk_int8_type(self.ctx)
        self.int16type = mk_int16_type(self.ctx)
        self.int32type = mk_int32_type(self.ctx)
        self.int64type = mk_int64_type(self.ctx)
        self.uint8type = mk_uint8_type(self.ctx)
        self.uint16type = mk_uint16_type(self.ctx)
        self.uint32type = mk_uint32_type(self.ctx)
        self.uint64type = mk_uint64_type(self.ctx)
        self.realtype = mk_real_type(self.ctx)
        self.float16type = mk_float16_type(self.ctx)
        self.float32type = mk_float32_type(self.ctx)
        self.float64type = mk_float64_type(self.ctx)
        self.inttype = mk_int_type(self.ctx)
        self.undef = mk_undef(self.ctx)
        self.true = mk_true(self.ctx)
        self.false = mk_false(self.ctx)
        self.namespaces = []
        self.recipe = Recipe(self)

    def __del__(self):
        del_ctx(self.ctx)

    @_recorded
    def push_namespace(self, name):
        """
        Pushes a namespace
        """
        push_namespace(self.ctx, name)
        self.namespaces.append(name)

    @_recorded
    def pop_namespace(self):
        """
        Pops a namespace
        """
        if len(self.namespaces) == 0:
            raise Exception('Cannot pop namespace, empty list')
        pop_namespace(self.ctx)
        return self.namespaces.pop()

    def mk_boolean_type(self):
        """
        Creates boolean type
        """
        return self.booleantype

    def mk_int8_type(self):
        """
        Creates int8 type
        """
        return self.int8type

    def mk_int16_type(self):
        """
        Creates int16 type
        """
        return self.int16type

    def mk_int32_type(self):
        """
        Creates int32 type
        """
        return self.int32type

    def mk_int64_type(self):
        """
        Creates int64 type
        """
        return self.int64type

    def mk_uint8_type(self):
        """
        Creates uint8 type
        """
        return self.uint8type

    def mk_uint16_type(self):
        """
        Creates uint16 type
        """
        return self.uint16type

    def mk_uint32_type(self):
        """
        Creates uint32 type
        """
        return self.uint32type

    def mk_uint64_type(self):
        """
        Creates uint64 type
        """
        return self.uint64type

    def mk_real_type(self):
        """
        Creates real type
        """
        return self.realtype

    def mk_float16_type(self):
        """
        Creates float16 type
        """
        return self.float16type

    def mk_float32_type(self):
        """
        Creates float32 type
        """
        return self.float32type

    def mk_float64_type(self):
        """
        Creates float64 type
        """
        return self.float64type

    def mk_int_type(self):
        """
        Creates infinite precision int type
        """
        return self.inttype

    def mk_undef(self):
        """
        Creates undef net
        """
        return self.undef

    @_recorded
    def mk_true(self, name=None):
        """
        Creates net true
        """
        return self._register(self.true, name)

    @_recorded
    def mk_false(self, name=None):
        """
        Creates net false
        """
        return self._register(self.false, name)

    @_recorded
    def mk_number(self, value, type_, name=None):
        """
        Creates a number from a value and a type
        """
        return self._register(mk_number(self.ctx, value, type_), name)

    @_recorded
    def mk_not(self, x, name=None):
        """
        Creates the net !x
        """
        return self._register(mk_not(self.ctx, x), name=name)

    @_recorded
    def mk_and(self, x, y, name=None):
        """
        Creates the net x && y
        """
        return self._register(mk_and(self.ctx, x, y), name=name)

    @_recorded
    def mk_or(self, x, y, name=None):
        """
        Creates the net x || y
        """
        return self._register(mk_or(self.ctx, x, y), name=name)

    @_recorded
    def mk_xor(self, x, y, name=None):
        """
        Creates the net x ^ y
        """
        return self._register(mk_xor(self.ctx, x, y), name=name)

    @_recorded
    def mk_implies(self, x, y, name=None):
        """
        Creates the net x -> y
        """
        return self._register(mk_or(self.ctx, mk_not(self.ctx, x), y), name=name)

    @_recorded
    def mk_iff(self, x, y, name=None):
        """
        Creates the net x <-> y
        """
        return self._register(mk_iff(self.ctx, x, y), name=name)

    @_recorded
    def mk_eq(self, x, y, name=None):
        """
        Creates the predicate x = y
        """
        return self._register(mk_eq(self.ctx, x, y), name=name)

    @_recorded
    def mk_leq(self, x, y, name=None):
        """
        Creates the predicate x <= y
        """
        return self._register(mk_leq(self.ctx, x, y), name=name)

    @_recorded
    def mk_lt(self, x, y, name=None):
        """
        Creates the predicate x < y
        """
        return self._register(mk_lt(self.ctx, x, y), name=name)

    @_recorded
    def mk_geq(self, x, y, name=None):
        """
        Creates the predicate x >= y
        """
        return self._register(mk_geq(self.ctx, x, y), name=name)

    @_recorded
    def mk_gt(self, x, y, name=None):
        """
        Creates the predicate x > y
        """
        return self._register(mk_gt(self.ctx, x, y), name=name)

    @_recorded
    def mk_neq(self, x, y, name=None):
        """
        Creates the predicate x != y
        """
        return self._register(mk_neq(self.ctx, x, y), name=name)

    @_recorded
    def mk_add(self, x, y, name=None):
        """
        Creates the term x + y
        """
        return self._register(mk_add(self.ctx, x, y), name=name)

    @_recorded
    def mk_mul(self, x, y, name=None):
        """
        Creates the term x * y
        """
        return self._register(mk_mul(self.ctx, x, y), name=name)

    @_recorded
    def mk_div(self, x, y, name=None):
        """
        Creates the term x / y
        """
        return self._register(mk_div(self.ctx, x, y), name=name)

    @_recorded
    def mk_mod(self, x, y, name=None):
        """
        Creates the term x % y
        """
        return self._register(mk_mod(self.ctx, x, y), name=name)

    @_recorded
    def mk_sub(self, x, y, name=None):
        """
        Creates the term x - y
        """
        return self._register(mk_sub(self.ctx, x, y), name=name)

    @_recorded
    def mk_minus(self, x, name=None):
        """
        Creates the term -x
        """
        return self._register(mk_minus(self.ctx, x), name=name)

    @_recorded
    def mk_ite(self, i, t, e, name=None):
        """
        Creates the term ite(i, t, e)
        """
        return self._register(mk_ite(self.ctx, i, t, e), name=name)

    @_recorded
    def mk_input(self, name, type_):
        """
        Creates a primary input
        """
        return self._register_input(mk_input(self.ctx, name, type_), type_, name=name)

    @_recorded
    def mk_output(self, x, name=None):
        """
        Tag a net as output
        """
        mk_output(self.ctx, x)
        self._register_output(x, name=name)

    @_recorded
    def mk_latch(self, name, type_):
        """
        Creates a latch
        """
        return self._register_latch(mk_latch(self.ctx, name, type_), name=name)

    @_recorded
    def set_latch_init_next(self, latch, init, nex):
        """
        Sets the initial and next value of a latch
        """
        set_latch_init_next(self.ctx, latch, init, nex)

    @_recorded
    def mk_substitute(self, term, new_term, old_term):
        """
        Replaces the occurrences of oldTerm, that are found in term, with newTerm
        """
        return mk_substitute(self.ctx, term, new_term, old_term)

    @_recorded
    def mk_assumption(self, net):
        """
        Creates an assumption
        @deprecated
        """
        mk_assumption(self.ctx, net)

    @_recorded
    def push_assumption(self, net):
        """
        Pushes an assumption
        """
        push_assumption(self.ctx, net)

    @_recorded
    def pop_assumption(self):
        """
        Pops an assumption
        """
        pop_assumption(self.ctx)

    @_recorded
    def mk_cast_to_int8(self, net, name=None):
        """
        Casts a net to an int8
        """
        return self._register(mk_cast_to_int8(self.ctx, net), name)

    @_recorded
    def mk_cast_to_int16(self, net, name=None):
        """
        Casts a net to an int16
        """
        return self._register(mk_cast_to_int16(self.ctx, net), name)

    @_recorded
    def mk_cast_to_int32(self, net, name=None):
        """
        Casts a net to an int32
        """
        return self._register(mk_cast_to_int32(self.ctx, net), name)

    @_recorded
    def mk_cast_to_int64(self, net, name=None):
        """
        Casts a net to an int64
        """
        return self._register(mk_cast_to_int64(self.ctx, net), name)

    @_recorded
    def mk_cast_to_uint8(self, net, name=None):
        """
        Casts a net to an uint8
        """
        return self._register(mk_cast_to_uint8(self.ctx, net), name)

    @_recorded
    def mk_cast_to_uint16(self, net, name=None):
        """
        Casts a net to an uint16
        """
        return self._register(mk_cast_to_uint16(self.ctx, net), name)

    @_recorded
    def mk_cast_to_uint32(self, net, name=None):
        """
        Casts a net to an uint32
        """
        return self._register(mk_cast_to_uint32(self.ctx, net), name)

    @_recorded
    def mk_cast_to_uint64(self, net, name=None):
        """
        Casts a net to an uint64
        """
        return self._register(mk_cast_to_uint64(self.ctx, net), name)

    def mk_bmc(self):
        """
        Creates a BMC engine
        """
        return engine.Bmc(self.ctx)

    def mk_optimizing_bmc(self):
        """
        Creates an optimizing BMC engine
        """
        return engine.OptimizingBmc(self.ctx)

    def mk_backward_reach(self):
        """
        Creates a backward reachability engine
        """
        return engine.BackwardReach(self.ctx)

    def mk_pdr(self):
        """
        Creates an IC3/PDR engine
        """
        return engine.Pdr(self.ctx)

    def mk_portfolio(self, engines=portfolio.ENGINES, max_depth=None):
        """
        Creates a portfolio: an engine that runs several engines in parallel,
        each in a process of its own, and stops them all at the first
        conclusive answer (see intrepyd.portfolio)
        """
        return portfolio.Portfolio(self, engines, max_depth)

    def mk_simulator(self):
        """
        Creates a simulator
        """
        return simulator.Simulator(self.ctx)

    def mk_trace(self):
        """
        Creates an empty trace
        """
        return trace.Trace(self.ctx)

    def to_string(self, net):
        """
        Returns the given net as a string, as given from the underlying smt-solver.
        """
        size = prepare_value_for_net(self.ctx, net)
        value = ''
        for i in range(size):
            value += value_at(i)
        return value

    def get_default_value(self, type_):
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

    def _current_namespace_prefix(self):
        result = ''
        for namespace in self.namespaces:
            result += namespace + '.'
        return result

    def _register(self, rawnet, name):
        if name is None:
            name = '__n' + str(rawnet)
        name = self._current_namespace_prefix() + name
        # Potentially overrides previous
        self.nets[name] = rawnet
        if rawnet not in self.net2name:
            self.net2name[rawnet] = name
        return rawnet

    def _register_input(self, rawnet, type_, name):
        rawnet = self._register(rawnet, name)
        self.inputs[name] = rawnet
        self.input2type[rawnet] = type_
        return rawnet

    def _register_latch(self, rawnet, name):
        rawnet = self._register(rawnet, name)
        self.latches[name] = rawnet
        return rawnet

    def _register_output(self, rawnet, name):
        if name is None:
            name = '__o' + str(rawnet)
        rawnet = self._register(rawnet, name)
        self.outputs[name] = rawnet
