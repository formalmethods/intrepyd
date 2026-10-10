"""
Automated Test Generation for MC/DC (Modified Condition / Decision Coverage).

MC/DC asks, for every **decision** (a boolean expression) and each of its
**conditions** (the atomic boolean sub-expressions), for a pair of tests that
show the condition *independently* flips the decision: the two tests differ in
that one condition, agree on the others, and the decision differs between them.
Such a pair is an *independence pair*, and the generated table collects one per
condition.

The circuit is given as a subclass of :class:`intrepyd.circuit.Circuit` (the
same class the translators use). ``compute_mcdc`` builds it twice in the same
context, as instances ``InstA`` and ``InstB`` under their own namespaces, and
looks up the decision and condition nets by name in each instance's ``nets``
dictionary — so the circuit must register, in ``self.nets``, every net named by
``decisions``. See the documentation and ``tests/test_atg.py`` for an example.
"""

import pandas as pd
from intrepyd.engine import EngineResult

def compute_mcdc(context, class_, decisions, max_depth):
    """
    Computes MC/DC tests in the form of a table, one per decision.

    Args:
        context: the intrepyd context to use
        class_ (class): a subclass of :class:`intrepyd.circuit.Circuit` that
                    builds the circuit and registers every decision and
                    condition net, by name, in ``self.nets``
        decisions (Dictionary): maps each decision to its conditions, all by
                    net name (the names used as keys in the circuit's ``nets``)::

                { decisionName : [conditionName, ...] }

        max_depth (int): the maximum BMC depth to search for each test

    Returns:
        a triple ``(tables, independence_pairs, unreachable)``: the raw MC/DC
        table per decision, the independence pair (two test indices) per
        condition, and the conditions whose objective is unreachable
    """

    # Fetches and duplicates the circuit, each under its own namespace
    inst_a = class_(context, 'InstA')
    inst_b = class_(context, 'InstB')
    inst_a.mk_circuit(put_namespace=True)
    inst_b.mk_circuit(put_namespace=True)

    # Creates test objectives
    decision2testobjectives = {decision :\
            compute_mcdc_targets(context, inst_a, inst_b, decision, conditions)\
            for decision, conditions in decisions.items()}

    # Compute MC/DC traces: this is the computationally
    # expensive part that calls model checking routines
    decision2traces, trace2condition, decision2unreachable =\
            solve_mcdc_targets(context, decision2testobjectives, decisions, max_depth)

    # Compute MC/DC tables from traces
    decision2table, decision2independencepairs =\
            compute_mcdc_tables(context, inst_a, inst_b,\
                                decision2traces, trace2condition, decisions)

    return decision2table, decision2independencepairs, decision2unreachable


def compute_mcdc_targets(context, inst_a, inst_b, decision, conditions):
    """
    Computes the MC/DC reachability target for the
    two copies of the circuit.

    Args:
        context: the intrepyd context to use
        inst_a: an instance of the circuit
        inst_b: an instance of the circuit
        decision: the name of a decision
        conditions: the list of names of the conditions

    Returns:
        a map from targets to conditions for which target is an independence pair
    """
    decision_a = inst_a.nets[decision]
    decision_b = inst_b.nets[decision]
    decisiona_diff_decisionb = context.mk_neq(decision_a, decision_b)

    conditiona_neq_conditionb = []
    conditions_a = []
    conditions_b = []
    for condition in conditions:
        condition_a = inst_a.nets[condition]
        conditions_a.append(condition_a)
        condition_b = inst_b.nets[condition]
        conditions_b.append(condition_b)
        conditiona_neq_conditionb.append(context.mk_neq(condition_a, condition_b))

    targets = {}
    for i in range(len(conditions)):
        # Building test objective for the i-th condition
        condition_a = conditions_a[i]
        condition_b = conditions_b[i]
        # i-th condition must differ in A and B
        conj1 = conditiona_neq_conditionb[i]
        # test objective must differ in A and B
        conj2 = decisiona_diff_decisionb
        # decisionA[not(cA)/cA] != decisionA
        not_condition_a = context.mk_not(condition_a)
        decisiona_not_ca = context.mk_substitute(decision_a, not_condition_a, condition_a)
        conj3 = context.mk_neq(decisiona_not_ca, decision_a)
        # decisionB[not(cB)/cB] != decisionB
        not_condition_b = context.mk_not(condition_b)
        decisiona_not_cb = context.mk_substitute(decision_b, not_condition_b, condition_b)
        conj4 = context.mk_neq(decisiona_not_cb, decision_b)
        # Creates final conjunction
        tmp1 = context.mk_and(conj1, conj2)
        tmp2 = context.mk_and(tmp1, conj3)
        target = context.mk_and(tmp2, conj4)
        targets[target] = i

    return targets


def solve_mcdc_targets(context, decision2testobjectives, decisions, max_depth):
    """
    Solves the MC/DC targets, maximizing the number of solved
    test objectives per each call.
    """
    # Bmc engine will be used to compute counterexamples
    bmc = context.mk_optimizing_bmc()

    testobjectives2decision = {}
    testobjectives2condition = {}
    decision2traces = {}
    decision2unreachable = {}
    targets = []
    for decision, tos in decision2testobjectives.items():
        decision2traces[decision] = []
        decision2unreachable[decision] = []
        for test_objective, condition in tos.items():
            testobjectives2decision[test_objective] = decision
            testobjectives2condition[test_objective] = condition
            targets.append(test_objective)
    assert len(testobjectives2decision) == len(testobjectives2condition)
    total_targets = len(targets)

    # Compute unreachable targets first
    total_unreached = 0
    total_reached = 0
    for target in targets:
        breach = context.mk_backward_reach()
        breach.add_target(target)
        result = breach.reach_targets()
        if result == EngineResult.UNREACHABLE:
            decision = testobjectives2decision[target]
            condition = decision2testobjectives[decision][target]
            condition = decisions[decision][condition]
            decision2unreachable[decision].append(condition)

            total_unreached += 1
        elif result == EngineResult.REACHABLE:
            bmc.add_target(target)
            total_reached += 1

    # print('There are', totalTargets, 'test objectives:')
    # print('-', totalUnreached, 'unreachable test objectives')
    # print('-', totalReached, 'reachable test objectives')
    trace2condition = {}

    if total_unreached == total_targets:
        return decision2traces, trace2condition, decision2unreachable

    # Compute counterexamples for reachable targets
    done = False
    depth = 0
    bmc_total_reached = 0
    while not done:
        bmc.set_current_depth(depth)
        result = bmc.reach_targets()
        if result != EngineResult.REACHABLE:
            if depth == max_depth:
                done = True
            depth += 1
            continue
        reached = bmc.get_last_reached_targets()
        trace = bmc.get_last_trace()
        for reached_target in reached:
            decision = testobjectives2decision[reached_target]
            decision2traces[decision].append(trace)
            trace2condition[trace] = testobjectives2condition[reached_target]
            bmc_total_reached += 1
        bmc.remove_last_reached_targets()
        if bmc_total_reached == total_reached:
            done = True

    total_undecided = total_reached - bmc_total_reached
    if total_undecided != 0:
        print('There are', total_undecided, 'undecided test objectives within depth', max_depth)

    return decision2traces, trace2condition, decision2unreachable


def compute_mcdc_tables(context, inst_a, inst_b, decision2traces, trace2condition, decisions):
    """
    Computes MC/DC tables out of counterexamples.
    """
    decision2table = {}
    decision2independencepairs = {}
    seen = {}
    for decision, traces in decision2traces.items():
        inst_a_conds_dec =\
          [inst_a.nets[cond] for cond in decisions[decision]] + [inst_a.nets[decision]]
        inst_a_testnets =\
          list(inst_a.inputs.values()) + inst_a_conds_dec
        inst_b_conds_dec =\
          [inst_b.nets[cond] for cond in decisions[decision]] + [inst_b.nets[decision]]
        inst_b_testnets = list(inst_b.inputs.values()) + inst_b_conds_dec
        # the header is the condition names plus the decision; build a new list
        # so the caller's decisions dict is not mutated
        header = list(decisions[decision]) + [decision]
        header_nets_a = set(inst_a_conds_dec)
        # Enable this to include inputs in the tests (but you need to add also names in headers)
        # header_nets_a = set(inst_a_testnets)
        header_nets_b = set(inst_b_conds_dec)
        # Enable this to include inputs in the tests (but you need to add also names in headers)
        # header_nets_b = set(inst_b_testnets)
        decision2table[decision] = [header]
        decision2independencepairs[decision] = {}
        test_number = 0
        for trace in traces:
            test_a_number = None
            test_b_number = None
            # Enrich the traces with the value of the output
            # by performing a simulation
            simulator = context.mk_simulator()
            for net in inst_a_testnets:
                simulator.add_watch(net)
            for net in inst_b_testnets:
                simulator.add_watch(net)
            simulator.simulate(trace, trace.get_max_depth())
            full_test_a = trace.get_as_net_dictionary()
            full_test_b = trace.get_as_net_dictionary()
            test_a_candidate = [v[0] for k, v in full_test_a.items()\
                                  if (k in inst_a_testnets and k in header_nets_a)]
            test_b_candidate = [v[0] for k, v in full_test_b.items()\
                                  if (k in inst_b_testnets and k in header_nets_b)]
            test_a_hash = compute_hash(test_a_candidate)
            test_b_hash = compute_hash(test_b_candidate)

            if test_a_hash in seen:
                _, test_a_number = seen[test_a_hash]
            else:
                seen[test_a_hash] = (test_a_candidate, test_number)
                decision2table[decision].append(test_a_candidate)
                test_a_number = test_number
                test_number += 1

            if test_b_hash in seen:
                _, test_b_number = seen[test_b_hash]
            else:
                seen[test_b_hash] = (test_b_candidate, test_number)
                decision2table[decision].append(test_b_candidate)
                test_b_number = test_number
                test_number += 1

            condition = trace2condition[trace]
            condition = decisions[decision][condition]
            decision2independencepairs[decision][condition] = (test_a_number, test_b_number)
    return decision2table, decision2independencepairs


def compute_hash(test):
    """
    Computes a unique hash for a test
    """
    result = ""
    for val in test:
        result += val
    return result


def compute_pretty_tables(decision2table):
    """
    Postprocess raw MC/DC tables to get something presentation ready.
    """
    decision2prettytable = {}
    first = True
    for decision, table in decision2table.items():
        pretty_table = []
        for row in table:
            if first:
                first = False
                pretty_table.append(row)
            else:
                pretty_table.append(row[0])
                pretty_table.append(row[1])
        decision2prettytable[decision] = pretty_table
    return decision2prettytable


def get_tables_as_dataframe(decision2table):
    """
    Postprocess table to turn into a dataframe
    """
    result = {}
    for decision, table in decision2table.items():
        if len(table) == 1:
            continue
        dataframe = pd.DataFrame(table[1:], columns=table[0])
        dataframe = dataframe.drop_duplicates()
        result[decision] = dataframe
    return result
