
"""
Provides some tools that could be used almost out of the box
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
import os
import importlib
from types import ModuleType
from typing import TYPE_CHECKING
from pandas import read_csv
from intrepyd.api import Net
import intrepyd.lustre2py.translator as ltr
import intrepyd.iec611312py.translator as itr
import intrepyd.simulink as sml

if TYPE_CHECKING:
    from intrepyd.context import Context

def translate_lustre(infilename: str, topnode: str, realtype: str,
                     outmodule: str = 'encoding', inttype: str = 'int32') -> ModuleType:
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


def translate_simulink(infilename: str, outmodule: str = 'encoding', realtype: str = 'float',
                       variables: Mapping[str, str] | None = None,
                       scripts: Sequence[str] | None = None, mats: Sequence[str] | None = None,
                       callbacks: bool = True) -> ModuleType:
    """
    Translates a Simulink model, a .mdl or a .slx file, into intrepyd syntax

    The circuit of the module has the root Inport and Outport blocks of the
    model as inputs and outputs, and as targets its Assertion blocks, reached
    when an assertion fails, and the errors that would stop a simulation of
    its Stateflow charts (a division by zero, a state inconsistency, a
    conversion out of range). realtype is 'float' (single and double as
    floats, exactly) or 'real' (as reals, which is not exact). The MATLAB
    workspace the model refers to is filled by the callbacks of the model,
    unless callbacks is False, then by the MAT files in mats, the MATLAB
    scripts in scripts, and the variables, a dictionary of MATLAB
    expressions. Raises intrepyd.simulink.SimulinkError, listing the blocks
    that cannot be translated, if the model cannot be. Needs the Simulink
    front-end library, see intrepyd.simulink.
    """
    python = sml.translate_file(infilename, realtype, variables, scripts, mats, callbacks)
    outfilename = outmodule + '.py'
    with open(outfilename, 'w', encoding='utf-8') as outfile:
        outfile.write(python)
    importlib.invalidate_caches()
    enc = importlib.import_module(outmodule)
    return enc


def translate_iec61131(infilename: str, outmodule: str = 'encoding') -> ModuleType:
    """
    Translates a ST iec61131 file into intrepyd syntax
    """
    outfilename = outmodule + '.py'
    itr.translate(infilename, outfilename)
    enc = importlib.import_module(outmodule)
    return enc


def simulate(ctx: Context, infile: str, depth: int, outputs: Iterable[Net]) -> None:
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
