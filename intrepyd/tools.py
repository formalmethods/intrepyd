
"""
Provides some tools that could be used almost out of the box
"""

import os
import importlib
from pandas import read_csv
import intrepyd.lustre2py.translator as ltr
import intrepyd.iec611312py.translator as itr

def translate_lustre(infilename, topnode, realtype, outmodule='encoding', inttype='int32'):
    """
    Translates a lustre file into intrepyd syntax

    inttype is 'int32' by default, as it always was; 'int' encodes lustre
    int as unbounded integers, its actual semantics, which is often much
    easier for the engines too
    """
    outfilename = outmodule + '.py'
    ltr.translate(infilename, topnode, outfilename, realtype, inttype)
    enc = importlib.import_module(outmodule)
    return enc


def translate_iec61131(infilename, outmodule='encoding'):
    """
    Translates a ST iec61131 file into intrepyd syntax
    """
    outfilename = outmodule + '.py'
    itr.translate(infilename, outfilename)
    enc = importlib.import_module(outmodule)
    return enc


def simulate(ctx, infile, depth, outputs):
    """
    Simulates the design using default values for inputs or by taking
    input values from an existing simulation file
    """
    sim_file = os.path.basename(infile) + '.csv'
    trace = ctx.mk_trace()
    if os.path.isfile(sim_file):
        print('Re-simulating using input values from ' + sim_file)
        sim_data = read_csv(sim_file, index_col=0)
        depth = trace.set_from_dataframe(sim_data, ctx.inputs)
    else:
        print('Simulating using default values into ' + sim_file)
        dpt = 0
        while dpt <= depth:
            for _, net in ctx.inputs.items():
                trace.set_value(net, dpt, ctx.get_default_value(ctx.input2type[net]))
            dpt += 1
    simulator = ctx.mk_simulator()
    for output in outputs:
        simulator.add_watch(output)
    simulator.simulate(trace, depth)
    dataframe = trace.get_as_dataframe(ctx.net2name)
    dataframe.to_csv(sim_file)
    print('Simulation result written to ' + sim_file)
    print(dataframe)
