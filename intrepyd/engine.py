"""
This module implements the verification engines
"""

from __future__ import annotations

from collections.abc import Iterable
from enum import Enum
from typing import TYPE_CHECKING
import intrepyd as ip
from intrepyd.api import Net, INT_ENGINE_RESULT_REACHABLE,\
                         INT_ENGINE_RESULT_UNKNOWN,\
                         INT_ENGINE_RESULT_UNREACHABLE

if TYPE_CHECKING:
    from intrepyd.trace import Trace

class EngineResult(Enum):
    """
    Results from engine's reachability calls
    """
    REACHABLE = INT_ENGINE_RESULT_REACHABLE
    UNREACHABLE = INT_ENGINE_RESULT_UNREACHABLE
    UNKNOWN = INT_ENGINE_RESULT_UNKNOWN

def _api_result_to_engine_result(result: int) -> EngineResult:
    if result == INT_ENGINE_RESULT_REACHABLE:
        return EngineResult.REACHABLE
    if result == INT_ENGINE_RESULT_UNREACHABLE:
        return EngineResult.UNREACHABLE
    return EngineResult.UNKNOWN

class Engine:
    """
    Abstract intreface for an Engine
    """

    def __init__(self, ctx: int) -> None:
        self.ctx = ctx
        self.last_result = EngineResult.UNKNOWN

    def add_target(self, net: Net) -> None:
        """
        Adds a target to be solved
        """
        raise NotImplementedError('Should have implemented this')

    def reach_targets(self) -> EngineResult:
        """
        Tries to reach any of the previously added targets
        """
        assert self.can_reach()
        self.last_result = _api_result_to_engine_result(self._reach_targets_impl())
        return self.last_result

    def get_last_reached_targets(self) -> Iterable[Net]:
        """
        Returns the list of targets that has been reached last
        """
        if self.last_result != EngineResult.REACHABLE:
            return ()
        last_reached_targets_no = self._get_last_reached_targets_number_impl()
        return (self._get_last_reached_target_impl(i) for i in range(last_reached_targets_no))

    def get_last_trace(self) -> Trace:
        """
        Returns the last produced trace
        """
        raise NotImplementedError('Should have implemented this')

    def remove_last_reached_targets(self) -> None:
        """
        Removes all the reached targets from the last call from the engine
        """
        return self._remove_last_reached_targets_impl()

    def add_watch(self, net: Net) -> None:
        """
        Track the value of net in future traces
        """
        raise NotImplementedError('Should have implemented this')

    def set_produce_certificates(self) -> None:
        """
        Makes an UNREACHABLE answer come with a proof certificate, which
        get_last_certificate() returns: an SMT-LIB 2 script, each of whose
        check-sat must answer unsat, that any SMT solver can run to check the
        proof (z3 FILE, cvc5 FILE, ...). The library checks it first, with a
        solver of its own: a certificate that does not hold turns the answer
        into UNKNOWN. Needs intrepid 1.4 or newer.
        """
        self._set_produce_certificates_impl()

    def get_last_certificate(self) -> str | None:
        """
        Returns the proof certificate of the last answer, if it was
        UNREACHABLE and certificates were asked for (set_produce_certificates),
        as SMT-LIB 2 text; None otherwise
        """
        if self.last_result != EngineResult.UNREACHABLE:
            return None
        return self._get_last_certificate_impl()

    def can_reach(self) -> bool:
        """
        Tells if the engine can reach targets
        """
        raise NotImplementedError('Should have implemented this')

    def can_prove(self) -> bool:
        """
        Tells if the engine can prove targets to be unreachable
        """
        raise NotImplementedError('Should have implemented this')

    def can_optimize(self) -> bool:
        """
        Tells if the engine can prove targets to be unreachable
        """
        raise NotImplementedError('Should have implemented this')

    def _reach_targets_impl(self) -> int:
        """
        Engine-dependent reachability search for the added targets
        """
        raise NotImplementedError('Should have implemented this')

    def _get_last_reached_targets_number_impl(self) -> int:
        """
        Engine-dependent retrieval of last reached targets number
        """
        raise NotImplementedError('Should have implemented this')

    def _get_last_reached_target_impl(self, target: int) -> Net:
        """
        Engine-dependent retrieval of last reached targets
        """
        raise NotImplementedError('Should have implemented this')

    def _remove_last_reached_targets_impl(self) -> None:
        """
        Engine-dependent removal of last reached targets
        """
        raise NotImplementedError('Should have implemented this')

    def _set_produce_certificates_impl(self) -> None:
        """
        Engine-dependent request of proof certificates
        """
        raise NotImplementedError('Should have implemented this')

    def _get_last_certificate_impl(self) -> str | None:
        """
        Engine-dependent retrieval of the last proof certificate
        """
        raise NotImplementedError('Should have implemented this')

class Bmc(Engine):
    """
    A Bounded Model Checking engine
    """

    def __init__(self, ctx: int) -> None:
        Engine.__init__(self, ctx)
        self.bmc = ip.api.mk_engine_bmc(self.ctx)
        self._can_prove = False

    def add_target(self, net: Net) -> None:
        ip.api.bmc_add_target(self.ctx, self.bmc, net)

    def get_last_trace(self) -> Trace:
        if self.last_result != EngineResult.REACHABLE:
            raise Exception('Cannot get a trace as last result was not REACHABLE')
        target = next(iter(self.get_last_reached_targets()))
        cex = ip.api.bmc_get_trace(self.ctx, self.bmc, target)
        return ip.trace.Trace(self.ctx, cex)

    def add_watch(self, net: Net) -> None:
        ip.api.bmc_add_watch(self.ctx, self.bmc, net)

    def set_current_depth(self, depth: int) -> None:
        """
        Sets the current depth to use for BMC
        """
        ip.api.set_bmc_current_depth(self.bmc, depth)

    def set_use_induction(self) -> None:
        """
        Turn on induction
        """
        self._can_prove = True
        ip.api.set_bmc_use_induction(self.bmc)

    def set_use_attack_path_axioms(self, source: Net, target: Net) -> None:
        """
        Tells bmc to apply internally axioms for source and target of an attack
        """
        ip.api.set_bmc_use_attack_path_axioms(self.ctx, self.bmc, source, target)

    def set_allow_targets_at_any_depth(self) -> None:
        """
        Looks for counterexamples at any depth, not just the current
        """
        ip.api.set_bmc_allow_targets_at_any_depth(self.bmc)

    def can_reach(self) -> bool:
        return True

    def can_prove(self) -> bool:
        return self._can_prove

    def can_optimize(self) -> bool:
        return False

    def _reach_targets_impl(self) -> int:
        return ip.api.bmc_reach_targets(self.bmc)

    def _get_last_reached_targets_number_impl(self) -> int:
        return ip.api.bmc_last_reached_targets_number(self.bmc)

    def _get_last_reached_target_impl(self, target: int) -> Net:
        return ip.api.bmc_last_reached_target(self.bmc, target)

    def _remove_last_reached_targets_impl(self) -> None:
        return ip.api.bmc_remove_last_reached_targets(self.bmc)

    def _set_produce_certificates_impl(self) -> None:
        ip.api.set_bmc_produce_certificates(self.bmc)

    def _get_last_certificate_impl(self) -> str | None:
        return ip.api.bmc_get_certificate(self.bmc)

class OptimizingBmc(Bmc):
    """
    An Optimizing Bounded Model Checking engine
    """

    def __init__(self, ctx: int) -> None:
        Bmc.__init__(self, ctx)
        ip.api.set_bmc_optimize(self.bmc)

    def can_optimize(self) -> bool:
        return True

class BackwardReach(Engine):
    """
    A Backward Reachability Model Checking algorithm
    """

    def __init__(self, ctx: int) -> None:
        Engine.__init__(self, ctx)
        self.breach = ip.api.mk_engine_br(self.ctx)

    def add_target(self, net: Net) -> None:
        ip.api.br_add_target(self.ctx, self.breach, net)

    def get_last_trace(self) -> Trace:
        if self.last_result != EngineResult.REACHABLE:
            raise Exception('Cannot get a trace as last result was not REACHABLE')
        target = next(iter(self.get_last_reached_targets()))
        rawtrace = ip.api.br_get_trace(self.ctx, self.breach, target)
        return ip.trace.Trace(self.ctx, rawtrace)

    def add_watch(self, net: Net) -> None:
        ip.api.br_add_watch(self.ctx, self.breach, net)

    def can_reach(self) -> bool:
        return True

    def can_prove(self) -> bool:
        return True

    def can_optimize(self) -> bool:
        return False

    def _reach_targets_impl(self) -> int:
        return ip.api.br_reach_targets(self.breach)

    def _get_last_reached_targets_number_impl(self) -> int:
        return ip.api.br_last_reached_targets_number(self.breach)

    def _get_last_reached_target_impl(self, target: int) -> Net:
        return ip.api.br_last_reached_target(self.breach, target)

    def _remove_last_reached_targets_impl(self) -> None:
        return ip.api.br_remove_last_reached_targets(self.breach)

    def _set_produce_certificates_impl(self) -> None:
        ip.api.set_br_produce_certificates(self.breach)

    def _get_last_certificate_impl(self) -> str | None:
        return ip.api.br_get_certificate(self.breach)


class Pdr(Engine):
    """
    An IC3/PDR engine, on top of z3's Spacer: it can prove targets
    unreachable by finding an inductive invariant, also when k-induction and
    backward reachability cannot; it works best on unbounded integers
    """

    def __init__(self, ctx: int) -> None:
        Engine.__init__(self, ctx)
        self.pdr = ip.api.mk_engine_pdr(self.ctx)

    def add_target(self, net: Net) -> None:
        ip.api.pdr_add_target(self.ctx, self.pdr, net)

    def get_last_trace(self) -> Trace:
        if self.last_result != EngineResult.REACHABLE:
            raise Exception('Cannot get a trace as last result was not REACHABLE')
        target = next(iter(self.get_last_reached_targets()))
        rawtrace = ip.api.pdr_get_trace(self.ctx, self.pdr, target)
        return ip.trace.Trace(self.ctx, rawtrace)

    def add_watch(self, net: Net) -> None:
        ip.api.pdr_add_watch(self.ctx, self.pdr, net)

    def can_reach(self) -> bool:
        return True

    def can_prove(self) -> bool:
        return True

    def can_optimize(self) -> bool:
        return False

    def _reach_targets_impl(self) -> int:
        return ip.api.pdr_reach_targets(self.pdr)

    def _get_last_reached_targets_number_impl(self) -> int:
        return ip.api.pdr_last_reached_targets_number(self.pdr)

    def _get_last_reached_target_impl(self, target: int) -> Net:
        return ip.api.pdr_last_reached_target(self.pdr, target)

    def _remove_last_reached_targets_impl(self) -> None:
        return ip.api.pdr_remove_last_reached_targets(self.pdr)

    def _set_produce_certificates_impl(self) -> None:
        ip.api.set_pdr_produce_certificates(self.pdr)

    def _get_last_certificate_impl(self) -> str | None:
        return ip.api.pdr_get_certificate(self.pdr)
