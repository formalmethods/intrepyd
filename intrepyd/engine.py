"""
This module implements the verification engines
"""

from enum import Enum
import intrepyd as ip
from intrepyd.api import INT_ENGINE_RESULT_REACHABLE,\
                         INT_ENGINE_RESULT_UNKNOWN,\
                         INT_ENGINE_RESULT_UNREACHABLE

class EngineResult(Enum):
    """
    Results from engine's reachability calls
    """
    REACHABLE = INT_ENGINE_RESULT_REACHABLE
    UNREACHABLE = INT_ENGINE_RESULT_UNREACHABLE
    UNKNOWN = INT_ENGINE_RESULT_UNKNOWN

def _api_result_to_engine_result(result):
    if result == INT_ENGINE_RESULT_REACHABLE:
        return EngineResult.REACHABLE
    if result == INT_ENGINE_RESULT_UNREACHABLE:
        return EngineResult.UNREACHABLE
    return EngineResult.UNKNOWN

class Engine:
    """
    Abstract intreface for an Engine
    """

    def __init__(self, ctx):
        self.ctx = ctx
        self.last_result = EngineResult.UNKNOWN

    def add_target(self, net):
        """
        Adds a target to be solved
        """
        raise NotImplementedError('Should have implemented this')

    def reach_targets(self):
        """
        Tries to reach any of the previously added targets
        """
        assert self.can_reach()
        self.last_result = _api_result_to_engine_result(self._reach_targets_impl())
        return self.last_result

    def get_last_reached_targets(self):
        """
        Returns the list of targets that has been reached last
        """
        if self.last_result != EngineResult.REACHABLE:
            return ()
        last_reached_targets_no = self._get_last_reached_targets_number_impl()
        return (self._get_last_reached_target_impl(i) for i in range(last_reached_targets_no))

    def get_last_trace(self):
        """
        Returns the last produced trace
        """
        raise NotImplementedError('Should have implemented this')

    def remove_last_reached_targets(self):
        """
        Removes all the reached targets from the last call from the engine
        """
        return self._remove_last_reached_targets_impl()

    def add_watch(self, net):
        """
        Track the value of net in future traces
        """
        raise NotImplementedError('Should have implemented this')

    def can_reach(self):
        """
        Tells if the engine can reach targets
        """
        raise NotImplementedError('Should have implemented this')

    def can_prove(self):
        """
        Tells if the engine can prove targets to be unreachable
        """
        raise NotImplementedError('Should have implemented this')

    def can_optimize(self):
        """
        Tells if the engine can prove targets to be unreachable
        """
        raise NotImplementedError('Should have implemented this')

    def _reach_targets_impl(self):
        """
        Engine-dependent reachability search for the added targets
        """
        raise NotImplementedError('Should have implemented this')

    def _get_last_reached_targets_number_impl(self):
        """
        Engine-dependent retrieval of last reached targets number
        """
        raise NotImplementedError('Should have implemented this')

    def _get_last_reached_target_impl(self, target):
        """
        Engine-dependent retrieval of last reached targets
        """
        raise NotImplementedError('Should have implemented this')

    def _remove_last_reached_targets_impl(self):
        """
        Engine-dependent removal of last reached targets
        """
        raise NotImplementedError('Should have implemented this')

class Bmc(Engine):
    """
    A Bounded Model Checking engine
    """

    def __init__(self, ctx):
        Engine.__init__(self, ctx)
        self.bmc = ip.api.mk_engine_bmc(self.ctx)
        self._can_prove = False

    def add_target(self, net):
        ip.api.bmc_add_target(self.ctx, self.bmc, net)

    def get_last_trace(self):
        if self.last_result != EngineResult.REACHABLE:
            raise Exception('Cannot get a trace as last result was not REACHABLE')
        target = next(self.get_last_reached_targets())
        cex = ip.api.bmc_get_trace(self.ctx, self.bmc, target)
        return ip.trace.Trace(self.ctx, cex)

    def add_watch(self, net):
        ip.api.bmc_add_watch(self.ctx, self.bmc, net)

    def set_current_depth(self, depth):
        """
        Sets the current depth to use for BMC
        """
        ip.api.set_bmc_current_depth(self.bmc, depth)

    def set_use_induction(self):
        """
        Turn on induction
        """
        self._can_prove = True
        ip.api.set_bmc_use_induction(self.bmc)

    def set_use_attack_path_axioms(self, source, target):
        """
        Tells bmc to apply internally axioms for source and target of an attack
        """
        ip.api.set_bmc_use_attack_path_axioms(self.ctx, self.bmc, source, target)

    def set_allow_targets_at_any_depth(self):
        """
        Looks for counterexamples at any depth, not just the current
        """
        ip.api.set_bmc_allow_targets_at_any_depth(self.bmc)

    def can_reach(self):
        return True

    def can_prove(self):
        return self._can_prove

    def can_optimize(self):
        return False

    def _reach_targets_impl(self):
        return ip.api.bmc_reach_targets(self.bmc)

    def _get_last_reached_targets_number_impl(self):
        return ip.api.bmc_last_reached_targets_number(self.bmc)

    def _get_last_reached_target_impl(self, target):
        return ip.api.bmc_last_reached_target(self.bmc, target)

    def _remove_last_reached_targets_impl(self):
        return ip.api.bmc_remove_last_reached_targets(self.bmc)

class OptimizingBmc(Bmc):
    """
    An Optimizing Bounded Model Checking engine
    """

    def __init__(self, ctx):
        Bmc.__init__(self, ctx)
        ip.api.set_bmc_optimize(self.bmc)

    def can_optimize(self):
        return True

class BackwardReach(Engine):
    """
    A Backward Reachability Model Checking algorithm
    """

    def __init__(self, ctx):
        Engine.__init__(self, ctx)
        self.breach = ip.api.mk_engine_br(self.ctx)

    def add_target(self, net):
        ip.api.br_add_target(self.ctx, self.breach, net)

    def get_last_trace(self):
        if self.last_result != EngineResult.REACHABLE:
            raise Exception('Cannot get a trace as last result was not REACHABLE')
        target = next(self.get_last_reached_targets())
        rawtrace = ip.api.br_get_trace(self.ctx, self.breach, target)
        return ip.trace.Trace(self.ctx, rawtrace)

    def add_watch(self, net):
        ip.api.br_add_watch(self.ctx, self.breach, net)

    def can_reach(self):
        return True

    def can_prove(self):
        return True

    def can_optimize(self):
        return False

    def _reach_targets_impl(self):
        return ip.api.br_reach_targets(self.breach)

    def _get_last_reached_targets_number_impl(self):
        return ip.api.br_last_reached_targets_number(self.breach)

    def _get_last_reached_target_impl(self, target):
        return ip.api.br_last_reached_target(self.breach, target)

    def _remove_last_reached_targets_impl(self):
        return ip.api.br_remove_last_reached_targets(self.breach)


class Pdr(Engine):
    """
    An IC3/PDR engine, on top of z3's Spacer: it can prove targets
    unreachable by finding an inductive invariant, also when k-induction and
    backward reachability cannot; it works best on unbounded integers
    """

    def __init__(self, ctx):
        Engine.__init__(self, ctx)
        self.pdr = ip.api.mk_engine_pdr(self.ctx)

    def add_target(self, net):
        ip.api.pdr_add_target(self.ctx, self.pdr, net)

    def get_last_trace(self):
        if self.last_result != EngineResult.REACHABLE:
            raise Exception('Cannot get a trace as last result was not REACHABLE')
        target = next(self.get_last_reached_targets())
        rawtrace = ip.api.pdr_get_trace(self.ctx, self.pdr, target)
        return ip.trace.Trace(self.ctx, rawtrace)

    def add_watch(self, net):
        ip.api.pdr_add_watch(self.ctx, self.pdr, net)

    def can_reach(self):
        return True

    def can_prove(self):
        return True

    def can_optimize(self):
        return False

    def _reach_targets_impl(self):
        return ip.api.pdr_reach_targets(self.pdr)

    def _get_last_reached_targets_number_impl(self):
        return ip.api.pdr_last_reached_targets_number(self.pdr)

    def _get_last_reached_target_impl(self, target):
        return ip.api.pdr_last_reached_target(self.pdr, target)

    def _remove_last_reached_targets_impl(self):
        return ip.api.pdr_remove_last_reached_targets(self.pdr)
