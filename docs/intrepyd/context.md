Module intrepyd.context
=======================
The context module exposes the class Context, which
can be used to construct terms, formulas, simulators,
engines, and traces

Example:

from intrepyd.context import Context

ctx = Context()
bt = ctx.mk_boolean_type()
a = ctx.mk_input('a', bt)

Classes
-------

`Context()`
:   An intrepyd context

    ### Methods

    `get_default_value(self, type_)`
    :   Returns a default value for the given type

    `mk_add(self, x, y, name=None)`
    :   Creates the term x + y

    `mk_and(self, x, y, name=None)`
    :   Creates the net x && y

    `mk_assumption(self, net)`
    :   Creates an assumption
        @deprecated

    `mk_backward_reach(self)`
    :   Creates a backward reachability engine

    `mk_bmc(self)`
    :   Creates a BMC engine

    `mk_boolean_type(self)`
    :   Creates boolean type

    `mk_cast_to_int16(self, net, name=None)`
    :   Casts a net to an int16

    `mk_cast_to_int32(self, net, name=None)`
    :   Casts a net to an int32

    `mk_cast_to_int64(self, net, name=None)`
    :   Casts a net to an int64

    `mk_cast_to_int8(self, net, name=None)`
    :   Casts a net to an int8

    `mk_cast_to_uint16(self, net, name=None)`
    :   Casts a net to an uint16

    `mk_cast_to_uint32(self, net, name=None)`
    :   Casts a net to an uint32

    `mk_cast_to_uint64(self, net, name=None)`
    :   Casts a net to an uint64

    `mk_cast_to_uint8(self, net, name=None)`
    :   Casts a net to an uint8

    `mk_div(self, x, y, name=None)`
    :   Creates the term x / y

    `mk_eq(self, x, y, name=None)`
    :   Creates the predicate x = y

    `mk_false(self, name=None)`
    :   Creates net false

    `mk_float16_type(self)`
    :   Creates float16 type

    `mk_float32_type(self)`
    :   Creates float32 type

    `mk_float64_type(self)`
    :   Creates float64 type

    `mk_geq(self, x, y, name=None)`
    :   Creates the predicate x >= y

    `mk_gt(self, x, y, name=None)`
    :   Creates the predicate x > y

    `mk_iff(self, x, y, name=None)`
    :   Creates the net x <-> y

    `mk_implies(self, x, y, name=None)`
    :   Creates the net x -> y

    `mk_input(self, name, type_)`
    :   Creates a primary input

    `mk_int16_type(self)`
    :   Creates int16 type

    `mk_int32_type(self)`
    :   Creates int32 type

    `mk_int64_type(self)`
    :   Creates int64 type

    `mk_int8_type(self)`
    :   Creates int8 type

    `mk_int_type(self)`
    :   Creates infinite precision int type

    `mk_ite(self, i, t, e, name=None)`
    :   Creates the term ite(i, t, e)

    `mk_latch(self, name, type_)`
    :   Creates a latch

    `mk_leq(self, x, y, name=None)`
    :   Creates the predicate x <= y

    `mk_lt(self, x, y, name=None)`
    :   Creates the predicate x < y

    `mk_minus(self, x, name=None)`
    :   Creates the term -x

    `mk_mod(self, x, y, name=None)`
    :   Creates the term x % y

    `mk_mul(self, x, y, name=None)`
    :   Creates the term x * y

    `mk_neq(self, x, y, name=None)`
    :   Creates the predicate x != y

    `mk_not(self, x, name=None)`
    :   Creates the net !x

    `mk_number(self, value, type_, name=None)`
    :   Creates a number from a value and a type

    `mk_optimizing_bmc(self)`
    :   Creates an optimizing BMC engine

    `mk_or(self, x, y, name=None)`
    :   Creates the net x || y

    `mk_output(self, x, name=None)`
    :   Tag a net as output

    `mk_real_type(self)`
    :   Creates real type

    `mk_simulator(self)`
    :   Creates a simulator

    `mk_sub(self, x, y, name=None)`
    :   Creates the term x - y

    `mk_substitute(self, term, new_term, old_term)`
    :   Replaces the occurrences of oldTerm, that are found in term, with newTerm

    `mk_trace(self)`
    :   Creates an empty trace

    `mk_true(self, name=None)`
    :   Creates net true

    `mk_uint16_type(self)`
    :   Creates uint16 type

    `mk_uint32_type(self)`
    :   Creates uint32 type

    `mk_uint64_type(self)`
    :   Creates uint64 type

    `mk_uint8_type(self)`
    :   Creates uint8 type

    `mk_undef(self)`
    :   Creates undef net

    `mk_xor(self, x, y, name=None)`
    :   Creates the net x ^ y

    `pop_assumption(self)`
    :   Pops an assumption

    `pop_namespace(self)`
    :   Pops a namespace

    `push_assumption(self, net)`
    :   Pushes an assumption

    `push_namespace(self, name)`
    :   Pushes a namespace

    `set_latch_init_next(self, latch, init, nex)`
    :   Sets the initial and next value of a latch

    `to_string(self, net)`
    :   Returns the given net as a string, as given from the underlying smt-solver.