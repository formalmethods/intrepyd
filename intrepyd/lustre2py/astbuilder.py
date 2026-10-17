"""
This module implements the main parsing routine of Lustre files
"""

from intrepyd.lustre2py.LustreVisitor import LustreVisitor
from intrepyd.lustre2py.node import Node
from intrepyd.lustre2py.expression import LiteralExpression, ZeroaryExpression,\
                                          UnaryExpression, BinaryExpression, InitCurrExpression,\
                                          ITEExpression, Expression, CallExpression,\
                                          TupleExpression
from intrepyd.lustre2py.variable import VarDeclGroup
from intrepyd.lustre2py.instruction import Equation
from intrepyd.lustre2py.datatype import Primitive
from intrepyd.lustre2py.errors import LustreError


def _unsupported(ctx, what):
    """Refuses a construct of the grammar this front end does not translate."""
    raise LustreError(f'{what} are not supported', ctx.start.line, ctx.start.column + 1)

class ASTBuilder(LustreVisitor):
    """
    Vistor that builds the internal AST for the
    Lustre program
    """
    def __init__(self):
        self._nodes = []
        self._current_node = None

    @property
    def nodes(self):
        """
        Getter
        """
        return self._nodes

    def visitNode(self, ctx):
        new_node = Node(ctx.getChild(1).getText())
        self._current_node = new_node
        if not ctx.inp is None:
            lst = ctx.inp.accept(self)
            for decl in lst:
                new_node.add_input_decl(decl)
        if not ctx.outp is None:
            lst = ctx.outp.accept(self)
            for decl in lst:
                new_node.add_output_decl(decl)
        if not ctx.local is None:
            lst = ctx.local.accept(self)
            for decl in lst:
                new_node.add_local_decl(decl)
        if not ctx.instrlst is None:
            ctx.instrlst.accept(self)
        self._nodes.append(new_node)
        self._current_node = None

    def visitVarDeclList(self, ctx):
        return [ctx.getChild(i).accept(self) for i in range(0, ctx.getChildCount(), 2)]

    def visitVarDeclGroup(self, ctx):
        var_list = [ctx.getChild(i).accept(self) for i in range(0, ctx.getChildCount() - 2, 2)]
        datatype = ctx.getChild(ctx.getChildCount() - 1).accept(self)
        return VarDeclGroup(var_list, datatype)

    def visitInitCurrExpr(self, ctx):
        init = ctx.getChild(0).accept(self)
        curr = ctx.getChild(2).accept(self)
        return InitCurrExpression(init, curr)

    def visitNotExpr(self, ctx):
        arg = ctx.getChild(1).accept(self)
        return UnaryExpression('not', arg)

    def visitNegateExpr(self, ctx):
        arg = ctx.getChild(1).accept(self)
        return UnaryExpression('-', arg)

    def visitPreExpr(self, ctx):
        arg = ctx.getChild(1).accept(self)
        return UnaryExpression('pre', arg)

    def visitBinaryExpr(self, ctx):
        left = ctx.getChild(0).accept(self)
        right = ctx.getChild(2).accept(self)
        return BinaryExpression(ctx.op.text, left, right)

    def visitIfThenElseExpr(self, ctx):
        if_ = ctx.getChild(1).accept(self)
        then_ = ctx.getChild(3).accept(self)
        else_ = ctx.getChild(5).accept(self)
        return ITEExpression(if_, then_, else_)

    def visitIdExpr(self, ctx):
        return ZeroaryExpression(ctx.getText())

    def visitIntExpr(self, ctx):
        return LiteralExpression(ctx.getText(), Expression.INT)

    def visitRealExpr(self, ctx):
        return LiteralExpression(ctx.getText(), Expression.REAL)

    def visitBoolExpr(self, ctx):
        return LiteralExpression(ctx.getText(), Expression.BOOL)

    def visitTupleExpr(self, ctx):
        expressions = [ctx.getChild(i).accept(self)\
                        for i in range(1, ctx.getChildCount() - 1, 2)]
        return TupleExpression(expressions)

    def visitEquation(self, ctx):
        lhs = None
        if not ctx.pos1 is None:
            lhs = ctx.pos1.accept(self)
        if not ctx.pos2 is None:
            lhs = ctx.pos2.accept(self)
        expr = ctx.pos3.accept(self)
        self._current_node.add_equation(Equation(lhs, expr))

    def visitLhs(self, ctx):
        return [ctx.getChild(i).accept(self) for i in range(0, ctx.getChildCount(), 2)]

    def visitNodeCallExpr(self, ctx):
        cid = ctx.getChild(0).getText()
        params = [ctx.getChild(i).accept(self)\
                        for i in range(2, ctx.getChildCount() - 1, 2)]
        return CallExpression(cid, params)

    def visitProp(self, ctx):
        expr = ctx.getChild(1).accept(self)
        self._current_node.add_property(expr, _label(expr, 'property', ctx))

    def visitAssertion(self, ctx):
        expr = ctx.getChild(1).accept(self)
        self._current_node.add_assertion(expr, _label(expr, 'assumption', ctx))

    def visitMain(self, ctx):
        self._current_node.main = True

    def visitBaseEID(self, ctx):
        return ctx.getText()

    def visitArrayEID(self, ctx):
        _unsupported(ctx, 'arrays')

    def visitRecordEID(self, ctx):
        _unsupported(ctx, 'records')

    def visitIvc(self, ctx):
        _unsupported(ctx, '--%IVC annotations')

    def visitRealizabilityInputs(self, ctx):
        _unsupported(ctx, '--%REALIZABLE annotations')

    def visitCondactExpr(self, ctx):
        _unsupported(ctx, 'condact expressions')

    def visitCastExpr(self, ctx):
        _unsupported(ctx, 'casts (real, floor)')

    def visitRecordExpr(self, ctx):
        _unsupported(ctx, 'records')

    def visitArrayExpr(self, ctx):
        _unsupported(ctx, 'arrays')

    def visitArrayAccessExpr(self, ctx):
        _unsupported(ctx, 'arrays')

    def visitRecordAccessExpr(self, ctx):
        _unsupported(ctx, 'records')

    def visitPrimitiveType(self, ctx):
        return Primitive(ctx.getChild(0).getText())

    def visitSubrangeType(self, ctx):
        _unsupported(ctx, 'subrange types')

    def visitArrayType(self, ctx):
        _unsupported(ctx, 'arrays')

    def visitUserType(self, ctx):
        _unsupported(ctx, 'user-defined types')

    def visitRecordType(self, ctx):
        _unsupported(ctx, 'records')

    def visitEnumType(self, ctx):
        _unsupported(ctx, 'enumerations')

    def visitRecordUpdateExpr(self, ctx):
        _unsupported(ctx, 'records')

    def visitArrayUpdateExpr(self, ctx):
        _unsupported(ctx, 'arrays')

    def visitConstant(self, ctx):
        _unsupported(ctx, 'constants')

    def visitDatatypedef(self, ctx):
        _unsupported(ctx, 'type definitions')


def _label(expr, what, ctx):
    """A property's or an assertion's name: the variable it is, else what it is
    and its line."""
    if expr.kind == Expression.ZEROARY:
        return expr.name
    return f'{what}_line{ctx.start.line}'
