import intrepyd as ip
import intrepyd.api
import intrepyd.engine
import collections

class Context(object):
    """
    An intrepid context
    """
    def __init__(self):
       self.ctx = ip.api.mk_ctx()
       self.inputs = collections.OrderedDict()
       self.outputs = collections.OrderedDict()
       self.latches = {}
       self.nets = {}
       self.booleantype = ip.api.mk_boolean_type(self.ctx)
       self.int8type = ip.api.mk_int8_type(self.ctx)
       self.int16type = ip.api.mk_int16_type(self.ctx)
       self.int32type = ip.api.mk_int32_type(self.ctx)
       self.uint8type = ip.api.mk_uint8_type(self.ctx)
       self.uint16type = ip.api.mk_uint16_type(self.ctx)
       self.uint32type = ip.api.mk_uint32_type(self.ctx)
       self.realtype = ip.api.mk_real_type(self.ctx)
       self.doubletype = ip.api.mk_double_type(self.ctx)
       self.undef = ip.api.mk_undef(self.ctx)
       self.true = ip.api.mk_true(self.ctx)
       self.false = ip.api.mk_false(self.ctx)

    def __del__(self):
        ip.api.del_ctx(self.ctx)

    def mk_boolean_type(self):
       return self.booleantype

    def mk_int8_type(self):
        return self.int8type

    def mk_int16_type(self):
        return self.int16type

    def mk_int32_type(self):
        return self.int32type

    def mk_uint8_type(self):
        return self.uint8type

    def mk_uint16_type(self):
        return self.uint16type

    def mk_uint32_type(self):
        return self.uint32type

    def mk_real_type(self):
        return self.realtype

    def mk_double_type(self):
        return self.doubletype

    def mk_undef(self):
        return self.undef

    def mk_true(self, name=None):
        return self._register(self.true, name)

    def mk_false(self, name=None):
        return self._register(self.false, name)

    def mk_number(self, value, type_, name=None):
        return self._register(ip.api.mk_number(self.ctx, value, type_), name)

    def mk_not(self, x, name=None):
        return self._register(ip.api.mk_not(self.ctx, x), name=name)

    def mk_and(self, x, y, name=None):
        return self._register(ip.api.mk_and(self.ctx, x, y), name=name)

    def mk_or(self, x, y, name=None):
        return self._register(ip.api.mk_or(self.ctx, x, y), name=name)

    def mk_xor(self, x, y, name=None):
        return self._register(ip.api.mk_xor(self.ctx, x, y), name=name)

    def mk_iff(self, x, y, name=None):
        return self._register(ip.api.mk_iff(self.ctx, x, y), name=name)

    def mk_eq(self, x, y, name=None):
        return self._register(ip.api.mk_eq(self.ctx, x, y), name=name)

    def mk_leq(self, x, y, name=None):
        return self._register(ip.api.mk_leq(self.ctx, x, y), name=name)

    def mk_lt(self, x, y, name=None):
        return self._register(ip.api.mk_lt(self.ctx, x, y), name=name)

    def mk_geq(self, x, y, name=None):
        return self._register(ip.api.mk_geq(self.ctx, x, y), name=name)

    def mk_gt(self, x, y, name=None):
        return self._register(ip.api.mk_gt(self.ctx, x, y), name=name)

    def mk_neq(self, x, y, name=None):
        return self._register(ip.api.mk_neq(self.ctx, x, y), name=name)

    def mk_add(self, x, y, name=None):
        return self._register(ip.api.mk_add(self.ctx, x, y), name=name)

    def mk_mul(self, x, y, name=None):
        return self._register(ip.api.mk_mul(self.ctx, x, y), name=name)

    def mk_sub(self, x, y, name=None):
        return self._register(ip.api.mk_sub(self.ctx, x, y), name=name)

    def mk_minus(self, x, name=None):
        return self._register(ip.api.mk_minus(self.ctx, x), name=name)

    def mk_ite(self, i, t, e, name=None):
        return self._register(ip.api.mk_ite(self.ctx, i, t, e), name=name)

    def mk_input(self, name, type_):
        return self._register_input(ip.api.mk_input(self.ctx, name, type_), name=name)

    def mk_output(self, x, name=None):
        self._register_output(ip.api.mk_output(self.ctx, x), name=name)

    def mk_latch(self, name, type_):
        return self._register_latch(ip.api.mk_latch(self.ctx, name, type_), name=name)

    def set_latch_init_next(self, latch, init, next):
        ip.api.set_latch_init_next(self.ctx, latch, init, next)

    def mk_substitute(self, term, newTerm, oldTerm):
        return ip.api.mk_substitute(self.ctx, term, newTerm, oldTerm)

    def mk_assumption(self, net):
        ip.api.mk_assumption(self.ctx, net)

    def mk_bmc(self):
        return ip.engine.Bmc(self.ctx)

    def mk_backward_reach(self):
        return ip.engine.BackwardReach(self.ctx)

    def to_string(ctx, net):
        """
        Returns the given net as a string, as given from the underlying smt-solver.
        """
        size = ip.api.prepare_value_for_net(ctx, net)
        value = ''
        for i in range(size):
            value += ip.api.value_at(i)
        return value

    def _register(self, rawnet, name):
        if name in self.nets:
            raise Exception('Name already used: ' + name)
        self.nets[name] = rawnet
        return rawnet

    def _register_input(self, rawnet, name):
        name = self._register(rawnet, name)
        self.inputs[name] = rawnet
        return rawnet

    def _register_latch(self, rawnet, name):
        name = self._register(rawnet, rawtype, name)
        self.latches[name] = rawnet
        return rawnet

    def _register_output(self, rawnet, name):
        if name == None:
            name = '__o' + str(rawnet)
        name = self._register(rawnet, name)
        self.outputs[name] = rawnet