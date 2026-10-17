"""
This module implements infrastructure to store instructions
"""

from intrepyd.visitable import Visitable
from intrepyd.lustre2py.expression import Expression, UnaryExpression, BinaryExpression,\
                                          ITEExpression, InitCurrExpression, CallExpression,\
                                          TupleExpression

class Instruction(Visitable):
    """
    Abstract class that stores instructions
    """
    def __init__(self, kind):
        self._kind = kind

    EQUATION = 'EQUATION'
    PROPERTY = 'PROPERTY'
    ASSERTION = 'ASSERTION'
    MAIN = 'MAIN'
    REAL_INPUTS = 'REAL_INPUTS'
    IVC = 'IVC'


class Equation(Instruction):
    """
    Class for representing equations
    """
    def __init__(self, lhs, expression):
        Instruction.__init__(self, Instruction.EQUATION)
        self._lhs = lhs
        self._expression = expression

    @property
    def lhs(self):
        """
        Getter
        """
        return self._lhs

    @property
    def expression(self):
        """
        Getter
        """
        return self._expression

    def push_pre(self):
        """
        Push pre to variables
        """
        self._expression = _expression_pre_pusher(self._expression, 0)


class RealInputs(Instruction):
    """
    Class for representing realizability inputs
    """
    def __init__(self, ids):
        Instruction.__init__(self, Instruction.REAL_INPUTS)
        self._ids = ids


class Ivc(Instruction):
    """
    Class for representing ivcs
    """
    def __init__(self, ids):
        Instruction.__init__(self, Instruction.IVC)
        self._ids = ids


class Property(Instruction):
    """
    Class for representing properties
    """
    def __init__(self, expr):
        Instruction.__init__(self, Instruction.PROPERTY)
        self._expression = expr

def _expression_pre_pusher(expr, num_pre):
    assert num_pre >= 0
    if expr.kind == Expression.LITERAL:
        return expr
    if expr.kind == Expression.ZEROARY:
        result = expr
        for _ in range(num_pre):
            result = UnaryExpression('pre', result)
        return result
    if expr.kind == Expression.UNARY:
        result = None
        if expr.operator == 'pre':
            return _expression_pre_pusher(expr.operand, num_pre + 1)
        new_operand = _expression_pre_pusher(expr.operand, num_pre)
        return UnaryExpression(expr.operator, new_operand)
    if expr.kind == Expression.BINARY:
        new_left = _expression_pre_pusher(expr.left, num_pre)
        new_right = _expression_pre_pusher(expr.right, num_pre)
        return BinaryExpression(expr.operator, new_left, new_right)
    if expr.kind == Expression.ITE:
        new_if_ = _expression_pre_pusher(expr.if_, num_pre)
        new_then_ = _expression_pre_pusher(expr.then_, num_pre)
        new_else_ = _expression_pre_pusher(expr.else_, num_pre)
        return ITEExpression(new_if_, new_then_, new_else_)
    if expr.kind == Expression.INITCURR:
        new_init = _expression_pre_pusher(expr.init, num_pre)
        new_curr = _expression_pre_pusher(expr.curr, num_pre)
        return InitCurrExpression(new_init, new_curr)
    if expr.kind == Expression.CALL:
        new_params = [_expression_pre_pusher(param, num_pre) for param in expr.params]
        return CallExpression(expr.cid, new_params)
    if expr.kind == Expression.TUPLE:
        new_exprs = [_expression_pre_pusher(expression, num_pre) for expression in expr.expressions]
        return TupleExpression(new_exprs)
    raise TypeError('Unhandled kind' + expr.kind)


def push_pre(expr):
    """
    An expression with its 'pre' operators pushed to its variables
    """
    return _expression_pre_pusher(expr, 0)
