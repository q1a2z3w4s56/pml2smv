#!/usr/bin/env python3
"""
PML to SMV Converter - 修复版 v3
正确处理 do 循环中的非确定性选择语义
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple
from collections import defaultdict
import re
import argparse
import sys

from pml_visitor_v3 import (
    parse_pml, parse_pml_file, ProgramModel, VariableTracker,
    SendAction, ReceiveAction, AssignAction, SkipAction,
    format_action, format_expression
)


# ============================================================
# IR 数据结构
# ============================================================

@dataclass
class IRAction:
    action_type: str
    channel: Optional[str] = None
    message: Optional[str] = None
    is_variable: bool = False
    
    @staticmethod
    def parse(action_str: str, local_vars: Dict[str, str] = None) -> 'IRAction': 
        action_str = action_str.strip()
        if action_str == 'skip' or action_str == 'ε' or not action_str: 
            return IRAction('skip')
        
        local_vars = local_vars or {}
        
        if '!' in action_str: 
            match = re.match(r'(\w+)\s*!\s*(\w+)', action_str)
            if match:
                return IRAction('send', channel=match. group(1), message=match.group(2),
                               is_variable=match.group(2) in local_vars)
        
        if '?' in action_str: 
            match = re.match(r'(\w+)\s*\?\s*(\w+)', action_str)
            if match: 
                return IRAction('receive', channel=match.group(1), message=match.group(2),
                               is_variable=match.group(2) in local_vars)
        
        return IRAction('skip')


@dataclass
class IRTransition:
    source: str
    target: str
    guard: Optional[str]
    actions: List[IRAction]
    is_timeout: bool = False
    
    @classmethod
    def from_parsed(cls, source:  str, target: str, guard: Optional[str],
                    action_strs: List[str], local_vars: Dict[str, str] = None) -> 'IRTransition': 
        is_timeout = guard == 'timeout' if guard else False
        if is_timeout:
            guard = None
        actions = [IRAction. parse(a, local_vars) for a in action_strs]
        return cls(source, target, guard, actions, is_timeout)
    
    def get_recv(self) -> Optional[IRAction]:
        for a in self.actions:
            if a. action_type == 'receive':
                return a
        return None
    
    def get_send(self) -> Optional[IRAction]:
        for a in self. actions:
            if a.action_type == 'send': 
                return a
        return None
    
    def uses_variable_message(self) -> bool:
        return any(a.is_variable for a in self.actions)
    
    def has_channel_action(self) -> bool:
        return any(a.action_type in ('send', 'receive') for a in self.actions)
    
    def is_unconditional(self) -> bool:
        """检查是否是无条件转换（无通道操作且无守卫）"""
        return not self. has_channel_action() and not self.guard and not self.is_timeout


@dataclass
class IRProcess:
    name: str
    states: List[str]
    initial_state: str
    transitions: List[IRTransition]
    local_vars: Dict[str, str] = field(default_factory=dict)
    state_entry_assignments: Dict[str, Dict[str, str]] = field(default_factory=dict)


@dataclass
class IRModel:
    mtype: List[str]
    channels: List[str]
    processes: List[IRProcess]


# ============================================================
# PML 到 IR 转换
# ============================================================

class PMLToIRConverter: 
    def __init__(self, program: ProgramModel):
        self.program = program
        self.tracker = VariableTracker(program)
    
    def convert(self) -> IRModel:
        mtype = self.program.mtype_values
        channels = list(self.program. channels. keys())
        
        processes = []
        for proc_name, proc in self.program.processes.items():
            ir_proc = self._convert_process(proc)
            processes.append(ir_proc)
        
        return IRModel(mtype=mtype, channels=channels, processes=processes)
    
    def _convert_process(self, proc) -> IRProcess: 
        analysis = self. tracker.analyze_process(proc)
        local_vars = analysis['local_vars']
        
        transitions = []
        for trans in analysis['simplified_transitions']:
            ir_trans = IRTransition.from_parsed(
                source=trans. source,
                target=trans.target,
                guard=trans.guard,
                action_strs=trans.actions,
                local_vars=local_vars
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
# 条件分析器
# ============================================================

@dataclass
class TransitionCondition:
    """转换的使能条件分析结果"""
    recv_channel: Optional[str] = None
    recv_message: Optional[str] = None
    send_channel:  Optional[str] = None
    guard_expr: Optional[str] = None
    is_timeout: bool = False
    is_unconditional:  bool = False
    
    def get_smv_condition(self, proc_name: str, proc_local_vars: Dict[str, str]) -> str:
        """生成 SMV 条件表达式"""
        parts = []
        
        if self.recv_channel and self.recv_message:
            parts. append(f"{self.recv_channel} = {self.recv_message}")
        
        if self.send_channel: 
            parts.append(f"{self. send_channel} = EMPTY")
        
        if self.guard_expr:
            g = self.guard_expr. strip("()")
            g = g.replace("==", "=")
            g = g.replace("&&", "&")
            g = g.replace("||", "|")
            g = re.sub(r'\btrue\b', 'TRUE', g, flags=re. IGNORECASE)
            g = re. sub(r'\bfalse\b', 'FALSE', g, flags=re. IGNORECASE)
            for var_name in proc_local_vars:
                if proc_local_vars[var_name] in ('bool', 'boolean'):
                    g = re.sub(rf'\b{var_name}\b', f'{proc_name}_{var_name}', g)
            parts.append(g)
        
        return " & ".join(parts)
    
    def can_coexist_with(self, other:  'TransitionCondition') -> bool:
        """检查两个条件是否可以同时满足"""
        # timeout 和无条件转换是独立的 fallback，不参与条件合并
        if self.is_timeout or other.is_timeout:
            return False
        if self.is_unconditional or other.is_unconditional:
            return False
        
        # 如果都有接收操作，必须是相同的通道和消息才能共存
        if self.recv_channel and other.recv_channel:
            if self.recv_channel != other.recv_channel or self.recv_message != other.recv_message:
                return False
        
        # 如果一个有接收，另一个没有，它们不兼容
        # （有接收的转换只在特定消息时使能，无接收的转换在其他时候使能）
        if (self.recv_channel is None) != (other.recv_channel is None):
            return False
        
        # 守卫条件不同则不兼容
        if self.guard_expr != other.guard_expr:
            return False
        
        return True
        
    def is_more_specific_than(self, other: 'TransitionCondition') -> bool:
        """检查 self 是否比 other 更具体"""
        self_parts = 0
        other_parts = 0
        
        if self.recv_channel: 
            self_parts += 1
        if self.send_channel:
            self_parts += 1
        if self.guard_expr:
            self_parts += 1
            
        if other. recv_channel: 
            other_parts += 1
        if other.send_channel:
            other_parts += 1
        if other.guard_expr:
            other_parts += 1
        
        return self_parts > other_parts


def analyze_transition(t: IRTransition) -> TransitionCondition: 
    """分析转换的使能条件"""
    cond = TransitionCondition()
    cond.is_timeout = t.is_timeout
    cond.is_unconditional = t. is_unconditional()
    
    recv = t.get_recv()
    if recv:
        cond.recv_channel = recv.channel
        cond.recv_message = recv.message
    
    send = t.get_send()
    if send:
        cond.send_channel = send.channel
    
    if t.guard: 
        cond. guard_expr = t.guard
    
    return cond


# ============================================================
# SMV 生成器 - 修复版
# ============================================================

class SMVGenerator:
    def __init__(self, model: IRModel):
        self.model = model
        self.lines:  List[str] = []
        self. indent = "  "
    
    def generate(self) -> str:
        self.lines = []
        self._add_header()
        self._add_variables()
        self._add_init()
        self._add_transitions()
        self._add_fairness()
        self._add_properties()
        return "\n".join(self.lines)
    
    def _add_header(self):
        self.lines.extend([
            "-- ============================================================",
            "-- SMV Model (Auto-generated from PML)",
            "-- ============================================================",
            "",
            "MODULE main",
            ""
        ])
    
    def _add_variables(self):
        self.lines. append("VAR")
        
        procs = ", ".join(f"P_{p. name}" for p in self.model.processes)
        self.lines.append(f"{self.indent}turn :  {{{procs}}};")
        self.lines.append("")
        
        if self.model.mtype:
            msgs = ", ".join(["EMPTY"] + self.model.mtype)
            for ch in self.model. channels:
                self.lines.append(f"{self.indent}{ch} : {{{msgs}}};")
            self.lines. append("")
        
        for proc in self.model. processes: 
            if len(proc.states) == 1:
                states = ", ".join(proc.states + ["_DUMMY"])
            else:
                states = ", ".join(proc. states)
            self.lines.append(f"{self.indent}{proc.name}_s : {{{states}}};")
            
            for var_name, var_type in proc.local_vars.items():
                if var_type in ('bool', 'boolean'):
                    self.lines.append(f"{self. indent}{proc.name}_{var_name} : boolean;")
        
        self.lines.append("")
    
    def _add_init(self):
        self.lines.append("ASSIGN")
        
        procs = ", ".join(f"P_{p.name}" for p in self.model.processes)
        self.lines.append(f"{self. indent}init(turn) := {{{procs}}};")
        
        for ch in self.model. channels:
            self.lines.append(f"{self.indent}init({ch}) := EMPTY;")
        
        for proc in self.model.processes:
            self.lines.append(f"{self.indent}init({proc. name}_s) := {proc.initial_state};")
            
            for var_name, var_type in proc.local_vars.items():
                if var_type in ('bool', 'boolean'):
                    init_val = "FALSE"
                    if proc.initial_state in proc.state_entry_assignments: 
                        if var_name in proc. state_entry_assignments[proc.initial_state]:
                            val = proc.state_entry_assignments[proc.initial_state][var_name]
                            init_val = "TRUE" if val. lower() in ('true', '1') else "FALSE"
                    self. lines.append(f"{self.indent}init({proc.name}_{var_name}) := {init_val};")
        
        self.lines.append("")
    
    def _add_transitions(self):
        procs = ", ".join(f"P_{p.name}" for p in self.model.processes)
        self.lines.append(f"{self.indent}next(turn) := {{{procs}}};")
        self.lines.append("")
        
        for proc in self.model.processes:
            self._add_process_state_transition(proc)
            self._add_process_var_transitions(proc)
        
        self._add_channel_transitions()
    
    def _expand_transition_for_mtype(self, t: IRTransition) -> List[Tuple[IRTransition, str]]:
        if not t.uses_variable_message():
            return [(t, None)]
        
        expanded = []
        for msg in self.model.mtype:
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
    
    def _format_targets(self, targets:  Set[str]) -> str:
        if len(targets) == 1:
            return list(targets)[0]
        else:
            return "{" + ", ".join(sorted(targets)) + "}"
    
    def _add_process_state_transition(self, proc: IRProcess):
        """添加进程状态转换 - 正确处理非确定性"""
        self.lines.append(f"{self.indent}-- {proc.name} state")
        self.lines.append(f"{self.indent}next({proc.name}_s) := case")
        self.lines.append(f"{self.indent}{self.indent}turn != P_{proc.name} :  {proc.name}_s;")
        
        # 按源状态分组
        by_source:  Dict[str, List[IRTransition]] = defaultdict(list)
        for t in proc.transitions:
            expanded = self._expand_transition_for_mtype(t)
            for exp_t, _ in expanded:
                by_source[exp_t.source]. append(exp_t)
        
        for state in proc.states:
            if state not in by_source: 
                continue
            
            trans_list = by_source[state]
            
            # 分析每个转换的条件
            trans_with_cond:  List[Tuple[IRTransition, TransitionCondition]] = []
            for t in trans_list:
                cond = analyze_transition(t)
                trans_with_cond.append((t, cond))
            
            # 分类转换
            timeout_trans = [(t, c) for t, c in trans_with_cond if c. is_timeout]
            unconditional_trans = [(t, c) for t, c in trans_with_cond if c.is_unconditional]
            conditional_trans = [(t, c) for t, c in trans_with_cond 
                                if not c.is_timeout and not c.is_unconditional]
            
            # 生成所有可能的条件组合
            generated_cases = self._generate_state_cases(
                proc, state, conditional_trans, unconditional_trans, timeout_trans
            )
            
            for smv_cond, targets in generated_cases: 
                targets_str = self._format_targets(targets)
                if smv_cond: 
                    self. lines.append(
                        f"{self.indent}{self.indent}{proc.name}_s = {state} & {smv_cond} :  {targets_str};"
                    )
                else: 
                    self.lines.append(
                        f"{self. indent}{self.indent}{proc. name}_s = {state} : {targets_str};"
                    )
        
        self.lines.append(f"{self.indent}{self.indent}TRUE :  {proc.name}_s;")
        self.lines.append(f"{self.indent}esac;")
        self.lines.append("")
    
    def _generate_state_cases(
        self, 
        proc: IRProcess, 
        state: str,
        conditional_trans: List[Tuple[IRTransition, TransitionCondition]],
        unconditional_trans: List[Tuple[IRTransition, TransitionCondition]],
        timeout_trans:  List[Tuple[IRTransition, TransitionCondition]]
    ) -> List[Tuple[str, Set[str]]]: 
        """生成状态的所有 case 分支"""
        cases:  List[Tuple[str, Set[str]]] = []
        
        # 收集所有唯一的条件
        unique_conds:  Dict[str, Tuple[TransitionCondition, Set[str]]] = {}
        
        for t, cond in conditional_trans: 
            smv_cond = cond.get_smv_condition(proc.name, proc. local_vars)
            if smv_cond not in unique_conds:
                unique_conds[smv_cond] = (cond, set())
            unique_conds[smv_cond][1].add(t. target)
        
        # 找出所有可以同时满足的条件组合
        cond_list = list(unique_conds.keys())
        cond_objs = {k: v[0] for k, v in unique_conds.items()}
        
        # 生成组合条件
        # 对于每个条件，检查哪些其他条件可以与之共存
        processed_combinations:  Set[frozenset] = set()
        
        for i, cond1_str in enumerate(cond_list):
            cond1_obj = cond_objs[cond1_str]
            compatible_conds = [cond1_str]
            
            for j, cond2_str in enumerate(cond_list):
                if i != j:
                    cond2_obj = cond_objs[cond2_str]
                    if cond1_obj.can_coexist_with(cond2_obj):
                        compatible_conds.append(cond2_str)
            
            # 生成这个条件组合的目标
            combo_key = frozenset(compatible_conds)
            if combo_key in processed_combinations: 
                continue
            processed_combinations.add(combo_key)
            
            # 计算交集条件（最具体的条件）
            # 对于可以同时满足的条件，使用最具体的那个作为 case 条件
            combined_targets = set()
            for c_str in compatible_conds:
                combined_targets.update(unique_conds[c_str][1])
        
        # 重新生成：按条件的具体程度排序
        # 更具体的条件放前面，包含更多可能的目标
        sorted_conds = sorted(cond_list, key=lambda x: (
            -len([p for p in x.split('&') if p.strip()]),  # 条件数量降序
            x  # 字典序
        ))
        
        # 对于每个条件，计算其可达目标（包括兼容条件的目标）
        for cond_str in sorted_conds:
            cond_obj = cond_objs[cond_str]
            targets = set(unique_conds[cond_str][1])
            
            # 添加所有兼容条件的目标
            for other_cond_str in cond_list: 
                if other_cond_str != cond_str: 
                    other_cond_obj = cond_objs[other_cond_str]
                    if cond_obj. can_coexist_with(other_cond_obj):
                        targets. update(unique_conds[other_cond_str][1])
            
            # 如果有无条件转换，也要加入
            for t, _ in unconditional_trans:
                targets.add(t.target)
            
            cases.append((cond_str, targets))
        
        # 添加无条件和 timeout 的 fallback
        fallback_targets = set()
        for t, _ in unconditional_trans: 
            fallback_targets.add(t.target)
        for t, _ in timeout_trans:
            fallback_targets. add(t.target)
        
        if fallback_targets: 
            cases.append(("", fallback_targets))
        
        return cases
    
    def _add_process_var_transitions(self, proc: IRProcess):
        """添加进程局部变量的转换"""
        for var_name, var_type in proc. local_vars.items():
            if var_type == 'mtype':
                continue
            
            if var_type not in ('bool', 'boolean'):
                continue
            
            full_name = f"{proc.name}_{var_name}"
            
            # 收集赋值信息
            assignments:  List[Tuple[str, str, str, str, bool, bool]] = []
            
            for t in proc.transitions:
                expanded = self._expand_transition_for_mtype(t)
                for exp_t, _ in expanded: 
                    if exp_t.target in proc.state_entry_assignments: 
                        if var_name in proc.state_entry_assignments[exp_t.target]: 
                            val = proc.state_entry_assignments[exp_t.target][var_name]
                            cond = analyze_transition(exp_t)
                            smv_cond = cond.get_smv_condition(proc.name, proc.local_vars)
                            smv_val = self._convert_value(val, var_type)
                            assignments.append((
                                exp_t.source, exp_t.target, smv_cond, smv_val,
                                cond.is_timeout, cond.is_unconditional
                            ))
            
            if not assignments:
                self.lines.append(f"{self.indent}next({full_name}) := {full_name};")
                self.lines.append("")
                continue
            
            self.lines.append(f"{self.indent}-- {full_name}")
            self.lines.append(f"{self.indent}next({full_name}) := case")
            self.lines.append(f"{self.indent}{self.indent}turn != P_{proc.name} : {full_name};")
            
            # 按源状态分组
            by_source: Dict[str, List[Tuple[str, str, bool, bool]]] = defaultdict(list)
            for source, target, cond, val, is_timeout, is_uncond in assignments: 
                by_source[source].append((cond, val, is_timeout, is_uncond))
            
            for source in sorted(by_source. keys()):
                items = by_source[source]
                
                # 分类
                channel_items = [(c, v) for c, v, t, u in items if not t and not u and c]
                uncond_items = [(c, v) for c, v, t, u in items if u]
                timeout_items = [(c, v) for c, v, t, u in items if t]
                
                # 处理有条件的
                cond_to_values: Dict[str, Set[str]] = defaultdict(set)
                for cond, val in channel_items: 
                    cond_to_values[cond].add(val)
                
                # 无条件的值
                uncond_values = set(v for _, v in uncond_items)
                
                sorted_conds = sorted(cond_to_values.keys(),
                                     key=lambda x:  (-len(x.split('&')), x))
                
                for cond in sorted_conds:
                    values = set(cond_to_values[cond])
                    # 加入无条件的值
                    if uncond_values: 
                        values = values | uncond_values
                    val_str = self._format_targets(values)
                    if cond: 
                        self. lines.append(
                            f"{self.indent}{self.indent}{proc. name}_s = {source} & {cond} : {val_str};"
                        )
                
                # 兜底
                fallback_values = uncond_values | set(v for _, v in timeout_items)
                if fallback_values:
                    val_str = self._format_targets(fallback_values)
                    self.lines.append(
                        f"{self. indent}{self.indent}{proc.name}_s = {source} :  {val_str};"
                    )
            
            self.lines.append(f"{self.indent}{self.indent}TRUE : {full_name};")
            self.lines.append(f"{self.indent}esac;")
            self.lines.append("")
    
    def _convert_value(self, val: str, var_type: str) -> str:
        val = val.strip()
        if var_type in ('bool', 'boolean'):
            if val.lower() in ('true', '1'):
                return 'TRUE'
            elif val.lower() in ('false', '0'):
                return 'FALSE'
        return val
    
    def _add_channel_transitions(self):
        for ch in self.model. channels:
            self._add_single_channel_transition(ch)
    
    def _add_single_channel_transition(self, ch:  str):
        """添加单个通道的转换"""
        self.lines.append(f"{self.indent}-- {ch}")
        self.lines.append(f"{self. indent}next({ch}) := case")
        
        # 收集所有发送和接收操作
        send_cases:  List[Tuple[str, Set[str]]] = []  # (condition, messages)
        recv_cases: List[str] = []  # conditions
        
        for proc in self.model. processes:
            by_source:  Dict[str, List[IRTransition]] = defaultdict(list)
            for t in proc.transitions:
                by_source[t. source].append(t)
            
            for state, trans_list in by_source.items():
                # 展开所有转换
                expanded_trans:  List[IRTransition] = []
                for t in trans_list:
                    expanded = self._expand_transition_for_mtype(t)
                    for exp_t, _ in expanded: 
                        expanded_trans.append(exp_t)
                
                # 分析每个转换
                trans_with_cond = [(t, analyze_transition(t)) for t in expanded_trans]
                
                # 处理发送操作
                for t, cond in trans_with_cond: 
                    if cond.is_timeout or cond.is_unconditional: 
                        continue
                    
                    send = t.get_send()
                    if send and send.channel == ch:
                        # 构建发送条件
                        cond_parts = [
                            f"turn = P_{proc.name}",
                            f"{proc.name}_s = {state}",
                            f"{ch} = EMPTY"
                        ]
                        
                        recv = t.get_recv()
                        if recv:
                            cond_parts. append(f"{recv.channel} = {recv.message}")
                        
                        if cond.guard_expr:
                            guard = cond.get_smv_condition(proc.name, proc.local_vars)
                            # 只添加守卫部分
                            guard_parts = [p for p in guard.split(' & ') 
                                         if not any(c in p for c in self.model.channels)]
                            cond_parts.extend(guard_parts)
                        
                        full_cond = " & ".join(cond_parts)
                        
                        # 检查是否有不发送的替代
                        has_no_send_alt = False
                        for other_t, other_cond in trans_with_cond:
                            if other_t is t:
                                continue
                            other_send = other_t.get_send()
                            if other_send is None or other_send.channel != ch:
                                if cond.can_coexist_with(other_cond):
                                    has_no_send_alt = True
                                    break
                        
                        # 检查无条件转换
                        if not has_no_send_alt:
                            has_no_send_alt = any(c.is_unconditional for _, c in trans_with_cond)
                        
                        # 添加到发送条件
                        found = False
                        for i, (existing_cond, msgs) in enumerate(send_cases):
                            if existing_cond == full_cond:
                                msgs. add(send.message)
                                if has_no_send_alt:
                                    msgs.add("EMPTY")
                                found = True
                                break
                        
                        if not found:
                            msgs = {send.message}
                            if has_no_send_alt:
                                msgs.add("EMPTY")
                            send_cases. append((full_cond, msgs))
                    
                    # 处理接收操作
                    recv = t.get_recv()
                    if recv and recv.channel == ch:
                        cond_parts = [
                            f"turn = P_{proc.name}",
                            f"{proc.name}_s = {state}",
                            f"{ch} = {recv.message}"
                        ]
                        
                        send = t.get_send()
                        if send:
                            cond_parts.append(f"{send.channel} = EMPTY")
                        
                        if cond.guard_expr:
                            guard = cond. get_smv_condition(proc.name, proc.local_vars)
                            guard_parts = [p for p in guard.split(' & ') 
                                         if not any(c in p for c in self.model. channels)]
                            cond_parts. extend(guard_parts)
                        
                        full_cond = " & ". join(cond_parts)
                        recv_cases.append(full_cond)
        
        # 输出发送条件
        for cond, msgs in send_cases:
            msg_str = self._format_targets(msgs)
            self.lines.append(f"{self.indent}{self.indent}{cond} :  {msg_str};")
        
        # 输出接收条件
        for cond in recv_cases:
            self.lines.append(f"{self. indent}{self.indent}{cond} : EMPTY;")
        
        self.lines.append(f"{self.indent}{self.indent}TRUE : {ch};")
        self.lines.append(f"{self.indent}esac;")
        self.lines.append("")
    
    def _add_fairness(self):
        self.lines.append("-- Fairness constraints")
        for proc in self.model. processes:
            self. lines.append(f"FAIRNESS turn = P_{proc.name}")
        self.lines.append("")
    
    def _add_properties(self):
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
        
        self. lines.append("")


# ============================================================
# 辅助函数
# ============================================================

def pml_to_smv(pml_code: str, debug: bool = False) -> str:
    program = parse_pml(pml_code, silent=not debug, debug=debug)
    converter = PMLToIRConverter(program)
    ir_model = converter.convert()
    generator = SMVGenerator(ir_model)
    return generator.generate()


def print_ir_model(ir_model: IRModel):
    print("=" * 70)
    print("Intermediate Representation (IR)")
    print("=" * 70)
    
    print(f"\nMType: {ir_model.mtype}")
    print(f"\nChannels: {ir_model.channels}")
    
    print(f"\nProcesses ({len(ir_model.processes)}):")
    for proc in ir_model. processes:
        print(f"\n  Process: {proc.name}")
        print(f"    States:  {proc.states}")
        print(f"    Initial State: {proc.initial_state}")
        
        if proc.local_vars:
            print(f"    Local Variables: {proc.local_vars}")
        
        if proc.state_entry_assignments: 
            print(f"    State Entry Assignments:")
            for state, assigns in proc.state_entry_assignments.items():
                assign_str = ", ". join(f"{k}={v}" for k, v in assigns.items())
                print(f"      {state}:  {{{assign_str}}}")
        
        print(f"    Transitions ({len(proc.transitions)}):")
        for t in proc. transitions:
            cond = analyze_transition(t)
            guard_str = f" [{t.guard}]" if t.guard else ""
            if t.is_timeout:
                guard_str = " [timeout]"
            
            actions_str = []
            for a in t.actions:
                var_marker = " (var)" if a.is_variable else ""
                if a.action_type == 'send':
                    actions_str.append(f"{a.channel}!  {a.message}{var_marker}")
                elif a.action_type == 'receive': 
                    actions_str.append(f"{a.channel}?  {a.message}{var_marker}")
                else:
                    actions_str.append("skip")
            
            actions = "; ".join(actions_str) if actions_str else "ε"
            markers = []
            if cond.is_timeout:
                markers. append("timeout")
            if cond. is_unconditional:
                markers. append("unconditional")
            marker_str = f" ({', '.join(markers)})" if markers else ""
            print(f"      {t.source} -> {t.target}{guard_str}:  [{actions}]{marker_str}")

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
