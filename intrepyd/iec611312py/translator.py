"""
Implementation of translation from OpenPLC to py
"""

import datetime
import sys
from intrepyd.iec611312py.plcopen import parse_plc_open_file
from intrepyd.iec611312py.flattener import Flattener
from intrepyd.iec611312py.flatstmt2intrepyd import FlatStmt2Intrepyd
from intrepyd.iec611312py.inferdatatype import InferDatatypeBottomUp, InferDatatypeTopDown
from intrepyd.iec611312py.datatype import Datatype
from . utils import sanitize_name

TAB = 4 * ' '
FIRSTTICK = 'first_tick'
CONTEXT = 'self.context'

def flush():
    """
    Flushes stdout
    """
    sys.stdout.flush()

def translate(filename, outfilename):
    """
    Translates an openPLC ST file into intrepyd
    """
    print('Parsing')
    pous = parse_plc_open_file(filename)
    print('... done')
    flush()
    with open(outfilename, 'w', encoding='utf-8') as outfile:
        top_level = True
        for pou in pous:
            name2var = {var.name: var for var in pou.input_vars +
                        pou.local_vars + pou.output_vars}
            if top_level:
                _dump_header(pou, name2var, filename, outfile)
            _translate_pou(pou, name2var, outfile)
            top_level = False
        _dump_footer(outfile)

def _translate_pou(pou, name2var, outfile):
    print('Translating POU', pou.dtname)

    print('Flattening')
    flattener = Flattener()
    flattened_statements = flattener.flatten_stmt_block(pou.statements)
    print('... done')
    flush()

    print('Inferring datatypes bottom up')
    idbu = InferDatatypeBottomUp()
    idbu.process_statements(flattened_statements)
    print('... done')
    flush()

    print('Inferring datatypes top down')
    idtd = InferDatatypeTopDown()
    idtd.process_statements(flattened_statements)
    print('... done')
    flush()

    #
    # Prepare the formal arguments of the main function
    #
    args = ''
    sep = ''
    for var in pou.input_vars:
        if not Datatype.is_primitive(var.datatype.dtname):
            for name, _ in var.datatype.fields.items():
                args += sep + sanitize_name(var.name + '.' + name)
                sep = ', '
        else:
            args += sep + var.name
            sep = ', '
    #
    # Function declaration
    #
    outfile.write(
        TAB + 'def ' + pou.dtname + '(self, ' + args + '):\n')
    flush()
    var2latch = {}
    for var in pou.local_vars:
        _declare_local(var, outfile, var2latch, name2var)
    for var in pou.output_vars:
        _declare_output(var, outfile, name2var)
    flush()
    print('  Writing statements')
    flatstmt2intrepyd = FlatStmt2Intrepyd(8, CONTEXT, var2latch, outfile)
    flatstmt2intrepyd.process_statements(flattened_statements)
    print('  ... done')
    flush()
    sep = ''
    outs = ''
    if len(pou.output_vars) == 0:
        raise RuntimeError('Pou has no outputs')
    print('  Writing outputs')
    for out in pou.output_vars:
        if not Datatype.is_primitive(out.datatype.dtname):
            for name, _ in out.datatype.fields.items():
                qualified_name = out.name + '.' + name
                outs += sep + sanitize_name(qualified_name)
                sep = ', '
        else:
            outs += sep + out.name
            sep = ', '
    print('  ... done')
    flush()
    outfile.write(TAB + TAB + 'return ' + outs)
    outfile.write('\n\n')


def _dump_header(pou, name2var, filename, outfile):
    today = str(datetime.date.today())
    outfile.write('# Translated from ' + filename +
                  ' using intrepyd.iec611312py on ' + today)
    outfile.write('\n\n')
    outfile.write('import intrepyd as ip\n')
    outfile.write('import intrepyd.circuit\n')
    outfile.write('class IEC61131Circuit(ip.circuit.Circuit):\n')
    outfile.write(TAB + 'def __init__(self, ctx, name):\n')
    outfile.write(
        TAB + TAB + 'ip.circuit.Circuit.__init__(self, ctx, name)\n')
    outfile.write(TAB + TAB + 'bool_type = ' +
                  CONTEXT + '.mk_boolean_type()\n')
    outfile.write(TAB + TAB + FIRSTTICK + ' = ' + CONTEXT +
                  '.mk_latch("' + FIRSTTICK + '", bool_type)\n')
    outfile.write(TAB + TAB + CONTEXT +
                  '.set_latch_init_next(' + FIRSTTICK + ', ' +
                  CONTEXT + '.mk_true(), ' + CONTEXT + '.mk_false())\n')
    outfile.write('\n')
    outfile.write(TAB + 'def _mk_inputs(self):\n')
    for inp in pou.input_vars:
        _declare_input(inp, outfile, name2var)
    if len(pou.input_vars) == 0:
        outfile.write(TAB + TAB + 'pass\n')
    outfile.write('\n')
    outfile.write(TAB + 'def _mk_naked_circuit_impl(self, inputs):\n')
    outfile.write(TAB + TAB + 'input_keys = list(inputs)\n')
    #
    # Prepare input keys that are actual arguments of main function
    #
    args = ''
    sep = ''
    i = 0
    for var in pou.input_vars:
        if not Datatype.is_primitive(var.datatype.dtname):
            for _, _ in var.datatype.fields.items():
                args += sep + 'inputs[input_keys[' + str(i) + ']]'
                sep = ', '
                i += 1
        else:
            args += sep + 'inputs[input_keys[' + str(i) + ']]'
            sep = ', '
            i += 1
    #
    # Prepare the outputs
    #
    sep = ''
    outs = ''
    if len(pou.output_vars) == 0:
        raise RuntimeError('Pou has no outputs')
    for out in pou.output_vars:
        if not Datatype.is_primitive(out.datatype.dtname):
            for name, _ in out.datatype.fields.items():
                outs += sep + sanitize_name(out.name + '.' + name)
                sep = ', '
        else:
            outs += sep + out.name
            sep = ', '
    #
    # Calls the main function
    #
    outfile.write(TAB + TAB + outs + ' = self.' +
                  pou.dtname + '(' + args + ')\n')
    outfile.write(TAB + TAB + 'outputs = {}\n')
    #
    # Inserts the outputs into the dictionary
    #
    for out in pou.output_vars:
        if not Datatype.is_primitive(out.datatype.dtname):
            for name, _ in out.datatype.fields.items():
                qualified_name = out.name + '.' + name
                outfile.write(
                    TAB + TAB + "outputs['" + qualified_name + "'] = " +
                    sanitize_name(qualified_name) + "\n")
        else:
            outfile.write(
                TAB + TAB + "outputs['" + out.name + "'] = " + out.name + "\n")
    outfile.write(TAB + TAB + 'return outputs\n')
    outfile.write('\n')

def _dump_footer(outfile):
    outfile.write('def mk_instance(ctx, name):\n')
    outfile.write(TAB + 'return IEC61131Circuit(ctx, name)\n')
    outfile.write('\n')

def _datatype2py(datatype):
    if datatype.dtname == 'BOOL':
        return CONTEXT + '.mk_boolean_type()'
    if datatype.dtname == 'USINT':
        return CONTEXT + '.mk_uint8_type()'
    if datatype.dtname == 'UINT':
        return CONTEXT + '.mk_uint16_type()'
    if datatype.dtname == 'UDINT':
        return CONTEXT + '.mk_uint32_type()'
    if datatype.dtname == 'ULINT':
        return CONTEXT + '.mk_uint64_type()'
    if datatype.dtname == 'SINT':
        return CONTEXT + '.mk_int8_type()'
    if datatype.dtname == 'INT':
        return CONTEXT + '.mk_int16_type()'
    if datatype.dtname == 'DINT':
        return CONTEXT + '.mk_int32_type()'
    if datatype.dtname == 'LINT':
        return CONTEXT + '.mk_int64_type()'
    if datatype.dtname == 'REAL':
        return CONTEXT + '.mk_float32_type()'
    if datatype.dtname == 'LREAL':
        return CONTEXT + '.mk_float64_type()'
    return None

def _datatype2init(datatype):
    if datatype.dtname == 'BOOL':
        return CONTEXT + '.mk_false()'
    return CONTEXT + '.mk_number("0", ' + _datatype2py(datatype) + ')'


def _declare_input_helper(name, datatype, outfile):
    sane_name = sanitize_name(name)
    datatypepy = _datatype2py(datatype)
    if datatypepy is None:
        raise RuntimeError('Datatype for ' + datatype.dtname + ' is None')
    outfile.write(TAB + TAB + sane_name + ' = ' + CONTEXT +
                  ".mk_input('" + name + "', "
                                + datatypepy + ')\n')
    outfile.write(
        TAB + TAB + "self.inputs['" + name + "'] = " + sane_name + '\n')


def _declare_input(inp, outfile, name2var):
    datatypepy = _datatype2py(inp.datatype)
    if datatypepy is None:
        if not inp.name in name2var:
            raise RuntimeError('Could not find datatype for ' + inp.name)
        var = name2var[inp.name]
        for field_name, field_var in var.datatype.fields.items():
            _declare_input_helper(var.name + '.' + field_name,
                               field_var.datatype, outfile)
    else:
        _declare_input_helper(inp.name, inp.datatype, outfile)


def _declare_output(out, outfile, name2var):
    datatypepy = _datatype2py(out.datatype)
    if datatypepy is None:
        if not out.name in name2var:
            raise RuntimeError('Could not find datatype for ' + out.name)
        var = name2var[out.name]
        for field_name, field_var in var.datatype.fields.items():
            _declare_output_helper(var.name + '.' + field_name,
                                field_var.datatype, outfile)
    else:
        _declare_output_helper(out.name, out.datatype, outfile)


def _declare_output_helper(name, datatype, outfile):
    sane_name = sanitize_name(name)
    datatypepy = _datatype2py(datatype)
    if datatypepy is None:
        raise RuntimeError('Datatype for ' + datatype.dtname + ' is None')
    outfile.write(TAB + TAB + sane_name + ' = ' + _datatype2init(datatype) + '\n')


def _declare_local_helper(name, datatype, outfile, var2latch):
    sane_name = sanitize_name(name)
    datatypepy = _datatype2py(datatype)
    if datatypepy is None:
        raise RuntimeError('Datatype for ' + datatype.dtname + ' is None')
    outfile.write(TAB + TAB +
                  sane_name + ' = ' + CONTEXT + '.mk_latch("' + name + '", ' +
                  datatypepy + ')\n')
    init = _datatype2init(datatype)
    var2latch[name] = (sane_name, init)


def _declare_local(var, outfile, var2latch, name2var):
    datatypepy = _datatype2py(var.datatype)
    if datatypepy is None:
        if not var.name in name2var:
            raise RuntimeError('Could not find datatype for ' + var.name)
        var = name2var[var.name]
        for field_name, field_var in var.datatype.fields.items():
            _declare_local_helper(var.name + '.' + field_name,
                               field_var.datatype, outfile, var2latch)
    else:
        _declare_local_helper(var.name, var.datatype, outfile, var2latch)
