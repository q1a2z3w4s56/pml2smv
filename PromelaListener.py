# Generated from Promela.g4 by ANTLR 4.13.2
from antlr4 import *
if "." in __name__:
    from .PromelaParser import PromelaParser
else:
    from PromelaParser import PromelaParser

# This class defines a complete listener for a parse tree produced by PromelaParser.
class PromelaListener(ParseTreeListener):

    # Enter a parse tree produced by PromelaParser#spec.
    def enterSpec(self, ctx:PromelaParser.SpecContext):
        pass

    # Exit a parse tree produced by PromelaParser#spec.
    def exitSpec(self, ctx:PromelaParser.SpecContext):
        pass


    # Enter a parse tree produced by PromelaParser#module.
    def enterModule(self, ctx:PromelaParser.ModuleContext):
        pass

    # Exit a parse tree produced by PromelaParser#module.
    def exitModule(self, ctx:PromelaParser.ModuleContext):
        pass


    # Enter a parse tree produced by PromelaParser#defineDecl.
    def enterDefineDecl(self, ctx:PromelaParser.DefineDeclContext):
        pass

    # Exit a parse tree produced by PromelaParser#defineDecl.
    def exitDefineDecl(self, ctx:PromelaParser.DefineDeclContext):
        pass


    # Enter a parse tree produced by PromelaParser#defineBody.
    def enterDefineBody(self, ctx:PromelaParser.DefineBodyContext):
        pass

    # Exit a parse tree produced by PromelaParser#defineBody.
    def exitDefineBody(self, ctx:PromelaParser.DefineBodyContext):
        pass


    # Enter a parse tree produced by PromelaParser#mtypeDecl.
    def enterMtypeDecl(self, ctx:PromelaParser.MtypeDeclContext):
        pass

    # Exit a parse tree produced by PromelaParser#mtypeDecl.
    def exitMtypeDecl(self, ctx:PromelaParser.MtypeDeclContext):
        pass


    # Enter a parse tree produced by PromelaParser#chanDecl.
    def enterChanDecl(self, ctx:PromelaParser.ChanDeclContext):
        pass

    # Exit a parse tree produced by PromelaParser#chanDecl.
    def exitChanDecl(self, ctx:PromelaParser.ChanDeclContext):
        pass


    # Enter a parse tree produced by PromelaParser#varDecl.
    def enterVarDecl(self, ctx:PromelaParser.VarDeclContext):
        pass

    # Exit a parse tree produced by PromelaParser#varDecl.
    def exitVarDecl(self, ctx:PromelaParser.VarDeclContext):
        pass


    # Enter a parse tree produced by PromelaParser#varItem.
    def enterVarItem(self, ctx:PromelaParser.VarItemContext):
        pass

    # Exit a parse tree produced by PromelaParser#varItem.
    def exitVarItem(self, ctx:PromelaParser.VarItemContext):
        pass


    # Enter a parse tree produced by PromelaParser#typename.
    def enterTypename(self, ctx:PromelaParser.TypenameContext):
        pass

    # Exit a parse tree produced by PromelaParser#typename.
    def exitTypename(self, ctx:PromelaParser.TypenameContext):
        pass


    # Enter a parse tree produced by PromelaParser#typedefDecl.
    def enterTypedefDecl(self, ctx:PromelaParser.TypedefDeclContext):
        pass

    # Exit a parse tree produced by PromelaParser#typedefDecl.
    def exitTypedefDecl(self, ctx:PromelaParser.TypedefDeclContext):
        pass


    # Enter a parse tree produced by PromelaParser#proctype.
    def enterProctype(self, ctx:PromelaParser.ProctypeContext):
        pass

    # Exit a parse tree produced by PromelaParser#proctype.
    def exitProctype(self, ctx:PromelaParser.ProctypeContext):
        pass


    # Enter a parse tree produced by PromelaParser#paramList.
    def enterParamList(self, ctx:PromelaParser.ParamListContext):
        pass

    # Exit a parse tree produced by PromelaParser#paramList.
    def exitParamList(self, ctx:PromelaParser.ParamListContext):
        pass


    # Enter a parse tree produced by PromelaParser#paramGroup.
    def enterParamGroup(self, ctx:PromelaParser.ParamGroupContext):
        pass

    # Exit a parse tree produced by PromelaParser#paramGroup.
    def exitParamGroup(self, ctx:PromelaParser.ParamGroupContext):
        pass


    # Enter a parse tree produced by PromelaParser#init.
    def enterInit(self, ctx:PromelaParser.InitContext):
        pass

    # Exit a parse tree produced by PromelaParser#init.
    def exitInit(self, ctx:PromelaParser.InitContext):
        pass


    # Enter a parse tree produced by PromelaParser#inlineDecl.
    def enterInlineDecl(self, ctx:PromelaParser.InlineDeclContext):
        pass

    # Exit a parse tree produced by PromelaParser#inlineDecl.
    def exitInlineDecl(self, ctx:PromelaParser.InlineDeclContext):
        pass


    # Enter a parse tree produced by PromelaParser#sequence.
    def enterSequence(self, ctx:PromelaParser.SequenceContext):
        pass

    # Exit a parse tree produced by PromelaParser#sequence.
    def exitSequence(self, ctx:PromelaParser.SequenceContext):
        pass


    # Enter a parse tree produced by PromelaParser#step.
    def enterStep(self, ctx:PromelaParser.StepContext):
        pass

    # Exit a parse tree produced by PromelaParser#step.
    def exitStep(self, ctx:PromelaParser.StepContext):
        pass


    # Enter a parse tree produced by PromelaParser#xrxsDecl.
    def enterXrxsDecl(self, ctx:PromelaParser.XrxsDeclContext):
        pass

    # Exit a parse tree produced by PromelaParser#xrxsDecl.
    def exitXrxsDecl(self, ctx:PromelaParser.XrxsDeclContext):
        pass


    # Enter a parse tree produced by PromelaParser#skipStmt.
    def enterSkipStmt(self, ctx:PromelaParser.SkipStmtContext):
        pass

    # Exit a parse tree produced by PromelaParser#skipStmt.
    def exitSkipStmt(self, ctx:PromelaParser.SkipStmtContext):
        pass


    # Enter a parse tree produced by PromelaParser#breakStmt.
    def enterBreakStmt(self, ctx:PromelaParser.BreakStmtContext):
        pass

    # Exit a parse tree produced by PromelaParser#breakStmt.
    def exitBreakStmt(self, ctx:PromelaParser.BreakStmtContext):
        pass


    # Enter a parse tree produced by PromelaParser#gotoStmt.
    def enterGotoStmt(self, ctx:PromelaParser.GotoStmtContext):
        pass

    # Exit a parse tree produced by PromelaParser#gotoStmt.
    def exitGotoStmt(self, ctx:PromelaParser.GotoStmtContext):
        pass


    # Enter a parse tree produced by PromelaParser#labeledStmt.
    def enterLabeledStmt(self, ctx:PromelaParser.LabeledStmtContext):
        pass

    # Exit a parse tree produced by PromelaParser#labeledStmt.
    def exitLabeledStmt(self, ctx:PromelaParser.LabeledStmtContext):
        pass


    # Enter a parse tree produced by PromelaParser#ifStmt.
    def enterIfStmt(self, ctx:PromelaParser.IfStmtContext):
        pass

    # Exit a parse tree produced by PromelaParser#ifStmt.
    def exitIfStmt(self, ctx:PromelaParser.IfStmtContext):
        pass


    # Enter a parse tree produced by PromelaParser#doStmt.
    def enterDoStmt(self, ctx:PromelaParser.DoStmtContext):
        pass

    # Exit a parse tree produced by PromelaParser#doStmt.
    def exitDoStmt(self, ctx:PromelaParser.DoStmtContext):
        pass


    # Enter a parse tree produced by PromelaParser#atomicStmt.
    def enterAtomicStmt(self, ctx:PromelaParser.AtomicStmtContext):
        pass

    # Exit a parse tree produced by PromelaParser#atomicStmt.
    def exitAtomicStmt(self, ctx:PromelaParser.AtomicStmtContext):
        pass


    # Enter a parse tree produced by PromelaParser#dstepStmt.
    def enterDstepStmt(self, ctx:PromelaParser.DstepStmtContext):
        pass

    # Exit a parse tree produced by PromelaParser#dstepStmt.
    def exitDstepStmt(self, ctx:PromelaParser.DstepStmtContext):
        pass


    # Enter a parse tree produced by PromelaParser#blockStmt.
    def enterBlockStmt(self, ctx:PromelaParser.BlockStmtContext):
        pass

    # Exit a parse tree produced by PromelaParser#blockStmt.
    def exitBlockStmt(self, ctx:PromelaParser.BlockStmtContext):
        pass


    # Enter a parse tree produced by PromelaParser#assertStmt.
    def enterAssertStmt(self, ctx:PromelaParser.AssertStmtContext):
        pass

    # Exit a parse tree produced by PromelaParser#assertStmt.
    def exitAssertStmt(self, ctx:PromelaParser.AssertStmtContext):
        pass


    # Enter a parse tree produced by PromelaParser#printfStmt.
    def enterPrintfStmt(self, ctx:PromelaParser.PrintfStmtContext):
        pass

    # Exit a parse tree produced by PromelaParser#printfStmt.
    def exitPrintfStmt(self, ctx:PromelaParser.PrintfStmtContext):
        pass


    # Enter a parse tree produced by PromelaParser#printmStmt.
    def enterPrintmStmt(self, ctx:PromelaParser.PrintmStmtContext):
        pass

    # Exit a parse tree produced by PromelaParser#printmStmt.
    def exitPrintmStmt(self, ctx:PromelaParser.PrintmStmtContext):
        pass


    # Enter a parse tree produced by PromelaParser#sendStatement.
    def enterSendStatement(self, ctx:PromelaParser.SendStatementContext):
        pass

    # Exit a parse tree produced by PromelaParser#sendStatement.
    def exitSendStatement(self, ctx:PromelaParser.SendStatementContext):
        pass


    # Enter a parse tree produced by PromelaParser#receiveStatement.
    def enterReceiveStatement(self, ctx:PromelaParser.ReceiveStatementContext):
        pass

    # Exit a parse tree produced by PromelaParser#receiveStatement.
    def exitReceiveStatement(self, ctx:PromelaParser.ReceiveStatementContext):
        pass


    # Enter a parse tree produced by PromelaParser#runStmt.
    def enterRunStmt(self, ctx:PromelaParser.RunStmtContext):
        pass

    # Exit a parse tree produced by PromelaParser#runStmt.
    def exitRunStmt(self, ctx:PromelaParser.RunStmtContext):
        pass


    # Enter a parse tree produced by PromelaParser#callStmt.
    def enterCallStmt(self, ctx:PromelaParser.CallStmtContext):
        pass

    # Exit a parse tree produced by PromelaParser#callStmt.
    def exitCallStmt(self, ctx:PromelaParser.CallStmtContext):
        pass


    # Enter a parse tree produced by PromelaParser#assignStatement.
    def enterAssignStatement(self, ctx:PromelaParser.AssignStatementContext):
        pass

    # Exit a parse tree produced by PromelaParser#assignStatement.
    def exitAssignStatement(self, ctx:PromelaParser.AssignStatementContext):
        pass


    # Enter a parse tree produced by PromelaParser#exprStmt.
    def enterExprStmt(self, ctx:PromelaParser.ExprStmtContext):
        pass

    # Exit a parse tree produced by PromelaParser#exprStmt.
    def exitExprStmt(self, ctx:PromelaParser.ExprStmtContext):
        pass


    # Enter a parse tree produced by PromelaParser#selectStmt.
    def enterSelectStmt(self, ctx:PromelaParser.SelectStmtContext):
        pass

    # Exit a parse tree produced by PromelaParser#selectStmt.
    def exitSelectStmt(self, ctx:PromelaParser.SelectStmtContext):
        pass


    # Enter a parse tree produced by PromelaParser#forStmt.
    def enterForStmt(self, ctx:PromelaParser.ForStmtContext):
        pass

    # Exit a parse tree produced by PromelaParser#forStmt.
    def exitForStmt(self, ctx:PromelaParser.ForStmtContext):
        pass


    # Enter a parse tree produced by PromelaParser#normalSend.
    def enterNormalSend(self, ctx:PromelaParser.NormalSendContext):
        pass

    # Exit a parse tree produced by PromelaParser#normalSend.
    def exitNormalSend(self, ctx:PromelaParser.NormalSendContext):
        pass


    # Enter a parse tree produced by PromelaParser#sortedSend.
    def enterSortedSend(self, ctx:PromelaParser.SortedSendContext):
        pass

    # Exit a parse tree produced by PromelaParser#sortedSend.
    def exitSortedSend(self, ctx:PromelaParser.SortedSendContext):
        pass


    # Enter a parse tree produced by PromelaParser#normalRecv.
    def enterNormalRecv(self, ctx:PromelaParser.NormalRecvContext):
        pass

    # Exit a parse tree produced by PromelaParser#normalRecv.
    def exitNormalRecv(self, ctx:PromelaParser.NormalRecvContext):
        pass


    # Enter a parse tree produced by PromelaParser#randomRecv.
    def enterRandomRecv(self, ctx:PromelaParser.RandomRecvContext):
        pass

    # Exit a parse tree produced by PromelaParser#randomRecv.
    def exitRandomRecv(self, ctx:PromelaParser.RandomRecvContext):
        pass


    # Enter a parse tree produced by PromelaParser#pollRecv.
    def enterPollRecv(self, ctx:PromelaParser.PollRecvContext):
        pass

    # Exit a parse tree produced by PromelaParser#pollRecv.
    def exitPollRecv(self, ctx:PromelaParser.PollRecvContext):
        pass


    # Enter a parse tree produced by PromelaParser#randomPollRecv.
    def enterRandomPollRecv(self, ctx:PromelaParser.RandomPollRecvContext):
        pass

    # Exit a parse tree produced by PromelaParser#randomPollRecv.
    def exitRandomPollRecv(self, ctx:PromelaParser.RandomPollRecvContext):
        pass


    # Enter a parse tree produced by PromelaParser#recvArgs.
    def enterRecvArgs(self, ctx:PromelaParser.RecvArgsContext):
        pass

    # Exit a parse tree produced by PromelaParser#recvArgs.
    def exitRecvArgs(self, ctx:PromelaParser.RecvArgsContext):
        pass


    # Enter a parse tree produced by PromelaParser#recvArg.
    def enterRecvArg(self, ctx:PromelaParser.RecvArgContext):
        pass

    # Exit a parse tree produced by PromelaParser#recvArg.
    def exitRecvArg(self, ctx:PromelaParser.RecvArgContext):
        pass


    # Enter a parse tree produced by PromelaParser#assignExpr.
    def enterAssignExpr(self, ctx:PromelaParser.AssignExprContext):
        pass

    # Exit a parse tree produced by PromelaParser#assignExpr.
    def exitAssignExpr(self, ctx:PromelaParser.AssignExprContext):
        pass


    # Enter a parse tree produced by PromelaParser#incrExpr.
    def enterIncrExpr(self, ctx:PromelaParser.IncrExprContext):
        pass

    # Exit a parse tree produced by PromelaParser#incrExpr.
    def exitIncrExpr(self, ctx:PromelaParser.IncrExprContext):
        pass


    # Enter a parse tree produced by PromelaParser#decrExpr.
    def enterDecrExpr(self, ctx:PromelaParser.DecrExprContext):
        pass

    # Exit a parse tree produced by PromelaParser#decrExpr.
    def exitDecrExpr(self, ctx:PromelaParser.DecrExprContext):
        pass


    # Enter a parse tree produced by PromelaParser#varRef.
    def enterVarRef(self, ctx:PromelaParser.VarRefContext):
        pass

    # Exit a parse tree produced by PromelaParser#varRef.
    def exitVarRef(self, ctx:PromelaParser.VarRefContext):
        pass


    # Enter a parse tree produced by PromelaParser#argList.
    def enterArgList(self, ctx:PromelaParser.ArgListContext):
        pass

    # Exit a parse tree produced by PromelaParser#argList.
    def exitArgList(self, ctx:PromelaParser.ArgListContext):
        pass


    # Enter a parse tree produced by PromelaParser#optionList.
    def enterOptionList(self, ctx:PromelaParser.OptionListContext):
        pass

    # Exit a parse tree produced by PromelaParser#optionList.
    def exitOptionList(self, ctx:PromelaParser.OptionListContext):
        pass


    # Enter a parse tree produced by PromelaParser#optionNormal.
    def enterOptionNormal(self, ctx:PromelaParser.OptionNormalContext):
        pass

    # Exit a parse tree produced by PromelaParser#optionNormal.
    def exitOptionNormal(self, ctx:PromelaParser.OptionNormalContext):
        pass


    # Enter a parse tree produced by PromelaParser#optionElse.
    def enterOptionElse(self, ctx:PromelaParser.OptionElseContext):
        pass

    # Exit a parse tree produced by PromelaParser#optionElse.
    def exitOptionElse(self, ctx:PromelaParser.OptionElseContext):
        pass


    # Enter a parse tree produced by PromelaParser#lenExpr.
    def enterLenExpr(self, ctx:PromelaParser.LenExprContext):
        pass

    # Exit a parse tree produced by PromelaParser#lenExpr.
    def exitLenExpr(self, ctx:PromelaParser.LenExprContext):
        pass


    # Enter a parse tree produced by PromelaParser#trueExpr.
    def enterTrueExpr(self, ctx:PromelaParser.TrueExprContext):
        pass

    # Exit a parse tree produced by PromelaParser#trueExpr.
    def exitTrueExpr(self, ctx:PromelaParser.TrueExprContext):
        pass


    # Enter a parse tree produced by PromelaParser#numberExpr.
    def enterNumberExpr(self, ctx:PromelaParser.NumberExprContext):
        pass

    # Exit a parse tree produced by PromelaParser#numberExpr.
    def exitNumberExpr(self, ctx:PromelaParser.NumberExprContext):
        pass


    # Enter a parse tree produced by PromelaParser#bitwiseOrExpr.
    def enterBitwiseOrExpr(self, ctx:PromelaParser.BitwiseOrExprContext):
        pass

    # Exit a parse tree produced by PromelaParser#bitwiseOrExpr.
    def exitBitwiseOrExpr(self, ctx:PromelaParser.BitwiseOrExprContext):
        pass


    # Enter a parse tree produced by PromelaParser#nrPrExpr.
    def enterNrPrExpr(self, ctx:PromelaParser.NrPrExprContext):
        pass

    # Exit a parse tree produced by PromelaParser#nrPrExpr.
    def exitNrPrExpr(self, ctx:PromelaParser.NrPrExprContext):
        pass


    # Enter a parse tree produced by PromelaParser#bitwiseAndExpr.
    def enterBitwiseAndExpr(self, ctx:PromelaParser.BitwiseAndExprContext):
        pass

    # Exit a parse tree produced by PromelaParser#bitwiseAndExpr.
    def exitBitwiseAndExpr(self, ctx:PromelaParser.BitwiseAndExprContext):
        pass


    # Enter a parse tree produced by PromelaParser#mulDivModExpr.
    def enterMulDivModExpr(self, ctx:PromelaParser.MulDivModExprContext):
        pass

    # Exit a parse tree produced by PromelaParser#mulDivModExpr.
    def exitMulDivModExpr(self, ctx:PromelaParser.MulDivModExprContext):
        pass


    # Enter a parse tree produced by PromelaParser#bitwiseNotExpr.
    def enterBitwiseNotExpr(self, ctx:PromelaParser.BitwiseNotExprContext):
        pass

    # Exit a parse tree produced by PromelaParser#bitwiseNotExpr.
    def exitBitwiseNotExpr(self, ctx:PromelaParser.BitwiseNotExprContext):
        pass


    # Enter a parse tree produced by PromelaParser#parenExpr.
    def enterParenExpr(self, ctx:PromelaParser.ParenExprContext):
        pass

    # Exit a parse tree produced by PromelaParser#parenExpr.
    def exitParenExpr(self, ctx:PromelaParser.ParenExprContext):
        pass


    # Enter a parse tree produced by PromelaParser#timeoutExpr.
    def enterTimeoutExpr(self, ctx:PromelaParser.TimeoutExprContext):
        pass

    # Exit a parse tree produced by PromelaParser#timeoutExpr.
    def exitTimeoutExpr(self, ctx:PromelaParser.TimeoutExprContext):
        pass


    # Enter a parse tree produced by PromelaParser#stringExpr.
    def enterStringExpr(self, ctx:PromelaParser.StringExprContext):
        pass

    # Exit a parse tree produced by PromelaParser#stringExpr.
    def exitStringExpr(self, ctx:PromelaParser.StringExprContext):
        pass


    # Enter a parse tree produced by PromelaParser#nemptyExpr.
    def enterNemptyExpr(self, ctx:PromelaParser.NemptyExprContext):
        pass

    # Exit a parse tree produced by PromelaParser#nemptyExpr.
    def exitNemptyExpr(self, ctx:PromelaParser.NemptyExprContext):
        pass


    # Enter a parse tree produced by PromelaParser#enabledExpr.
    def enterEnabledExpr(self, ctx:PromelaParser.EnabledExprContext):
        pass

    # Exit a parse tree produced by PromelaParser#enabledExpr.
    def exitEnabledExpr(self, ctx:PromelaParser.EnabledExprContext):
        pass


    # Enter a parse tree produced by PromelaParser#unaryMinusExpr.
    def enterUnaryMinusExpr(self, ctx:PromelaParser.UnaryMinusExprContext):
        pass

    # Exit a parse tree produced by PromelaParser#unaryMinusExpr.
    def exitUnaryMinusExpr(self, ctx:PromelaParser.UnaryMinusExprContext):
        pass


    # Enter a parse tree produced by PromelaParser#lastExpr.
    def enterLastExpr(self, ctx:PromelaParser.LastExprContext):
        pass

    # Exit a parse tree produced by PromelaParser#lastExpr.
    def exitLastExpr(self, ctx:PromelaParser.LastExprContext):
        pass


    # Enter a parse tree produced by PromelaParser#npExpr.
    def enterNpExpr(self, ctx:PromelaParser.NpExprContext):
        pass

    # Exit a parse tree produced by PromelaParser#npExpr.
    def exitNpExpr(self, ctx:PromelaParser.NpExprContext):
        pass


    # Enter a parse tree produced by PromelaParser#falseExpr.
    def enterFalseExpr(self, ctx:PromelaParser.FalseExprContext):
        pass

    # Exit a parse tree produced by PromelaParser#falseExpr.
    def exitFalseExpr(self, ctx:PromelaParser.FalseExprContext):
        pass


    # Enter a parse tree produced by PromelaParser#conditionalExpr.
    def enterConditionalExpr(self, ctx:PromelaParser.ConditionalExprContext):
        pass

    # Exit a parse tree produced by PromelaParser#conditionalExpr.
    def exitConditionalExpr(self, ctx:PromelaParser.ConditionalExprContext):
        pass


    # Enter a parse tree produced by PromelaParser#addSubExpr.
    def enterAddSubExpr(self, ctx:PromelaParser.AddSubExprContext):
        pass

    # Exit a parse tree produced by PromelaParser#addSubExpr.
    def exitAddSubExpr(self, ctx:PromelaParser.AddSubExprContext):
        pass


    # Enter a parse tree produced by PromelaParser#bitwiseXorExpr.
    def enterBitwiseXorExpr(self, ctx:PromelaParser.BitwiseXorExprContext):
        pass

    # Exit a parse tree produced by PromelaParser#bitwiseXorExpr.
    def exitBitwiseXorExpr(self, ctx:PromelaParser.BitwiseXorExprContext):
        pass


    # Enter a parse tree produced by PromelaParser#varRefExpr.
    def enterVarRefExpr(self, ctx:PromelaParser.VarRefExprContext):
        pass

    # Exit a parse tree produced by PromelaParser#varRefExpr.
    def exitVarRefExpr(self, ctx:PromelaParser.VarRefExprContext):
        pass


    # Enter a parse tree produced by PromelaParser#logicalAndExpr.
    def enterLogicalAndExpr(self, ctx:PromelaParser.LogicalAndExprContext):
        pass

    # Exit a parse tree produced by PromelaParser#logicalAndExpr.
    def exitLogicalAndExpr(self, ctx:PromelaParser.LogicalAndExprContext):
        pass


    # Enter a parse tree produced by PromelaParser#nfullExpr.
    def enterNfullExpr(self, ctx:PromelaParser.NfullExprContext):
        pass

    # Exit a parse tree produced by PromelaParser#nfullExpr.
    def exitNfullExpr(self, ctx:PromelaParser.NfullExprContext):
        pass


    # Enter a parse tree produced by PromelaParser#pidExpr.
    def enterPidExpr(self, ctx:PromelaParser.PidExprContext):
        pass

    # Exit a parse tree produced by PromelaParser#pidExpr.
    def exitPidExpr(self, ctx:PromelaParser.PidExprContext):
        pass


    # Enter a parse tree produced by PromelaParser#fullExpr.
    def enterFullExpr(self, ctx:PromelaParser.FullExprContext):
        pass

    # Exit a parse tree produced by PromelaParser#fullExpr.
    def exitFullExpr(self, ctx:PromelaParser.FullExprContext):
        pass


    # Enter a parse tree produced by PromelaParser#relationalExpr.
    def enterRelationalExpr(self, ctx:PromelaParser.RelationalExprContext):
        pass

    # Exit a parse tree produced by PromelaParser#relationalExpr.
    def exitRelationalExpr(self, ctx:PromelaParser.RelationalExprContext):
        pass


    # Enter a parse tree produced by PromelaParser#pcValueExpr.
    def enterPcValueExpr(self, ctx:PromelaParser.PcValueExprContext):
        pass

    # Exit a parse tree produced by PromelaParser#pcValueExpr.
    def exitPcValueExpr(self, ctx:PromelaParser.PcValueExprContext):
        pass


    # Enter a parse tree produced by PromelaParser#shiftExpr.
    def enterShiftExpr(self, ctx:PromelaParser.ShiftExprContext):
        pass

    # Exit a parse tree produced by PromelaParser#shiftExpr.
    def exitShiftExpr(self, ctx:PromelaParser.ShiftExprContext):
        pass


    # Enter a parse tree produced by PromelaParser#logicalOrExpr.
    def enterLogicalOrExpr(self, ctx:PromelaParser.LogicalOrExprContext):
        pass

    # Exit a parse tree produced by PromelaParser#logicalOrExpr.
    def exitLogicalOrExpr(self, ctx:PromelaParser.LogicalOrExprContext):
        pass


    # Enter a parse tree produced by PromelaParser#notExpr.
    def enterNotExpr(self, ctx:PromelaParser.NotExprContext):
        pass

    # Exit a parse tree produced by PromelaParser#notExpr.
    def exitNotExpr(self, ctx:PromelaParser.NotExprContext):
        pass


    # Enter a parse tree produced by PromelaParser#impliesExpr.
    def enterImpliesExpr(self, ctx:PromelaParser.ImpliesExprContext):
        pass

    # Exit a parse tree produced by PromelaParser#impliesExpr.
    def exitImpliesExpr(self, ctx:PromelaParser.ImpliesExprContext):
        pass


    # Enter a parse tree produced by PromelaParser#emptyExpr.
    def enterEmptyExpr(self, ctx:PromelaParser.EmptyExprContext):
        pass

    # Exit a parse tree produced by PromelaParser#emptyExpr.
    def exitEmptyExpr(self, ctx:PromelaParser.EmptyExprContext):
        pass


    # Enter a parse tree produced by PromelaParser#unaryPlusExpr.
    def enterUnaryPlusExpr(self, ctx:PromelaParser.UnaryPlusExprContext):
        pass

    # Exit a parse tree produced by PromelaParser#unaryPlusExpr.
    def exitUnaryPlusExpr(self, ctx:PromelaParser.UnaryPlusExprContext):
        pass


    # Enter a parse tree produced by PromelaParser#runExpr.
    def enterRunExpr(self, ctx:PromelaParser.RunExprContext):
        pass

    # Exit a parse tree produced by PromelaParser#runExpr.
    def exitRunExpr(self, ctx:PromelaParser.RunExprContext):
        pass


    # Enter a parse tree produced by PromelaParser#equalityExpr.
    def enterEqualityExpr(self, ctx:PromelaParser.EqualityExprContext):
        pass

    # Exit a parse tree produced by PromelaParser#equalityExpr.
    def exitEqualityExpr(self, ctx:PromelaParser.EqualityExprContext):
        pass



del PromelaParser