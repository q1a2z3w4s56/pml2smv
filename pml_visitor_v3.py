"""
PML Visitor实现 - 改进版 v5
新增功能：
1. 分离局部变量和全局变量的追踪
2. 识别状态入口处的变量赋值（state_entry_assignments）
3. 简化transition输出，区分trigger和action
4. 非通道类型参数也识别为局部变量
"""

from antlr4 import CommonTokenStream, InputStream
from antlr4.error. ErrorListener import ErrorListener
from PromelaLexer import PromelaLexer
from PromelaParser import PromelaParser
from PromelaVisitor import PromelaVisitor

from ir_model import *
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import re
import copy


class PMLErrorListener(ErrorListener):
    def __init__(self):
        super().__init__()
        self.errors = []
    
    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        self.errors.append(f"Line {line}:{column} - {msg}")


class OptionResult(Enum):
    GOTO = "goto"
    BREAK = "break"
    CONTINUE = "continue"
    FALLTHROUGH = "fallthrough"


@dataclass
class ProcessTemplate:
    name:  str
    parameters: List[Tuple[str, str]]
    states: Dict[str, State] = field(default_factory=dict)
    transitions: List[Transition] = field(default_factory=list)
    local_variables: Dict[str, Variable] = field(default_factory=dict)
    initial_state: Optional[str] = None
    state_entry_assignments:  Dict[str, Dict[str, str]] = field(default_factory=dict)


@dataclass
class RunStatement:
    proctype_name: str
    arguments: List[str]


@dataclass
class OptionParseResult:
    result_type: OptionResult
    target_state: Optional[str] = None
    guard: Optional[Expression] = None
    actions: List[Action] = field(default_factory=list)
    intermediate_label: Optional[str] = None
    post_label_actions: List[Action] = field(default_factory=list)


@dataclass
class SimplifiedTransition: 
    """简化的转换，区分trigger和action"""
    source:  str
    target:  str
    guard: Optional[str]
    triggers: List[Dict]  # receive 操作作为触发器
    actions: List[Dict]   # 赋值操作和 send 操作
    
    @classmethod
    def from_parsed(cls, source: str, target:  str, guard: Optional[str], 
                    triggers: List[Dict], actions: List[Dict]):
        return cls(source=source, target=target, guard=guard, 
                   triggers=triggers, actions=actions)


class PMLVisitorImpl(PromelaVisitor):
    
    def __init__(self, debug=False):
        super().__init__()
        self.program = ProgramModel()
        self.debug = debug
        # 新增：追踪 init 块中的全局变量初始化
        self.init_assignments: Dict[str, str] = {}  # 变量名 -> 初始值

        self.current_process:  Optional[Process] = None
        self. current_state: Optional[str] = None
        self.collected_labels: List[str] = []
        
        self.process_templates: Dict[str, ProcessTemplate] = {}
        self.run_statements: List[RunStatement] = []
        self.defines: Dict[str, str] = {}
        self.process_instance_count:  Dict[str, int] = {}
        
        self.break_target_stack: List[str] = []
        
        # 追踪状态入口的变量赋值
        self.state_entry_assignments: Dict[str, Dict[str, str]] = {}
        # 追踪局部变量声明
        self. local_var_declarations: Dict[str, str] = {}  # 变量名 -> 类型
        # 追踪哪些变量是参数
        self. parameter_names: Set[str] = set()
        # 追踪哪些参数是通道类型
        self. channel_parameter_names: Set[str] = set()

    def _debug(self, msg):
        if self. debug:
            print(f"[DEBUG] {msg}")

    # ==================== 顶层规则 ====================
    
    def visitSpec(self, ctx: PromelaParser.SpecContext):
        for module in ctx.module():
            self.visit(module)
        self._instantiate_processes()
        return self.program
    
    def visitModule(self, ctx:  PromelaParser. ModuleContext):
        return self.visitChildren(ctx)
    
    # ==================== Define声明 ====================
    
    def visitDefineDecl(self, ctx: PromelaParser. DefineDeclContext):
        if ctx.ID() and ctx.defineBody():
            name = ctx.ID().getText()
            value = ctx.defineBody().getText()
            self.defines[name] = value
            if ctx.defineBody().expr():
                self. program.defines[name] = self._visit_expr(ctx.defineBody().expr())
        return None
    
    # ==================== MType声明 ====================
    
    def visitMtypeDecl(self, ctx: PromelaParser.MtypeDeclContext):
        for child in ctx.children or []:
            if hasattr(child, 'getSymbol'):
                token = child.getSymbol()
                if token. type == PromelaLexer.ID:
                    self.program.mtype_values. append(child.getText())
        return None
    
    # ==================== 通道声明 ====================
    
    def visitChanDecl(self, ctx: PromelaParser.ChanDeclContext):
        name = ctx.ID().getText() if ctx.ID() else None
        if name is None:
            return None
        capacity = 0
        if ctx. expr():
            capacity_val = self._eval_const_expr(ctx. expr(), allow_symbolic=True)
            capacity = capacity_val
        msg_types = [t.getText() for t in ctx.typename()] or ['mtype']
        self.program.channels[name] = Channel(
            name=name, capacity=capacity, message_types=msg_types
        )
        return None
    
    # ==================== 变量声明 ====================
    
    def visitVarDecl(self, ctx: PromelaParser.VarDeclContext):
        if ctx.typename() is None:
            return None
        
        var_type = self._get_var_type(ctx.typename())
        var_type_str = ctx.typename().getText()
        
        for var_item in ctx.varItem():
            result = self._parse_var_item(var_item)
            if result is None:
                continue
            name, is_array, array_size, init_value = result
            
            variable = Variable(
                name=name, var_type=var_type, is_array=is_array,
                array_size=array_size, initial_value=init_value,
                is_global=(self.current_process is None)
            )
            
            if self.current_process is None:
                self. program.global_variables[name] = variable
            else:
                self.current_process.local_variables[name] = variable
                # 追踪局部变量声明
                self. local_var_declarations[name] = var_type_str
        
        return None
    
    def _parse_var_item(self, ctx):
        if ctx is None or ctx.ID() is None:
            return None
        
        name = ctx.ID().getText()
        is_array = False
        array_size = None
        init_value = None
        
        exprs = ctx.expr() if ctx.expr() else []
        if exprs:
            text = ctx.getText()
            if '[' in text: 
                is_array = True
                array_size = self._eval_const_expr(exprs[0])
                if len(exprs) >= 2:
                    init_value = self._visit_expr(exprs[1])
            else:
                init_value = self._visit_expr(exprs[0])
        
        return name, is_array, array_size, init_value
    
    def _get_var_type(self, ctx) -> VarType:
        if ctx is None: 
            return VarType.INT
        type_mapping = {
            'bit': VarType. BIT, 'bool': VarType. BOOL, 'byte': VarType. BYTE,
            'short': VarType. SHORT, 'int': VarType. INT, 'mtype': VarType.MTYPE,
            'chan': VarType. CHAN, 'pid': VarType. PID,
        }
        return type_mapping.get(ctx.getText(), VarType.INT)
    
    # ==================== Proctype声明 ====================
    
    def visitProctype(self, ctx:  PromelaParser. ProctypeContext):
        is_active = False
        active_count = 1
        
        full_text = ctx.getText()
        if 'active' in full_text:
            is_active = True
            match = re.search(r'active\[(\d+)\]', full_text)
            if match: 
                active_count = int(match. group(1))
        
        name = ctx.ID().getText() if ctx.ID() else "unnamed"
        self._debug(f"Processing proctype: {name}")
        
        parameters = []
        self.parameter_names = set()
        self.channel_parameter_names = set()
        if ctx.paramList():
            for param_group in ctx.paramList().paramGroup():
                if param_group.typename() is None:
                    continue
                param_type = param_group.typename().getText()
                for id_node in param_group. ID():
                    param_name = id_node.getText()
                    parameters.append((param_name, param_type))
                    self.parameter_names.add(param_name)
                    # 识别通道类型参数
                    if param_type == 'chan': 
                        self.channel_parameter_names. add(param_name)
        
        process = Process(
            name=name, states={}, transitions=[], local_variables={},
            parameters=parameters, is_active=is_active, active_count=active_count
        )
        
        self.current_process = process
        self. current_state = None
        self.collected_labels = []
        self.break_target_stack = []
        self.state_entry_assignments = {}
        self.local_var_declarations = {}
        
        if ctx.sequence():
            self._collect_labels_from_sequence(ctx.sequence())
            self._debug(f"Collected labels: {self. collected_labels}")
        
        for label in self.collected_labels:
            process.states[label] = State(name=label)
        
        if ctx.sequence():
            self._process_proctype_sequence(ctx.sequence())
        
        if self.collected_labels:
            initial = self.collected_labels[0]
            process.initial_state = initial
            process.states[initial]. is_initial = True
        
        self._cleanup_internal_states(process)
        
        # 保存状态入口赋值信息
        process.state_entry_assignments = copy.deepcopy(self.state_entry_assignments)
        process.local_var_types = copy.deepcopy(self.local_var_declarations)
        
        if parameters:
            template = ProcessTemplate(
                name=name, parameters=parameters,
                states=copy.deepcopy(process.states),
                transitions=copy.deepcopy(process.transitions),
                local_variables=copy.deepcopy(process.local_variables),
                initial_state=process. initial_state,
                state_entry_assignments=copy.deepcopy(self.state_entry_assignments)
            )
            template.local_var_types = copy. deepcopy(self.local_var_declarations)
            template.channel_parameter_names = copy.copy(self.channel_parameter_names)
            self.process_templates[name] = template
        elif is_active:
            for i in range(active_count):
                if active_count > 1:
                    instance_name = f"{name}_{i}"
                    proc_copy = self._copy_process(process, instance_name)
                    self.program.processes[instance_name] = proc_copy
                else:
                    self.program.processes[name] = process
        else:
            self. program.processes[name] = process
        
        self. current_process = None
        return None
    
    def _cleanup_internal_states(self, process:  Process):
        used_states = set()
        for trans in process.transitions:
            used_states.add(trans.source)
            used_states. add(trans.target)
        
        states_to_remove = []
        for state_name in process.states:
            if state_name. startswith('__') and state_name not in used_states: 
                states_to_remove.append(state_name)
        
        for state_name in states_to_remove: 
            del process.states[state_name]
    
    def _copy_process(self, process: Process, new_name: str) -> Process:
        new_proc = Process(
            name=new_name,
            states=copy.deepcopy(process.states),
            transitions=copy. deepcopy(process.transitions),
            local_variables=copy.deepcopy(process.local_variables),
            parameters=process.parameters. copy(),
            initial_state=process. initial_state,
            is_active=process.is_active,
            active_count=1
        )
        if hasattr(process, 'state_entry_assignments'):
            new_proc.state_entry_assignments = copy.deepcopy(process.state_entry_assignments)
        if hasattr(process, 'local_var_types'):
            new_proc. local_var_types = copy.deepcopy(process.local_var_types)
        return new_proc
    
    # ==================== 标签收集 ====================
    
    def _collect_labels_from_sequence(self, ctx):
        if ctx is None: 
            return
        for step in ctx.step():
            self._collect_labels_from_step(step)
    
    def _collect_labels_from_step(self, ctx):
        if ctx is None:
            return
        
        if ctx.getChildCount() >= 2:
            first, second = ctx.getChild(0), ctx.getChild(1)
            if hasattr(first, 'getSymbol') and hasattr(second, 'getText'):
                if second.getText() == ': ':
                    label = first.getText()
                    if label not in self. collected_labels: 
                        self.collected_labels.append(label)
        
        if ctx.varDecl() or ctx.xrxsDecl():
            return
        
        stmts = ctx. stmt()
        if stmts: 
            for stmt in stmts:
                self._collect_labels_from_stmt(stmt)
    
    def _collect_labels_from_stmt(self, ctx):
        if ctx is None:
            return
        
        ctx_class = type(ctx).__name__
        
        if ctx_class == 'LabeledStmtContext':
            for i in range(ctx.getChildCount()):
                child = ctx. getChild(i)
                if hasattr(child, 'getSymbol'):
                    token = child.getSymbol()
                    if token.type == PromelaLexer. ID:
                        label = child.getText()
                        if label not in self. collected_labels: 
                            self.collected_labels.append(label)
                        break
                elif hasattr(child, 'getText') and child.getText() == ':':
                    break
            if ctx.stmt():
                self._collect_labels_from_stmt(ctx.stmt())
        
        elif ctx_class in ['IfStmtContext', 'DoStmtContext']: 
            if ctx.optionList():
                for option in ctx.optionList().option():
                    if option.sequence():
                        self._collect_labels_from_sequence(option. sequence())
        
        elif ctx_class in ['AtomicStmtContext', 'DstepStmtContext', 'BlockStmtContext']: 
            if ctx. sequence():
                self._collect_labels_from_sequence(ctx. sequence())
    
    # ==================== 序列处理 ====================
    
    def _process_proctype_sequence(self, ctx):
        if ctx is None: 
            return
        
        steps = list(ctx.step())
        print(f"Processing sequence with {len(steps)} steps")
        current_actions = []
        
        if self.current_state is None:
            if self.collected_labels:
                self. current_state = self.collected_labels[0]
            else:
                initial_state_name = f"__init_{self.current_process.name}"
                self.current_process.states[initial_state_name] = State(
                    name=initial_state_name, is_initial=True
                )
                self.current_state = initial_state_name
                self.current_process.initial_state = initial_state_name
        
        i = 0
        while i < len(steps):
            step = steps[i]
            
            label = self._get_step_label(step)
            if label: 
                self.current_state = label
                current_actions = []
                i += 1
                continue
            
            if step.varDecl():
                self. visit(step.varDecl())
                i += 1
                continue
            
            if step.xrxsDecl():
                i += 1
                continue
            
            stmts = step. stmt()
            if stmts: 
                stmt = stmts[0]
                ctx_class = type(stmt).__name__
                
                if ctx_class == 'DoStmtContext': 
                    remaining_steps = steps[i+1:]
                    next_label_offset = self._find_next_label_offset(remaining_steps)
                    
                    if next_label_offset is not None:
                        steps_to_process = remaining_steps[: next_label_offset]
                        self._process_do_stmt_with_remaining(stmt, current_actions. copy(), steps_to_process)
                        current_actions = []
                        i = i + 1 + next_label_offset
                        continue
                    else:
                        self._process_do_stmt_with_remaining(stmt, current_actions. copy(), remaining_steps)
                        current_actions = []
                        break
                
                elif ctx_class == 'IfStmtContext': 
                    remaining_steps = steps[i+1:]
                    next_label_offset = self._find_next_label_offset(remaining_steps)
                    
                    if next_label_offset is not None:
                        steps_to_process = remaining_steps[:next_label_offset]
                        self._process_if_stmt_with_remaining(stmt, current_actions.copy(), steps_to_process)
                        current_actions = []
                        i = i + 1 + next_label_offset
                        continue
                    else: 
                        self._process_if_stmt_with_remaining(stmt, current_actions. copy(), remaining_steps)
                        current_actions = []
                        break
                else:
                    self._process_stmt_in_sequence(stmt, current_actions)
            
            i += 1
    
    def _find_next_label_offset(self, steps) -> Optional[int]: 
        for idx, step in enumerate(steps):
            label = self._get_step_label(step)
            if label and label in self.collected_labels:
                return idx
            stmts = step. stmt()
            if stmts: 
                stmt = stmts[0]
                if type(stmt).__name__ == 'LabeledStmtContext':
                    label = self._get_label_from_labeled_stmt(stmt)
                    if label and label in self.collected_labels:
                        return idx
        return None
    
    def _get_step_label(self, ctx) -> Optional[str]:
        if ctx. getChildCount() >= 2:
            first, second = ctx.getChild(0), ctx.getChild(1)
            if hasattr(first, 'getSymbol') and hasattr(second, 'getText'):
                if second.getText() == ':':
                    return first.getText()
        return None
    
    def _process_stmt_in_sequence(self, ctx, current_actions:  List[Action]):
        ctx_class = type(ctx).__name__
        
        if ctx_class == 'LabeledStmtContext':
            label = self._get_label_from_labeled_stmt(ctx)
            if label: 
                self.current_state = label
                current_actions. clear()
            if ctx.stmt():
                self._process_stmt_in_sequence(ctx.stmt(), current_actions)
        
        elif ctx_class == 'GotoStmtContext':
            target = ctx.ID().getText() if ctx.ID() else None
            if target and self.current_state and self.current_process:
                self. current_process.transitions. append(Transition(
                    source=self.current_state, target=target,
                    guard=None, actions=current_actions. copy()
                ))
            current_actions.clear()
        
        elif ctx_class == 'IfStmtContext': 
            self._process_if_stmt(ctx, current_actions. copy())
            current_actions.clear()
        
        elif ctx_class == 'DoStmtContext':
            self._process_do_stmt(ctx, current_actions.copy())
            current_actions.clear()
        
        elif ctx_class in ['AtomicStmtContext', 'BlockStmtContext']: 
            if ctx.sequence():
                self._process_proctype_sequence(ctx.sequence())
        
        elif ctx_class == 'ForStmtContext': 
            self._process_for_stmt(ctx, current_actions.copy())
            current_actions.clear()
        
        else:
            action = self._stmt_to_action(ctx)
            if action:
                current_actions.append(action)
    
    def _get_label_from_labeled_stmt(self, ctx) -> Optional[str]:
        for i in range(ctx. getChildCount()):
            child = ctx.getChild(i)
            if hasattr(child, 'getSymbol'):
                token = child.getSymbol()
                if token. type == PromelaLexer.ID:
                    return child.getText()
            elif hasattr(child, 'getText') and child.getText() == ':':
                break
        return None
    
    # ==================== if/do 处理 ====================
    
    def _process_if_stmt(self, ctx, prefix_actions: List[Action]):
        if not self. current_state or not self.current_process:
            return
        
        source_state = self.current_state
        
        if ctx.optionList():
            for option in ctx.optionList().option():
                self._process_option(option, source_state, prefix_actions. copy(), is_do=False)
    
    def _process_if_stmt_with_remaining(self, ctx, prefix_actions:  List[Action], remaining_steps: List):
        if not self.current_state or not self.current_process:
            return
        source_state = self. current_state
        fallthrough_target = None
        post_if_actions = []
        for step in remaining_steps: 
            stmts = step. stmt()
            if stmts: 
                stmt = stmts[0]
                stmt_class = type(stmt).__name__
                if stmt_class == 'GotoStmtContext':
                    fallthrough_target = stmt.ID().getText()
                    break
                else:
                    action = self._stmt_to_action(stmt)
                    if action:
                        post_if_actions.append(action)
        if ctx.optionList():
            for option in ctx.optionList().option():
                results = self._parse_option_sequence(option. sequence(), is_do=False)
                for r in results:
                    all_actions = prefix_actions + r.actions
                    if r.result_type == OptionResult.GOTO: 
                        tgt = r.target_state or fallthrough_target or source_state
                        if r.intermediate_label:
                            self.current_process.transitions.append(Transition(
                                source=source_state, target=r.intermediate_label,
                                guard=r.guard, actions=all_actions
                            ))
                            if r.post_label_actions:
                                self.current_process. transitions.append(Transition(
                                    source=r.intermediate_label, target=tgt,
                                    guard=None, actions=r.post_label_actions
                                ))
                        else: 
                            self. current_process.transitions.append(Transition(
                                source=source_state, target=tgt,
                                guard=r. guard, actions=all_actions
                            ))
                    elif r.result_type == OptionResult. FALLTHROUGH and fallthrough_target: 
                        all_actions. extend(post_if_actions)
                        self.current_process. transitions.append(Transition(
                            source=source_state, target=fallthrough_target,
                            guard=r.guard, actions=all_actions
                        ))
    
    def _process_do_stmt(self, ctx, prefix_actions: List[Action]):
        if not self.current_state or not self.current_process:
            return
        source_state = self. current_state
        
        exit_state_name = f"__do_exit_{id(ctx)}"
        self.current_process. states[exit_state_name] = State(name=exit_state_name)
        self.break_target_stack. append(exit_state_name)
        
        if ctx. optionList():
            for option in ctx. optionList().option():
                self._process_option(option, source_state, prefix_actions.copy(), is_do=True)
        
        if self.break_target_stack:
            exit_target = self.break_target_stack.pop()
            if exit_target. startswith('__do_exit_'):
                self. current_state = exit_target
    
    def _process_do_stmt_with_remaining(self, ctx, prefix_actions:  List[Action], remaining_steps: List):
        if not self.current_state or not self.current_process:
            return
        source_state = self.current_state
        
        exit_state_name = f"__do_exit_{id(ctx)}"
        self.current_process.states[exit_state_name] = State(name=exit_state_name)
        self.break_target_stack.append(exit_state_name)
        
        if ctx.optionList():
            for option in ctx.optionList().option():
                self._process_option(option, source_state, prefix_actions. copy(), is_do=True)
        
        if self. break_target_stack:
            self.break_target_stack.pop()
        self.current_state = exit_state_name
        
        if remaining_steps:
            post_break_actions = []
            for step in remaining_steps:
                label = self._get_step_label(step)
                if label:
                    self.current_state = label
                    post_break_actions = []
                    continue
                
                if step.varDecl():
                    self.visit(step. varDecl())
                    continue
                
                if step.xrxsDecl():
                    continue
                
                stmts = step. stmt()
                if stmts: 
                    stmt = stmts[0]
                    stmt_class = type(stmt).__name__
                    
                    if stmt_class == 'GotoStmtContext':
                        target = stmt.ID().getText()
                        self.current_process. transitions.append(Transition(
                            source=self.current_state, target=target,
                            guard=None, actions=post_break_actions
                        ))
                        post_break_actions = []
                        break
                    elif stmt_class == 'IfStmtContext':
                        self._process_if_stmt_with_remaining(stmt, post_break_actions. copy(),
                                                             remaining_steps[remaining_steps.index(step)+1:])
                        break
                    elif stmt_class == 'DoStmtContext':
                        self._process_do_stmt_with_remaining(stmt, post_break_actions.copy(),
                                                             remaining_steps[remaining_steps.index(step)+1:])
                        break
                    else: 
                        action = self._stmt_to_action(stmt)
                        if action:
                            post_break_actions. append(action)
    
    def _process_option(self, ctx, source_state:  str, prefix_actions:  List[Action], is_do: bool):
        if ctx. sequence() is None:
            return
        results = self._parse_option_sequence(ctx.sequence(), is_do)
        for r in results: 
            all_actions = prefix_actions + r.actions
            if r.result_type == OptionResult. GOTO:
                target = r.target_state or source_state
                if r. intermediate_label: 
                    self.current_process.transitions. append(Transition(
                        source=source_state, target=r.intermediate_label,
                        guard=r.guard, actions=all_actions
                    ))
                    if r.post_label_actions:
                        self.current_process.transitions.append(Transition(
                            source=r. intermediate_label, target=target,
                            guard=None, actions=r.post_label_actions
                        ))
                else:
                    self.current_process.transitions.append(Transition(
                        source=source_state, target=target,
                        guard=r.guard, actions=all_actions
                    ))
            elif r.result_type == OptionResult.BREAK:
                if self.break_target_stack:
                    break_target = self. break_target_stack[-1]
                    self.current_process.transitions. append(Transition(
                        source=source_state, target=break_target,
                        guard=r.guard, actions=all_actions
                    ))
            elif r.result_type == OptionResult. CONTINUE and is_do:
                self.current_process. transitions.append(Transition(
                    source=source_state, target=source_state,
                    guard=r. guard, actions=all_actions
                ))
    
    def _parse_option_sequence(self, seq_ctx, is_do: bool) -> List[OptionParseResult]:
        if seq_ctx is None:
            return [OptionParseResult(
                result_type=OptionResult. CONTINUE if is_do else OptionResult.FALLTHROUGH
            )]
        
        steps = list(seq_ctx.step())
        guard = None
        current_actions = []
        first_stmt_processed = False
        i = 0
        
        while i < len(steps):
            step = steps[i]
            
            if self._is_else_step(step):
                guard = VarExpr(name='else')
                i += 1
                first_stmt_processed = True
                continue
            
            if step.varDecl():
                self.visit(step.varDecl())
                i += 1
                continue
            
            if step.xrxsDecl():
                i += 1
                continue
            
            stmts = step.stmt()
            if not stmts: 
                i += 1
                continue
            
            stmt = stmts[0]
            ctx_class = type(stmt).__name__
            
            split_result = self._check_greedy_split(stmt)
            
            if split_result: 
                obj, leftover = split_result
                if not first_stmt_processed and isinstance(obj, Expression):
                    guard = obj
                elif isinstance(obj, Action):
                    current_actions.append(obj)
                
                if leftover and i + 1 < len(steps):
                    next_text = steps[i+1].getText()
                    combined = f"{leftover} {next_text}"
                    recovered = self._parse_text_as_action(combined)
                    if recovered: 
                        current_actions.append(recovered)
                        i += 2
                        first_stmt_processed = True
                        continue
                
                i += 1
                first_stmt_processed = True
                continue
            
            has_arrow = self._step_has_arrow(step)
            
            if not first_stmt_processed and has_arrow and ctx_class == 'ExprStmtContext': 
                text = stmt.getText()
                if '!' not in text and '?' not in text: 
                    guard = self._visit_expr(stmt. expr())
                    i += 1
                    first_stmt_processed = True
                    continue
            
            if ctx_class == 'LabeledStmtContext':
                label = self._get_label_from_labeled_stmt(stmt)
                inner_stmt = stmt.stmt()
                post_label_actions = []
                final_target = None
                
                if inner_stmt:
                    inner_class = type(inner_stmt).__name__
                    if inner_class == 'GotoStmtContext':
                        final_target = inner_stmt.ID().getText()
                    else:
                        inner_action = self._stmt_to_action(inner_stmt)
                        if inner_action:
                            post_label_actions. append(inner_action)
                
                for j in range(i + 1, len(steps)):
                    r_step = steps[j]
                    r_stmts = r_step.stmt()
                    if r_stmts: 
                        r_stmt = r_stmts[0]
                        r_class = type(r_stmt).__name__
                        if r_class == 'GotoStmtContext':
                            final_target = r_stmt.ID().getText()
                            break
                        elif r_class == 'BreakStmtContext':
                            break
                        else: 
                            r_action = self._stmt_to_action(r_stmt)
                            if r_action:
                                post_label_actions.append(r_action)
                
                if label: 
                    return [OptionParseResult(
                        result_type=OptionResult.GOTO,
                        target_state=final_target,
                        guard=guard,
                        actions=current_actions. copy(),
                        intermediate_label=label,
                        post_label_actions=post_label_actions
                    )]
            
            if ctx_class == 'GotoStmtContext':
                target = stmt.ID().getText() if stmt.ID() else None
                return [OptionParseResult(
                    result_type=OptionResult.GOTO, target_state=target,
                    guard=guard, actions=current_actions.copy()
                )]
            
            elif ctx_class == 'BreakStmtContext':
                return [OptionParseResult(
                    result_type=OptionResult.BREAK,
                    guard=guard, actions=current_actions.copy()
                )]
            
            elif ctx_class == 'IfStmtContext':
                nested = self._process_nested_if_in_option(stmt, guard, current_actions. copy(), is_do)
                extra_actions = []
                for j in range(i+1, len(steps)):
                    r_stmts = steps[j].stmt()
                    if r_stmts: 
                        r_stmt = r_stmts[0]
                        r_class = type(r_stmt).__name__
                        if r_class == 'GotoStmtContext':
                            target = r_stmt. ID().getText()
                            for nr in nested:
                                if nr.result_type in [OptionResult. CONTINUE, OptionResult. FALLTHROUGH]: 
                                    nr. result_type = OptionResult.GOTO
                                    nr. target_state = target
                                nr.actions. extend(extra_actions)
                            return nested
                        elif r_class == 'BreakStmtContext':
                            for nr in nested: 
                                if nr. result_type in [OptionResult. CONTINUE, OptionResult.FALLTHROUGH]: 
                                    nr.result_type = OptionResult. BREAK
                                nr.actions.extend(extra_actions)
                            return nested
                        else: 
                            r_action = self._stmt_to_action(r_stmt)
                            if r_action:
                                extra_actions.append(r_action)
                
                for nr in nested:
                    nr.actions.extend(extra_actions)
                return nested
            
            action = self._stmt_to_action(stmt)
            if action:
                current_actions.append(action)
            
            first_stmt_processed = True
            i += 1
        
        return [OptionParseResult(
            result_type=OptionResult.CONTINUE if is_do else OptionResult.FALLTHROUGH,
            guard=guard, actions=current_actions. copy()
        )]

    def _process_nested_if_in_option(self, ctx, outer_guard, prefix_actions, is_do):
        results = []
        if ctx.optionList():
            for option in ctx.optionList().option():
                nested = self._parse_option_sequence(option.sequence(), is_do)
                for r in nested:
                    combined_guard = r.guard if r.guard else outer_guard
                    results.append(OptionParseResult(
                        result_type=r.result_type,
                        target_state=r. target_state,
                        guard=combined_guard,
                        actions=prefix_actions + r.actions,
                        intermediate_label=r. intermediate_label,
                        post_label_actions=r. post_label_actions
                    ))
        return results or [OptionParseResult(
            result_type=OptionResult.CONTINUE if is_do else OptionResult.FALLTHROUGH
        )]
    
    def _process_for_stmt(self, ctx, prefix_actions: List[Action]):
        if not self.current_state or not self.current_process:
            return

        var_name = ctx.ID().getText()
        min_expr = self._visit_expr(ctx.expr(0))
        max_expr = self._visit_expr(ctx.expr(1))

        base = f"__for_{var_name}_{id(ctx)}"
        states = {n: f"{base}_{n}" for n in ['cond', 'body', 'incr', 'exit']}

        for name in states. values():
            self.current_process. states[name] = State(name=name)

        self.current_process. transitions.append(Transition(
            source=self.current_state, target=states['cond'],
            guard=None,
            actions=prefix_actions + [AssignAction(target=VarExpr(name=var_name), value=min_expr)]
        ))

        self.current_process. transitions.append(Transition(
            source=states['cond'], target=states['body'],
            guard=BinaryExpr(left=VarExpr(name=var_name), op='<=', right=max_expr)
        ))
        self.current_process.transitions.append(Transition(
            source=states['cond'], target=states['exit'],
            guard=BinaryExpr(left=VarExpr(name=var_name), op='>', right=max_expr)
        ))

        self.current_state = states['body']

        if ctx.sequence():
            self._process_proctype_sequence(ctx.sequence())
            if self.current_state:
                self. current_process.transitions.append(Transition(
                    source=self.current_state, target=states['incr'],
                    guard=None, actions=[]
                ))
        else:
            self.current_process. transitions.append(Transition(
                source=states['body'], target=states['incr'],
                guard=None, actions=[]
            ))

        self.current_process.transitions.append(Transition(
            source=states['incr'], target=states['cond'],
            guard=None,
            actions=[AssignAction(
                target=VarExpr(name=var_name),
                value=BinaryExpr(left=VarExpr(name=var_name), op='+', right=ConstExpr(value=1))
            )]
        ))

        self.current_state = states['exit']
    
    def _check_greedy_split(self, stmt_ctx) -> Optional[Tuple[object, str]]:
        ctx_class = type(stmt_ctx).__name__
        
        if ctx_class == 'ExprStmtContext': 
            expr = stmt_ctx.expr()
            if type(expr).__name__ == 'ImpliesExprContext': 
                left, right = expr.expr(0), expr.expr(1)
                if self._is_simple_id(right):
                    return (self._visit_expr(left), right.getText())
        
        elif ctx_class == 'ReceiveStatementContext':
            recv_stmt = stmt_ctx.receiveStmt() if hasattr(stmt_ctx, 'receiveStmt') else stmt_ctx
            if recv_stmt and recv_stmt.recvArgs():
                args = recv_stmt.recvArgs().recvArg()
                if args: 
                    last_arg = args[-1]
                    if hasattr(last_arg, 'expr') and last_arg.expr():
                        last_expr = last_arg. expr()
                        if type(last_expr).__name__ == 'ImpliesExprContext': 
                            left, right = last_expr. expr(0), last_expr.expr(1)
                            if self._is_simple_id(right):
                                channel = self._get_varref_name(recv_stmt.varRef())
                                variables = [a. getText() for a in args[:-1]] + [left.getText()]
                                return (ReceiveAction(channel=channel, variables=variables), right.getText())
        
        return None
    
    def _is_simple_id(self, expr_ctx) -> bool:
        t = type(expr_ctx).__name__
        if t in ['VarRefExprContext', 'TerminalNodeImpl']:
            return True
        return bool(re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*(\[.*\])?$', expr_ctx.getText()))
    
    def _parse_text_as_action(self, text: str) -> Optional[Action]:
        text = text.strip()
        
        match = re.match(r'^(\w+(?:\[.*?\])?)\s*!\s*(.+)$', text)
        if match: 
            msgs = [m.strip().rstrip(';') for m in match.group(2).split(',')]
            return SendAction(channel=match.group(1), messages=msgs)
        
        match = re.match(r'^(\w+(?:\[.*?\])?)\s*\?\s*(.+)$', text)
        if match: 
            vars_list = [v.strip().rstrip(';') for v in match. group(2).split(',')]
            return ReceiveAction(channel=match.group(1), variables=vars_list)
        
        return None
    
    def _step_has_arrow(self, step_ctx) -> bool:
        for i in range(step_ctx.getChildCount()):
            child = step_ctx.getChild(i)
            if hasattr(child, 'getText') and child.getText() == '->':
                return True
        return False
    
    def _is_else_step(self, step_ctx) -> bool:
        for i in range(step_ctx.getChildCount()):
            child = step_ctx.getChild(i)
            if hasattr(child, 'getText') and child.getText() == 'else':
                return True
        return False
    
    def _stmt_to_action(self, stmt) -> Optional[Action]: 
        ctx_class = type(stmt).__name__
        
        handlers = {
            'SendStatementContext': self._parse_send_action,
            'ReceiveStatementContext': self._parse_receive_action,
            'AssignStatementContext':  self._parse_assign_action,
            'SkipStmtContext': lambda _: SkipAction(),
            'ExprStmtContext': self._parse_expr_stmt_action,
            'SelectStmtContext': self._parse_select_action,
        }
        
        handler = handlers.get(ctx_class)
        return handler(stmt) if handler else None
    
    def _parse_select_action(self, ctx) -> Optional[SelectAction]:
        if not ctx.ID() or len(ctx.expr()) < 2:
            return None
        return SelectAction(
            target=VarExpr(name=ctx.ID().getText()),
            min_val=self._visit_expr(ctx.expr(0)),
            max_val=self._visit_expr(ctx.expr(1))
        )
    
    # ==================== Init进程 ====================
    
    def visitInit(self, ctx: PromelaParser.InitContext):
        process = Process(
            name="init", states={}, transitions=[], local_variables={},
            parameters=[], is_active=True, active_count=1
        )
        
        self.current_process = process
        self.init_assignments = {}  # 重置
        
        if ctx.sequence():
            self._process_init_sequence(ctx.sequence())
        
        # 将 init 块中的赋值保存到 program 中
        self.program.init_assignments = self.init_assignments.copy()
        
        self.program.init_process = process
        self.current_process = None
        return None
    
    
    def _process_init_sequence(self, ctx):
        if ctx is None:
            return
        for step in ctx.step():
            self._process_init_step(step)
    
    def _process_init_step(self, ctx):
        if ctx.varDecl():
            self.visit(ctx.varDecl())
            return
        
        stmts = ctx. stmt()
        if stmts: 
            for stmt in stmts:
                self._process_init_stmt(stmt)
    
    def _process_init_stmt(self, ctx):
        ctx_class = type(ctx).__name__
        
        if ctx_class == 'RunStmtContext':
            self._handle_run_stmt(ctx)
        elif ctx_class in ['BlockStmtContext', 'AtomicStmtContext']:
            if ctx.sequence():
                self._process_init_sequence(ctx.sequence())
        # 新增：处理赋值语句
        elif ctx_class == 'AssignStatementContext':
            self._handle_init_assignment(ctx)
    
    # 新增方法
    def _handle_init_assignment(self, ctx):
        """处理 init 块中的赋值语句"""
        assignment = ctx.assignment()
        if assignment is None:
            return
        
        # 只处理简单赋值 (var = value)
        if assignment.getChildCount() == 3 and assignment.getChild(1).getText() == '=':
            target = self._get_varref_full_name(assignment.varRef())
            value = assignment.expr().getText()
            
        # 不解析 define 宏，保留原始符号名称
        # if value in self.defines:
        #     value = self.defines[value]
            
            self.init_assignments[target] = value

    def _get_varref_full_name(self, varref_ctx) -> str:
        """获取变量引用的完整名称，包括数组索引"""
        if varref_ctx is None:
            return ""
        
        ids = varref_ctx.ID()
        exprs = varref_ctx.expr() if varref_ctx.expr() else []
        
        name = ids[0].getText() if ids else varref_ctx.getText()
        
        if exprs:
            # 有数组索引
            index = exprs[0].getText()
            return f"{name}[{index}]"
        
        return name

    def _handle_run_stmt(self, ctx):
        proc_name = ctx. ID().getText() if ctx.ID() else None
        if proc_name is None:
            return
        
        arguments = []
        if ctx.argList():
            for expr in ctx.argList().expr():
                arguments.append(expr.getText())
        
        self.run_statements. append(RunStatement(proctype_name=proc_name, arguments=arguments))
    
    def _instantiate_processes(self):
        for run_stmt in self. run_statements: 
            proc_name = run_stmt.proctype_name
            
            if proc_name not in self.process_templates:
                continue
            
            template = self.process_templates[proc_name]
            
            if proc_name not in self.process_instance_count:
                self. process_instance_count[proc_name] = 0
            
            instance_id = self. process_instance_count[proc_name]
            self.process_instance_count[proc_name] += 1
            
            param_mapping = {}
            non_channel_params = {}  # 新增：非通道���数映射
            channel_param_names = getattr(template, 'channel_parameter_names', set())
            
            for i, (param_name, param_type) in enumerate(template.parameters):
                if i < len(run_stmt.arguments):
                    arg_value = run_stmt. arguments[i]
                    param_mapping[param_name] = arg_value
                    # 如果不是通道参数，记录为非通道参数
                    if param_name not in channel_param_names: 
                        non_channel_params[param_name] = (param_type, arg_value)
            
            instance_name = f"{proc_name}_{run_stmt.arguments[0]}" if run_stmt. arguments else f"{proc_name}_{instance_id}"
            
            process = self._instantiate_process(template, instance_name, param_mapping, non_channel_params)
            self.program.processes[instance_name] = process
    
    def _instantiate_process(self, template: ProcessTemplate, instance_name: str,
                            param_mapping: Dict[str, str], 
                            non_channel_params:  Dict[str, Tuple[str, str]] = None) -> Process:
        process = Process(
            name=instance_name,
            states=copy.deepcopy(template.states),
            transitions=[],
            local_variables=copy.deepcopy(template.local_variables),
            parameters=[],
            initial_state=template. initial_state,
            is_active=True,
            active_count=1
        )
        
        # 只替换通道参数，不替换其他参数
        channel_param_mapping = {}
        channel_param_names = getattr(template, 'channel_parameter_names', set())
        for param_name, param_value in param_mapping. items():
            if param_name in channel_param_names: 
                channel_param_mapping[param_name] = param_value
        
        for trans in template.transitions:
            # 只用通道参数映射进行替换
            new_trans = self._substitute_transition(trans, channel_param_mapping)
            process.transitions. append(new_trans)
        
        # 复制状态入口赋值信息
        if hasattr(template, 'state_entry_assignments'):
            process.state_entry_assignments = copy.deepcopy(template.state_entry_assignments)
        if hasattr(template, 'local_var_types'):
            process.local_var_types = copy.deepcopy(template.local_var_types)
        
        # 将非通道参数作为局部变量，并记录其初始值
        if non_channel_params:
            if not hasattr(process, 'parameter_variables'):
                process. parameter_variables = {}
            for param_name, (param_type, param_value) in non_channel_params. items():
                process.parameter_variables[param_name] = {
                    'type':  param_type,
                    'value': param_value
                }
                # 同时添加到 local_var_types
                if hasattr(process, 'local_var_types'):
                    process.local_var_types[param_name] = param_type
        
        return process
    
    def _substitute_transition(self, trans: Transition, param_mapping: Dict[str, str]) -> Transition:
        new_actions = []
        
        for action in trans.actions:
            if isinstance(action, SendAction):
                new_actions.append(SendAction(
                    channel=param_mapping.get(action.channel, action.channel),
                    messages=action. messages. copy()
                ))
            elif isinstance(action, ReceiveAction):
                new_actions.append(ReceiveAction(
                    channel=param_mapping.get(action.channel, action.channel),
                    variables=action. variables.copy()
                ))
            elif isinstance(action, AssignAction):
                # 替换赋值操作中的参数引用
                new_target = self._substitute_expr(action.target, param_mapping)
                new_value = self._substitute_expr(action.value, param_mapping)
                new_actions.append(AssignAction(target=new_target, value=new_value))
            else:
                new_actions.append(action)
        
        # 替换 guard 中的参数引用
        new_guard = self._substitute_expr(trans.guard, param_mapping) if trans.guard else None
        
        return Transition(
            source=trans.source, target=trans. target,
            guard=new_guard, actions=new_actions, is_atomic=trans.is_atomic
        )
    
    def _substitute_expr(self, expr: Expression, param_mapping: Dict[str, str]) -> Expression:
        """递归替换表达式中的参数引用"""
        if expr is None:
            return None
        
        if isinstance(expr, VarExpr):
            # 如果变量名在参数映射中，替换为实际值
            if expr.name in param_mapping:
                new_value = param_mapping[expr.name]
                # 尝试解析为数字
                try: 
                    return ConstExpr(value=int(new_value))
                except ValueError:
                    return VarExpr(name=new_value, index=expr.index, field=expr.field)
            # 替换索引表达式中的参数
            if expr.index:
                new_index = self._substitute_expr(expr.index, param_mapping)
                return VarExpr(name=expr.name, index=new_index, field=expr.field)
            return expr
        
        elif isinstance(expr, BinaryExpr):
            return BinaryExpr(
                left=self._substitute_expr(expr.left, param_mapping),
                op=expr.op,
                right=self._substitute_expr(expr.right, param_mapping)
            )
        
        elif isinstance(expr, UnaryExpr):
            return UnaryExpr(
                op=expr. op,
                operand=self._substitute_expr(expr. operand, param_mapping)
            )
        
        elif isinstance(expr, ConstExpr):
            return expr
        
        return expr
    
    # ==================== 动作解析 ====================
    
    def _parse_send_action(self, ctx) -> Optional[SendAction]:
        send_stmt = ctx. sendStmt() if hasattr(ctx, 'sendStmt') else ctx
        if send_stmt is None:
            return None
        channel = None
        messages = []
        if hasattr(send_stmt, 'varRef') and send_stmt. varRef():
            channel = self._get_varref_name(send_stmt. varRef())
        if hasattr(send_stmt, 'argList') and send_stmt.argList():
            for expr in send_stmt.argList().expr():
                msg = expr.getText()
                msg = msg.rstrip(';')
                if msg. endswith('->'):
                    msg = msg[:-2]. rstrip()
                messages.append(msg)
        if channel is None: 
            match = re.match(r'(\w+)\s*!\s*(\w+)', ctx.getText())
            if match:
                channel, messages = match.group(1), [match.group(2)]
        return SendAction(channel=channel, messages=messages) if channel else None
    
    def _parse_receive_action(self, ctx) -> Optional[ReceiveAction]:
        recv_stmt = ctx. receiveStmt() if hasattr(ctx, 'receiveStmt') else ctx
        if recv_stmt is None: 
            return None
        
        channel = None
        variables = []
        
        if hasattr(recv_stmt, 'varRef') and recv_stmt.varRef():
            channel = self._get_varref_name(recv_stmt.varRef())
        
        if hasattr(recv_stmt, 'recvArgs') and recv_stmt.recvArgs():
            for recv_arg in recv_stmt. recvArgs().recvArg():
                if hasattr(recv_arg, 'expr') and recv_arg.expr():
                    variables.append(recv_arg.expr().getText())
        
        if channel is None: 
            match = re.match(r'(\w+)\s*\?\s*(\w+)', ctx.getText())
            if match:
                channel, variables = match. group(1), [match.group(2)]
        
        return ReceiveAction(channel=channel, variables=variables) if channel else None
    
    def _get_varref_name(self, varref_ctx) -> str:
        if varref_ctx.ID():
            ids = varref_ctx.ID()
            if ids: 
                return ids[0]. getText()
        return varref_ctx.getText()
    
    def _parse_assign_action(self, ctx) -> Optional[AssignAction]: 
        assignment = ctx.assignment()
        
        if assignment. getChildCount() == 2:
            op = assignment.getChild(1).getText()
            var_expr = self._visit_varref(assignment.varRef())
            op_str = '+' if op == '++' else '-'
            return AssignAction(
                target=var_expr,
                value=BinaryExpr(left=var_expr, op=op_str, right=ConstExpr(1))
            )
        
        if assignment.getChildCount() == 3 and assignment.getChild(1).getText() == '=': 
            target = self._visit_varref(assignment. varRef())
            value = self._visit_expr(assignment. expr())
            return AssignAction(target=target, value=value)
        
        return None
    
    def _parse_expr_stmt_action(self, ctx) -> Optional[Action]: 
        text = ctx.getText()
        if '?' in text and '? ?' not in text:
            match = re.match(r'(\w+)\s*\?\s*(\w+)', text)
            if match: 
                return ReceiveAction(channel=match.group(1), variables=[match.group(2)])
        return None
    
    # ==================== 表达式 ====================
    
    def _visit_expr(self, ctx) -> Optional[Expression]:
        if ctx is None:
            return None
        
        ctx_class = type(ctx).__name__
        
        simple_handlers = {
            'NumberExprContext': lambda c: ConstExpr(value=int(c. NUMBER().getText())),
            'TrueExprContext': lambda _: ConstExpr(value=True),
            'FalseExprContext':  lambda _: ConstExpr(value=False),
            'TimeoutExprContext': lambda _: VarExpr(name='timeout'),
        }
        
        if ctx_class in simple_handlers: 
            return simple_handlers[ctx_class](ctx)
        
        if ctx_class == 'VarRefExprContext':
            return self._visit_varref(ctx. varRef()) if ctx.varRef() else VarExpr(name=ctx.getText())
        
        if ctx_class == 'ParenExprContext': 
            return self._visit_expr(ctx.expr()) if ctx.expr() else None
        
        if ctx_class == 'NotExprContext': 
            return UnaryExpr(op='!', operand=self._visit_expr(ctx.expr())) if ctx.expr() else None
        
        if ctx_class == 'EqualityExprContext':
            exprs = ctx.expr()
            if exprs and len(exprs) >= 2:
                op = '=='
                for i in range(ctx.getChildCount()):
                    child_text = ctx.getChild(i).getText()
                    if child_text in ['==', '!=']: 
                        op = child_text
                        break
                return BinaryExpr(
                    left=self._visit_expr(exprs[0]),
                    op=op,
                    right=self._visit_expr(exprs[1])
                )
        
        if hasattr(ctx, 'expr') and callable(ctx.expr):
            exprs = ctx.expr()
            if isinstance(exprs, list) and len(exprs) >= 2:
                return BinaryExpr(
                    left=self._visit_expr(exprs[0]),
                    op=self._get_binary_operator(ctx),
                    right=self._visit_expr(exprs[1])
                )
        
        text = ctx.getText()
        if text. lstrip('-').isdigit():
            return ConstExpr(value=int(text))
        return VarExpr(name=text)
    
    def _visit_varref(self, ctx) -> VarExpr: 
        ids = ctx.ID()
        exprs = ctx.expr() if ctx.expr() else []
        
        name = ids[0]. getText() if ids else ctx.getText()
        index = self._visit_expr(exprs[0]) if exprs else None
        
        return VarExpr(name=name, index=index)
    
    def _get_binary_operator(self, ctx) -> str:
        ctx_class = type(ctx).__name__
        op_map = {
            'EqualityExprContext': '==',
            'LogicalAndExprContext': '&&',
            'LogicalOrExprContext': '||',
            'RelationalExprContext':  '<',
            'AddSubExprContext': '+',
            'MulDivModExprContext': '*',
        }
        return op_map.get(ctx_class, '? ')
    
    def _eval_const_expr(self, ctx, allow_symbolic:  bool = False):
        if ctx is None:
            return 0 if not allow_symbolic else None
        text = ctx.getText()
        try:
            return int(text)
        except ValueError:
            pass
        if text in self.defines:
            val = self.defines[text]
            try:
                return int(val)
            except ValueError:
                return val if allow_symbolic else 0
        return text if allow_symbolic else 0


# ==================== 变量追踪和简化输出 ====================
class VariableTracker:
    """追踪变量赋值并生成状态入口赋值，区分trigger和action，过滤共性赋值"""
    
    def __init__(self, program:  ProgramModel):
        self.program = program
        self.global_var_names = set(program.global_variables.keys())
    
    def analyze_process(self, process: Process) -> Dict:   
        """分析进程，提取变量信息，区分trigger和action，过滤掉状态入口的共性赋值"""
        result = {
            'name': process.name,
            'states': list(process.states. keys()),
            'initial_state': process. initial_state,
            'local_vars': {},
            'parameter_variables': {},
            'state_entry_assignments':   {},
            'simplified_transitions': []
        }
        
        # 收集局部变量类型
        if hasattr(process, 'local_var_types'):
            result['local_vars'] = process.local_var_types. copy()
        else:
            for var_name, var in process.local_variables.items():
                result['local_vars'][var_name] = var. var_type. value
        
        # 收集参数变量（非通道类型的参数）
        if hasattr(process, 'parameter_variables'):
            result['parameter_variables'] = process.parameter_variables.copy()
        
        # 用于检查变量是否是 mtype 类型的局部变量
        mtype_local_vars = set()
        for var_name, var_type in result['local_vars']. items():
            if var_type == 'mtype': 
                mtype_local_vars.add(var_name)
        
        # 第一遍：收集每个状态所有出边的【前缀赋值】，确定共性赋值
        state_prefix_assigns = {}
        
        for trans in process.transitions:
            source = trans.source
            
            if source not in state_prefix_assigns: 
                state_prefix_assigns[source] = []
            
            prefix_assigns = {}
            seen_vars = set()
            
            for action in trans.actions:
                if isinstance(action, (SendAction, ReceiveAction)):
                    break
                
                if isinstance(action, AssignAction):
                    if isinstance(action.target, VarExpr):
                        var_name = action. target.name
                        if action.target.index: 
                            var_key = f"{var_name}[{format_expression(action.target. index)}]"
                        else: 
                            var_key = var_name
                        
                        if var_key in seen_vars: 
                            break
                        
                        value_str = format_expression(action. value)
                        prefix_assigns[var_key] = value_str
                        seen_vars.add(var_key)
            
            state_prefix_assigns[source]. append(prefix_assigns)
        
        # 计算每个状态的共性入口赋值
        state_entry_assignments = {}
        for state, all_trans_assigns in state_prefix_assigns.items():
            if not all_trans_assigns:
                continue
            
            common_assigns = dict(all_trans_assigns[0])
            
            for trans_assigns in all_trans_assigns[1:]: 
                keys_to_remove = []
                for var_key, value_str in common_assigns.items():
                    if var_key not in trans_assigns or trans_assigns[var_key] != value_str:
                        keys_to_remove.append(var_key)
                for key in keys_to_remove:
                    del common_assigns[key]
            
            if common_assigns: 
                state_entry_assignments[state] = common_assigns
        
        result['state_entry_assignments'] = state_entry_assignments
        
        # 第二遍：生成简化的转换，过滤掉状态入口的共性赋值
        for trans in process.transitions:
            source = trans.source
            target = trans.target
            
            entry_assigns = state_entry_assignments.get(source, {})
            
            triggers = []
            actions = []
            
            var_assign_count = {}
            
            for action in trans.actions:
                if isinstance(action, ReceiveAction):
                    # 检查接收的变量是否是 mtype 类型的局部变量
                    is_var = False
                    if action.variables:
                        for var in action.variables:
                            if var in mtype_local_vars:
                                is_var = True
                                break
                    
                    triggers.append({
                        'type': 'receive',
                        'channel': action.channel,
                        'variables': action.variables,
                        'is_variable': is_var
                    })
                elif isinstance(action, SendAction):
                    # 检查发送的消息是否是 mtype 类型的局部变量
                    is_var = False
                    if action.messages:
                        for msg in action.messages:
                            if msg in mtype_local_vars:
                                is_var = True
                                break
                    
                    triggers. append({
                        'type': 'send',
                        'channel': action. channel,
                        'messages': action. messages,
                        'is_variable':  is_var
                    })
                elif isinstance(action, AssignAction):
                    if isinstance(action. target, VarExpr):
                        var_name = action.target.name
                        if action. target.index:
                            var_key = f"{var_name}[{format_expression(action. target.index)}]"
                        else:
                            var_key = var_name
                        value_str = format_expression(action.value)
                        
                        var_assign_count[var_key] = var_assign_count.get(var_key, 0) + 1
                        
                        if var_assign_count[var_key] == 1 and var_key in entry_assigns and entry_assigns[var_key] == value_str:
                            continue
                        
                        actions.append({
                            'type': 'assign',
                            'target': format_expression(action. target),
                            'value': format_expression(action. value)
                        })
                elif isinstance(action, SkipAction):
                    actions.append({'type': 'skip'})
                elif isinstance(action, SelectAction):
                    actions.append({
                        'type': 'select',
                        'target': format_expression(action.target),
                        'min_val': format_expression(action. min_val),
                        'max_val': format_expression(action.max_val)
                    })
            
            guard_str = format_expression(trans. guard) if trans.guard else None
            
            result['simplified_transitions']. append(SimplifiedTransition(
                source=source,
                target=target,
                guard=guard_str,
                triggers=triggers,
                actions=actions
            ))
        
        return result
    
    def _is_channel_variable(self, channel_name: str) -> bool:
        """检查通道名是否是变量（参数传入的通道）"""
        return channel_name not in self.program. channels


def format_action(action: Action) -> str:
    """格式化动作为字符串"""
    if isinstance(action, SendAction):
        return f"{action.channel}!  {','.join(str(m) for m in action.messages)}"
    elif isinstance(action, ReceiveAction):
        return f"{action.channel}?  {','.join(action.variables)}"
    elif isinstance(action, AssignAction):
        return f"{format_expression(action. target)} = {format_expression(action.value)}"
    elif isinstance(action, SkipAction):
        return "skip"
    elif isinstance(action, SelectAction):
        return f"select({format_expression(action.target)}: {format_expression(action.min_val)}..{format_expression(action.max_val)})"
    return str(type(action).__name__)


def format_action_dict(action_dict: Dict) -> str:
    """格式化动作字典为字符串"""
    action_type = action_dict. get('type', '')
    if action_type == 'send':
        return f"{action_dict['channel']}! {','.join(action_dict['messages'])}"
    elif action_type == 'receive':
        return f"{action_dict['channel']}?  {','.join(action_dict['variables'])}"
    elif action_type == 'assign':
        return f"{action_dict['target']} = {action_dict['value']}"
    elif action_type == 'skip':
        return "skip"
    elif action_type == 'select':
        return f"select({action_dict['target']}: {action_dict['min_val']}..{action_dict['max_val']})"
    return str(action_dict)


def format_expression(expr: Expression) -> str:
    """格式化表达式为字符串"""
    if expr is None:
        return "None"
    if isinstance(expr, ConstExpr):
        return str(expr.value)
    elif isinstance(expr, VarExpr):
        result = expr.name
        if expr.index:
            result += f"[{format_expression(expr. index)}]"
        if expr.field:
            result += f".{expr.field}"
        return result
    elif isinstance(expr, BinaryExpr):
        return f"({format_expression(expr.left)} {expr.op} {format_expression(expr.right)})"
    elif isinstance(expr, UnaryExpr):
        return f"{expr.op}{format_expression(expr.operand)}"
    return str(expr)


def print_program(program: ProgramModel):
    """打印程序模型"""
    print("=" * 70)
    print("PML解析结果")
    print("=" * 70)
    
    print(f"\nMType: {program.mtype_values}")
    
    print(f"\nChannels ({len(program.channels)}):")
    for name, chan in program.channels. items():
        print(f"  {name}: capacity={chan.capacity}, types={chan.message_types}")
    
    print(f"\nGlobal Variables ({len(program. global_variables)}):")
    for name, var in program. global_variables.items():
        arr = f"[{var. array_size}]" if var.is_array else ""
        print(f"  {var.var_type.value} {name}{arr}")
    
    if program.defines:
        print(f"\nDefines ({len(program.defines)}):")
        for name, val in program.defines. items():
            print(f"  {name} = {format_expression(val)}")
    
    print(f"\nProcesses ({len(program.processes)}):")
    for proc_name, proc in program.processes.items():
        print(f"\n  Process:  {proc_name}")
        print(f"    Active: {proc.is_active}")
        if proc.parameters:
            print(f"    Parameters:  {proc.parameters}")
        print(f"    States ({len(proc.states)}): {list(proc.states. keys())}")
        print(f"    Initial State: {proc.initial_state}")
        print(f"    Transitions ({len(proc.transitions)}):")
        for trans in proc.transitions:
            actions_str = "; ".join(format_action(a) for a in trans.actions) or "ε"
            guard_str = f" [{format_expression(trans.guard)}]" if trans.guard else ""
            print(f"      {trans.source} -> {trans.target}{guard_str}:  [{actions_str}]")


def print_enhanced_program(program:  ProgramModel):
    """打印增强的程序模型，包含变量追踪信息，区分trigger和action，过滤共性赋值"""
    print("=" * 70)
    print("PML解析结果 (增强版 v5)")
    print("=" * 70)
    
    print(f"\nMType: {program.mtype_values}")
    
    print(f"\nChannels ({len(program. channels)}):")
    for name, chan in program.channels. items():
        print(f"  {name}: capacity={chan.capacity}, types={chan.message_types}")
    
    print(f"\nGlobal Variables ({len(program.global_variables)}):")
    for name, var in program.global_variables.items():
        arr = f"[{var. array_size}]" if var.is_array else ""
        init = f" = {format_expression(var.initial_value)}" if var.initial_value else ""
        print(f"  {var. var_type.value} {name}{arr}{init}")
    
    tracker = VariableTracker(program)
    
    print(f"\nProcesses ({len(program.processes)}):")
    for proc_name, proc in program.processes.items():
        analysis = tracker.analyze_process(proc)
        
        print(f"\n  Process: {proc_name}")
        print(f"    States:  {analysis['states']}")
        print(f"    Initial State: {analysis['initial_state']}")
        
        if analysis['local_vars']:
            print(f"    Local Variables:")
            for var_name, var_type in analysis['local_vars'].items():
                print(f"      {var_type} {var_name}")
        
        # 显示参数变量
        if analysis['parameter_variables']: 
            print(f"    Parameter Variables (instantiated):")
            for var_name, var_info in analysis['parameter_variables'].items():
                print(f"      {var_info['type']} {var_name} = {var_info['value']}")
        
        if analysis['state_entry_assignments']:
            print(f"    State Entry Assignments:")
            for state, assigns in analysis['state_entry_assignments'].items():
                assign_str = ", ".join(f"{k}={v}" for k, v in assigns.items())
                print(f"      {state}:  {{{assign_str}}}")
        
        print(f"    Transitions ({len(analysis['simplified_transitions'])}):")
        for trans in analysis['simplified_transitions']:
            guard_str = f" [{trans.guard}]" if trans.guard else ""
            
            # 格式化 triggers
            trigger_strs = []
            for t in trans.triggers:
                trigger_strs.append(format_action_dict(t))
            trigger_str = "; ".join(trigger_strs) if trigger_strs else ""
            
            # 格式化 actions (过滤共性赋值后的)
            action_strs = []
            for a in trans.actions:
                action_strs.append(format_action_dict(a))
            action_str = "; ".join(action_strs) if action_strs else "ε"
            
            # 组合输出
            if trigger_str: 
                print(f"      {trans.source} -> {trans.target}{guard_str}")
                print(f"        triggers: [{trigger_str}]")
                print(f"        actions:   [{action_str}]")
            else:
                print(f"      {trans.source} -> {trans.target}{guard_str}")
                print(f"        actions:  [{action_str}]")


def format_action(action: Action) -> str:
    """格式化动作为字符串"""
    if isinstance(action, SendAction):
        return f"{action.channel}!  {','.join(str(m) for m in action.messages)}"
    elif isinstance(action, ReceiveAction):
        return f"{action.channel}?  {','.join(action.variables)}"
    elif isinstance(action, AssignAction):
        return f"{format_expression(action. target)} = {format_expression(action. value)}"
    elif isinstance(action, SkipAction):
        return "skip"
    elif isinstance(action, SelectAction):
        return f"select({format_expression(action.target)}: {format_expression(action.min_val)}..{format_expression(action.max_val)})"
    return str(type(action).__name__)


def format_action_dict(action_dict: Dict) -> str:
    """格式化动作字典为字符串"""
    action_type = action_dict. get('type', '')
    if action_type == 'send':
        return f"{action_dict['channel']}! {','.join(action_dict['messages'])}"
    elif action_type == 'receive':
        return f"{action_dict['channel']}?  {','.join(action_dict['variables'])}"
    elif action_type == 'assign':
        return f"{action_dict['target']} = {action_dict['value']}"
    elif action_type == 'skip':
        return "skip"
    elif action_type == 'select':
        return f"select({action_dict['target']}: {action_dict['min_val']}..{action_dict['max_val']})"
    return str(action_dict)


def format_expression(expr: Expression) -> str:
    """格式化表达式为字符串"""
    if expr is None:
        return "None"
    if isinstance(expr, ConstExpr):
        return str(expr.value)
    elif isinstance(expr, VarExpr):
        result = expr.name
        if expr.index:
            result += f"[{format_expression(expr. index)}]"
        if expr.field:
            result += f".{expr.field}"
        return result
    elif isinstance(expr, BinaryExpr):
        return f"({format_expression(expr.left)} {expr.op} {format_expression(expr.right)})"
    elif isinstance(expr, UnaryExpr):
        return f"{expr.op}{format_expression(expr.operand)}"
    return str(expr)


def print_program(program: ProgramModel):
    """打印程序模型"""
    print("=" * 70)
    print("PML解析结果")
    print("=" * 70)
    
    print(f"\nMType: {program.mtype_values}")
    
    print(f"\nChannels ({len(program.channels)}):")
    for name, chan in program.channels. items():
        print(f"  {name}: capacity={chan.capacity}, types={chan.message_types}")
    
    print(f"\nGlobal Variables ({len(program.global_variables)}):")
    for name, var in program.global_variables.items():
        arr = f"[{var. array_size}]" if var.is_array else ""
        print(f"  {var.var_type.value} {name}{arr}")
    
    if program.defines:
        print(f"\nDefines ({len(program.defines)}):")
        for name, val in program.defines. items():
            print(f"  {name} = {format_expression(val)}")
    
    print(f"\nProcesses ({len(program.processes)}):")
    for proc_name, proc in program.processes.items():
        print(f"\n  Process: {proc_name}")
        print(f"    Active:  {proc.is_active}")
        if proc.parameters:
            print(f"    Parameters:  {proc.parameters}")
        print(f"    States ({len(proc.states)}): {list(proc.states. keys())}")
        print(f"    Initial State: {proc. initial_state}")
        print(f"    Transitions ({len(proc. transitions)}):")
        for trans in proc.transitions:
            actions_str = "; ".join(format_action(a) for a in trans.actions) or "ε"
            guard_str = f" [{format_expression(trans.guard)}]" if trans. guard else ""
            print(f"      {trans.source} -> {trans.target}{guard_str}:  [{actions_str}]")


def print_enhanced_program(program:  ProgramModel):
    """打印增强的程序模型，包含变量追踪信息，区分trigger和action"""
    print("=" * 70)
    print("PML解析结果 (增强版 v5)")
    print("=" * 70)
    
    print(f"\nMType: {program.mtype_values}")
    
    print(f"\nChannels ({len(program. channels)}):")
    for name, chan in program.channels. items():
        print(f"  {name}: capacity={chan.capacity}, types={chan.message_types}")
    
    print(f"\nGlobal Variables ({len(program.global_variables)}):")
    for name, var in program.global_variables.items():
        arr = f"[{var. array_size}]" if var.is_array else ""
        init = f" = {format_expression(var.initial_value)}" if var.initial_value else ""
        print(f"  {var. var_type.value} {name}{arr}{init}")
    
    tracker = VariableTracker(program)
    
    print(f"\nProcesses ({len(program. processes)}):")
    for proc_name, proc in program. processes.items():
        analysis = tracker.analyze_process(proc)
        
        print(f"\n  Process: {proc_name}")
        print(f"    States:  {analysis['states']}")
        print(f"    Initial State: {analysis['initial_state']}")
        
        if analysis['local_vars']:
            print(f"    Local Variables:")
            for var_name, var_type in analysis['local_vars'].items():
                print(f"      {var_type} {var_name}")
        
        # 新增：显示参数变量
        if analysis['parameter_variables']: 
            print(f"    Parameter Variables (instantiated):")
            for var_name, var_info in analysis['parameter_variables'].items():
                print(f"      {var_info['type']} {var_name} = {var_info['value']}")
        
        if analysis['state_entry_assignments']:
            print(f"    State Entry Assignments:")
            for state, assigns in analysis['state_entry_assignments'].items():
                assign_str = ", ".join(f"{k}={v}" for k, v in assigns.items())
                print(f"      {state}:  {{{assign_str}}}")
        
        print(f"    Transitions ({len(analysis['simplified_transitions'])}):")
        for trans in analysis['simplified_transitions']:
            guard_str = f" [{trans.guard}]" if trans.guard else ""
            
            # 格式化 triggers
            trigger_strs = []
            for t in trans.triggers:
                trigger_strs.append(format_action_dict(t))
            trigger_str = "; ".join(trigger_strs) if trigger_strs else ""
            
            # 格式化 actions
            action_strs = []
            for a in trans.actions:
                action_strs. append(format_action_dict(a))
            action_str = "; ".join(action_strs) if action_strs else "ε"
            
            # 组合输出
            if trigger_str: 
                print(f"      {trans. source} -> {trans.target}{guard_str}")
                print(f"        triggers: [{trigger_str}]")
                print(f"        actions:   [{action_str}]")
            else:
                print(f"      {trans.source} -> {trans.target}{guard_str}")
                print(f"        actions:  [{action_str}]")


# ==================== 主函数 ====================

def parse_pml(pml_code: str, silent: bool = False, debug: bool = False) -> ProgramModel:
    input_stream = InputStream(pml_code)
    
    lexer = PromelaLexer(input_stream)
    error_listener = PMLErrorListener()
    lexer. removeErrorListeners()
    lexer.addErrorListener(error_listener)
    
    token_stream = CommonTokenStream(lexer)
    
    parser = PromelaParser(token_stream)
    parser.removeErrorListeners()
    parser.addErrorListener(error_listener)
    
    tree = parser.spec()
    
    if error_listener.errors and not silent:
        print("语法警告:")
        for err in error_listener. errors[: 10]: 
            print(f"  {err}")
    
    visitor = PMLVisitorImpl(debug=debug)
    program = visitor.visit(tree)
    
    return program


def parse_pml_file(filepath: str, silent:  bool = False) -> ProgramModel: 
    with open(filepath, 'r', encoding='utf-8') as f:
        pml_code = f.read()
    return parse_pml(pml_code, silent)


# ==================== 测试 ====================

if __name__ == "__main__":
    test_pml = '''
mtype = { DCCP_REQUEST, 
          DCCP_RESPONSE, 
          DCCP_DATA, 
          DCCP_ACK, 
          DCCP_DATAACK, 
          DCCP_CLOSEREQ, 
          DCCP_CLOSE, 
          DCCP_RESET,
          DCCP_SYNC,
          DCCP_SYNCACK };

chan AtoN = [1] of { mtype };
chan NtoA = [1] of { mtype };  /* 改为缓冲通道 */
chan BtoN = [1] of { mtype };
chan NtoB = [1] of { mtype };  /* 改为缓冲通道 */

int state[2];
int before_state[2];

#define ClosedState    0
#define ListenState    1
#define RequestState   2
#define RespondState   3
#define PartOpenState  4
#define OpenState      5
#define CloseReqState  6
#define ClosingState   7
#define TimeWaitState  8

#define StableState    9
#define ChangingState  10
#define UnstableState  11
#define EndState       -1

#define leftClosed       (state[0] == ClosedState)
#define rightEstablished (state[1] == OpenState)

#define leftListen   (state[0] == ListenState)
#define leftTimeWait (state[0] == TimeWaitState)
#define leftRespond  (state[0] == RespondState)
#define leftLTR      (leftListen || leftTimeWait || leftRespond)
#define leftTR       (              leftTimeWait || leftRespond)

/* 网络进程 - 转发消息*/
proctype Network() {
    mtype msg;
    do
    :: AtoN ?  msg -> 
       if
       :: NtoB !  msg;  /* 正常转发 */
       fi
    :: BtoN ? msg -> 
       if
       :: NtoA ! msg;  /* 正常转发 */
       fi
    od
}

proctype DCCP(chan snd, rcv; int i) {
    bool I_am_active;
CLOSED:
    I_am_active = false;
    before_state[i] = state[i];
    state[i] = ClosedState;
    if
    ::  state[i] = OPENState; i = 0; goto LISTEN; /* passive open */
    ::  snd ! DCCP_REQUEST;  /* active  open */ 
       goto REQUEST; 
    fi
LISTEN:
    before_state[i] = state[i];
    state[i] = ListenState;
    if
    :: rcv ? DCCP_REQUEST -> /* rcv request  */
       snd ! DCCP_RESPONSE; /* snd response */ 
       goto RESPOND;
    :: timeout -> goto CLOSED;
    fi
/* ...  其余 DCCP 进程代码保持不变 ...  */
REQUEST:
    I_am_active = true;
    before_state[i] = state[i];
    state[i] = RequestState;
    if
    :: rcv ? DCCP_RESPONSE -> 
       snd ! DCCP_ACK;
       goto PARTOPEN;
    ::  rcv ? DCCP_RESET -> goto CLOSED;
    :: rcv ?  DCCP_SYNC -> snd ! DCCP_RESET; goto CLOSED;
    :: timeout -> goto CLOSED;
    fi
RESPOND:
    I_am_active = false;
    before_state[i] = state[i];
    state[i] = RespondState;
    do
    :: rcv ? DCCP_ACK     -> goto OPEN;
    :: rcv ? DCCP_DATAACK -> goto OPEN; 
    :: timeout -> 
        if
        :: snd ! DCCP_RESET;
        :: skip;
        fi
        goto CLOSED;
    ::  snd ! DCCP_DATA;
    od
PARTOPEN: 
    before_state[i] = state[i];
    state[i] = PartOpenState;
    do
    ::  rcv ? DCCP_DATA;    snd ! DCCP_ACK; goto OPEN;
    :: rcv ?  DCCP_DATAACK; snd ! DCCP_ACK; goto OPEN;
    ::  snd ! DCCP_DATAACK;
    ::  timeout -> goto CLOSED;
    ::  rcv ? DCCP_CLOSEREQ -> snd ! DCCP_CLOSE; goto CLOSING;
    :: rcv ?  DCCP_CLOSE    -> snd !  DCCP_RESET; goto CLOSED;
    :: rcv ? DCCP_ACK      -> goto OPEN;
    od
OPEN:
    before_state[i] = state[i];
    state[i] = OpenState;
    do
    :: snd !  DCCP_DATA;
    :: snd ! DCCP_DATAACK;
    :: rcv ?  DCCP_ACK;
    ::  rcv ? DCCP_DATA;
    :: rcv ?  DCCP_DATAACK;
    ::  I_am_active == true -> 
       snd ! DCCP_CLOSEREQ;
       goto CLOSEREQ;
    ::  rcv ? DCCP_CLOSE ->
       snd !  DCCP_RESET;
       goto CLOSED;
    :: I_am_active == true ->
       snd ! DCCP_CLOSE;
       goto CLOSING;
    :: rcv ? DCCP_CLOSEREQ ->
       snd !  DCCP_CLOSE;
       goto CLOSING;
    :: goto CLOSED;
    od
CLOSEREQ:
    before_state[i] = state[i];
    state[i] = CloseReqState;
    rcv ? DCCP_CLOSE;
    snd ! DCCP_RESET;
    goto CLOSED;
CLOSING: 
    before_state[i] = state[i];
    state[i] = ClosingState;
    if
    ::  rcv ? DCCP_RESET ->
       goto TIMEWAIT;
    :: timeout -> goto CLOSED;
    fi
TIMEWAIT:
    before_state[i] = state[i];
    state[i] = TimeWaitState;
    skip;
    goto CLOSED;
}

init {
    state[0] = ClosedState;
    state[1] = ClosedState;
    before_state[0] = ClosedState;
    before_state[1] = ClosedState;
    run Network();              /* 启动网络进程 */
    run DCCP(AtoN, NtoA, 0);
    run DCCP(BtoN, NtoB, 1);
}
'''
    
    print("\n" + "=" * 70)
    print("测试:  DCCP协议PML")
    print("=" * 70)
    
    try: 
        program = parse_pml(test_pml, debug=False)
        
        # 使用增强版输出
        print_enhanced_program(program)
        
        print("\n" + "=" * 70)
        
    except Exception as e: 
        print(f"解析错误: {e}")
        import traceback
        traceback. print_exc()
