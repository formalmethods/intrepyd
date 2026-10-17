"""
This module implements the main parsing routine of Lustre files
"""

import re

from antlr4 import InputStream, CommonTokenStream
from antlr4.error.ErrorListener import ErrorListener
from intrepyd.lustre2py.LustreLexer import LustreLexer
from intrepyd.lustre2py.LustreParser import LustreParser
from intrepyd.lustre2py.astbuilder import ASTBuilder
from intrepyd.lustre2py.ast import Ast
from intrepyd.lustre2py.errors import LustreError

# Kind2's contracts: annotations in comments (--@, (*@ ... *), /*@ ... */) and
# contract nodes. The grammar would read the annotations as comments, and drop them.
_CONTRACTS = re.compile(r'--@|\(\*@|/\*@|^[ \t]*contract\b', re.MULTILINE)


class _Refuse(ErrorListener):
    """A syntax error stops the parse, said with its place (ANTLR prints it and goes on)."""

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):  # pylint: disable=invalid-name,too-many-arguments,too-many-positional-arguments
        raise LustreError(f'syntax error: {msg}', line, column + 1)


def parse(infile):
    """
    Parse the provided input file into the AST of its nodes. Raises
    LustreError, with the line, for a syntax error, a construct not
    supported, or Kind2's contracts.
    """
    with open(infile, encoding='utf-8') as handle:
        text = handle.read()
    contract = _CONTRACTS.search(text)
    if contract:
        line = text.count('\n', 0, contract.start()) + 1
        column = contract.start() - (text.rfind('\n', 0, contract.start()) + 1) + 1
        raise LustreError("Kind2's contracts are not supported", line, column)
    lexer = LustreLexer(InputStream(text))
    lexer.removeErrorListeners()
    lexer.addErrorListener(_Refuse())
    parser = LustreParser(CommonTokenStream(lexer))
    parser.removeErrorListeners()
    parser.addErrorListener(_Refuse())
    tree = parser.program()
    ast_builder = ASTBuilder()
    ast_builder.visit(tree)
    return Ast(ast_builder.nodes)
