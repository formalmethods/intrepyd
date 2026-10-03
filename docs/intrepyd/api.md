Module intrepyd.api
===================

Functions
---------

    
`apitrace_dump_to_file(filename)`
:   apitrace_dump_to_file(char const * filename)
    
    Parameters
    ----------
    filename: char const *

    
`apitrace_print_to_stderr()`
:   apitrace_print_to_stderr()

    
`apitrace_print_to_stdout()`
:   apitrace_print_to_stdout()

    
`bmc_add_target(ctx, engine, target)`
:   bmc_add_target(Int_ctx ctx, Int_engine_bmc engine, Int_net target)
    
    Parameters
    ----------
    ctx: Int_ctx
    engine: Int_engine_bmc
    target: Int_net

    
`bmc_add_watch(ctx, engine, watch)`
:   bmc_add_watch(Int_ctx ctx, Int_engine_bmc engine, Int_net watch)
    
    Parameters
    ----------
    ctx: Int_ctx
    engine: Int_engine_bmc
    watch: Int_net

    
`bmc_get_trace(ctx, bmc, target)`
:   bmc_get_trace(Int_ctx ctx, Int_engine_bmc bmc, Int_net target) -> Int_trace
    
    Parameters
    ----------
    ctx: Int_ctx
    bmc: Int_engine_bmc
    target: Int_net

    
`bmc_last_reached_target(engine, n)`
:   bmc_last_reached_target(Int_engine_bmc engine, unsigned int n) -> Int_net
    
    Parameters
    ----------
    engine: Int_engine_bmc
    n: unsigned int

    
`bmc_last_reached_targets_number(engine)`
:   bmc_last_reached_targets_number(Int_engine_bmc engine) -> unsigned int
    
    Parameters
    ----------
    engine: Int_engine_bmc

    
`bmc_reach_targets(engine)`
:   bmc_reach_targets(Int_engine_bmc engine) -> Int_engine_result
    
    Parameters
    ----------
    engine: Int_engine_bmc

    
`bmc_remove_last_reached_targets(engine)`
:   bmc_remove_last_reached_targets(Int_engine_bmc engine)
    
    Parameters
    ----------
    engine: Int_engine_bmc

    
`br_add_target(ctx, engine, target)`
:   br_add_target(Int_ctx ctx, Int_engine_br engine, Int_net target)
    
    Parameters
    ----------
    ctx: Int_ctx
    engine: Int_engine_br
    target: Int_net

    
`br_add_watch(ctx, engine, watch)`
:   br_add_watch(Int_ctx ctx, Int_engine_br engine, Int_net watch)
    
    Parameters
    ----------
    ctx: Int_ctx
    engine: Int_engine_br
    watch: Int_net

    
`br_get_trace(ctx, br, target)`
:   br_get_trace(Int_ctx ctx, Int_engine_br br, Int_net target) -> Int_trace
    
    Parameters
    ----------
    ctx: Int_ctx
    br: Int_engine_br
    target: Int_net

    
`br_last_reached_target(engine, n)`
:   br_last_reached_target(Int_engine_br engine, unsigned int n) -> Int_net
    
    Parameters
    ----------
    engine: Int_engine_br
    n: unsigned int

    
`br_last_reached_targets_number(engine)`
:   br_last_reached_targets_number(Int_engine_br engine) -> unsigned int
    
    Parameters
    ----------
    engine: Int_engine_br

    
`br_reach_targets(engine)`
:   br_reach_targets(Int_engine_br engine) -> Int_engine_result
    
    Parameters
    ----------
    engine: Int_engine_br

    
`br_remove_last_reached_targets(engine)`
:   br_remove_last_reached_targets(Int_engine_br engine)
    
    Parameters
    ----------
    engine: Int_engine_br

    
`check_exception()`
:   check_exception() -> char *

    
`clear_exception()`
:   clear_exception()

    
`del_ctx(ctx)`
:   del_ctx(Int_ctx ctx)
    
    Parameters
    ----------
    ctx: Int_ctx

    
`get_bit(arg1, net, bit)`
:   get_bit(Int_ctx arg1, Int_net net, unsigned int bit) -> Int_net
    
    Parameters
    ----------
    arg1: Int_ctx
    net: Int_net
    bit: unsigned int

    
`mk_add(ctx, x, y)`
:   mk_add(Int_ctx ctx, Int_net x, Int_net y) -> Int_net
    
    Parameters
    ----------
    ctx: Int_ctx
    x: Int_net
    y: Int_net

    
`mk_and(ctx, x, y)`
:   mk_and(Int_ctx ctx, Int_net x, Int_net y) -> Int_net
    
    Parameters
    ----------
    ctx: Int_ctx
    x: Int_net
    y: Int_net

    
`mk_assumption(arg1, net)`
:   mk_assumption(Int_ctx arg1, Int_net net)
    
    Parameters
    ----------
    arg1: Int_ctx
    net: Int_net

    
`mk_boolean_type(ctx)`
:   mk_boolean_type(Int_ctx ctx) -> Int_type
    
    Parameters
    ----------
    ctx: Int_ctx

    
`mk_cast_to_int16(ctx, term)`
:   mk_cast_to_int16(Int_ctx ctx, Int_net term) -> Int_net
    
    Parameters
    ----------
    ctx: Int_ctx
    term: Int_net

    
`mk_cast_to_int32(ctx, term)`
:   mk_cast_to_int32(Int_ctx ctx, Int_net term) -> Int_net
    
    Parameters
    ----------
    ctx: Int_ctx
    term: Int_net

    
`mk_cast_to_int64(ctx, term)`
:   mk_cast_to_int64(Int_ctx ctx, Int_net term) -> Int_net
    
    Parameters
    ----------
    ctx: Int_ctx
    term: Int_net

    
`mk_cast_to_int8(ctx, term)`
:   mk_cast_to_int8(Int_ctx ctx, Int_net term) -> Int_net
    
    Parameters
    ----------
    ctx: Int_ctx
    term: Int_net

    
`mk_cast_to_uint16(ctx, term)`
:   mk_cast_to_uint16(Int_ctx ctx, Int_net term) -> Int_net
    
    Parameters
    ----------
    ctx: Int_ctx
    term: Int_net

    
`mk_cast_to_uint32(ctx, term)`
:   mk_cast_to_uint32(Int_ctx ctx, Int_net term) -> Int_net
    
    Parameters
    ----------
    ctx: Int_ctx
    term: Int_net

    
`mk_cast_to_uint64(ctx, term)`
:   mk_cast_to_uint64(Int_ctx ctx, Int_net term) -> Int_net
    
    Parameters
    ----------
    ctx: Int_ctx
    term: Int_net

    
`mk_cast_to_uint8(ctx, term)`
:   mk_cast_to_uint8(Int_ctx ctx, Int_net term) -> Int_net
    
    Parameters
    ----------
    ctx: Int_ctx
    term: Int_net

    
`mk_ctx()`
:   mk_ctx() -> Int_ctx

    
`mk_div(ctx, x, y)`
:   mk_div(Int_ctx ctx, Int_net x, Int_net y) -> Int_net
    
    Parameters
    ----------
    ctx: Int_ctx
    x: Int_net
    y: Int_net

    
`mk_engine_bmc(ctx)`
:   mk_engine_bmc(Int_ctx ctx) -> Int_engine_bmc
    
    Parameters
    ----------
    ctx: Int_ctx

    
`mk_engine_br(ctx)`
:   mk_engine_br(Int_ctx ctx) -> Int_engine_br
    
    Parameters
    ----------
    ctx: Int_ctx

    
`mk_eq(ctx, x, y)`
:   mk_eq(Int_ctx ctx, Int_net x, Int_net y) -> Int_net
    
    Parameters
    ----------
    ctx: Int_ctx
    x: Int_net
    y: Int_net

    
`mk_false(ctx)`
:   mk_false(Int_ctx ctx) -> Int_net
    
    Parameters
    ----------
    ctx: Int_ctx

    
`mk_float16_type(ctx)`
:   mk_float16_type(Int_ctx ctx) -> Int_type
    
    Parameters
    ----------
    ctx: Int_ctx

    
`mk_float32_type(ctx)`
:   mk_float32_type(Int_ctx ctx) -> Int_type
    
    Parameters
    ----------
    ctx: Int_ctx

    
`mk_float64_type(ctx)`
:   mk_float64_type(Int_ctx ctx) -> Int_type
    
    Parameters
    ----------
    ctx: Int_ctx

    
`mk_geq(ctx, x, y)`
:   mk_geq(Int_ctx ctx, Int_net x, Int_net y) -> Int_net
    
    Parameters
    ----------
    ctx: Int_ctx
    x: Int_net
    y: Int_net

    
`mk_gt(ctx, x, y)`
:   mk_gt(Int_ctx ctx, Int_net x, Int_net y) -> Int_net
    
    Parameters
    ----------
    ctx: Int_ctx
    x: Int_net
    y: Int_net

    
`mk_iff(ctx, x, y)`
:   mk_iff(Int_ctx ctx, Int_net x, Int_net y) -> Int_net
    
    Parameters
    ----------
    ctx: Int_ctx
    x: Int_net
    y: Int_net

    
`mk_input(ctx, name, type)`
:   mk_input(Int_ctx ctx, char const * name, Int_type type) -> Int_net
    
    Parameters
    ----------
    ctx: Int_ctx
    name: char const *
    type: Int_type

    
`mk_int16_type(ctx)`
:   mk_int16_type(Int_ctx ctx) -> Int_type
    
    Parameters
    ----------
    ctx: Int_ctx

    
`mk_int32_type(ctx)`
:   mk_int32_type(Int_ctx ctx) -> Int_type
    
    Parameters
    ----------
    ctx: Int_ctx

    
`mk_int64_type(ctx)`
:   mk_int64_type(Int_ctx ctx) -> Int_type
    
    Parameters
    ----------
    ctx: Int_ctx

    
`mk_int8_type(ctx)`
:   mk_int8_type(Int_ctx ctx) -> Int_type
    
    Parameters
    ----------
    ctx: Int_ctx

    
`mk_int_type(ctx)`
:   mk_int_type(Int_ctx ctx) -> Int_type
    
    Parameters
    ----------
    ctx: Int_ctx

    
`mk_ite(ctx, i, t, e)`
:   mk_ite(Int_ctx ctx, Int_net i, Int_net t, Int_net e) -> Int_net
    
    Parameters
    ----------
    ctx: Int_ctx
    i: Int_net
    t: Int_net
    e: Int_net

    
`mk_latch(ctx, name, type)`
:   mk_latch(Int_ctx ctx, char const * name, Int_type type) -> Int_net
    
    Parameters
    ----------
    ctx: Int_ctx
    name: char const *
    type: Int_type

    
`mk_leq(ctx, x, y)`
:   mk_leq(Int_ctx ctx, Int_net x, Int_net y) -> Int_net
    
    Parameters
    ----------
    ctx: Int_ctx
    x: Int_net
    y: Int_net

    
`mk_lt(ctx, x, y)`
:   mk_lt(Int_ctx ctx, Int_net x, Int_net y) -> Int_net
    
    Parameters
    ----------
    ctx: Int_ctx
    x: Int_net
    y: Int_net

    
`mk_minus(ctx, x)`
:   mk_minus(Int_ctx ctx, Int_net x) -> Int_net
    
    Parameters
    ----------
    ctx: Int_ctx
    x: Int_net

    
`mk_mod(ctx, x, y)`
:   mk_mod(Int_ctx ctx, Int_net x, Int_net y) -> Int_net
    
    Parameters
    ----------
    ctx: Int_ctx
    x: Int_net
    y: Int_net

    
`mk_mul(ctx, x, y)`
:   mk_mul(Int_ctx ctx, Int_net x, Int_net y) -> Int_net
    
    Parameters
    ----------
    ctx: Int_ctx
    x: Int_net
    y: Int_net

    
`mk_neq(ctx, x, y)`
:   mk_neq(Int_ctx ctx, Int_net x, Int_net y) -> Int_net
    
    Parameters
    ----------
    ctx: Int_ctx
    x: Int_net
    y: Int_net

    
`mk_not(ctx, x)`
:   mk_not(Int_ctx ctx, Int_net x) -> Int_net
    
    Parameters
    ----------
    ctx: Int_ctx
    x: Int_net

    
`mk_number(ctx, value, type)`
:   mk_number(Int_ctx ctx, char const * value, Int_type type) -> Int_net
    
    Parameters
    ----------
    ctx: Int_ctx
    value: char const *
    type: Int_type

    
`mk_or(ctx, x, y)`
:   mk_or(Int_ctx ctx, Int_net x, Int_net y) -> Int_net
    
    Parameters
    ----------
    ctx: Int_ctx
    x: Int_net
    y: Int_net

    
`mk_output(arg1, net)`
:   mk_output(Int_ctx arg1, Int_net net)
    
    Parameters
    ----------
    arg1: Int_ctx
    net: Int_net

    
`mk_real_type(ctx)`
:   mk_real_type(Int_ctx ctx) -> Int_type
    
    Parameters
    ----------
    ctx: Int_ctx

    
`mk_simulator(ctx)`
:   mk_simulator(Int_ctx ctx) -> Int_simulator
    
    Parameters
    ----------
    ctx: Int_ctx

    
`mk_sub(ctx, x, y)`
:   mk_sub(Int_ctx ctx, Int_net x, Int_net y) -> Int_net
    
    Parameters
    ----------
    ctx: Int_ctx
    x: Int_net
    y: Int_net

    
`mk_substitute(ctx, term, new_subterm, old_subterm)`
:   mk_substitute(Int_ctx ctx, Int_net term, Int_net new_subterm, Int_net old_subterm) -> Int_net
    
    Parameters
    ----------
    ctx: Int_ctx
    term: Int_net
    new_subterm: Int_net
    old_subterm: Int_net

    
`mk_trace(ctx)`
:   mk_trace(Int_ctx ctx) -> Int_trace
    
    Parameters
    ----------
    ctx: Int_ctx

    
`mk_true(ctx)`
:   mk_true(Int_ctx ctx) -> Int_net
    
    Parameters
    ----------
    ctx: Int_ctx

    
`mk_uint16_type(ctx)`
:   mk_uint16_type(Int_ctx ctx) -> Int_type
    
    Parameters
    ----------
    ctx: Int_ctx

    
`mk_uint32_type(ctx)`
:   mk_uint32_type(Int_ctx ctx) -> Int_type
    
    Parameters
    ----------
    ctx: Int_ctx

    
`mk_uint64_type(ctx)`
:   mk_uint64_type(Int_ctx ctx) -> Int_type
    
    Parameters
    ----------
    ctx: Int_ctx

    
`mk_uint8_type(ctx)`
:   mk_uint8_type(Int_ctx ctx) -> Int_type
    
    Parameters
    ----------
    ctx: Int_ctx

    
`mk_undef(ctx)`
:   mk_undef(Int_ctx ctx) -> Int_net
    
    Parameters
    ----------
    ctx: Int_ctx

    
`mk_xor(ctx, x, y)`
:   mk_xor(Int_ctx ctx, Int_net x, Int_net y) -> Int_net
    
    Parameters
    ----------
    ctx: Int_ctx
    x: Int_net
    y: Int_net

    
`pop_assumption(arg1)`
:   pop_assumption(Int_ctx arg1)
    
    Parameters
    ----------
    arg1: Int_ctx

    
`pop_namespace(ctx)`
:   pop_namespace(Int_ctx ctx)
    
    Parameters
    ----------
    ctx: Int_ctx

    
`prepare_value_for_net(ctx, net)`
:   prepare_value_for_net(Int_ctx ctx, Int_net net) -> unsigned int
    
    Parameters
    ----------
    ctx: Int_ctx
    net: Int_net

    
`push_assumption(arg1, net)`
:   push_assumption(Int_ctx arg1, Int_net net)
    
    Parameters
    ----------
    arg1: Int_ctx
    net: Int_net

    
`push_namespace(ctx, name)`
:   push_namespace(Int_ctx ctx, char const * name)
    
    Parameters
    ----------
    ctx: Int_ctx
    name: char const *

    
`set_bit(arg1, x, bit, y)`
:   set_bit(Int_ctx arg1, Int_net x, unsigned int bit, Int_net y) -> Int_net
    
    Parameters
    ----------
    arg1: Int_ctx
    x: Int_net
    bit: unsigned int
    y: Int_net

    
`set_bmc_allow_targets_at_any_depth(engine)`
:   set_bmc_allow_targets_at_any_depth(Int_engine_bmc engine)
    
    Parameters
    ----------
    engine: Int_engine_bmc

    
`set_bmc_current_depth(engine, depth)`
:   set_bmc_current_depth(Int_engine_bmc engine, unsigned int depth)
    
    Parameters
    ----------
    engine: Int_engine_bmc
    depth: unsigned int

    
`set_bmc_optimize(engine)`
:   set_bmc_optimize(Int_engine_bmc engine)
    
    Parameters
    ----------
    engine: Int_engine_bmc

    
`set_bmc_use_attack_path_axioms(ctx, engine, source, target)`
:   set_bmc_use_attack_path_axioms(Int_ctx ctx, Int_engine_bmc engine, Int_net source, Int_net target)
    
    Parameters
    ----------
    ctx: Int_ctx
    engine: Int_engine_bmc
    source: Int_net
    target: Int_net

    
`set_bmc_use_induction(engine)`
:   set_bmc_use_induction(Int_engine_bmc engine)
    
    Parameters
    ----------
    engine: Int_engine_bmc

    
`set_latch_init_next(ctx, latch, init, next)`
:   set_latch_init_next(Int_ctx ctx, Int_net latch, Int_net init, Int_net next)
    
    Parameters
    ----------
    ctx: Int_ctx
    latch: Int_net
    init: Int_net
    next: Int_net

    
`simulator_add_watch(ctx, simulator, watch)`
:   simulator_add_watch(Int_ctx ctx, Int_simulator simulator, Int_net watch)
    
    Parameters
    ----------
    ctx: Int_ctx
    simulator: Int_simulator
    watch: Int_net

    
`simulator_simulate(simulator, trace, depth)`
:   simulator_simulate(Int_simulator simulator, Int_trace trace, unsigned int depth)
    
    Parameters
    ----------
    simulator: Int_simulator
    trace: Int_trace
    depth: unsigned int

    
`throw_exception(msg)`
:   throw_exception(char const * msg)
    
    Parameters
    ----------
    msg: char const *

    
`trace_get_max_depth(trace)`
:   trace_get_max_depth(Int_trace trace) -> unsigned int
    
    Parameters
    ----------
    trace: Int_trace

    
`trace_get_watched_net(trace, i)`
:   trace_get_watched_net(Int_trace trace, unsigned int i) -> Int_net
    
    Parameters
    ----------
    trace: Int_trace
    i: unsigned int

    
`trace_get_watched_nets_number(trace)`
:   trace_get_watched_nets_number(Int_trace trace) -> unsigned int
    
    Parameters
    ----------
    trace: Int_trace

    
`trace_prepare_value_for_net(ctx, cex, net, depth)`
:   trace_prepare_value_for_net(Int_ctx ctx, Int_trace cex, Int_net net, unsigned int depth) -> unsigned int
    
    Parameters
    ----------
    ctx: Int_ctx
    cex: Int_trace
    net: Int_net
    depth: unsigned int

    
`trace_set_value(ctx, trace, net, depth, value)`
:   trace_set_value(Int_ctx ctx, Int_trace trace, Int_net net, unsigned int depth, char const * value)
    
    Parameters
    ----------
    ctx: Int_ctx
    trace: Int_trace
    net: Int_net
    depth: unsigned int
    value: char const *

    
`value_at(i)`
:   value_at(unsigned int i) -> char
    
    Parameters
    ----------
    i: unsigned int