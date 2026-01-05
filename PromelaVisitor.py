# Generated from Promela.g4 by ANTLR 4.13.2
from antlr4 import *
if "." in __name__:
    from .PromelaParser import PromelaParser
else:
    from PromelaParser import PromelaParser

# This class defines a complete generic visitor for a parse tree produced by PromelaParser.

class PromelaVisitor(ParseTreeVisitor):

    # Visit a parse tree produced by PromelaParser#spec.
    def visitSpec(self, ctx:PromelaParser.SpecContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#module.
    def visitModule(self, ctx:PromelaParser.ModuleContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#defineDecl.
    def visitDefineDecl(self, ctx:PromelaParser.DefineDeclContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#defineBody.
    def visitDefineBody(self, ctx:PromelaParser.DefineBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#mtypeDecl.
    def visitMtypeDecl(self, ctx:PromelaParser.MtypeDeclContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#chanDecl.
    def visitChanDecl(self, ctx:PromelaParser.ChanDeclContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#varDecl.
    def visitVarDecl(self, ctx:PromelaParser.VarDeclContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#varItem.
    def visitVarItem(self, ctx:PromelaParser.VarItemContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#typename.
    def visitTypename(self, ctx:PromelaParser.TypenameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#typedefDecl.
    def visitTypedefDecl(self, ctx:PromelaParser.TypedefDeclContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#proctype.
    def visitProctype(self, ctx:PromelaParser.ProctypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#paramList.
    def visitParamList(self, ctx:PromelaParser.ParamListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#paramGroup.
    def visitParamGroup(self, ctx:PromelaParser.ParamGroupContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#init.
    def visitInit(self, ctx:PromelaParser.InitContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#inlineDecl.
    def visitInlineDecl(self, ctx:PromelaParser.InlineDeclContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#sequence.
    def visitSequence(self, ctx:PromelaParser.SequenceContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#step.
    def visitStep(self, ctx:PromelaParser.StepContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#xrxsDecl.
    def visitXrxsDecl(self, ctx:PromelaParser.XrxsDeclContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#skipStmt.
    def visitSkipStmt(self, ctx:PromelaParser.SkipStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#breakStmt.
    def visitBreakStmt(self, ctx:PromelaParser.BreakStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#gotoStmt.
    def visitGotoStmt(self, ctx:PromelaParser.GotoStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#labeledStmt.
    def visitLabeledStmt(self, ctx:PromelaParser.LabeledStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#ifStmt.
    def visitIfStmt(self, ctx:PromelaParser.IfStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#doStmt.
    def visitDoStmt(self, ctx:PromelaParser.DoStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#atomicStmt.
    def visitAtomicStmt(self, ctx:PromelaParser.AtomicStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#dstepStmt.
    def visitDstepStmt(self, ctx:PromelaParser.DstepStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#blockStmt.
    def visitBlockStmt(self, ctx:PromelaParser.BlockStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#assertStmt.
    def visitAssertStmt(self, ctx:PromelaParser.AssertStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#printfStmt.
    def visitPrintfStmt(self, ctx:PromelaParser.PrintfStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#printmStmt.
    def visitPrintmStmt(self, ctx:PromelaParser.PrintmStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#sendStatement.
    def visitSendStatement(self, ctx:PromelaParser.SendStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#receiveStatement.
    def visitReceiveStatement(self, ctx:PromelaParser.ReceiveStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#runStmt.
    def visitRunStmt(self, ctx:PromelaParser.RunStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#callStmt.
    def visitCallStmt(self, ctx:PromelaParser.CallStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#assignStatement.
    def visitAssignStatement(self, ctx:PromelaParser.AssignStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#exprStmt.
    def visitExprStmt(self, ctx:PromelaParser.ExprStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#selectStmt.
    def visitSelectStmt(self, ctx:PromelaParser.SelectStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#forStmt.
    def visitForStmt(self, ctx:PromelaParser.ForStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#normalSend.
    def visitNormalSend(self, ctx:PromelaParser.NormalSendContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#sortedSend.
    def visitSortedSend(self, ctx:PromelaParser.SortedSendContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#normalRecv.
    def visitNormalRecv(self, ctx:PromelaParser.NormalRecvContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#randomRecv.
    def visitRandomRecv(self, ctx:PromelaParser.RandomRecvContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#pollRecv.
    def visitPollRecv(self, ctx:PromelaParser.PollRecvContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#randomPollRecv.
    def visitRandomPollRecv(self, ctx:PromelaParser.RandomPollRecvContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#recvArgs.
    def visitRecvArgs(self, ctx:PromelaParser.RecvArgsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#recvArg.
    def visitRecvArg(self, ctx:PromelaParser.RecvArgContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#assignExpr.
    def visitAssignExpr(self, ctx:PromelaParser.AssignExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#incrExpr.
    def visitIncrExpr(self, ctx:PromelaParser.IncrExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#decrExpr.
    def visitDecrExpr(self, ctx:PromelaParser.DecrExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#varRef.
    def visitVarRef(self, ctx:PromelaParser.VarRefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#argList.
    def visitArgList(self, ctx:PromelaParser.ArgListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#optionList.
    def visitOptionList(self, ctx:PromelaParser.OptionListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#optionNormal.
    def visitOptionNormal(self, ctx:PromelaParser.OptionNormalContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#optionElse.
    def visitOptionElse(self, ctx:PromelaParser.OptionElseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#lenExpr.
    def visitLenExpr(self, ctx:PromelaParser.LenExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#trueExpr.
    def visitTrueExpr(self, ctx:PromelaParser.TrueExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#numberExpr.
    def visitNumberExpr(self, ctx:PromelaParser.NumberExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#bitwiseOrExpr.
    def visitBitwiseOrExpr(self, ctx:PromelaParser.BitwiseOrExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#nrPrExpr.
    def visitNrPrExpr(self, ctx:PromelaParser.NrPrExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#bitwiseAndExpr.
    def visitBitwiseAndExpr(self, ctx:PromelaParser.BitwiseAndExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#mulDivModExpr.
    def visitMulDivModExpr(self, ctx:PromelaParser.MulDivModExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#bitwiseNotExpr.
    def visitBitwiseNotExpr(self, ctx:PromelaParser.BitwiseNotExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#parenExpr.
    def visitParenExpr(self, ctx:PromelaParser.ParenExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#timeoutExpr.
    def visitTimeoutExpr(self, ctx:PromelaParser.TimeoutExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#stringExpr.
    def visitStringExpr(self, ctx:PromelaParser.StringExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#nemptyExpr.
    def visitNemptyExpr(self, ctx:PromelaParser.NemptyExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#enabledExpr.
    def visitEnabledExpr(self, ctx:PromelaParser.EnabledExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#unaryMinusExpr.
    def visitUnaryMinusExpr(self, ctx:PromelaParser.UnaryMinusExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#lastExpr.
    def visitLastExpr(self, ctx:PromelaParser.LastExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#npExpr.
    def visitNpExpr(self, ctx:PromelaParser.NpExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#falseExpr.
    def visitFalseExpr(self, ctx:PromelaParser.FalseExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#conditionalExpr.
    def visitConditionalExpr(self, ctx:PromelaParser.ConditionalExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#addSubExpr.
    def visitAddSubExpr(self, ctx:PromelaParser.AddSubExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#bitwiseXorExpr.
    def visitBitwiseXorExpr(self, ctx:PromelaParser.BitwiseXorExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#varRefExpr.
    def visitVarRefExpr(self, ctx:PromelaParser.VarRefExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#logicalAndExpr.
    def visitLogicalAndExpr(self, ctx:PromelaParser.LogicalAndExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#nfullExpr.
    def visitNfullExpr(self, ctx:PromelaParser.NfullExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#pidExpr.
    def visitPidExpr(self, ctx:PromelaParser.PidExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#fullExpr.
    def visitFullExpr(self, ctx:PromelaParser.FullExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#relationalExpr.
    def visitRelationalExpr(self, ctx:PromelaParser.RelationalExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#pcValueExpr.
    def visitPcValueExpr(self, ctx:PromelaParser.PcValueExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#shiftExpr.
    def visitShiftExpr(self, ctx:PromelaParser.ShiftExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#logicalOrExpr.
    def visitLogicalOrExpr(self, ctx:PromelaParser.LogicalOrExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#notExpr.
    def visitNotExpr(self, ctx:PromelaParser.NotExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#impliesExpr.
    def visitImpliesExpr(self, ctx:PromelaParser.ImpliesExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#emptyExpr.
    def visitEmptyExpr(self, ctx:PromelaParser.EmptyExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#unaryPlusExpr.
    def visitUnaryPlusExpr(self, ctx:PromelaParser.UnaryPlusExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#runExpr.
    def visitRunExpr(self, ctx:PromelaParser.RunExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PromelaParser#equalityExpr.
    def visitEqualityExpr(self, ctx:PromelaParser.EqualityExprContext):
        return self.visitChildren(ctx)



del PromelaParser