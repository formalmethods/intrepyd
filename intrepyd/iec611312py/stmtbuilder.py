"""
This module implements the main parsing routine of IEC61131 text
"""

from intrepyd.iec611312py.IEC61131ParserVisitor import IEC61131ParserVisitor
from intrepyd.iec611312py.statement import Assignment, IfThenElse, Case
from intrepyd.iec611312py.expression import VariableOcc, ConstantOcc, Expression, Range, FunctionOcc, ParamInit, TRUE
from intrepyd.iec611312py.variable import Variable

def isNumber(text):
    for char in text:
        if not char.isdigit() and char != '.':
            return False
    return True

def computeCompositeDatatype(var, name2var):
    tokens = var.split('.')
    if len(tokens) != 2:
        raise RuntimeError('Cannot handle nested structures')
    baseType = name2var[tokens[0]]
    for name, variable in baseType.datatype.fields.items():
        if name == tokens[1]:
            return variable.datatype
    return None

class STMTBuilder(IEC61131ParserVisitor):
    """
    Vistor that builds statements from the IEC program
    """
    def __init__(self, name2var, pou2inputs):
        self._statements = []
        self._name2var = name2var
        self._pou2inputs = pou2inputs

    @property
    def statements(self):
        return self._statements

    def visitBodyST(self, ctx):
        self._statements = ctx.getChild(0).accept(self)

    def visitStmt_block(self, ctx):
        return [ctx.getChild(i).accept(self) for i in range(ctx.getChildCount())]

    def visitSt_stmt(self, ctx):
        return ctx.getChild(0).accept(self)

    def visit_stmt(self, ctx):
        return ctx.getChild(0).accept(self)

    def visitAssignVariable(self, ctx):
        lhs = ctx.getChild(0).accept(self)
        rhs = ctx.getChild(2).accept(self)
        return Assignment(lhs, rhs)

    def visitAssignCompositeAccess(self, ctx):
        lhs = ctx.getChild(0).accept(self)
        rhs = ctx.getChild(2).accept(self)
        return Assignment(lhs, rhs)

    def visitExpression(self, ctx):
        return ctx.getChild(0).accept(self)

    def visitBinaryBoolExpression(self, ctx):
        return self._binaryExpressionHelper(ctx)

    def visitBinaryTermExpression(self, ctx):
        return self._binaryExpressionHelper(ctx)

    def visitUnaryBoolExpression(self, ctx):
        return self._unaryExpressionHelper(ctx)

    def visitUnaryTermExpression(self, ctx):
        return self._unaryExpressionHelper(ctx)

    def visitLeafBoolExpression(self, ctx):
        return ctx.getChild(0).accept(self)

    def visitParBoolExpression(self, ctx):
        return ctx.subexpr.accept(self)

    def visitParTermExpression(self, ctx):
        return ctx.subexpr.accept(self)

    def visitSimple_var(self, ctx):
        var = ctx.getChild(0).getText()
        if not var in self._name2var:
            raise RuntimeError('Undeclared variable ' + var)
        return VariableOcc(self._name2var[var])

    def visitComposite_access(self, ctx):
        base = ctx.getChild(0).getText()
        if not base in self._name2var:
            raise RuntimeError('Undeclared variable ' + base)
        var = ctx.getText()
        if not var in self._name2var:
            datatype = computeCompositeDatatype(var, self._name2var)
            self._name2var[var] = Variable(var, datatype, Variable.FIELD)
        return VariableOcc(self._name2var[var])

    def visitArray_access(self, ctx):
        raise NotImplementedError

    def visitVariable_bit_access(self, ctx):
        raise NotImplementedError

    def visitConstant(self, ctx):
        cst = ctx.getText()
        return ConstantOcc(cst)

    def visitCallBoolExpression(self, ctx):
        return self._callExpressionHelper(ctx)

    def visitCallTermExpression(self, ctx):
        return self._callExpressionHelper(ctx)

    def visitCustomCallExpression(self, ctx):
        pouName = ctx.getChild(0).getText()
        if not pouName in self._pou2inputs:
            raise('Could not find pou ' + pouName)
        inputs = self._pou2inputs[pouName]
        paramInits = []
        param = 0
        if ctx.getChildCount() > 2:
            for i in range(2, ctx.getChildCount(), 2):
                paramInit = ctx.getChild(i).accept(self)
                paramInits.append(paramInit)
                paramInit.rhs.datatype = inputs[param].datatype
                param += 1
        return FunctionOcc(ctx.getChild(0).getText(), paramInits)

    def visitFunc_param_init(self, ctx):
        param = ctx.getChild(0).getText()
        value = ctx.getChild(2).getText()
        if isNumber(value):
            return ParamInit(param, ConstantOcc(value)) # type will be set by caller
        return ParamInit(param, VariableOcc(Variable(value, None, Variable.TEMP))) # type will be set by caller

    def visitIf_stmt(self, ctx):
        return ctx.getChild(0).accept(self)

    def visitIf_simple_stmt(self, ctx):
        conditions = []
        statements = []
        conditions.append(ctx.ifexpr.accept(self))
        statements.append(ctx.ifstmt.accept(self))
        return IfThenElse(conditions, statements)

    def visitIf_elseif_stmt(self, ctx):
        conditions = []
        statements = []
        conditions.append(ctx.ifexpr.accept(self))
        statements.append(ctx.ifstmt.accept(self))
        conds, stmts = ctx.elsifstmt.accept(self)
        for cond in conds:
            conditions.append(cond)
        for stmt in stmts:
            statements.append(stmt)
        return IfThenElse(conditions, statements)

    def visitIf_else_stmt(self, ctx):
        conditions = []
        statements = []
        conditions.append(ctx.ifexpr.accept(self))
        statements.append(ctx.ifstmt.accept(self))
        conditions.append(TRUE)
        statements.append(ctx.elsestmt.accept(self))
        return IfThenElse(conditions, statements)

    def visitIf_complete_stmt(self, ctx):
        conditions = []
        statements = []
        conditions.append(ctx.ifexpr.accept(self))
        statements.append(ctx.ifstmt.accept(self))
        conds, stmts = ctx.elsifstmt.accept(self)
        for cond in conds:
            conditions.append(cond)
        for stmt in stmts:
            statements.append(stmt)
        conditions.append(TRUE)
        statements.append(ctx.elsestmt.accept(self))
        return IfThenElse(conditions, statements)

    def visitElsif_stmt_list(self, ctx):
        conditions = []
        statements = []
        for i in range(ctx.getChildCount()):
            cond, stmt = ctx.getChild(i).accept(self)
            conditions.append(cond)
            statements.append(stmt)
        return conditions, statements

    def visitElsif_stmt(self, ctx):
        return ctx.expr.accept(self), ctx.stmtblock.accept(self)

    def visitCase_stmt(self, ctx):
        expression = ctx.expr.accept(self)
        selections, statements = ctx.casesel.accept(self)
        if ctx.getChildCount() == 7:
            # There is else too
            selections.append([expression])
            statements.append(ctx.elsestmt.accept(self))
        return Case(expression, selections, statements)

    def visitCase_selections(self, ctx):
        selections = []
        statements = []
        for i in range(ctx.getChildCount()):
            sel, stmt = ctx.getChild(i).accept(self)
            selections.append(sel)
            statements.append(stmt)
        return selections, statements

    def visitCase_selection(self, ctx):
        return ctx.getChild(0).accept(self), ctx.getChild(2).accept(self)

    def visitCase_list(self, ctx):
        return [ctx.getChild(i).accept(self) for i in range(0, ctx.getChildCount(), 2)]

    def visitCaseRange(self, ctx):
        return Range(ctx.start.getText(), ctx.to.getText())

    def visitCaseExpression(self, ctx):
        return ctx.getChild(0).accept(self)

    def _binaryExpressionHelper(self, ctx):
        operator = ctx.op.text
        arguments = [ctx.getChild(0).accept(self), ctx.getChild(2).accept(self)]
        return Expression(operator, arguments)

    def _unaryExpressionHelper(self, ctx):
        operator = ctx.getChild(0).getText()
        return Expression(operator, [ctx.getChild(1).accept(self)])

    def _callExpressionHelper(self, ctx):
        operator = ctx.getChild(0).getText()
        arguments = [ctx.getChild(2).accept(self)]
        return Expression(operator, arguments)
