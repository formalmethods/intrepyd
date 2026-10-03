# Generated from Formula.g4 by ANTLR 4.9.1
from antlr4 import *
from io import StringIO
from typing import TextIO
import sys



def serializedATN():
    with StringIO() as buf:
        buf.write("\3\u608b\ua72a\u8133\ub9ed\u417c\u3be7\u7786\u5964\2\17")
        buf.write("O\b\1\4\2\t\2\4\3\t\3\4\4\t\4\4\5\t\5\4\6\t\6\4\7\t\7")
        buf.write("\4\b\t\b\4\t\t\t\4\n\t\n\4\13\t\13\4\f\t\f\4\r\t\r\4\16")
        buf.write("\t\16\3\2\3\2\3\2\3\2\3\3\3\3\3\3\3\3\3\4\3\4\3\4\3\4")
        buf.write("\3\5\3\5\3\5\3\5\3\6\3\6\3\6\3\6\3\7\3\7\3\7\3\7\3\b\3")
        buf.write("\b\3\b\3\t\3\t\3\t\3\n\3\n\3\13\3\13\3\f\3\f\7\fB\n\f")
        buf.write("\f\f\16\fE\13\f\3\r\6\rH\n\r\r\r\16\rI\3\r\3\r\3\16\3")
        buf.write("\16\2\2\17\3\3\5\4\7\5\t\6\13\7\r\b\17\t\21\n\23\13\25")
        buf.write("\f\27\r\31\16\33\17\3\2\5\5\2C\\aac|\6\2\62;C\\aac|\5")
        buf.write("\2\13\f\16\17\"\"\2P\2\3\3\2\2\2\2\5\3\2\2\2\2\7\3\2\2")
        buf.write("\2\2\t\3\2\2\2\2\13\3\2\2\2\2\r\3\2\2\2\2\17\3\2\2\2\2")
        buf.write("\21\3\2\2\2\2\23\3\2\2\2\2\25\3\2\2\2\2\27\3\2\2\2\2\31")
        buf.write("\3\2\2\2\2\33\3\2\2\2\3\35\3\2\2\2\5!\3\2\2\2\7%\3\2\2")
        buf.write("\2\t)\3\2\2\2\13-\3\2\2\2\r\61\3\2\2\2\17\65\3\2\2\2\21")
        buf.write("8\3\2\2\2\23;\3\2\2\2\25=\3\2\2\2\27?\3\2\2\2\31G\3\2")
        buf.write("\2\2\33M\3\2\2\2\35\36\7p\2\2\36\37\7q\2\2\37 \7v\2\2")
        buf.write(" \4\3\2\2\2!\"\7P\2\2\"#\7Q\2\2#$\7V\2\2$\6\3\2\2\2%&")
        buf.write("\7r\2\2&\'\7t\2\2\'(\7g\2\2(\b\3\2\2\2)*\7R\2\2*+\7T\2")
        buf.write("\2+,\7G\2\2,\n\3\2\2\2-.\7c\2\2./\7p\2\2/\60\7f\2\2\60")
        buf.write("\f\3\2\2\2\61\62\7C\2\2\62\63\7P\2\2\63\64\7F\2\2\64\16")
        buf.write("\3\2\2\2\65\66\7q\2\2\66\67\7t\2\2\67\20\3\2\2\289\7Q")
        buf.write("\2\29:\7T\2\2:\22\3\2\2\2;<\7*\2\2<\24\3\2\2\2=>\7+\2")
        buf.write("\2>\26\3\2\2\2?C\t\2\2\2@B\t\3\2\2A@\3\2\2\2BE\3\2\2\2")
        buf.write("CA\3\2\2\2CD\3\2\2\2D\30\3\2\2\2EC\3\2\2\2FH\t\4\2\2G")
        buf.write("F\3\2\2\2HI\3\2\2\2IG\3\2\2\2IJ\3\2\2\2JK\3\2\2\2KL\b")
        buf.write("\r\2\2L\32\3\2\2\2MN\13\2\2\2N\34\3\2\2\2\5\2CI\3\b\2")
        buf.write("\2")
        return buf.getvalue()


class FormulaLexer(Lexer):

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [ DFA(ds, i) for i, ds in enumerate(atn.decisionToState) ]

    T__0 = 1
    T__1 = 2
    T__2 = 3
    T__3 = 4
    T__4 = 5
    T__5 = 6
    T__6 = 7
    T__7 = 8
    T__8 = 9
    T__9 = 10
    ID = 11
    WS = 12
    ERROR = 13

    channelNames = [ u"DEFAULT_TOKEN_CHANNEL", u"HIDDEN" ]

    modeNames = [ "DEFAULT_MODE" ]

    literalNames = [ "<INVALID>",
            "'not'", "'NOT'", "'pre'", "'PRE'", "'and'", "'AND'", "'or'", 
            "'OR'", "'('", "')'" ]

    symbolicNames = [ "<INVALID>",
            "ID", "WS", "ERROR" ]

    ruleNames = [ "T__0", "T__1", "T__2", "T__3", "T__4", "T__5", "T__6", 
                  "T__7", "T__8", "T__9", "ID", "WS", "ERROR" ]

    grammarFileName = "Formula.g4"

    def __init__(self, input=None, output:TextIO = sys.stdout):
        super().__init__(input, output)
        self.checkVersion("4.9.1")
        self._interp = LexerATNSimulator(self, self.atn, self.decisionsToDFA, PredictionContextCache())
        self._actions = None
        self._predicates = None


