"""
Translates a lustre file into an intrepyd equivalent
"""

import datetime
import intrepyd.lustre2py.parser as lusp
from intrepyd.lustre2py.errors import LustreError
from intrepyd.lustre2py.expression import Expression
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

INT_TYPES = ['int', 'int8', 'int16', 'int32', 'int64']
REAL_TYPES = ['real', 'float16', 'float32', 'float64']

def translate(filename, topnode, outfilename, realtype, inttype='int32'):
    """
    Translates a lustre file into a python

    realtype and inttype choose how lustre real and int are encoded. For
    int, 'int' is the unbounded integers of lustre itself, while 'int8' to
    'int64' are machine integers of that width, which can overflow: a
    property may then hold with one encoding and not with the other.
    """
    if not realtype in REAL_TYPES:
        raise Exception('Unsupported real type ' + realtype)
    if not inttype in INT_TYPES:
        raise Exception('Unsupported int type ' + inttype)
    # Parse lustre into AST
    ast = lusp.parse(filename)
    top = choose_top(ast, topnode)
    # Compute nodes prototypes
    node2proto = {node.name : compute_node_prototype(node) for node in ast.nodes}
    node2inputs = {node.name : compute_node_names(node.input_decls) for node in ast.nodes}
    node2outputs = {node.name : compute_node_names(node.output_decls) for node in ast.nodes}
    # Translate AST into intrepyd
    encoding = ''
    properties = []
    ast_printer = Ast2Intrepyd(node2proto, realtype, top.name)
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

    with open(outfilename, 'w', encoding='utf-8') as outfile:
        today = str(datetime.date.today())
        outfile.write('# Translated from ' + filename + ' using intrepyd.lustre2py on ' + today)
        outfile.write('\n\n')
        outfile.write('import intrepyd as ip\n')
        outfile.write('import intrepyd.scr\n')
        outfile.write('import intrepyd.circuit\n')
        outfile.write('\n')
        outfile.write('def _unique(names, name):\n')
        outfile.write(TAB + 'if name not in names:\n')
        outfile.write(TAB + TAB + 'return name\n')
        outfile.write(TAB + 'k = 2\n')
        outfile.write(TAB + "while f'{name}#{k}' in names:\n")
        outfile.write(TAB + TAB + 'k += 1\n')
        outfile.write(TAB + "return f'{name}#{k}'\n")
        outfile.write('\n')
        # outfile.write(LATCH2PRE + ' = {}\n')
        # outfile.write(LATCHEQUIV + ' = []\n\n')
        outfile.write('class LustreCircuit(ip.circuit.Circuit):\n')
        outfile.write(TAB + 'def __init__(self, ctx, name):\n')
        outfile.write(TAB + TAB + 'ip.circuit.Circuit.__init__(self, ctx, name)\n')
        outfile.write(TAB + TAB + BOOLTYPE + ' = ' + CONTEXT + '.mk_boolean_type()\n')
        outfile.write(TAB + TAB + INTTYPE + ' = ' + CONTEXT + '.mk_' + inttype + '_type()\n')
        outfile.write(TAB + TAB + REALTYPE + ' = ' + CONTEXT + '.mk_' + realtype + '_type()\n')
        outfile.write(TAB + TAB + FIRSTTICK + ' = ' + CONTEXT +\
                      '.mk_latch("__first_tick", ' + BOOLTYPE + ')\n')
        outfile.write(TAB + TAB + CONTEXT +\
                      '.set_latch_init_next(' + FIRSTTICK + ', ctx.mk_true(), ctx.mk_false())\n')
        outfile.write('\n')
        # a property (--%PROPERTY) of each node instance, and an assertion
        # (assert), which constrains the inputs at every step
        outfile.write(TAB + 'def _lustre_property(self, name, net):\n')
        outfile.write(TAB + TAB + 'self.properties[_unique(self.properties, name)] = net\n')
        outfile.write('\n')
        outfile.write(TAB + 'def _lustre_assumption(self, name, net):\n')
        outfile.write(TAB + TAB + CONTEXT + '.push_assumption(net)\n')
        outfile.write(TAB + TAB + 'self.assumptions[_unique(self.assumptions, name)] = net\n')
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
            index += 1
            outfile.write(TAB + TAB + "outputs['" + name + "'] = " + name + "\n")
        outfile.write(TAB + TAB + 'return outputs\n')
        outfile.write('\n')
        outfile.write(encoding)
        outfile.write('\n')
        outfile.write('def mk_instance(ctx, name):\n')
        outfile.write(TAB + 'return LustreCircuit(ctx, name)\n')
        outfile.write('\n')


def _calls(expr, found):
    """The nodes an expression calls, into found."""
    if expr.kind == Expression.CALL:
        found.add(expr.cid)
        for param in expr.params:
            _calls(param, found)
    for child in ('operand', 'left', 'right', 'if_', 'then_', 'else_', 'init', 'curr'):
        sub = getattr(expr, child, None)
        if sub is not None and hasattr(sub, 'kind'):
            _calls(sub, found)
    for sub in getattr(expr, 'expressions', None) or []:
        _calls(sub, found)


def _literal_kinds(expr, found):
    """The kinds of the literals in an expression, into found."""
    if expr.kind == Expression.LITERAL:
        found.add(expr.datatype)
    for child in ('operand', 'left', 'right', 'if_', 'then_', 'else_', 'init', 'curr'):
        sub = getattr(expr, child, None)
        if sub is not None and hasattr(sub, 'kind'):
            _literal_kinds(sub, found)
    for sub in (getattr(expr, 'expressions', None) or []) + (getattr(expr, 'params', None) or []):
        _literal_kinds(sub, found)


def _expressions(node):
    return [eq.expression for eq in node.equations] + list(node.properties) + list(node.assertions)


def top_candidates(ast):
    """The nodes no other node calls, in their order: those that can be the top one."""
    called = set()
    for node in ast.nodes:
        for expr in _expressions(node):
            _calls(expr, called)
    return [node.name for node in ast.nodes if node.name not in called]


def choose_top(ast, topnode=None):
    """The top node: the one given, else the one --%MAIN marks, else the only
    one no other calls. LustreError if there is none, or no way to choose."""
    if topnode:
        for node in ast.nodes:
            if node.name == topnode:
                return node
        raise LustreError(f'no node {topnode} in the file (its nodes: '
                          f'{", ".join(n.name for n in ast.nodes)})')
    mains = [node for node in ast.nodes if node.main]
    if mains:
        return mains[-1]
    candidates = top_candidates(ast)
    if len(candidates) == 1:
        return next(node for node in ast.nodes if node.name == candidates[0])
    if not ast.nodes:
        raise LustreError('the file has no node')
    raise LustreError(f'the file has several top nodes ({", ".join(candidates)}): '
                      'say which one (--%MAIN, or --node)')


def describe(filename):
    """What a Lustre file is, without translating it: its nodes, the top one
    (--%MAIN) if it says, the nodes that can be the top one, and whether it
    uses int and real (whose encodings are to be chosen). LustreError for a
    file that cannot be translated."""
    ast = lusp.parse(filename)
    types, literals = set(), set()
    for node in ast.nodes:
        for decl in node.input_decls + node.output_decls + node.local_decls:
            types.add(decl.datatype.name)
        for expr in _expressions(node):
            _literal_kinds(expr, literals)
    mains = [node.name for node in ast.nodes if node.main]
    return {
        'nodes': [node.name for node in ast.nodes],
        'main': mains[-1] if mains else None,
        'candidates': top_candidates(ast),
        'int': 'int' in types or Expression.INT in literals,
        'real': 'real' in types or Expression.REAL in literals,
        'properties': sum(len(node.properties) for node in ast.nodes),
        'assertions': sum(len(node.assertions) for node in ast.nodes),
    }
