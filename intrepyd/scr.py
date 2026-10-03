"""
This module implements infrastructure to deal with SCR requirements
"""

import csv
import os.path

def _mk_raising_edge(ctx, edge_net, past_edge_net, past_when):
    n_1 = ctx.mk_not(past_edge_net)
    n_2 = ctx.mk_and(n_1, past_when)
    n_3 = ctx.mk_and(n_2, edge_net)
    return n_3

def _mk_falling_edge(ctx, edge_net, past_edge_net, past_when):
    n_1 = ctx.mk_not(edge_net)
    n_2 = ctx.mk_and(n_1, past_when)
    n_3 = ctx.mk_and(n_2, past_edge_net)
    return n_3

def _mk_row_condition(ctx, inputs, past_inputs, mode_str2mode, modes, past_mode, row, row_number):
    assert len(inputs) == len(past_inputs)
    assert len(row) == len(inputs) + 2

    old_mode_idx = mode_str2mode[row[0]]

    if old_mode_idx is None:
        raise Exception('Cannot find mode:', row[0])

    old_mode_net = modes[old_mode_idx]

    raising_edge = False
    falling_edge = False
    edge_net = None
    past_edge_net = None
    past_when = ctx.mk_eq(old_mode_net, past_mode)

    for i in range(1, len(row) - 1):
        conj = None
        if row[i] == 't':
            conj = past_inputs[i-1]
        elif row[i] == 'f':
            conj = ctx.mk_not(past_inputs[i-1])
        elif row[i] == 'T':
            raising_edge = True
            edge_net = inputs[i-1]
            past_edge_net = past_inputs[i-1]
        elif row[i] == 'F':
            falling_edge = True
            edge_net = inputs[i-1]
            past_edge_net = past_inputs[i-1]
        else:
            pass
        if conj is not None:
            past_when = ctx.mk_and(past_when, conj)

    if edge_net is None or past_edge_net is None:
        raise Exception('Cannot find raising or falling edge in row ' + str(row_number))
    if raising_edge:
        return _mk_raising_edge(ctx, edge_net, past_edge_net, past_when)
    if falling_edge:
        return _mk_falling_edge(ctx, edge_net, past_edge_net, past_when)

    raise Exception('Unreachable location (is apparently reachable)')

def _retrieve_modes_order(ordfilename):
    mode_str2mode = {}
    mode_str2mode_value = {}
    lines = []
    with open(ordfilename, 'r', encoding='utf-8') as ordfile:
        lines = ordfile.readlines()
    i = 0
    for line in lines:
        pair = line.split()
        if len(pair) != 2:
            raise Exception('Parse error at line ' + str(i+1) + ' of ' + ordfilename)
        mode_str2mode[pair[0]] = i
        mode_str2mode_value[pair[0]] = pair[1]
        i += 1
    return mode_str2mode, mode_str2mode_value

def _mk_scr_helper(ctx, csvfilename, mode_str2mode, mode_str2mode_value,\
                   inputs, past_inputs, modes, past_mode):
    first_row = True
    result = past_mode
    row_number = 1
    with open(csvfilename, 'r', encoding='utf-8') as csvfile:
        for row in csv.reader(csvfile, delimiter=','):
            if len(inputs) + 2 != len(row):
                raise Exception(f'Input number mismatch: expected {len(inputs)}, '
                                f'actual {len(row) - 2}')
            if first_row:
                first_row = False
                continue
            row_number += 1
            row_condition = _mk_row_condition(ctx, inputs, past_inputs, mode_str2mode,\
                                              modes, past_mode, row, row_number)
            row_current_mode_str = str(mode_str2mode_value[row[-1]])
            row_current_mode_net = ctx.mk_number(row_current_mode_str, ctx.mk_int8_type())
            if row_current_mode_net is None:
                raise Exception('Cannot find mode:', row[-1])
            result = ctx.mk_ite(row_condition, row_current_mode_net, result)
    return result

def mk_scr(ctx, name, inputs, past_inputs, modes, past_mode):
    """
    Makes an SCR requirement
    """
    if len(inputs) != len(past_inputs):
        raise Exception('Inputs and past inputs differ in size')
    csvfilename = name + '.csv'
    ordfilename = name + '.ord'
    if not os.path.isfile(csvfilename):
        raise Exception('Cannot find ' + csvfilename)
    if not os.path.isfile(ordfilename):
        raise Exception('Cannot find ' + ordfilename)
    mode_str2mode, mode_str2mode_value = _retrieve_modes_order(ordfilename)
    return _mk_scr_helper(ctx, csvfilename, mode_str2mode, mode_str2mode_value,\
                          inputs, past_inputs, modes, past_mode)
