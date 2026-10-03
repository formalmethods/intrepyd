"""
Translates a lustre file into an intrepyd equivalent
"""

import datetime
import intrepyd.lustre2py.parser as lusp
from intrepyd.lustre2py.ast2intrepyd import Ast2Intrepyd, TAB, CONTEXT, FIRSTTICK,\
                                            LUSTREDT2INTREPYDDT, BOOLTYPE, INTTYPE,\
                                            REALTYPE #, LATCH2PRE, LATCHEQUIV

def compute_node_prototype(node):
    """
    Extracts node prototype
    """
    inputs = []
    for decl in node.input_decls:
        inputs += [decl.datatype.name] * len(decl.variables)
    outputs = []
    for decl in node.output_decls:
        outputs += [decl.datatype.name] * len(decl.variables)
    return (inputs, outputs)

def compute_node_names(decls):
    """
    Extracts node prototype
    """
    names = []
    for decl in decls:
        names += decl.variables
    return names

def translate(filename, topnode, outfilename, realtype):
    """
    Translates a lustre file into a python
    """
    if not realtype in ['real', 'float16', 'float32', 'float64']:
        raise Exception('Unsupported real type ' + realtype)
    # Parse lustre into AST
    ast = lusp.parse(filename)
    # Compute nodes prototypes
    node2proto = {node.name : compute_node_prototype(node) for node in ast.nodes}
    node2inputs = {node.name : compute_node_names(node.input_decls) for node in ast.nodes}
    node2outputs = {node.name : compute_node_names(node.output_decls) for node in ast.nodes}
    # Translate AST into intrepyd
    encoding = ''
    properties = []
    top = None
    ast_printer = Ast2Intrepyd(node2proto, realtype)
    for node in ast.nodes:
        # Important: sort equations by dependencies!
        node.sort_equations()
        # Important: push pre operators to leaves!
        node.push_pre_in_equations()
        # ast_printer = AstPrinter()
        # print node.accept(ast_printer)
        result, props = node.accept(ast_printer)
        encoding = result
        properties += props
        if node.main:
            top = node
        elif node.name == topnode:
            top = node
    if top is None:
        raise Exception('Top node not found')

    with open(outfilename, 'w', encoding='utf-8') as outfile:
        today = str(datetime.date.today())
        outfile.write('# Translated from ' + filename + ' using intrepyd.lustre2py on ' + today)
        outfile.write('\n\n')
        outfile.write('import intrepyd as ip\n')
        outfile.write('import intrepyd.scr\n')
        outfile.write('import intrepyd.circuit\n')
        # outfile.write(LATCH2PRE + ' = {}\n')
        # outfile.write(LATCHEQUIV + ' = []\n\n')
        outfile.write('class LustreCircuit(ip.circuit.Circuit):\n')
        outfile.write(TAB + 'def __init__(self, ctx, name):\n')
        outfile.write(TAB + TAB + 'ip.circuit.Circuit.__init__(self, ctx, name)\n')
        outfile.write(TAB + TAB + BOOLTYPE + ' = ' + CONTEXT + '.mk_boolean_type()\n')
        outfile.write(TAB + TAB + INTTYPE + ' = ' + CONTEXT + '.mk_int32_type()\n')
        outfile.write(TAB + TAB + REALTYPE + ' = ' + CONTEXT + '.mk_' + realtype + '_type()\n')
        outfile.write(TAB + TAB + FIRSTTICK + ' = ' + CONTEXT +\
                      '.mk_latch("' + FIRSTTICK + '", ' + BOOLTYPE + ')\n')
        outfile.write(TAB + TAB + CONTEXT +\
                      '.set_latch_init_next(' + FIRSTTICK + ', ctx.mk_true(), ctx.mk_false())\n')
        outfile.write('\n')
        outfile.write(TAB + 'def _mk_inputs(self):\n')
        index = 0
        inputs = []
        for ttype in node2proto[top.name][0]:
            net = f'i{index}'
            name = node2inputs[top.name][index]
            outfile.write(TAB + TAB + net + ' = ' + CONTEXT +\
                          ".mk_input('" + name + "', " +\
                          LUSTREDT2INTREPYDDT[ttype] + ')\n')
            outfile.write(TAB + TAB + "self.inputs['" + name + "'] = " + net + '\n')
            inputs.append(net)
            index += 1
        if index == 0:
            outfile.write(TAB + TAB + 'pass\n')
        outfile.write('\n')
        outfile.write(TAB + 'def _mk_naked_circuit_impl(self, inputs):\n')
        outfile.write(TAB + TAB + 'input_keys = list(inputs)\n')
        args = ''
        sep = ''
        index = 0
        for _ in inputs:
            args += sep + 'inputs[input_keys[' + str(index) + ']]'
            sep = ', '
            index += 1
        index = 0
        sep = ''
        outs = ''
        if len(node2proto[top.name][1]) == 0:
            raise RuntimeError('Top node has no outputs')
        for _ in node2proto[top.name][1]:
            name = node2outputs[top.name][index]
            index += 1
            outs += sep + name
            sep = ', '
        outfile.write(TAB + TAB + outs + ' = self.' + top.name + '(' + args + ')\n')
        outfile.write(TAB + TAB + 'outputs = {}\n')
        index = 0
        for _ in node2proto[top.name][1]:
            name = node2outputs[top.name][index]
            outfile.write(TAB + TAB + "outputs['" + name + "'] = " + name + "\n")
        outfile.write(TAB + TAB + 'return outputs\n')
        outfile.write('\n')
        outfile.write(encoding)
        outfile.write('\n')
        outfile.write('def mk_instance(ctx, name):\n')
        outfile.write(TAB + 'return LustreCircuit(ctx, name)\n')
        outfile.write('\n')
