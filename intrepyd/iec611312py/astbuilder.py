"""
Copyright (C) 2018 Roberto Bruttomesso <roberto.bruttomesso@gmail.com>

This file is distributed under the terms of the 3-clause BSD License.
A copy of the license can be found in the root directory or at
https://opensource.org/licenses/BSD-3-Clause.

Author: Roberto Bruttomesso <roberto.bruttomesso@gmail.com>
  Date: 29/10/2018

This module implements the main parsing routine of IEC61131 text
"""

from intrepyd.iec611312py.IEC61131ParserVisitor import IEC61131ParserVisitor

class ASTBuilder(IEC61131ParserVisitor):
    """
    Vistor that builds the internal AST for the
    IEC program
    """
    def __init__(self):
        pass
