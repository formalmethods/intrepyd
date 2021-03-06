/*
 * Copyright (C) 2017 Roberto Bruttomesso <roberto.bruttomesso@gmail.com>
 * 
 * This file is distributed under the terms of the 3-clause BSD License.
 * A copy of the license can be found in the root directory or at
 * https://opensource.org/licenses/BSD-3-Clause.
 * 
 * Author: Roberto Bruttomesso <roberto.bruttomesso@gmail.com>
 *   Date: 26/10/2017
 * 
 * A lexer for IEC61131-3 ST and IL languages
 */

grammar IEC61131Lexer;

fragment A              : [Aa];
fragment B              : [Bb];
fragment C              : [Cc];
fragment D              : [Dd];
fragment E              : [Ee];
fragment F              : [Ff];
fragment G              : [Gg];
fragment H              : [Hh];
fragment I              : [Ii];
fragment J              : [Jj];
fragment K              : [Kk];
fragment L              : [Ll];
fragment M              : [Mm];
fragment N              : [Nn];
fragment O              : [Oo];
fragment P              : [Pp];
fragment Q              : [Qq];
fragment R              : [Rr];
fragment S              : [Ss];
fragment T              : [Tt];
fragment U              : [Uu];
fragment V              : [Vv];
fragment W              : [Ww];
fragment X              : [Xx];
fragment Y              : [Yy];
fragment Z              : [Zz];

IEC_COMMENT             : '(*' (IEC_COMMENT|.)*? '*)' -> channel(HIDDEN);
C_COMMENT               : '/*' (C_COMMENT|.)*? '*/' -> channel(HIDDEN);
LINE_COMMENT            : '//' .*? '\n' -> channel(HIDDEN);

UDINT_TO_USINT          : U D I N T '_' T O '_' U S I N T;
USINT_TO_UDINT          : U S I N T '_' T O '_' U D I N T;
DINT_TO_UDINT           : D I N T '_' T O '_' U D I N T;
UDINT_TO_DINT           : U D I N T '_' T O '_' D I N T;
UINT_TO_USINT           : U I N T '_' T O '_' U S I N T;
USINT_TO_BYTE           : U S I N T '_' T O '_' B Y T E;
BYTE_TO_USINT           : B Y T E '_' T O '_' U S I N T;
USINT_TO_UINT           : U S I N T '_' T O '_' U I N T;
USINT_TO_DINT           : U S I N T '_' T O '_' D I N T;
DINT_TO_USINT           : D I N T '_' T O '_' U S I N T;
BYTE_TO_WORD            : B Y T E '_' T O '_' W O R D;
BYTE_TO_UINT            : B Y T E '_' T O '_' U I N T;
WORD_TO_BYTE            : W O R D '_' T O '_' B Y T E;
WORD_TO_UINT            : W O R D '_' T O '_' U I N T;
REAL_TO_UINT            : R E A L '_' T O '_' U I N T;
INT_TO_USINT            : I N T '_' T O '_' U S I N T;
UINT_TO_BOOL            : U I N T '_' T O '_' B O O L;
UINT_TO_WORD            : U I N T '_' T O '_' W O R D;
UINT_TO_REAL            : U I N T '_' T O '_' R E A L;
DINT_TO_UINT            : D I N T '_' T O '_' U I N T;
UINT_TO_DINT            : U I N T '_' T O '_' D I N T;
WORD_TO_INT             : W O R D '_' T O '_' I N T;
REAL_TO_INT             : R E A L '_' T O '_' I N T;
INT_TO_BOOL             : I N T '_' T O '_' B O O L;
BOOL_TO_INT             : B O O L '_' T O '_' I N T;
INT_TO_WORD             : I N T '_' T O '_' W O R D;
INT_TO_REAL             : I N T '_' T O '_' R E A L;
INT_TO_UINT             : I N T '_' T O '_' U I N T;
UINT_TO_INT             : U I N T '_' T O '_' I N T;

END_FUNCTION_BLOCK      : E N D '_' F U N C T I O N '_' B L O C K;
END_CONFIGURATION       : E N D '_' C O N F I G U R A T I O N;
END_TRANSITION          : E N D '_' T R A N S I T I O N;
LOC_PARTLY_VAR          : '%' ( I | Q | M );
FUNCTION_BLOCK          : F U N C T I O N '_' B L O C K;
END_INTERFACE           : E N D '_' I N T E R F A C E;
CONFIGURATION           : C O N F I G U R A T I O N;
MULTIBIT_PART           : '%' ( X | B | W | D | L );
DATE_AND_TIME           : D A T E '_' A N D '_' T I M E;
END_NAMESPACE           : E N D '_' N A M E S P A C E;
VAR_EXTERNAL            : V A R '_' E X T E R N A L;
END_FUNCTION            : E N D '_' F U N C T I O N;
END_RESOURCE            : E N D '_' R E S O U R C E;
INITIAL_STEP            : I N I T I A L '_' S T E P;
TIME_OF_DAY             : T I M E '_' O F '_' D A Y;
END_PROGRAM             : E N D '_' P R O G R A M;
END_ACTION              : E N D '_' A C T I O N;
END_METHOD              : E N D '_' M E T H O D;
TRANSITION              : T R A N S I T I O N;
VAR_GLOBAL              : V A R '_' G L O B A L;
NON_RETAIN              : N O N '_' R E T A I N;
NAMESPACE               : N A M E S P A C E;
VAR_OUTPUT              : V A R '_' O U T P U T;
VAR_IN_OUT              : V A R '_' I N '_' O U T;
VAR_ACCESS              : V A R '_' A C C E S S;
END_STRUCT              : E N D '_' S T R U C T;
READ_WRITE              : R E A D '_' W R I T E;
IMPLEMENTS              : I M P L E M E N T S;
VAR_CONFIG              : V A R '_' C O N F I G;
END_REPEAT              : E N D '_' R E P E A T;
END_WHILE               : E N D '_' W H I L E;
READ_ONLY               : R E A D '_' O N L Y;
PROTECTED               : P R O T E C T E D;
VAR_INPUT               : V A R '_' I N P U T;
END_CLASS               : E N D '_' C L A S S;
INTERFACE               : I N T E R F A C E;
ABSTRACT                : A B S T R A C T;
FUNCTION                : F U N C T I O N;
END_CASE                : E N D '_' C A S E;
RESOURCE                : R E S O U R C E;
INTERNAL                : I N T E R N A L;
CONTINUE                : C O N T I N U E;
PRIORITY                : P R I O R I T Y;
BOOL_EXP                : B O O L '_' E X P;
END_STEP                : E N D '_' S T E P;
CONSTANT                : C O N S T A N T;
OVERRIDE                : O V E R R I D E;
VAR_TEMP                : V A R '_' T E M P;
END_TYPE                : E N D '_' T Y P E;
INTERVAL                : I N T E R V A L;
EXTENDS                 : E X T E N D S;
PRIVATE                 : P R I V A T E;
TIME_MS                 : T '#' [0-9]+ M S;
PROGRAM                 : P R O G R A M;
END_VAR                 : E N D '_' V A R;
WSTRING                 : W S T R I N G;
OVERLAP                 : O V E R L A P;
END_FOR                 : E N D '_' F O R;
REPLACE                 : R E P L A C E;
PUBLIC                  : P U B L I C;
METHOD                  : M E T H O D;
ACTION                  : A C T I O N;
RETURN                  : R E T U R N;
STRING                  : S T R I N G;
STRUCT                  : S T R U C T;
RETAIN                  : R E T A I N;
TIME_S                  : T '#' [0-9]+ S;
R_EDGE                  : R '_' E D G E;
F_EDGE                  : F '_' E D G E;
R_TRIG                  : R '_' T R I G;
F_TRIG                  : F '_' T R I G;
REF_TO                  : R E F '_' T O;
SINGLE                  : S I N G L E;
END_IF                  : E N D '_' I F;
REPEAT                  : R E P E A T;
INSERT                  : I N S E R T;
DELETE                  : D E L E T E;
CONCAT                  : C O N C A T;
FINAL                   : F I N A L;
SUPER                   : S U P E R;
ARRAY                   : A R R A Y;
WCHAR                   : W C H A R;
USING                   : U S I N G;
CLASS                   : C L A S S;
FALSE                   : F A L S E;
DWORD                   : D W O R D;
LWORD                   : L W O R D;
USINT                   : U S I N T; 
UDINT                   : U D I N T;
ULINT                   : U L I N T;
LREAL                   : L R E A L;
LTIME                   : L T I M E;
LDATE                   : L D A T E;
CALCN                   : C A L C N;
RETCN                   : R E T C N;
JMPCN                   : J M P C N;
ELSIF                   : E L S I F;
WHILE                   : W H I L E;
UNTIL                   : U N T I L;
RIGHT                   : R I G H T;
LIMIT                   : L I M I T;
TRUNC                   : T R U N C;
ATAN2                   : A T A N '2';
EXIT                    : E X I T;
CASE                    : C A S E;
THIS                    : T H I S;
TASK                    : T A S K;
REAL                    : R E A L;
TIME                    : T I M E;
DATE                    : D A T E;
LTOD                    : L T O D;
BYTE                    : B Y T E;
WORD                    : W O R D;
CALC                    : C A L C;
TRUE                    : T R U E;
BOOL                    : B O O L;
WITH                    : W I T H;
STEP                    : S T E P;
CHAR                    : C H A R;
TYPE                    : T Y P E;
NULL                    : N U L L;
FROM                    : F R O M;
UINT                    : U I N T;
SINT                    : S I N T; 
DINT                    : D I N T;
LINT                    : L I N T;
ANDN                    : A N D N;
XORN                    : X O R N;
RETC                    : R E T C;
JMPC                    : J M P C;
THEN                    : T H E N;
ELSE                    : E L S E;
CTUD                    : C T U D;
SQRT                    : S Q R T;
ASIN                    : A S I N;
ACOS                    : A C O S;
ATAN                    : A T A N;
EXPT                    : E X P T;
MOVE                    : M O V E;
LEFT                    : L E F T;
FIND                    : F I N D;
FOR                     : F O R;
INT                     : I N T;
NOT                     : N O T;
MUL                     : M U L;
ADD                     : A D D;
TOD                     : T O D;
LDT                     : L D T;
VAR                     : V A R;
CAL                     : C A L;
CLK                     : C L K;
STN                     : S T N;
LDN                     : L D N;
AND                     : A N D;
XOR                     : X O R;
ORN                     : O R N;
SUB                     : S U B;
MOD                     : M O D;
DIV                     : D I V;
RET                     : R E T;
REF                     : R E F;
JMP                     : J M P;
CTU                     : C T U;
CTD                     : C T D;
TON                     : T O N;
TOF                     : T O F;
ABS                     : A B S;
LOG                     : L O G;
EXP                     : E X P;
SIN                     : S I N;
COS                     : C O S;
TAN                     : T A N;
SHL                     : S H L;
SHR                     : S H R;
ROL                     : R O L;
ROR                     : R O R;
SEL                     : S E L;
MAX                     : M A X;
MIN                     : M I N;
MUX                     : M U X;
LEN                     : L E N;
MID                     : M I D;
TP                      : T P;
SR                      : S R;
RS                      : R S;
BY                      : B Y;
DO                      : D O;
SD                      : S D;
DS                      : D S;
SL                      : S L;
DT                      : D T;
AT                      : A T;
CU                      : C U;
PV                      : P V;
PT                      : P T;
IN                      : I N;
OF                      : O F;
LD                      : L D;
TO                      : T O;
ON                      : O N;
ST                      : S T;
CD                      : C D;
OR                      : O R;
GT                      : G T;
GE                      : G E;
EQ                      : E Q;
LT                      : L T;
LE                      : L E;
NE                      : N E;
IF                      : I F;
LN                      : L N;

DIRECTVARIABLE          : [%][IQMRS][SDPA]?[SXBWDL]?[0-9]+('.'[0-9]+)*;
IDENTIFIER              : [A-Za-z_][A-Za-z0-9_]*;              
LETTER                  : [A-Za-z_];
DIGITS                  : [0-9]+;
BINARY_INT              : '2#' ( '_' ? [01] )+;
OCTAL_INT               : '8#' ( '_' ? [0-7] )+;
HEX_INT                 : '16#' ( '_' ? [0-9A-Fa-f] )+;
WS                      : [ \t\n\r]+ -> skip;
PRAGMA                  : '{' .*? '}' -> channel(HIDDEN);

ErrorCharacter          : . ;