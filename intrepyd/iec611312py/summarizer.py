"""
This module implements a summarizer for ST assignments
"""

from intrepyd.iec611312py.expression import Expression, VariableOcc, ConstantOcc, FunctionOcc, Ite
from intrepyd.iec611312py.statement import Assignment
from intrepyd.iec611312py.variable import Variable

class Summarizer:
    """
    Summarizer for ST assignments
    """
    def __init__(self):
        self._count = 0
        self._assignments = []

    @property
    def assignments(self):
        """
        Returns assignments
        """
        return self._assignments

    def _get_tmp_var_from_var(self, var):
        self._count += 1
        return VariableOcc(Variable(var.name + '___' +
               str(self._count), var.datatype, Variable.TEMP))

    def summarize_stmt_block(self, block):
        """
        Summarizes a statement block
        """
        summary = {}
        for assignment in block:
            if not isinstance(assignment, Assignment):
                raise RuntimeError('A non-assignment instruction was detected ' +
                                   str(type(assignment)))
            new_rhs = self.substitute(assignment.rhs, summary)
            summary[assignment.lhs.var] = new_rhs
        return [Assignment(VariableOcc(lhs), rhs) for lhs, rhs in summary.items()]

    def substitute_in_term(self, var, expression, term):
        """
        Substitute in term
        """
        result = None
        if isinstance(term, Expression):
            new_arguments = []
            for argument in term.arguments:
                new_arguments.append(self.substitute_in_term(var, expression, argument))
            result = Expression(term.operator, new_arguments)
        elif isinstance(term, Ite):
            i = self.substitute_in_term(var, expression, term.condition)
            t = self.substitute_in_term(var, expression, term.then_term)
            e = self.substitute_in_term(var, expression, term.else_term)
            result = Ite(i, t, e)
        elif isinstance(term, ConstantOcc):
            result = term
        elif isinstance(term, VariableOcc):
            if var == term.var:
                result = self._get_tmp_var_from_var(var)
                self._assignments.append(Assignment(result, expression))
            else:
                result = term
        elif isinstance(term, FunctionOcc):
            result = term
        else:
            raise NotImplementedError(f'Term not handled {type(term)}')
        return result

    def substitute(self, rhs, summary):
        """
        Substitute
        """
        result = rhs
        for key, value in summary.items():
            result = self.substitute_in_term(key, value, result)
        return result
