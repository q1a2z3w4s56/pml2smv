grammar Promela;

// ==================== Parser Rules ====================

spec:  module* EOF;

module: mtypeDecl
      | chanDecl
      | varDecl
      | typedefDecl
      | proctype
      | init
      | inlineDecl
      | defineDecl
      ;

// Preprocessor define
defineDecl: '#' 'define' ID defineBody;
defineBody:  expr;

// Mtype declaration
mtypeDecl: 'mtype' ('=' '{' ID (',' ID)* '}')? ';'? ;

// Channel declaration
chanDecl:  'chan' ID ('=' '[' expr ']' 'of' '{' typename (',' typename)* '}')? ';'?;

// Variable declaration
varDecl: typename varItem (',' varItem)* ';'? ;

varItem: ID ('[' expr ']')? ('=' expr)?;

// Type names
typename: 'bit' | 'bool' | 'byte' | 'short' | 'int' | 'mtype' | 'chan' | 'pid' | 'unsigned';

// Typedef
typedefDecl: 'typedef' ID '{' varDecl+ '}' ';'?;

// Process type declaration
proctype: ('active' ('[' expr ']')?)? 'proctype' ID '(' paramList?  ')'
          ('priority' expr)? ('provided' '(' expr ')')?
          '{' sequence '}';

paramList: paramGroup (';' paramGroup)*;
paramGroup: typename ID (',' ID)*;

// Init process
init: 'init' ('priority' expr)? '{' sequence '}';

// Inline declaration
inlineDecl: 'inline' ID '(' (ID (',' ID)*)? ')' '{' sequence '}';

// Sequence
sequence: step*;

// Step
step: varDecl
    | xrxsDecl
    | stmt ('unless' stmt)? (';' | '->')?
    | ID ':'                                    // 标签
    ;

// xr/xs exclusive channel declarations
xrxsDecl: ('xr' | 'xs') ID (',' ID)* ';'?;

// Statement
stmt: 'skip'                                                    # skipStmt
    | 'break'                                                   # breakStmt
    | 'goto' ID                                                 # gotoStmt
    | ID ':' stmt                                               # labeledStmt   // 修复：去掉了冒号后的空格
    | 'if' optionList 'fi'                                      # ifStmt
    | 'do' optionList 'od'                                      # doStmt
    | 'atomic' '{' sequence '}'                                 # atomicStmt
    | 'd_step' '{' sequence '}'                                 # dstepStmt
    | '{' sequence '}'                                          # blockStmt
    | 'assert' '(' expr ')'                                     # assertStmt
    | 'printf' '(' STRING (',' expr)* ')'                       # printfStmt
    | 'printm' '(' expr ')'                                     # printmStmt
    | sendStmt                                                  # sendStatement
    | receiveStmt                                               # receiveStatement
    | 'run' ID '(' argList?  ')'                                # runStmt
    | ID '(' argList?  ')'                                      # callStmt
    | assignment                                                # assignStatement
    | expr                                                      # exprStmt
    | 'select' '(' ID ':' expr '..' expr ')'                    # selectStmt  // 修复：点号不转义
    | 'for' '(' ID ':' expr '..' expr ')' '{' sequence '}'      # forStmt     // 修复：点号不转义
    ;

// Send statement
sendStmt:  varRef '!' argList                                    # normalSend
        | varRef '!!' argList                                    # sortedSend  // 修复：去掉了空格
        ;

// Receive statement
receiveStmt: varRef '?' recvArgs                                # normalRecv
           | varRef '??' recvArgs                               # randomRecv   // 修复：去掉了空格
           | varRef '?' '<' recvArgs '>'                        # pollRecv
           | varRef '??' '<' recvArgs '>'                       # randomPollRecv // 修复：去掉了空格
           ;

recvArgs: recvArg (',' recvArg)*;
recvArg: 'eval' '(' expr ')' | expr;

assignment: varRef '=' expr                                     # assignExpr
          | varRef '++'                                         # incrExpr
          | varRef '--'                                         # decrExpr
          ;

varRef: ID ('[' expr ']')? ('.' ID ('[' expr ']')?)*;

argList: expr (',' expr)*;

// Option list
optionList: option+;

option: '::' sequence                                           # optionNormal // 修复：去掉了空格
      | '::' 'else' ('->' | ';')? sequence                      # optionElse
      ;

// ==================== Expressions ====================

expr: '(' expr ')'                                              # parenExpr
    | varRef                                                    # varRefExpr
    | NUMBER                                                    # numberExpr
    | 'true'                                                    # trueExpr
    | 'false'                                                   # falseExpr
    | STRING                                                    # stringExpr
    | '_pid'                                                    # pidExpr
    | '_nr_pr'                                                  # nrPrExpr
    | '_last'                                                   # lastExpr
    | 'timeout'                                                 # timeoutExpr
    | 'np_'                                                     # npExpr
    | 'len' '(' varRef ')'                                      # lenExpr
    | 'empty' '(' varRef ')'                                    # emptyExpr
    | 'nempty' '(' varRef ')'                                   # nemptyExpr
    | 'full' '(' varRef ')'                                     # fullExpr
    | 'nfull' '(' varRef ')'                                    # nfullExpr
    | 'enabled' '(' expr ')'                                    # enabledExpr
    | 'pc_value' '(' expr ')'                                   # pcValueExpr
    | 'run' ID '(' argList?  ')'                                # runExpr
    | '!' expr                                                  # notExpr
    | '~' expr                                                  # bitwiseNotExpr
    | '-' expr                                                  # unaryMinusExpr
    | '+' expr                                                  # unaryPlusExpr
    | expr ('*' | '/' | '%') expr                               # mulDivModExpr
    | expr ('+' | '-') expr                                     # addSubExpr
    | expr ('<<' | '>>') expr                                   # shiftExpr
    | expr ('<' | '<=' | '>' | '>=') expr                       # relationalExpr
    | expr ('==' | '!=') expr                                   # equalityExpr
    | expr '&' expr                                             # bitwiseAndExpr
    | expr '^' expr                                             # bitwiseXorExpr
    | expr '|' expr                                             # bitwiseOrExpr
    | expr '&&' expr                                            # logicalAndExpr
    | expr '||' expr                                            # logicalOrExpr
    | expr '->' expr ':' expr                                   # conditionalExpr // 修复：去掉了冒号后的空格
    | expr '->' expr                                            # impliesExpr
    ;

// ==================== Lexer Rules ====================

// 多字符操作符
SORTED_SEND: '!!'; // 修复：去掉了空格
RANDOM_RECV: '??'; // 修复：去掉了空格
INCR: '++';
DECR: '--';
LSHIFT: '<<';
RSHIFT: '>>';
LE: '<=';
GE: '>=';
EQEQ:  '==';
NE: '!=';
AND: '&&';
OR: '||';
ARROW: '->';
COLONS: '::';

// 基本 tokens
NUMBER: [0-9]+;
ID:  [a-zA-Z_][a-zA-Z0-9_]*;
STRING: '"' (~["\\\r\n] | '\\' .)* '"';

// 跳过
COMMENT: '/*' .*?  '*/' -> skip;
LINE_COMMENT: '//' ~[\r\n]* -> skip;
WS: [ \t\r\n]+ -> skip;