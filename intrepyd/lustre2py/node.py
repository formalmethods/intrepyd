"""
This module implements infrastructure to store nodes
"""

from intrepyd.visitable import Visitable
from intrepyd.lustre2py.expression import Expression
from intrepyd.lustre2py.instruction import push_pre

_GREY = 1
_BLACK = 2

class Node(Visitable):  # pylint: disable=too-many-instance-attributes
    """
    Stores a node
    """
    def __init__(self, name):
        self._name = name
        self._input_decls = []
        self._output_decls = []
        self._local_decls = []
        self._equations = []
        self._main = False
        self._properties = []
        self._property_labels = []
        self._assertions = []
        self._assertion_labels = []

    @property
    def name(self):
        """
        Getter
        """
        return self._name

    @property
    def input_decls(self):
        """
        Getter
        """
        return self._input_decls

    @property
    def output_decls(self):
        """
        Getter
        """
        return self._output_decls

    @property
    def local_decls(self):
        """
        Getter
        """
        return self._local_decls

    @property
    def equations(self):
        """
        Getter
        """
        return self._equations

    @property
    def main(self):
        """
        Getter
        """
        return self._main

    @property
    def properties(self):
        """
        Getter
        """
        return self._properties

    @property
    def property_labels(self):
        """
        The names of the properties, in their order
        """
        return self._property_labels

    @property
    def assertions(self):
        """
        The assertions (assert e;): assumptions on the node's environment
        """
        return self._assertions

    @property
    def assertion_labels(self):
        """
        The names of the assertions, in their order
        """
        return self._assertion_labels

    @name.setter
    def name(self, value):
        self._name = value

    @main.setter
    def main(self, value):
        self._main = value

    def add_input_decl(self, inputs):
        """
        Add a new input declaration
        """
        self._input_decls.append(inputs)

    def add_output_decl(self, outputs):
        """
        Add a new output declaration
        """
        self._output_decls.append(outputs)

    def add_local_decl(self, llocals):
        """
        Add a new local declaration
        """
        self._local_decls.append(llocals)

    def add_equation(self, equation):
        """
        Adds an equation
        """
        self._equations.append(equation)

    def add_property(self, prop, label=None):
        """
        Adds a property declaration
        """
        self._properties.append(prop)
        self._property_labels.append(label or f'property{len(self._properties)}')

    def add_assertion(self, expr, label=None):
        """
        Adds an assertion (assert e;)
        """
        self._assertions.append(expr)
        self._assertion_labels.append(label or f'assumption{len(self._assertions)}')

    def sort_equations(self):
        """
        Sort equations in such a way that local variables are
        defined before their use.
        """
        eqtopology = EquationTopology(self.equations, self.local_decls + self.output_decls)
        topological_order = eqtopology.compute_topological_order()
        new_equations = [self.equations[i] for i in topological_order]
        self._equations = new_equations

    def push_pre_in_equations(self):
        """
        Rewrites rhs of equations in such a way that 'pre' operators
        are pushed to variables
        """
        for equat in self._equations:
            equat.push_pre()
        self._properties = [push_pre(prop) for prop in self._properties]
        self._assertions = [push_pre(expr) for expr in self._assertions]


class EquationTopology:
    """
    Utility class for sorting equation dependencies topologically
    """
    def __init__(self, equations, local_decls):
        self._equations = equations
        self._local_decls = local_decls

    def compute_topological_order(self):
        """
        Compute dependencies between equations w.r.t. use of local variables

        0. a = b + c
        1. b = c
        2. c = 5 + d

        0 -> [2, 3]
        1 -> [2]
        2 -> []       (d is not a local variable)
        """
        dependencies = self._compute_equation_dependencies()
        return self._compute_topological_order(dependencies)

    def _compute_topological_order(self, dependencies):
        seen = {}
        topological_order = []
        for eqnum, _ in dependencies.items():
            parent = {eqnum : None}
            self._compute_topological_order_rec(eqnum, dependencies,\
                                                topological_order, seen, parent)
        return topological_order

    def _compute_topological_order_rec(self, eqnum, dependencies,\
                                       topological_order, seen, parent):
        if eqnum in seen:
            if seen[eqnum] == _GREY:
                print('Dependency loop:', parent)
                raise Exception('Loop in equation dependencies')
            if seen[eqnum] == _BLACK:
                # Already seen
                return
        seen[eqnum] = _GREY
        # Visit dependencies first
        for dependency in dependencies[eqnum]:
            if eqnum == dependency:
                continue
            parent[dependency] = eqnum
            self._compute_topological_order_rec(dependency, dependencies,\
                                                topological_order, seen, parent)
        topological_order.append(eqnum)
        seen[eqnum] = _BLACK

    def _compute_equation_dependencies(self):
        localvars = self._retrieve_local_vars()
        var2equation = self._compute_var2equation(localvars)
        dependencies = {}
        index = 0
        for equat in self._equations:
            dependencies[index] = set(self._retrieve_used_equations(equat.expression, var2equation))
            index += 1
        return dependencies

    def _retrieve_used_equations(self, expr, var2equation):
        """
        Computes the equations that expr depends upon. For
        each variable in expr, store the equation where
        the variable is defined
        """
        used_equations = []
        if expr.kind == Expression.ZEROARY:
            if expr.name in var2equation:
                used_equations.append(var2equation[expr.name])
        elif expr.kind == Expression.UNARY:
            if expr.operator != 'pre':
                used_equations = self._retrieve_used_equations(expr.operand, var2equation)
        elif expr.kind == Expression.BINARY:
            used_equations = self._retrieve_used_equations(expr.left, var2equation) +\
                             self._retrieve_used_equations(expr.right, var2equation)
        elif expr.kind == Expression.ITE:
            used_equations = self._retrieve_used_equations(expr.if_, var2equation) +\
                             self._retrieve_used_equations(expr.then_, var2equation) +\
                             self._retrieve_used_equations(expr.else_, var2equation)
        elif expr.kind == Expression.INITCURR:
            used_equations = self._retrieve_used_equations(expr.init, var2equation) +\
                             self._retrieve_used_equations(expr.curr, var2equation)
        elif expr.kind == Expression.CALL:
            for param in expr.params:
                used_equations += self._retrieve_used_equations(param, var2equation)
        elif expr.kind == Expression.TUPLE:
            for expression in expr.expressions:
                used_equations += self._retrieve_used_equations(expression, var2equation)
        elif expr.kind == Expression.LITERAL:
            pass
        else:
            raise TypeError('Unhandled kind' + expr.kind)
        return used_equations

    def _retrieve_local_vars(self):
        local_vars = []
        for decl in self._local_decls:
            for var in decl.variables:
                local_vars.append(var)
        return set(local_vars)

    def _compute_var2equation(self, localvars):
        """
        Computes a dictionary that maps a variable
        on the lhs of an equation with the number of the
        equation itself
        """
        var2equation = {}
        index = 0
        for equat in self._equations:
            for lhs in equat.lhs:
                if lhs in localvars:
                    var2equation[lhs] = index
            index += 1
        return var2equation
