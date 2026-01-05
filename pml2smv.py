#!/usr/bin/env python3
"""
PML to SMV Converter - 完整整合版（修复 msg 变量展开）
将 Promela (PML) 模型转换为 NuSMV 模型
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple
from collections import defaultdict
import re
import argparse
import sys

# 导入 PML 解析器
from pml_visitor_v3 import (
    parse_pml, parse_pml_file, ProgramModel, VariableTracker,
    SendAction, ReceiveAction, AssignAction, SkipAction,
    format_action, format_expression
)


# ============================================================
# 第一部分：中间表示 (IR) 数据结构
# ============================================================

@dataclass
class IRAction:
    """中间表示的动作"""
    action_type: str  # 'send', 'receive', 'skip'
    channel: Optional[str] = None
    message: Optional[str] = None
    is_variable: bool = False  # 标记 message 是否是变量（需要展开）
    
    @staticmethod
    def parse(action_str:  str, local_vars: Dict[str, str] = None) -> 'IRAction': 
        """从字符串解析动作"""
        action_str = action_str.strip()
        if action_str == 'skip' or action_str == 'ε' or not action_str: 
            return IRAction('skip')
        
        local_vars = local_vars or {}
        
        # 解析发送:  channel!  message
        if '!' in action_str:
            match = re.match(r'(\w+)\s*!\s*(\w+)', action_str)
            if match:
                channel = match.group(1)
                message = match.group(2)
                # 检查 message 是否是局部变量
                is_var = message in local_vars
                return IRAction('send', channel=channel, message=message, is_variable=is_var)
        
        # 解析接收:  channel? message
        if '?' in action_str:
            match = re.match(r'(\w+)\s*\?\s*(\w+)', action_str)
            if match: 
                channel = match.group(1)
                message = match.group(2)
                # 检查 message 是否是局部变量
                is_var = message in local_vars
                return IRAction('receive', channel=channel, message=message, is_variable=is_var)
        
        return IRAction('skip')


@dataclass
class IRTransition:
    """中间表示的转换"""
    source: str
    target: str
    guard: Optional[str]
    actions: List[IRAction]
    is_timeout: bool = False
    
    @classmethod
    def from_parsed(cls, source: str, target:  str, guard: Optional[str],
                    action_strs: List[str], local_vars: Dict[str, str] = None) -> 'IRTransition': 
        """从解析结果创建转换"""
        is_timeout = guard == 'timeout' if guard else False
        if is_timeout:
            guard = None
        actions = [IRAction. parse(a, local_vars) for a in action_strs]
        return cls(source, target, guard, actions, is_timeout)
    
    def get_recv(self) -> Optional[IRAction]: 
        """获取接收动作"""
        for a in self.actions:
            if a. action_type == 'receive':
                return a
        return None
    
    def get_send(self) -> Optional[IRAction]:
        """获取发送动作"""
        for a in self. actions:
            if a.action_type == 'send': 
                return a
        return None
    
    def uses_variable_message(self) -> bool:
        """检查转换是否使用变量消息（需要展开）"""
        for a in self.actions:
            if a. is_variable: 
                return True
        return False


@dataclass
class IRProcess:
    """中间表示的进程"""
    name: str
    states: List[str]
    initial_state: str
    transitions: List[IRTransition]
    local_vars: Dict[str, str] = field(default_factory=dict)
    state_entry_assignments: Dict[str, Dict[str, str]] = field(default_factory=dict)


@dataclass
class IRModel:
    """中间表示的完整模型"""
    mtype: List[str]
    channels: List[str]
    processes: List[IRProcess]


# ============================================================
# 第二部分：PML 解析结果到 IR 的转换
# ============================================================

class PMLToIRConverter:
    """将 PML 解析结果转换为中间表示"""
    
    def __init__(self, program:  ProgramModel):
        self.program = program
        self. tracker = VariableTracker(program)
    
    def convert(self) -> IRModel:
        """转换为 IR 模型"""
        mtype = self.program.mtype_values
        channels = list(self.program. channels. keys())
        
        processes = []
        for proc_name, proc in self.program. processes.items():
            ir_proc = self._convert_process(proc)
            processes.append(ir_proc)
        
        return IRModel(mtype=mtype, channels=channels, processes=processes)
    
    def _convert_process(self, proc) -> IRProcess: 
        """转换单个进程"""
        analysis = self. tracker.analyze_process(proc)
        
        # 获取局部变量信息
        local_vars = analysis['local_vars']
        
        # 转换转换列表
        transitions = []
        for trans in analysis['simplified_transitions']:
            ir_trans = IRTransition.from_parsed(
                source=trans. source,
                target=trans.target,
                guard=trans.guard,
                action_strs=trans.actions,
                local_vars=local_vars  # 传递局部变量信息
            )
            transitions.append(ir_trans)
        
        return IRProcess(
            name=analysis['name'],
            states=analysis['states'],
            initial_state=analysis['initial_state'],
            transitions=transitions,
            local_vars=local_vars,
            state_entry_assignments=analysis['state_entry_assignments']
        )


# ============================================================
# 第三部分：SMV 生成器
# ============================================================

class SMVGenerator: 
    """从 IR 生成 SMV 代码"""
    
    def __init__(self, model: IRModel):
        self.model = model
        self. lines:  List[str] = []
        self. indent = "  "
    
    def generate(self) -> str:
        """生成完整的 SMV 代码"""
        self.lines = []
        self._add_header()
        self._add_variables()
        self._add_init()
        self._add_transitions()
        self._add_fairness()
        self._add_properties()
        return "\n".join(self.lines)
    
    def _add_header(self):
        """添加 SMV 文件头"""
        self. lines.extend([
            "-- ============================================================",
            "-- SMV Model (Auto-generated from PML)",
            "-- ============================================================",
            "",
            "MODULE main",
            ""
        ])
    
    def _add_variables(self):
        """添加变量声明"""
        self.lines.append("VAR")
        
        # turn 变量
        procs = ", ".join(f"P_{p. name}" for p in self.model.processes)
        self.lines.append(f"{self.indent}turn :  {{{procs}}};")
        self.lines.append("")
        
        # 通道变量
        if self.model.mtype:
            msgs = ", ".join(["EMPTY"] + self.model.mtype)
            for ch in self.model. channels:
                self.lines.append(f"{self.indent}{ch} : {{{msgs}}};")
            self.lines. append("")
        
        # 进程状态变量
        for proc in self. model.processes:
            if len(proc.states) == 1:
                states = ", ".join(proc.states + ["_DUMMY"])
            else:
                states = ", ".join(proc. states)
            self.lines.append(f"{self.indent}{proc.name}_s : {{{states}}};")
            
            # 局部变量（排除 mtype 类型的变量，因为它们会被展开）
            for var_name, var_type in proc.local_vars.items():
                if var_type in ('bool', 'boolean'):
                    self.lines.append(f"{self.indent}{proc.name}_{var_name} : boolean;")
                # mtype 类型的局部变量不需要声明，因为会被展开
        
        self.lines.append("")
    
    def _add_init(self):
        """添加初始化"""
        self.lines.append("ASSIGN")
        
        procs = ", ".join(f"P_{p.name}" for p in self.model.processes)
        self.lines.append(f"{self. indent}init(turn) := {{{procs}}};")
        
        for ch in self.model. channels:
            self.lines.append(f"{self.indent}init({ch}) := EMPTY;")
        
        for proc in self.model.processes:
            self.lines.append(f"{self. indent}init({proc.name}_s) := {proc.initial_state};")
            
            for var_name, var_type in proc.local_vars. items():
                if var_type in ('bool', 'boolean'):
                    init_val = "FALSE"
                    if proc.initial_state in proc.state_entry_assignments: 
                        if var_name in proc. state_entry_assignments[proc.initial_state]:
                            val = proc.state_entry_assignments[proc.initial_state][var_name]
                            init_val = "TRUE" if val. lower() in ('true', '1') else "FALSE"
                    self. lines.append(f"{self.indent}init({proc.name}_{var_name}) := {init_val};")
        
        self.lines.append("")
    
    def _add_transitions(self):
        """添加状态转换"""
        procs = ", ".join(f"P_{p.name}" for p in self.model.processes)
        self.lines.append(f"{self. indent}next(turn) := {{{procs}}};")
        self.lines.append("")
        
        for proc in self.model. processes:
            self._add_process_state_transition(proc)
            self._add_process_var_transitions(proc)
        
        self._add_channel_transitions()
    
    def _expand_transition_for_mtype(self, proc:  IRProcess, t: IRTransition) -> List[Tuple[IRTransition, str]]:
        """
        如果转换使用了 mtype 变量，则展开为所有可能的消息类型
        返回 (展开后的转换, 具体消息) 的列表
        """
        if not t.uses_variable_message():
            return [(t, None)]
        
        # 找出使用变量的动作
        expanded = []
        for msg in self.model.mtype:
            # 创建新的动作列表，替换变量为具体消息
            new_actions = []
            for a in t.actions:
                if a. is_variable: 
                    new_action = IRAction(
                        action_type=a.action_type,
                        channel=a.channel,
                        message=msg,
                        is_variable=False
                    )
                    new_actions.append(new_action)
                else: 
                    new_actions.append(a)
            
            new_trans = IRTransition(
                source=t.source,
                target=t.target,
                guard=t.guard,
                actions=new_actions,
                is_timeout=t. is_timeout
            )
            expanded. append((new_trans, msg))
        
        return expanded
    
    def _parse_condition(self, cond:  str) -> Set[str]:
        """将条件字符串解析为原子条件集合"""
        if not cond: 
            return set()
        return set(part.strip() for part in cond.split('&'))
    
    def _condition_implies(self, cond1: str, cond2: str) -> bool:
        """检查 cond1 是否蕴含 cond2"""
        parts1 = self._parse_condition(cond1)
        parts2 = self._parse_condition(cond2)
        return parts2.issubset(parts1)
    
    def _add_process_state_transition(self, proc: IRProcess):
        """添加进程状态转换"""
        self. lines.append(f"{self.indent}-- {proc.name} state")
        self.lines.append(f"{self.indent}next({proc.name}_s) := case")
        self.lines.append(f"{self.indent}{self.indent}turn != P_{proc.name} :  {proc.name}_s;")
        
        by_source:  Dict[str, List[IRTransition]] = defaultdict(list)
        for t in proc.transitions:
            # 展开使用变量的转换
            expanded = self._expand_transition_for_mtype(proc, t)
            for exp_t, _ in expanded:
                by_source[exp_t.source]. append(exp_t)
        
        for state in proc.states:
            if state not in by_source: 
                continue
            
            trans_list = by_source[state]
            
            cond_target_pairs:  List[Tuple[str, str]] = []
            for t in trans_list: 
                cond = self._build_guard_condition(proc, t)
                cond_target_pairs.append((cond, t.target))
            
            cond_to_targets:  Dict[str, Set[str]] = defaultdict(set)
            for cond, target in cond_target_pairs: 
                cond_to_targets[cond].add(target)
            
            all_conds = list(cond_to_targets.keys())
            
            merged_cond_to_targets:  Dict[str, Set[str]] = {}
            for cond in all_conds:
                targets = set(cond_to_targets[cond])
                for other_cond in all_conds: 
                    if other_cond != cond and self._condition_implies(cond, other_cond):
                        targets.update(cond_to_targets[other_cond])
                merged_cond_to_targets[cond] = targets
            
            sorted_conds = sorted(merged_cond_to_targets.keys(),
                                  key=lambda x: (-len(self._parse_condition(x)), x))
            
            for cond in sorted_conds:
                targets = merged_cond_to_targets[cond]
                targets_str = self._format_targets(targets)
                
                if cond: 
                    self. lines.append(
                        f"{self.indent}{self.indent}{proc.name}_s = {state} & {cond} :  {targets_str};"
                    )
                else: 
                    self.lines.append(
                        f"{self. indent}{self.indent}{proc.name}_s = {state} : {targets_str};"
                    )
        
        self.lines.append(f"{self.indent}{self.indent}TRUE :  {proc.name}_s;")
        self.lines.append(f"{self. indent}esac;")
        self.lines.append("")
    
    def _build_guard_condition(self, proc: IRProcess, t: IRTransition) -> str:
        """构建守卫条件"""
        parts = []
        
        recv = t.get_recv()
        if recv and not recv.is_variable:
            parts. append(f"{recv.channel} = {recv. message}")
        elif recv and recv.is_variable:
            # 变量接收 - 应该已经被展开了
            parts.append(f"{recv.channel} = {recv.message}")
        
        send = t.get_send()
        if send: 
            parts.append(f"{send. channel} = EMPTY")
        
        if t.guard:
            guard = self._convert_guard_expr(proc, t.guard)
            parts.append(guard)
        
        return " & ".join(parts)
    
    def _convert_guard_expr(self, proc: IRProcess, guard: str) -> str:
        """转换守卫表达式为 SMV 格式"""
        g = guard.strip("()")
        g = g.replace("==", "=")
        g = g. replace("&&", "&")
        g = g.replace("||", "|")
        g = re.sub(r'\btrue\b', 'TRUE', g, flags=re. IGNORECASE)
        g = re. sub(r'\bfalse\b', 'FALSE', g, flags=re. IGNORECASE)
        
        for var_name in proc.local_vars:
            if proc.local_vars[var_name] in ('bool', 'boolean'):
                g = re.sub(rf'\b{var_name}\b', f'{proc.name}_{var_name}', g)
        
        return g
    
    def _format_targets(self, targets: Set[str]) -> str:
        """格式化目标状态集合"""
        if len(targets) == 1:
            return list(targets)[0]
        else:
            return "{" + ", ".join(sorted(targets)) + "}"
    
    def _add_process_var_transitions(self, proc: IRProcess):
        """添加进程局部变量的转换"""
        for var_name, var_type in proc. local_vars.items():
            # 跳过 mtype 类型变量
            if var_type == 'mtype':
                continue
                
            if var_type not in ('bool', 'boolean'):
                continue
                
            full_name = f"{proc. name}_{var_name}"
            
            assignments:  List[Tuple[str, str, str, str]] = []
            
            for t in proc.transitions:
                # 展开转换
                expanded = self._expand_transition_for_mtype(proc, t)
                for exp_t, _ in expanded:
                    if exp_t.target in proc.state_entry_assignments: 
                        if var_name in proc.state_entry_assignments[exp_t.target]:
                            val = proc.state_entry_assignments[exp_t.target][var_name]
                            cond = self._build_guard_condition(proc, exp_t)
                            smv_val = self._convert_value(val, var_type)
                            assignments.append((exp_t.source, exp_t.target, cond, smv_val))
            
            if not assignments:
                self.lines.append(f"{self.indent}next({full_name}) := {full_name};")
                self.lines.append("")
                continue
            
            self.lines.append(f"{self.indent}-- {full_name}")
            self.lines.append(f"{self.indent}next({full_name}) := case")
            self.lines.append(f"{self. indent}{self.indent}turn != P_{proc.name} : {full_name};")
            
            by_source: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
            for source, target, cond, val in assignments:
                by_source[source].append((cond, val))
            
            for source in sorted(by_source. keys()):
                cond_val_pairs = by_source[source]
                
                cond_to_values: Dict[str, Set[str]] = defaultdict(set)
                for cond, val in cond_val_pairs: 
                    cond_to_values[cond].add(val)
                
                all_conds = list(cond_to_values.keys())
                
                merged_cond_to_values: Dict[str, Set[str]] = {}
                for cond in all_conds: 
                    values = set(cond_to_values[cond])
                    for other_cond in all_conds: 
                        if other_cond != cond and self._condition_implies(cond, other_cond):
                            values.update(cond_to_values[other_cond])
                    merged_cond_to_values[cond] = values
                
                sorted_conds = sorted(merged_cond_to_values.keys(),
                                      key=lambda x: (-len(self._parse_condition(x)), x))
                
                for cond in sorted_conds: 
                    values = merged_cond_to_values[cond]
                    val_str = self._format_targets(values)
                    if cond:
                        self.lines. append(
                            f"{self.indent}{self.indent}{proc.name}_s = {source} & {cond} : {val_str};"
                        )
                    else:
                        self.lines.append(
                            f"{self.indent}{self.indent}{proc. name}_s = {source} : {val_str};"
                        )
            
            self.lines.append(f"{self.indent}{self.indent}TRUE : {full_name};")
            self.lines.append(f"{self.indent}esac;")
            self.lines.append("")
    
    def _convert_value(self, val: str, var_type:  str) -> str:
        """转换值为 SMV 格式"""
        val = val.strip()
        if var_type in ('bool', 'boolean'):
            if val. lower() in ('true', '1'):
                return 'TRUE'
            elif val.lower() in ('false', '0'):
                return 'FALSE'
        return val
    
    def _add_channel_transitions(self):
        """添加通道转换"""
        for ch in self.model. channels:
            self._add_single_channel_transition(ch)
    
    def _add_single_channel_transition(self, ch: str):
        """添加单个通道的转换"""
        self.lines.append(f"{self. indent}-- {ch}")
        self.lines.append(f"{self.indent}next({ch}) := case")
        
        send_data:  Dict[str, Tuple[Set[str], bool]] = {}
        recv_conditions: List[str] = []
        
        for proc in self.model. processes:
            by_source: Dict[str, List[IRTransition]] = defaultdict(list)
            for t in proc.transitions:
                by_source[t. source].append(t)
            
            for state, trans_list in by_source.items():
                # 展开所有使用变量的转换
                expanded_trans_list = []
                for t in trans_list:
                    expanded = self._expand_transition_for_mtype(proc, t)
                    for exp_t, _ in expanded:
                        expanded_trans_list. append(exp_t)
                
                state_send_conds: Dict[str, Set[str]] = defaultdict(set)
                state_has_no_send:  Dict[str, bool] = defaultdict(lambda: False)
                
                for t in expanded_trans_list:
                    send = t.get_send()
                    recv = t.get_recv()
                    
                    if send and send.channel == ch:
                        cond_parts = [
                            f"turn = P_{proc.name}",
                            f"{proc.name}_s = {state}",
                            f"{ch} = EMPTY"
                        ]
                        if recv:
                            cond_parts. append(f"{recv.channel} = {recv.message}")
                        if t.guard:
                            cond_parts.append(self._convert_guard_expr(proc, t.guard))
                        
                        cond = " & ".join(cond_parts)
                        state_send_conds[cond]. add(send.message)
                    
                    if recv and recv.channel == ch:
                        cond_parts = [
                            f"turn = P_{proc.name}",
                            f"{proc.name}_s = {state}",
                            f"{ch} = {recv.message}"
                        ]
                        if send:
                            cond_parts.append(f"{send. channel} = EMPTY")
                        if t.guard:
                            cond_parts.append(self._convert_guard_expr(proc, t.guard))
                        
                        cond = " & ".join(cond_parts)
                        recv_conditions.append(cond)
                
                for cond in state_send_conds:
                    has_no_send = False
                    for t in expanded_trans_list: 
                        send = t.get_send()
                        if send is None or send.channel != ch:
                            t_full_cond_parts = [
                                f"turn = P_{proc.name}",
                                f"{proc.name}_s = {state}"
                            ]
                            t_cond = self._build_guard_condition(proc, t)
                            if t_cond: 
                                t_full_cond_parts.append(t_cond)
                            
                            send_cond_parts = self._parse_condition(cond)
                            no_send_cond_parts = set(t_full_cond_parts)
                            
                            if no_send_cond_parts. issubset(send_cond_parts):
                                has_no_send = True
                                break
                    
                    state_has_no_send[cond] = has_no_send
                
                for cond, msgs in state_send_conds.items():
                    if cond not in send_data:
                        send_data[cond] = (set(), False)
                    existing_msgs, existing_no_send = send_data[cond]
                    existing_msgs.update(msgs)
                    send_data[cond] = (existing_msgs, existing_no_send or state_has_no_send[cond])
        
        all_send_conds = list(send_data. keys())
        merged_send:  Dict[str, Tuple[Set[str], bool]] = {}
        
        for cond in all_send_conds: 
            msgs, has_no_send = send_data[cond]
            msgs = set(msgs)
            for other_cond in all_send_conds:
                if other_cond != cond and self._condition_implies(cond, other_cond):
                    other_msgs, other_no_send = send_data[other_cond]
                    msgs.update(other_msgs)
                    has_no_send = has_no_send or other_no_send
            merged_send[cond] = (msgs, has_no_send)
        
        sorted_send_conds = sorted(merged_send. keys(),
                                   key=lambda x: (-len(self._parse_condition(x)), x))
        
        for cond in sorted_send_conds: 
            msgs, has_no_send = merged_send[cond]
            if has_no_send:
                msgs = msgs | {"EMPTY"}
            msg_str = self._format_targets(msgs)
            self.lines.append(f"{self.indent}{self.indent}{cond} :  {msg_str};")
        
        for cond in recv_conditions:
            self.lines.append(f"{self.indent}{self.indent}{cond} :  EMPTY;")
        
        self. lines.append(f"{self.indent}{self.indent}TRUE : {ch};")
        self.lines.append(f"{self.indent}esac;")
        self.lines.append("")
    
    def _add_fairness(self):
        """添加公平性约束"""
        self.lines.append("-- Fairness constraints")
        for proc in self.model.processes:
            self. lines.append(f"FAIRNESS turn = P_{proc.name}")
        self.lines.append("")
    
    def _add_properties(self):
        """添加 CTL 属性"""
        self.lines.append("-- CTL Properties")
        
        dccp_procs = [p for p in self.model.processes if 'DCCP' in p.name. upper()]
        if len(dccp_procs) >= 2:
            p1, p2 = dccp_procs[0]. name, dccp_procs[1]. name
            if 'OPEN' in dccp_procs[0].states: 
                self.lines.append(f"SPEC EF ({p1}_s = OPEN & {p2}_s = OPEN)")
        
        for proc in dccp_procs: 
            if 'OPEN' in proc.states:
                self.lines.append(f"SPEC EF ({proc.name}_s = OPEN)")
        
        for proc in self.model.processes:
            if 'I_am_active' in proc.local_vars and 'CLOSEREQ' in proc. states:
                self. lines.append(
                    f"SPEC AG ({proc.name}_s = CLOSEREQ -> {proc.name}_I_am_active = TRUE)"
                )
        
        self.lines.append("")


# ============================================================
# 第四部分：主转换函数
# ============================================================

def pml_to_smv(pml_code: str, debug: bool = False) -> str:
    """将 PML 代码转换为 SMV 代码"""
    if debug:
        print("=" * 70)
        print("Step 1: Parsing PML...")
        print("=" * 70)
    
    program = parse_pml(pml_code, silent=not debug, debug=debug)
    
    if debug:
        print(f"  Found {len(program. mtype_values)} mtype values")
        print(f"  Found {len(program. channels)} channels")
        print(f"  Found {len(program.processes)} processes")
    
    if debug:
        print("\n" + "=" * 70)
        print("Step 2: Converting to IR...")
        print("=" * 70)
    
    converter = PMLToIRConverter(program)
    ir_model = converter.convert()
    
    if debug:
        print(f"  IR Model:")
        print(f"    MType:  {ir_model. mtype}")
        print(f"    Channels: {ir_model.channels}")
        for proc in ir_model.processes:
            print(f"    Process {proc.name}:")
            print(f"      States: {proc.states}")
            print(f"      Transitions: {len(proc.transitions)}")
            # 检查是否有需要展开的转换
            var_trans = [t for t in proc.transitions if t.uses_variable_message()]
            if var_trans:
                print(f"      Transitions with variable messages:  {len(var_trans)} (will be expanded to {len(var_trans) * len(ir_model.mtype)})")
    
    if debug: 
        print("\n" + "=" * 70)
        print("Step 3: Generating SMV...")
        print("=" * 70)
    
    generator = SMVGenerator(ir_model)
    smv_code = generator.generate()
    
    if debug:
        print(f"  Generated {len(smv_code. splitlines())} lines of SMV code")
    
    return smv_code


def pml_file_to_smv(input_path: str, output_path: Optional[str] = None,
                    debug:  bool = False) -> str:
    """将 PML 文件转换为 SMV 文件"""
    with open(input_path, 'r', encoding='utf-8') as f:
        pml_code = f.read()
    
    smv_code = pml_to_smv(pml_code, debug=debug)
    
    if output_path: 
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(smv_code)
        if debug:
            print(f"\nSMV code written to: {output_path}")
    
    return smv_code


# ============================================================
# 第五部分：打印中间结果函数
# ============================================================

def print_ir_model(ir_model: IRModel):
    """打印 IR 模型"""
    print("=" * 70)
    print("Intermediate Representation (IR)")
    print("=" * 70)
    
    print(f"\nMType: {ir_model.mtype}")
    print(f"\nChannels: {ir_model.channels}")
    
    print(f"\nProcesses ({len(ir_model.processes)}):")
    for proc in ir_model.processes:
        print(f"\n  Process:  {proc.name}")
        print(f"    States: {proc.states}")
        print(f"    Initial State: {proc.initial_state}")
        
        if proc.local_vars:
            print(f"    Local Variables:  {proc.local_vars}")
        
        if proc.state_entry_assignments: 
            print(f"    State Entry Assignments:")
            for state, assigns in proc.state_entry_assignments.items():
                assign_str = ", ". join(f"{k}={v}" for k, v in assigns. items())
                print(f"      {state}:  {{{assign_str}}}")
        
        print(f"    Transitions ({len(proc.transitions)}):")
        for t in proc.transitions:
            guard_str = f" [{t.guard}]" if t.guard else ""
            if t.is_timeout:
                guard_str = " [timeout]"
            
            actions_str = []
            for a in t.actions:
                var_marker = " (var)" if a.is_variable else ""
                if a.action_type == 'send':
                    actions_str.append(f"{a.channel}!  {a.message}{var_marker}")
                elif a.action_type == 'receive':
                    actions_str.append(f"{a. channel}?  {a.message}{var_marker}")
                else:
                    actions_str.append("skip")
            
            actions = "; ".join(actions_str) if actions_str else "ε"
            print(f"      {t.source} -> {t.target}{guard_str}:  [{actions}]")


# ============================================================
# 第六部分：命令行接口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description='Convert Promela (PML) to NuSMV (SMV)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples: 
  python pml2smv.py input.pml                    # 输出到 stdout
  python pml2smv.py input.pml -o output.smv      # 输出到文件
  python pml2smv.py input.pml --debug            # 显示调试信息
  python pml2smv.py input.pml --ir               # 显示中间表示
        """
    )
    
    parser. add_argument('input', nargs='?', help='Input PML file')
    parser.add_argument('-o', '--output', help='Output SMV file')
    parser.add_argument('--debug', action='store_true', help='Show debug information')
    parser.add_argument('--ir', action='store_true', help='Print intermediate representation')
    parser.add_argument('--test', action='store_true', help='Run built-in test')
    
    args = parser.parse_args()
    
    if args. test:
        run_test()
        return
    
    if not args.input:
        parser.print_help()
        return
    
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            pml_code = f.read()
        
        program = parse_pml(pml_code, silent=not args.debug, debug=args.debug)
        
        converter = PMLToIRConverter(program)
        ir_model = converter.convert()
        
        if args.ir:
            print_ir_model(ir_model)
            print()
        
        generator = SMVGenerator(ir_model)
        smv_code = generator.generate()
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f. write(smv_code)
            print(f"SMV code written to: {args.output}", file=sys.stderr)
        else:
            print(smv_code)
    
    except FileNotFoundError:
        print(f"Error: File not found: {args. input}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def run_test():
    """运行内置测试"""
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
    :: goto LISTEN; /* passive open */
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
    
    print("=" * 70)
    print("PML to SMV Converter - Test")
    print("=" * 70)
    
    try:
        print("\nStep 1: Parsing PML...")
        program = parse_pml(test_pml, silent=True)
        print(f"  Parsed successfully!")
        print(f"  - {len(program.mtype_values)} mtype values")
        print(f"  - {len(program.channels)} channels")
        print(f"  - {len(program.processes)} processes:")
        for name in program.processes. keys():
            print(f"      * {name}")
        
        print("\nStep 2: Converting to IR...")
        converter = PMLToIRConverter(program)
        ir_model = converter.convert()
        print(f"  Converted successfully!")
        
        print("\n" + "-" * 70)
        print_ir_model(ir_model)
        
        print("\n" + "-" * 70)
        print("\nStep 3: Generating SMV...")
        generator = SMVGenerator(ir_model)
        smv_code = generator.generate()
        print(f"  Generated {len(smv_code.splitlines())} lines of SMV code")
        
        print("\n" + "=" * 70)
        print("Generated SMV Code:")
        print("=" * 70)
        print(smv_code)
        
        output_file = "dccp_auto. smv"
        with open(output_file, 'w') as f:
            f.write(smv_code)
        print(f"\n-- Output written to {output_file}", file=sys.stderr)
        
    except Exception as e: 
        print(f"\nError: {e}")
        import traceback
        traceback. print_exc()


if __name__ == "__main__": 
    main()