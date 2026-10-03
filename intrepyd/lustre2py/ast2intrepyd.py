"""
This module implements a printer of an AST into Intrepyd syntax
"""

from intrepyd.lustre2py.visitor import Visitor
from intrepyd.lustre2py.instruction import Equation, Property
from intrepyd.lustre2py.node import Node
from intrepyd.lustre2py.expression import Expression

CTX = 'context'
CONTEXT = 'self.' + CTX
FIRSTTICK = 'self.__first_tick'
INTTYPE = 'self.__it'
REALTYPE = 'self.__rt'
BOOLTYPE = 'self.__bt'
TAB = ' ' * 4
DTAB = TAB + TAB
# LATCH2PRE = 'LATCH2PRE'
# LATCHEQUIV = 'LATCHEQUIV'
_DEFAULT_BOOL_INIT = CONTEXT + '.mk_false()'
_DEFAULT_ARIT_INIT = CONTEXT + '.mk_number("0", '

LUSTREOP2INTREPYDUNARYOP = {
    '-' : 'mk_minus',
    'not' : 'mk_not'
}

LUSTREOP2INTREPYDBINARYOP = {
    '+' : 'mk_add',
    '-' : 'mk_sub',
    '*' : 'mk_mul',
    '/' : 'mk_div',
    '=' : 'mk_eq',
    '<>' : 'mk_neq',
    '<' : 'mk_lt',
    '>' : 'mk_gt',
    '<=' : 'mk_leq',
    '>=' : 'mk_geq',
    '=>' : 'mk_implies',
    'div' : 'mk_div',
    'mod' : 'mk_mod',
    'or' : 'mk_or',
    'and' : 'mk_and',
    'xor' : 'mk_xor',
}

LUSTREDT2INTREPYDDT = {
    'bool' : BOOLTYPE,
    'int' : INTTYPE,
    'real' : REALTYPE
}

def _infer_datatype(expression, var2datatype, node2proto):
    if expression.kind == Expression.LITERAL:
        if expression.datatype == Expression.INT:
            return INTTYPE
        if expression.datatype == Expression.REAL:
            return REALTYPE
        if expression.datatype == Expression.BOOL:
            return BOOLTYPE
        raise TypeError('Unhandled type' + expression.datatype)
    if expression.kind == Expression.ZEROARY:
        if not expression.name in var2datatype:
            raise RuntimeError('Unknown type for ' + expression.name)
        name = var2datatype[expression.name].name
        assert name in LUSTREDT2INTREPYDDT
        return LUSTREDT2INTREPYDDT[name]
    if expression.kind == Expression.UNARY:
        if expression.operator == 'not':
            return BOOLTYPE
        if expression.operator == 'real':
            return REALTYPE
        if expression.operator == 'floor':
            return INTTYPE
        # Recursive call
        return _infer_datatype(expression.operand, var2datatype, node2proto)
    if expression.kind == Expression.BINARY:
        if expression.operator in set(['and', 'or', 'xor', '=>', '<', '>', '=', '<>', '<=', '>=']):
            return BOOLTYPE
        # Recursive call
        return _infer_datatype(expression.left, var2datatype, node2proto)
    if expression.kind == Expression.ITE:
        # Recursive call
        return _infer_datatype(expression.then_, var2datatype, node2proto)
    if expression.kind == Expression.INITCURR:
        # Recursive call
        return _infer_datatype(expression.init, var2datatype, node2proto)
    if expression.kind == Expression.CALL:
        assert expression.cid in node2proto
        # outputs = [1], first output = [0]
        ttype = node2proto[expression.cid][1][0]
        assert ttype in LUSTREDT2INTREPYDDT
        return LUSTREDT2INTREPYDDT[ttype]
    if expression.kind == Expression.TUPLE:
        assert len(expression.expressions) == 1
        # Recursive call
        return _infer_datatype(expression.expressions[0], var2datatype, node2proto)
    raise TypeError('Unhandled kind' + expression.kind)

def _contains(expression, var):
    if expression.kind == Expression.LITERAL:
        return False
    if expression.kind == Expression.ZEROARY:
        return expression.name == var
    if expression.kind == Expression.UNARY:
        return _contains(expression.operand, var)
    if expression.kind == Expression.BINARY:
        return _contains(expression.left, var) or _contains(expression.right, var)
    if expression.kind == Expression.ITE:
        return _contains(expression.if_, var) or\
               _contains(expression.then_, var) or\
               _contains(expression.else_, var)
    if expression.kind == Expression.INITCURR:
        return _contains(expression.init, var) or\
               _contains(expression.next, var)
    if expression.kind == Expression.CALL:
        for param in expression.params:
            if param == var:
                return True
        return False
    if expression.kind == Expression.TUPLE:
        for expr in expression.expressions:
            if _contains(expr, var):
                return True
        return False
    raise TypeError('Unhandled kind' + expression.kind)


class Ast2Intrepyd(Visitor):
    """
    Visitor for printing AST on stdout
    """
    def __init__(self, node2proto, realtype):
        self._result = ''
        self._main_node = None
        self._properties = []
        self._id = 0
        self._nid = 0
        self._var2datatype = {}
        self._latch_decls = []
        self._node2proto = node2proto
        self._pre_decls = set()
        self._realtype = realtype

    def _get_new_name(self):
        self._id += 1
        return '__l' + str(self._id)

    def _get_unique_namespace(self, name):
        self._nid += 1
        return f'"{name}.{self._nid}"'

    def _visit_node(self, node):
        assert isinstance(node, Node)
        self._pre_decls = set()
        self._var2datatype = {}
        self._latch_decls = []
        if node.main:
            self._main_node = node
        self._result += TAB + 'def ' + node.name + '(self'
        for inp in node.input_decls:
            self._result += ', ' + inp.accept(self)
        self._result += '):\n'
        for loc in node.local_decls:
            loc.accept(self)
        for out in node.output_decls:
            out.accept(self)
        for equat in node.equations:
            equat.accept(self)
        for latch_decl in self._latch_decls:
            new_name, init, operand = latch_decl
            # self._result += DTAB + 'if ' + operand + ' in ' + LATCH2PRE + ':\n'
            # pair = '(' + LATCH2PRE + '[' + operand + '], ' + new_name + ')'
            # self._result += DTAB + TAB + LATCHEQUIV + '.append(' + pair + ')\n'
            # self._result += DTAB + LATCH2PRE + '[' + operand + '] = ' + new_name + '\n'
            self._result += DTAB + CONTEXT +\
                            '.set_latch_init_next(' + new_name + ', ' +\
                                                  init + ', ' + operand + ')\n'
        for prop in node.properties:
            self._properties.append(prop.accept(self))
        sep = ''
        for out in node.output_decls:
            for var in out.variables:
                self._result += DTAB + CONTEXT + '.net2name[' + var + '] = "' + var + '"\n'
        self._result += DTAB + 'return '
        for out in node.output_decls:
            self._result += sep + out.accept(self)
            sep = ', '
        self._result += '\n\n'
        return self._result, self._properties

    def _visit_var_decl_list(self, lst):
        result = ''
        sep = ''
        for grp in lst.var_decl_groups:
            result += sep + grp.accept(self)
            sep = ', '
        return result

    def _visit_var_decl_group(self, grp):
        result = ''
        sep = ''
        for var in grp.variables:
            result += sep + var
            sep = ', '
            self._var2datatype[var] = grp.datatype
        return result

    def _visit_equation(self, equat):
        assert isinstance(equat, Equation)
        expr = equat.expression.accept(self)
        result = DTAB
        sep = ''
        for lhs in equat.lhs:
            result += sep + lhs
            sep = ', '
        result += ' = ' + expr + '\n'
        self._result += result

    def _visit_init_curr_expression(self, expr):
        new_name = self._get_new_name()
        init = expr.init.accept(self)
        curr = expr.curr.accept(self)
        self._result += DTAB + new_name + ' = ' +\
                        CONTEXT + '.mk_ite(' +\
                                  FIRSTTICK + ', ' +\
                                  init + ', ' + curr + ')\n'
        return new_name

    def _visit_literal_expression(self, expr):
        if expr.value == 'true':
            return CONTEXT + '.mk_true()'
        if expr.value == 'false':
            return CONTEXT + '.mk_false()'
        datatype = LUSTREDT2INTREPYDDT[expr.datatype]
        return CONTEXT + '.mk_number("' + expr.value + '", ' + datatype + ')'

    def _visit_zeroary_expression(self, expr):
        return expr.name

    def _visit_unary_expression(self, expr):
        operand = expr.operand.accept(self)
        if expr.operator == 'pre':
            new_name = 'pre_' + operand
            # return latch created in this function somewhere else
            if new_name in self._pre_decls:
                return new_name
            self._pre_decls.add(new_name)
            datatype = _infer_datatype(expr.operand, self._var2datatype, self._node2proto)
            self._result += DTAB + new_name + ' = ' + CONTEXT +\
                            '.mk_latch("' + new_name + '", ' + datatype + ')\n'
            init = None
            if datatype == BOOLTYPE:
                init = _DEFAULT_BOOL_INIT
            else:
                init = _DEFAULT_ARIT_INIT + datatype + ')'
            self._latch_decls.append((new_name, init, operand))
            return new_name
        new_name = self._get_new_name()
        self._result += DTAB + new_name + ' = '
        assert expr.operator in LUSTREOP2INTREPYDUNARYOP
        self._result += CONTEXT + '.' +\
                        LUSTREOP2INTREPYDUNARYOP[expr.operator] + '(' + operand + ')\n'
        return new_name

    def _visit_binary_expression(self, expr):
        new_name = self._get_new_name()
        left = expr.left.accept(self)
        right = expr.right.accept(self)
        self._result += DTAB + new_name + ' = '
        assert expr.operator in LUSTREOP2INTREPYDBINARYOP
        self._result += CONTEXT + '.' + LUSTREOP2INTREPYDBINARYOP[expr.operator] +\
                        '(' + left + ', ' + right + ')\n'
        return new_name

    def _visit_ite_expression(self, expr):
        new_name = self._get_new_name()
        if_ = expr.if_.accept(self)
        then_ = expr.then_.accept(self)
        else_ = expr.else_.accept(self)
        self._result += DTAB + new_name + ' = ' + CONTEXT +\
                        '.mk_ite(' + if_ + ', ' + then_ + ', ' + else_ + ')\n'
        return new_name

    def _visit_call_expression(self, expr):
        new_name = self._get_new_name()
        result = DTAB + CONTEXT +\
                 '.push_namespace(' + self._get_unique_namespace(expr.cid) + ')\n'
        result += DTAB + new_name + ' = self.' + expr.cid
        result += '('
        sep = ''
        for param in expr.params:
            param_name = param.accept(self)
            result += sep + param_name
            sep = ', '
        result += ')\n'
        self._result += result
        self._result += DTAB + CONTEXT + '.pop_namespace()\n'
        return new_name

    def _visit_primitive(self, obj):
        return obj.name

    def _visit_tuple_expression(self, ttuple):
        put_par = len(ttuple.expressions) > 1
        result = ''
        if put_par:
            result += '('
        sep = ''
        for expr in ttuple.expressions:
            result += sep + expr.accept(self)
            sep = ', '
        if put_par:
            result += ')'
        return result

    def _visit_enum(self, obj):
        raise NotImplementedError

    def _visit_struct(self, obj):
        raise NotImplementedError

    def _visit_array(self, obj):
        raise NotImplementedError

    def _visit_subrange(self, obj):
        raise NotImplementedError

    def _visit_property(self, obj):
        assert isinstance(obj, Property)
        result = obj.expression.accept(self)
        self._properties.append(result)
