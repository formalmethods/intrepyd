"""
Routines for pseudo-boolean functions
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING
from intrepyd.api import Net

if TYPE_CHECKING:
    from intrepyd.context import Context


def mk_at_most_one(ctx: Context, nets: Sequence[Net]) -> Net:
    """
    Computes "at most one net is true"

    Args:
        ctx: the context to use
        nets: the nets to use
    """
    at_most_one = ctx.mk_true()
    num_nets = len(nets)
    for i in range(num_nets - 1):
        for j in range(i + 1, num_nets):
            conj = ctx.mk_or(ctx.mk_not(nets[i]), ctx.mk_not(nets[j]))
            at_most_one = ctx.mk_and(at_most_one, conj)
    return at_most_one

def mk_at_least_one(ctx: Context, nets: Sequence[Net]) -> Net:
    """
    Computes "at least one net is true"

    Args:
        ctx: the context to use
        nets: the nets to use
    """
    at_least_one = ctx.mk_false()
    num_nets = len(nets)
    for i in range(num_nets):
        at_least_one = ctx.mk_or(at_least_one, nets[i])
    return at_least_one

def mk_exactly_one(ctx: Context, nets: Sequence[Net], name: str) -> Net:
    """
    Computes the pseudo-boolean constraint "exactly one is true".
    Uses the "commander variable" encoding described in
    "Efficient CNF Encoding for Selecting 1 from N Objects"
    by Will Klieber and Gihwon Kwon.

    Args:
        ctx: the context to use
        nets: the list of (Boolean) nets

    Returns:
        a net expressing the constraint "exactly one is true"
    """
    ctx.push_namespace(name)
    result = _mk_exactly_one_cv(ctx, nets)
    ctx.pop_namespace()
    return result

def _mk_exactly_one_cv(ctx: Context, nets: Sequence[Net], k: int = 3,
                       depth: int = 0, n_group: int = 0) -> Net:
    num_nets = len(nets)
    nets_to_process: Sequence[Net] = []
    if num_nets > k:
        # Recursively compute commander variables
        i = 0
        commander_variable = []
        n_group = 0
        while True:
            if i > num_nets:
                break
            group = []
            for j in range(i, min(i + k, num_nets)):
                group.append(nets[j])
            com_var = _mk_exactly_one_cv(ctx, group, k, depth + 1, n_group)
            commander_variable.append(com_var)
            i += k
            n_group += 1
        nets_to_process = commander_variable
    else:
        nets_to_process = nets

    # Encoding happens here
    num_nets = len(nets_to_process)
    com_var = ctx.mk_input("__cv_" + str(depth) + "_" + str(n_group), ctx.mk_boolean_type())
    exactly_one = ctx.mk_true()
    # Type 1 clauses
    at_most_one_true = mk_at_most_one(ctx, nets_to_process)
    exactly_one = ctx.mk_and(exactly_one, at_most_one_true)
    # Type 2 clauses
    cv_true_then_at_least_one_true = ctx.mk_not(com_var)
    for i in range(num_nets):
        cv_true_then_at_least_one_true = \
          ctx.mk_or(cv_true_then_at_least_one_true, nets_to_process[i])
    exactly_one = ctx.mk_and(exactly_one, cv_true_then_at_least_one_true)
    # Type 3 clauses
    cv_false_then_all_false = ctx.mk_true()
    for i in range(num_nets):
        conj = ctx.mk_or(com_var, ctx.mk_not(nets_to_process[i]))
        cv_false_then_all_false = ctx.mk_and(cv_false_then_all_false, conj)
    exactly_one = ctx.mk_and(exactly_one, cv_false_then_all_false)
    # Type 4 clauses
    if depth == 0:
        at_most_one_true = mk_at_most_one(ctx, nets_to_process)
        at_least_one_true = mk_at_least_one(ctx, nets_to_process)
        exactly_one = ctx.mk_and(exactly_one, at_most_one_true)
        exactly_one = ctx.mk_and(exactly_one, at_least_one_true)
    return exactly_one
