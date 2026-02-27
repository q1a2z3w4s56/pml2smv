#!/usr/bin/env python3
"""
PML to SMV Converter - 修复版 v5
新增功能：
1. 支持导出规范化的JSON中间表示
2. 支持新的 SimplifiedTransition 结构（triggers/actions 分离）
3. 支持赋值操作和变量处理
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Set, Optional, Tuple, Any, Union
from collections import defaultdict
import re
import argparse
import sys
import json

from pml_visitor_v3 import (
    parse_pml, parse_pml_file, ProgramModel, VariableTracker,
    SendAction, ReceiveAction, AssignAction, SkipAction, SelectAction,
    format_action, format_expression, SimplifiedTransition
)


# ============================================================
# IR 数据结构
# ============================================================

@dataclass
class IRChannelAction:
    """通道操作（send/receive）"""
    action_type: str  # 'send' or 'receive'
    channel: str
    message:  Optional[str] = None
    variables: Optional[List[str]] = None  # for receive
    messages: Optional[List[str]] = None   # for send
    is_variable: bool = False
    
    @staticmethod
    def from_trigger_dict(trigger:  Dict) -> 'IRChannelAction': 
        """从 SimplifiedTransition 的 trigger 字典创建"""
        action_type = trigger. get('type', '')
        if action_type == 'receive':
            variables = trigger.get('variables', [])
            return IRChannelAction(
                action_type='receive',
                channel=trigger. get('channel', ''),
                message=variables[0] if variables else None,
                variables=variables,
                is_variable=trigger.get('is_variable', False)
            )
        elif action_type == 'send':
            messages = trigger.get('messages', [])
            return IRChannelAction(
                action_type='send',
                channel=trigger.get('channel', ''),
                message=messages[0] if messages else None,
                messages=messages,
                is_variable=trigger.get('is_variable', False)
            )
        return IRChannelAction(action_type='skip', channel='')
    
    def to_json_dict(self) -> Optional[Dict[str, Any]]: 
        """转换为JSON格式的字典"""
        if self.action_type == 'skip':
            return None
        
        result = {
            "type": "send" if self.action_type == "send" else "recv",
            "channel": self.channel,
        }
        
        if self.action_type == 'send':
            result["messages"] = self.messages or ([self.message] if self.message else [])
        else:
            result["variables"] = self.variables or ([self.message] if self.message else [])
        
        if self.is_variable:
            result["is_variable"] = True
            
        return result


@dataclass
class IRAssignAction:
    """赋值操作"""
    target: str
    value: str
    
    @staticmethod
    def from_action_dict(action:  Dict) -> Optional['IRAssignAction']:
        """从 SimplifiedTransition 的 action 字典创建"""
        if action.get('type') == 'assign':
            return IRAssignAction(
                target=action.get('target', ''),
                value=action.get('value', '')
            )
        return None
    
    def to_json_dict(self) -> Dict[str, Any]: 
        return {
            "type": "assign",
            "target": self.target,
            "value": self. value
        }


@dataclass
class IRSelectAction:
    """选择操作"""
    target: str
    min_val: str
    max_val: str
    
    @staticmethod
    def from_action_dict(action:  Dict) -> Optional['IRSelectAction']: 
        if action.get('type') == 'select':
            return IRSelectAction(
                target=action.get('target', ''),
                min_val=action.get('min_val', ''),
                max_val=action.get('max_val', '')
            )
        return None
    
    def to_json_dict(self) -> Dict[str, Any]:
        return {
            "type": "select",
            "target":  self.target,
            "min":  self.min_val,
            "max": self.max_val
        }


@dataclass
class IRTransition:
    source: str
    target: str
    guard: Optional[str]
    triggers: List[IRChannelAction]  # 通道操作（send/receive）
    actions: List[Union[IRAssignAction, IRSelectAction]]  # 赋值和其他操作
    is_timeout: bool = False
    
    @classmethod
    def from_simplified(cls, trans: SimplifiedTransition) -> 'IRTransition':
        """从 SimplifiedTransition 创建"""
        is_timeout = trans. guard == 'timeout' if trans.guard else False
        guard = None if is_timeout else trans.guard
        
        # 解析 triggers
        triggers = []
        for t in trans.triggers:
            trigger = IRChannelAction. from_trigger_dict(t)
            if trigger. action_type != 'skip': 
                triggers.append(trigger)
        
        # 解析 actions
        actions = []
        for a in trans.actions:
            action_type = a. get('type', '')
            if action_type == 'assign':
                assign = IRAssignAction. from_action_dict(a)
                if assign:
                    actions.append(assign)
            elif action_type == 'select':
                select = IRSelectAction.from_action_dict(a)
                if select: 
                    actions.append(select)
            # skip 操作不需要记录
        
        return cls(
            source=trans.source,
            target=trans.target,
            guard=guard,
            triggers=triggers,
            actions=actions,
            is_timeout=is_timeout
        )
    
    def get_recv(self) -> Optional[IRChannelAction]:
        for t in self.triggers:
            if t. action_type == 'receive':
                return t
        return None
    
    def get_send(self) -> Optional[IRChannelAction]: 
        for t in self.triggers:
            if t.action_type == 'send':
                return t
        return None
    
    def get_all_channel_actions(self) -> List[IRChannelAction]:
        """获取所有通道操作"""
        return self. triggers
    
    def uses_variable_message(self) -> bool:
        return any(t.is_variable for t in self.triggers)
    
    def has_channel_action(self) -> bool:
        return len(self.triggers) > 0
    
    def is_unconditional(self) -> bool:
        """检查是否是无条件转换（无通道操作且无守卫）"""
        return not self.has_channel_action() and not self.guard and not self.is_timeout
    
    def to_json_dict(self) -> Dict[str, Any]: 
        """转换为JSON格式的字典"""
        result = {
            "from": self.source,
            "to":  self.target
        }
        
        # 处理 triggers (通道操作)
        if self. triggers:
            trigger_list = []
            for t in self.triggers:
                t_dict = t.to_json_dict()
                if t_dict:
                    trigger_list.append(t_dict)
            if trigger_list: 
                result["trigger"] = trigger_list
        
        # 处理 actions (赋值等操作)
        if self.actions:
            action_list = [a.to_json_dict() for a in self.actions]
            if action_list:
                result["actions"] = action_list
        
        # 处理 guard
        guards = []
        if self.is_timeout:
            guards.append("timeout")
        if self.guard:
            guards.append(self.guard)
        
        if guards: 
            result["guard"] = guards
        
        return result


@dataclass
class IRVariable:
    """变量定义"""
    name: str
    var_type: str
    initial_value: Optional[str] = None
    is_parameter: bool = False
    
    def to_json_dict(self) -> Dict[str, Any]: 
        result = {
            "name": self.name,
            "type": self.var_type
        }
        if self.initial_value is not None:
            result["initial_value"] = self. initial_value
        if self.is_parameter:
            result["is_parameter"] = True
        return result


@dataclass
class IRProcess:
    name: str
    states: List[str]
    initial_state: str
    transitions: List[IRTransition]
    local_vars: Dict[str, str] = field(default_factory=dict)
    parameter_vars: Dict[str, Dict[str, str]] = field(default_factory=dict)  # 新增：参数变量
    state_entry_assignments: Dict[str, Dict[str, str]] = field(default_factory=dict)
    
    def to_json_dict(self) -> Dict[str, Any]: 
        """转换为JSON格式的字典"""
        # 构建局部变量列表
        local_variables = []
        for var_name, var_type in self.local_vars.items():
            var_info = {"name": var_name, "type": var_type}
            # 检查是否是参数变量
            if var_name in self.parameter_vars:
                var_info["initial_value"] = self.parameter_vars[var_name].get('value')
                var_info["is_parameter"] = True
            local_variables.append(var_info)
        
        # 构建转换列表
        transitions = [t.to_json_dict() for t in self.transitions]
        
        result = {
            "role": self.name,
            "initialstate": self.initial_state,
            "states": self.states,
            "local_variables": local_variables,
            "transitions": transitions
        }
        
        # 只有非空时才添加 state_entry_assignments
        if self.state_entry_assignments: 
            result["state_entry_assignments"] = self.state_entry_assignments
        
        return result


@dataclass
class IRModel:
    mtype:  List[str]
    channels: List[str]
    processes: List[IRProcess]
    channel_details: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    global_variables: List[Dict[str, Any]] = field(default_factory=list)
    protocol_name: str = "Unknown"
    # 新增：init 块中的初始化赋值
    init_assignments: Dict[str, str] = field(default_factory=dict)
    
    def to_json_dict(self) -> Dict[str, Any]:
        """转换为规范的JSON格式"""
        # 构建通道列表
        channels = []
        for ch_name in self.channels:
            ch_info = self.channel_details. get(ch_name, {})
            channels.append({
                "name": ch_name,
                "buffer":  ch_info.get("capacity", 1),
                "types": ch_info. get("types", ["mtype"])
            })
        
        # 构建FSM列表
        fsm = [proc.to_json_dict() for proc in self.processes]
        
        # 构建进程名称列表
        process_names = [proc. name for proc in self.processes]
        result = {
            "protocol": self.protocol_name,
            "Processes": process_names,
            "mtype": self.mtype,
            "channels": channels,
            "global_variables": self.global_variables,
            "fsm": fsm
        }
        
        # 新增：添加 init_assignments
        if self.init_assignments:
            result["init_assignments"] = self.init_assignments
        
        return result
    
    def to_json_origin(self, indent:  int = 2) -> str:
        """导出为JSON字符串"""
        return json.dumps(self.to_json_dict(), indent=indent, ensure_ascii=False)

    def to_json(self, indent: int = 2) -> str:
        """导出为JSON字符串"""
        data = self.to_json_dict()
        
        def custom_format(obj, indent_level=0, is_array_element=False):
            indent_str = " " * indent_level
            
            if isinstance(obj, dict):
                if not obj:
                    return "{}"
                
                # 如果是数组中的元素（如transition对象），需要特殊处理缩进
                items = []
                for key, value in obj.items():
                    # 判断是否是transition对象
                    is_transition = key in ["from", "to", "trigger", "guard"]
                    
                    # 如果当前是transition对象且是数组元素，则让子元素对齐
                    if is_array_element and is_transition:
                        formatted_value = custom_format(value, indent_level + indent, False)
                    else:
                        formatted_value = custom_format(value, indent_level + indent, False)
                    
                    items.append(f'{indent_str}"{key}": {formatted_value}')
                
                if is_array_element:
                    # 数组中的字典元素，去掉前后的换行
                    return "{" + ", ".join(item.strip() for item in items) + "}"
                else:
                    return "{\n" + ",\n".join(items) + "\n" + " " * (indent_level - indent) + "}"
            
            elif isinstance(obj, list):
                if not obj:
                    return "[]"
                
                # 检查列表中的元素类型
                if all(isinstance(item, (str, int, float, bool)) for item in obj):
                    # 基本类型列表紧凑显示
                    items_str = ", ".join(json.dumps(item, ensure_ascii=False) for item in obj)
                    return f"[{items_str}]"
                elif all(isinstance(item, dict) for item in obj):
                    # 字典列表，每个字典一行
                    items = []
                    for item in obj:
                        formatted_item = custom_format(item, indent_level + indent, True)
                        items.append(f'{indent_str}{formatted_item}')
                    return "[\n" + ",\n".join(items) + "\n" + " " * (indent_level - indent) + "]"
                else:
                    # 混合类型列表
                    items = [custom_format(item, indent_level + indent, True) for item in obj]
                    return "[\n" + ",\n".join(items) + "\n" + " " * (indent_level - indent) + "]"
            else:
                return json.dumps(obj, ensure_ascii=False)
        
        return custom_format(data, 0, False)
    
# ============================================================
# PML 到 IR 转换
# ============================================================

class PMLToIRConverter:
    def __init__(self, program: ProgramModel):
        self.program = program
        self.tracker = VariableTracker(program)
    
    def convert(self, protocol_name: str = None) -> IRModel:
        mtype = self.program.mtype_values
        channels = list(self.program.channels.keys())
        
        # 收集通道详细信息
        channel_details = {}
        for ch_name, ch in self.program.channels.items():
            channel_details[ch_name] = {
                "capacity": ch.capacity,
                "types": ch.message_types
            }
        
        # 收集全局变量信息，并合并 init 赋值
        global_variables = []
        init_assigns = getattr(self.program, 'init_assignments', {})
        
        for var_name, var in self.program.global_variables.items():
            var_info = {
                "name": var_name,
                "type": var.var_type.value if hasattr(var.var_type, 'value') else str(var.var_type)
            }
            if var.is_array:
                var_info["is_array"] = True
                var_info["size"] = var.array_size
                # 查找数组元素的初始值
                initial_values = {}
                for i in range(var.array_size):
                    key = f"{var_name}[{i}]"
                    if key in init_assigns:
                        initial_values[str(i)] = init_assigns[key]
                if initial_values:
                    var_info["initial_values"] = initial_values
            else:
                # 非数组变量
                if var_name in init_assigns:
                    var_info["initial_value"] = init_assigns[var_name]
                elif var.initial_value is not None:
                    var_info["initial_value"] = format_expression(var.initial_value)
            
            global_variables.append(var_info)
        
        processes = []
        for proc_name, proc in self.program.processes.items():
            ir_proc = self._convert_process(proc)
            processes.append(ir_proc)
        
        # 尝试从进程名推断协议名
        if protocol_name is None:
            protocol_name = self._infer_protocol_name()
        
        return IRModel(
            mtype=mtype,
            channels=channels,
            processes=processes,
            channel_details=channel_details,
            global_variables=global_variables,
            protocol_name=protocol_name,
            init_assignments=init_assigns  # 保存原始赋值，以便需要时使用
        )
    
    def _infer_protocol_name(self) -> str:
        """从进程名推断协议名称"""
        for proc_name in self.program.processes.keys():
            if '_' in proc_name:
                base_name = proc_name.split('_')[0]
                if base_name not in ('Network', 'init'):
                    return base_name
            elif proc_name not in ('Network', 'init'):
                return proc_name
        return "Unknown"
    
    def _convert_process(self, proc) -> IRProcess: 
        analysis = self. tracker.analyze_process(proc)
        local_vars = analysis['local_vars']
        parameter_vars = analysis. get('parameter_variables', {})
        
        transitions = []
        for trans in analysis['simplified_transitions']:
            ir_trans = IRTransition.from_simplified(trans)
            transitions.append(ir_trans)
        
        return IRProcess(
            name=analysis['name'],
            states=analysis['states'],
            initial_state=analysis['initial_state'],
            transitions=transitions,
            local_vars=local_vars,
            parameter_vars=parameter_vars,
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
    send_message: Optional[str] = None
    guard_expr: Optional[str] = None
    is_timeout: bool = False
    is_unconditional: bool = False
    
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
            g = g. replace("&&", "&")
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
        if self.is_timeout or other.is_timeout:
            return False
        if self.is_unconditional or other.is_unconditional:
            return False
        
        if self.recv_channel and other.recv_channel:
            if self.recv_channel != other.recv_channel or self.recv_message != other.recv_message:
                return False
        
        if (self.recv_channel is None) != (other.recv_channel is None):
            return False
        
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
        if self. guard_expr:
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
        cond.send_message = send. message
    
    if t.guard:
        cond.guard_expr = t. guard
    
    return cond


# ============================================================
# SMV 生成器
# ============================================================

class SMVGenerator:  
    def __init__(self, model:  IRModel):
        self.model = model
        self.lines:  List[str] = []
        self.indent = "  "
        # 收集所有需要的整数变量及其可能的值
        self.int_vars: Dict[str, Set[str]] = {}
        # 记录数组变量的共享值域
        self.array_value_domains: Dict[str, Set[str]] = {}
        # 记录哪些数组变量应该共享值域（如 before_state 和 state）
        self.linked_arrays: Dict[str, str] = {}
        self._collect_int_variables()
    
    def _collect_int_variables(self):
        """收集所有整数变量及其可能的值"""
        # 从全局变量收集
        for var_info in self.model. global_variables:
            var_name = var_info['name']
            var_type = var_info. get('type', '')
            if var_type == 'int': 
                if var_info. get('is_array'):
                    size = var_info. get('size', 2)
                    # 初始化数组的共享值域
                    if var_name not in self.array_value_domains:
                        self.array_value_domains[var_name] = set()
                    for idx in range(size):
                        full_name = f"{var_name}[{idx}]"
                        self. int_vars[full_name] = self.array_value_domains[var_name]
                else: 
                    self.int_vars[var_name] = set()
        
        # 从进程的局部变量和参数变量收集
        for proc in self. model.processes:
            for var_name, var_type in proc.local_vars.items():
                if var_type == 'int': 
                    full_name = f"{proc.name}_{var_name}"
                    self.int_vars[full_name] = set()
            
            # 从参数变量获取初始值
            for var_name, var_info in proc.parameter_vars.items():
                if var_info.get('type') == 'int': 
                    full_name = f"{proc.name}_{var_name}"
                    if full_name not in self.int_vars:
                        self.int_vars[full_name] = set()
                    init_val = var_info. get('value', '0')
                    self.int_vars[full_name]. add(init_val)
        
        # 从状态入口赋值和转换中的赋值收集可能的值
        for proc in self.model. processes:
            # 确定这个进程的 i 参数值
            i_value = None
            if 'i' in proc.parameter_vars:
                i_value = proc.parameter_vars['i']. get('value')
            
            # 状态入口赋值
            for state, assigns in proc.state_entry_assignments.items():
                for target, value in assigns. items():
                    # 解析值中的变量引用
                    resolved_value = self._resolve_value(value, i_value)
                    self._add_int_var_value(target, resolved_value, proc.name, i_value)
            
            # 转换中的赋值
            for trans in proc.transitions:
                for action in trans.actions:
                    if isinstance(action, IRAssignAction):
                        resolved_value = self._resolve_value(action.value, i_value)
                        self._add_int_var_value(action.target, resolved_value, proc. name, i_value)
    
    def _resolve_value(self, value:  str, i_value: Optional[str]) -> str:
        """解析值中的变量引用，将 state[i] 替换为 state[0] 或 state[1]"""
        if i_value is None: 
            return value
        
        # 替换 [i] 为 [具体值]
        result = value
        if '[i]' in result: 
            result = result.replace('[i]', f'[{i_value}]')
        
        return result
    
    def _to_smv_var_name(self, var_name: str) -> str:
        """将变量名转换为 SMV 格式（将 [n] 替换为 _n）"""
        import re
        return re.sub(r'\[(\d+)\]', r'_\1', var_name)
    
    def _add_int_var_value(self, target: str, value:  str, proc_name: str, i_value: Optional[str] = None):
        """添加整数变量的可能值"""
        import re
        
        # 处理目标变量中的 [i]
        resolved_target = target
        if i_value is not None and '[i]' in target:
            resolved_target = target. replace('[i]', f'[{i_value}]')
        
        # 检查值是否引用了另一个数组变量（如 state[0]）
        array_ref_match = re. match(r'(\w+)\[(\d+)\]', value)
        if array_ref_match: 
            ref_array_name = array_ref_match.group(1)
            # 检查目标是否也是数组变量
            target_array_match = re.match(r'(\w+)\[(\d+)\]', resolved_target)
            if target_array_match:
                target_array_name = target_array_match.group(1)
                # 如果是不同的数组，记录它们应该共享值域
                if target_array_name != ref_array_name:
                    if ref_array_name in self.array_value_domains:
                        self.linked_arrays[target_array_name] = ref_array_name
            return  # 不添加变量引用作为值
        
        # 将值转换为 SMV 格式
        smv_value = self._to_smv_var_name(value)
        
        # 跳过变量引用（包含下划线后跟数字的形式，表示数组元素）
        if re.match(r'\w+_\d+$', smv_value):
            return
        
        # 处理数组索引
        if '[' in resolved_target: 
            base_name = resolved_target.split('[')[0]
            # 检查是否是全局数组变量
            for var_info in self.model. global_variables: 
                if var_info['name'] == base_name and var_info.get('is_array'):
                    # 添加到数组的共享值域
                    if base_name in self.array_value_domains:
                        self.array_value_domains[base_name].add(smv_value)
                    return
        
        # 检查是否是已知的整数变量
        if resolved_target in self. int_vars: 
            self.int_vars[resolved_target].add(smv_value)
        
        # 检查是否是进程局部变量
        full_name = f"{proc_name}_{target}"
        if full_name in self. int_vars: 
            self.int_vars[full_name].add(smv_value)
    
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
            f"-- SMV Model (Auto-generated from PML - {self.model.protocol_name})",
            "-- ============================================================",
            "",
            "MODULE main",
            ""
        ])
    
    def _get_array_value_domain(self, array_name: str) -> Set[str]: 
        """获取数组的值域，考虑链接的数组"""
        values = set(self.array_value_domains.get(array_name, set()))
        # 如果这个数组链接到另一个数组，合并值域
        if array_name in self. linked_arrays: 
            linked_name = self.linked_arrays[array_name]
            values. update(self.array_value_domains. get(linked_name, set()))
        # 检查是否有其他数组链接到这个数组
        for other_array, linked_to in self.linked_arrays.items():
            if linked_to == array_name:
                values.update(self. array_value_domains.get(other_array, set()))
        return values
    
    def _add_variables(self):
        self.lines.append("VAR")
        
        procs = ", ".join(f"P_{p.name}" for p in self.model. processes)
        self.lines.append(f"{self.indent}turn :  {{{procs}}};")
        self.lines.append("")
        
        if self.model.mtype: 
            msgs = ", ".join(["EMPTY"] + self.model.mtype)
            for ch in self.model.channels:
                self.lines.append(f"{self.indent}{ch} : {{{msgs}}};")
            self.lines.append("")
        
        # 首先收集所有链接数组的共享值域
        all_linked_values:  Dict[str, Set[str]] = {}
        for var_info in self. model.global_variables:
            var_name = var_info['name']
            var_type = var_info.get('type', '')
            if var_type == 'int' and var_info. get('is_array'):
                all_linked_values[var_name] = self._get_array_value_domain(var_name)
        
        # 添加全局整数变量
        for var_info in self.model.global_variables:
            var_name = var_info['name']
            var_type = var_info. get('type', '')
            if var_type == 'int': 
                if var_info.get('is_array'):
                    size = var_info. get('size', 2)
                    # 获取数组的共享值域（包括链接数组的值）
                    shared_values = set(all_linked_values.get(var_name, set()))
                    shared_values.add('0')  # 始终包含初始值
                    val_str = ", ".join(sorted(shared_values))
                    
                    for idx in range(size):
                        smv_name = f"{var_name}_{idx}"
                        self.lines.append(f"{self. indent}{smv_name} : {{{val_str}}};")
                else: 
                    values = self. int_vars.get(var_name, set())
                    values.add('0')
                    val_str = ", ".join(sorted(values))
                    self.lines.append(f"{self.indent}{var_name} : {{{val_str}}};")
        
        if self.model.global_variables:
            self.lines.append("")
        
        for proc in self.model.processes:
            if len(proc.states) == 1:
                states = ", ".join(proc.states + ["_DUMMY"])
            else:
                states = ", ".join(proc. states)
            self.lines.append(f"{self.indent}{proc.name}_s : {{{states}}};")
            
            for var_name, var_type in proc.local_vars.items():
                full_name = f"{proc.name}_{var_name}"
                if var_type in ('bool', 'boolean'):
                    self.lines.append(f"{self.indent}{full_name} : boolean;")
                elif var_type == 'int':
                    values = self.int_vars.get(full_name, set())
                    values. add('0')
                    # 确保包含所有可能的值（0 和 1 对于索引变量）
                    if var_name == 'i':
                        values.add('1')
                    val_str = ", ".join(sorted(values))
                    self. lines.append(f"{self.indent}{full_name} :  {{{val_str}}};")
        
        self.lines.append("")
    
    def _add_init(self):
        self.lines.append("ASSIGN")
        
        procs = ", ".join(f"P_{p.name}" for p in self.model.processes)
        self.lines.append(f"{self. indent}init(turn) := {{{procs}}};")
        
        for ch in self.model. channels:
            self.lines.append(f"{self.indent}init({ch}) := EMPTY;")
        
        # 初始化全局整数变量
        for var_info in self.model.global_variables:
            var_name = var_info['name']
            var_type = var_info. get('type', '')
            if var_type == 'int':
                init_val = var_info.get('initial_value', '0')
                if var_info.get('is_array'):
                    size = var_info.get('size', 2)
                    for idx in range(size):
                        smv_name = f"{var_name}_{idx}"
                        self.lines. append(f"{self.indent}init({smv_name}) := {init_val};")
                else:
                    self.lines. append(f"{self.indent}init({var_name}) := {init_val};")
        
        for proc in self.model.processes:
            self.lines.append(f"{self.indent}init({proc. name}_s) := {proc.initial_state};")
            
            for var_name, var_type in proc.local_vars.items():
                full_name = f"{proc.name}_{var_name}"
                if var_type in ('bool', 'boolean'):
                    init_val = "FALSE"
                    if var_name in proc.parameter_vars:
                        val = proc.parameter_vars[var_name]. get('value', '')
                        init_val = "TRUE" if val. lower() in ('true', '1') else "FALSE"
                    elif proc.initial_state in proc.state_entry_assignments: 
                        if var_name in proc.state_entry_assignments[proc.initial_state]:
                            val = proc. state_entry_assignments[proc.initial_state][var_name]
                            init_val = "TRUE" if val.lower() in ('true', '1') else "FALSE"
                    self.lines.append(f"{self. indent}init({full_name}) := {init_val};")
                elif var_type == 'int': 
                    init_val = "0"
                    if var_name in proc.parameter_vars:
                        init_val = proc. parameter_vars[var_name].get('value', '0')
                    self.lines.append(f"{self. indent}init({full_name}) := {init_val};")
        
        self.lines.append("")
    
    def _add_transitions(self):
        procs = ", ".join(f"P_{p.name}" for p in self.model.processes)
        self.lines.append(f"{self. indent}next(turn) := {{{procs}}};")
        self.lines.append("")
        
        for proc in self.model. processes:
            self._add_process_state_transition(proc)
            self._add_process_var_transitions(proc)
            self._add_process_int_var_transitions(proc)
        
        self._add_global_int_var_transitions()
        self._add_channel_transitions()
    
    def _expand_transition_for_mtype(self, t: IRTransition) -> List[Tuple[IRTransition, str]]: 
        """展开使用变量消息的转换为多个具体消息的转换"""
        if not t.uses_variable_message():
            return [(t, None)]
        
        variable_triggers = [trigger for trigger in t. triggers if trigger.is_variable]
        
        if not variable_triggers:
            return [(t, None)]
        
        expanded = []
        for msg in self.model.mtype:
            new_triggers = []
            for trigger in t.triggers:
                if trigger.is_variable: 
                    new_trigger = IRChannelAction(
                        action_type=trigger.action_type,
                        channel=trigger.channel,
                        message=msg,
                        messages=[msg] if trigger.action_type == 'send' else None,
                        variables=[msg] if trigger.action_type == 'receive' else None,
                        is_variable=False
                    )
                    new_triggers.append(new_trigger)
                else:
                    new_triggers.append(trigger)
            
            new_trans = IRTransition(
                source=t.source,
                target=t.target,
                guard=t.guard,
                triggers=new_triggers,
                actions=t.actions,
                is_timeout=t.is_timeout
            )
            expanded.append((new_trans, msg))
        
        return expanded
    
    def _format_targets(self, targets:  Set[str]) -> str:
        if len(targets) == 1:
            return list(targets)[0]
        else: 
            return "{" + ", ".join(sorted(targets)) + "}"
    
    def _add_process_state_transition(self, proc: IRProcess):
        """添加进程状态转换"""
        self.lines.append(f"{self.indent}-- {proc.name} state")
        self.lines.append(f"{self.indent}next({proc.name}_s) := case")
        self.lines.append(f"{self.indent}{self.indent}turn != P_{proc.name} :  {proc.name}_s;")
        
        by_source:  Dict[str, List[IRTransition]] = defaultdict(list)
        for t in proc.transitions:
            expanded = self._expand_transition_for_mtype(t)
            for exp_t, _ in expanded:
                by_source[exp_t.source]. append(exp_t)
        
        for state in proc.states:
            if state not in by_source: 
                continue
            
            trans_list = by_source[state]
            
            trans_with_cond:  List[Tuple[IRTransition, TransitionCondition]] = []
            for t in trans_list: 
                cond = analyze_transition(t)
                trans_with_cond.append((t, cond))
            
            timeout_trans = [(t, c) for t, c in trans_with_cond if c. is_timeout]
            unconditional_trans = [(t, c) for t, c in trans_with_cond if c.is_unconditional]
            conditional_trans = [(t, c) for t, c in trans_with_cond
                                if not c.is_timeout and not c. is_unconditional]
            
            generated_cases = self._generate_state_cases(
                proc, state, conditional_trans, unconditional_trans, timeout_trans
            )
            
            for smv_cond, targets in generated_cases: 
                targets_str = self._format_targets(targets)
                if smv_cond:
                    self.lines.append(
                        f"{self.indent}{self. indent}{proc.name}_s = {state} & {smv_cond} :  {targets_str};"
                    )
                else: 
                    self.lines.append(
                        f"{self. indent}{self.indent}{proc.name}_s = {state} : {targets_str};"
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
        timeout_trans: List[Tuple[IRTransition, TransitionCondition]]
    ) -> List[Tuple[str, Set[str]]]: 
        """生成状态的所有 case 分支"""
        cases: List[Tuple[str, Set[str]]] = []
        
        unique_conds:  Dict[str, Tuple[TransitionCondition, Set[str]]] = {}
        
        for t, cond in conditional_trans:
            smv_cond = cond.get_smv_condition(proc. name, proc.local_vars)
            if smv_cond not in unique_conds: 
                unique_conds[smv_cond] = (cond, set())
            unique_conds[smv_cond][1]. add(t.target)
        
        cond_list = list(unique_conds.keys())
        cond_objs = {k: v[0] for k, v in unique_conds.items()}
        
        sorted_conds = sorted(cond_list, key=lambda x: (
            -len([p for p in x. split('&') if p.strip()]),
            x
        ))
        
        for cond_str in sorted_conds:
            cond_obj = cond_objs[cond_str]
            targets = set(unique_conds[cond_str][1])
            
            for other_cond_str in cond_list: 
                if other_cond_str != cond_str: 
                    other_cond_obj = cond_objs[other_cond_str]
                    if cond_obj. can_coexist_with(other_cond_obj):
                        targets.update(unique_conds[other_cond_str][1])
            
            for t, _ in unconditional_trans:
                targets.add(t. target)
            
            cases.append((cond_str, targets))
        
        fallback_targets = set()
        for t, _ in unconditional_trans: 
            fallback_targets.add(t.target)
        for t, _ in timeout_trans:
            fallback_targets. add(t.target)
        
        if fallback_targets: 
            cases.append(("", fallback_targets))
        
        return cases
    
    def _add_process_var_transitions(self, proc: IRProcess):
        """添加进程布尔局部变量的转换"""
        for var_name, var_type in proc. local_vars.items():
            if var_type not in ('bool', 'boolean'):
                continue
            
            full_name = f"{proc.name}_{var_name}"
            
            assignments:  List[Tuple[str, str, str, str, bool, bool]] = []
            
            for t in proc.transitions:
                expanded = self._expand_transition_for_mtype(t)
                for exp_t, _ in expanded: 
                    # 检查状态入口赋值
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
                    
                    # 检查转换中的赋值操作
                    for action in exp_t.actions:
                        if isinstance(action, IRAssignAction):
                            if action.target == var_name:
                                cond = analyze_transition(exp_t)
                                smv_cond = cond.get_smv_condition(proc.name, proc. local_vars)
                                smv_val = self._convert_value(action. value, var_type)
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
            self.lines.append(f"{self. indent}{self.indent}turn != P_{proc.name} :  {full_name};")
            
            by_source: Dict[str, List[Tuple[str, str, bool, bool]]] = defaultdict(list)
            for source, target, cond, val, is_timeout, is_uncond in assignments: 
                by_source[source].append((cond, val, is_timeout, is_uncond))
            
            for source in sorted(by_source. keys()):
                items = by_source[source]
                
                channel_items = [(c, v) for c, v, t, u in items if not t and not u and c]
                uncond_items = [(c, v) for c, v, t, u in items if u]
                timeout_items = [(c, v) for c, v, t, u in items if t]
                
                cond_to_values:  Dict[str, Set[str]] = defaultdict(set)
                for cond, val in channel_items:
                    cond_to_values[cond].add(val)
                
                uncond_values = set(v for _, v in uncond_items)
                
                sorted_conds = sorted(cond_to_values.keys(),
                                     key=lambda x:  (-len(x. split('&')), x))
                
                for cond in sorted_conds: 
                    values = set(cond_to_values[cond])
                    if uncond_values: 
                        values = values | uncond_values
                    val_str = self._format_targets(values)
                    if cond: 
                        self. lines.append(
                            f"{self.indent}{self. indent}{proc.name}_s = {source} & {cond} : {val_str};"
                        )
                
                fallback_values = uncond_values | set(v for _, v in timeout_items)
                if fallback_values: 
                    val_str = self._format_targets(fallback_values)
                    self.lines.append(
                        f"{self. indent}{self.indent}{proc.name}_s = {source} :  {val_str};"
                    )
            
            self.lines.append(f"{self.indent}{self.indent}TRUE : {full_name};")
            self.lines.append(f"{self. indent}esac;")
            self.lines.append("")
    
    def _add_process_int_var_transitions(self, proc: IRProcess):
        """添加进程整数局部变量的转换"""
        for var_name, var_type in proc. local_vars.items():
            if var_type != 'int': 
                continue
            
            full_name = f"{proc.name}_{var_name}"
            
            # 收集所有赋值
            assignments: List[Tuple[str, str, str, str, bool, bool]] = []
            
            for t in proc.transitions:
                expanded = self._expand_transition_for_mtype(t)
                for exp_t, _ in expanded: 
                    # 检查转换中的赋值操作
                    for action in exp_t.actions:
                        if isinstance(action, IRAssignAction):
                            if action.target == var_name: 
                                cond = analyze_transition(exp_t)
                                smv_cond = cond.get_smv_condition(proc. name, proc.local_vars)
                                assignments.append((
                                    exp_t.source, exp_t.target, smv_cond, action.value,
                                    cond.is_timeout, cond.is_unconditional
                                ))
            
            if not assignments: 
                continue
            
            self.lines.append(f"{self.indent}-- {full_name}")
            self.lines.append(f"{self.indent}next({full_name}) := case")
            self.lines.append(f"{self.indent}{self.indent}turn != P_{proc.name} : {full_name};")
            
            by_source: Dict[str, List[Tuple[str, str, bool, bool]]] = defaultdict(list)
            for source, target, cond, val, is_timeout, is_uncond in assignments:
                by_source[source].append((cond, val, is_timeout, is_uncond))
            
            for source in sorted(by_source. keys()):
                items = by_source[source]
                
                for cond, val, is_timeout, is_uncond in items:
                    if cond:
                        self.lines.append(
                            f"{self.indent}{self.indent}{proc.name}_s = {source} & {cond} : {val};"
                        )
                    elif is_uncond or is_timeout: 
                        self.lines.append(
                            f"{self. indent}{self.indent}{proc.name}_s = {source} : {val};"
                        )
            
            self. lines.append(f"{self.indent}{self.indent}TRUE : {full_name};")
            self.lines.append(f"{self.indent}esac;")
            self.lines.append("")
    
    def _add_global_int_var_transitions(self):
        """添加全局整数变量的转换"""
        for var_info in self.model.global_variables:
            var_name = var_info['name']
            var_type = var_info.get('type', '')
            if var_type != 'int': 
                continue
            
            if var_info. get('is_array'):
                size = var_info.get('size', 2)
                for idx in range(size):
                    self._add_single_global_int_var_transition(var_name, idx)
            else:
                self._add_single_global_int_var_transition(var_name, None)
    
    def _add_single_global_int_var_transition(self, var_name:  str, idx: Optional[int]):
        """添加单个全局整数变量的转换"""
        if idx is not None:
            full_name = f"{var_name}[{idx}]"
            smv_name = f"{var_name}_{idx}"
        else:
            full_name = var_name
            smv_name = var_name
        
        # 收集所有赋值
        assignments: List[Tuple[str, str, str, str, str, bool, bool]] = []
        
        for proc in self.model. processes:
            # 确定这个进程的 i 参数值
            i_value = None
            if 'i' in proc.parameter_vars:
                i_value = proc.parameter_vars['i'].get('value')
            
            # 检查状态入口赋值
            for state, assigns in proc.state_entry_assignments.items():
                for target, value in assigns. items():
                    should_match = False
                    if target == full_name:
                        should_match = True
                    elif idx is not None and target == f"{var_name}[i]" and i_value == str(idx):
                        should_match = True
                    
                    if should_match:
                        # 解析值中的变量引用
                        resolved_value = self._resolve_value_for_smv(value, i_value)
                        
                        # 为进入这个状态的所有转换添加赋值
                        for t in proc.transitions:
                            if t.target == state:
                                cond = analyze_transition(t)
                                smv_cond = cond. get_smv_condition(proc.name, proc.local_vars)
                                assignments.append((
                                    proc.name, t. source, t.target, smv_cond, resolved_value,
                                    cond. is_timeout, cond.is_unconditional
                                ))
            
            # 检查转换中的赋值
            for t in proc.transitions:
                expanded = self._expand_transition_for_mtype(t)
                for exp_t, _ in expanded: 
                    for action in exp_t. actions:
                        if isinstance(action, IRAssignAction):
                            should_match = False
                            if action. target == full_name:
                                should_match = True
                            elif idx is not None and action. target == f"{var_name}[i]" and i_value == str(idx):
                                should_match = True
                            
                            if should_match: 
                                resolved_value = self._resolve_value_for_smv(action.value, i_value)
                                cond = analyze_transition(exp_t)
                                smv_cond = cond.get_smv_condition(proc.name, proc.local_vars)
                                assignments. append((
                                    proc.name, exp_t.source, exp_t.target, smv_cond, resolved_value,
                                    cond.is_timeout, cond.is_unconditional
                                ))
        
        if not assignments:
            return
        
        self. lines.append(f"{self.indent}-- {smv_name}")
        self.lines.append(f"{self.indent}next({smv_name}) := case")
        
        for proc_name, source, target, cond, val, is_timeout, is_uncond in assignments:
            turn_cond = f"turn = P_{proc_name} & {proc_name}_s = {source}"
            if cond:
                self.lines.append(f"{self.indent}{self.indent}{turn_cond} & {cond} : {val};")
            else:
                self. lines.append(f"{self.indent}{self.indent}{turn_cond} :  {val};")
        
        self. lines.append(f"{self.indent}{self.indent}TRUE : {smv_name};")
        self.lines.append(f"{self. indent}esac;")
        self.lines.append("")
    
    def _resolve_value_for_smv(self, value: str, i_value: Optional[str]) -> str:
        """将值转换为 SMV 格式，解析变量引用"""
        result = value
        
        # 替换 [i] 为具体的索引
        if i_value is not None and '[i]' in result: 
            result = result.replace('[i]', f'[{i_value}]')
        
        # 将 array[n] 转换为 array_n
        result = self._to_smv_var_name(result)
        
        return result
    
    def _convert_value(self, val: str, var_type: str) -> str:
        val = val.strip()
        if var_type in ('bool', 'boolean'):
            if val. lower() in ('true', '1'):
                return 'TRUE'
            elif val.lower() in ('false', '0'):
                return 'FALSE'
        return val
    
    def _add_channel_transitions(self):
        for ch in self.model. channels:
            self._add_single_channel_transition(ch)
    
    def _add_single_channel_transition(self, ch: str):
        """添加单个通道的转换"""
        self.lines.append(f"{self.indent}-- {ch}")
        self.lines.append(f"{self.indent}next({ch}) := case")
        
        send_cases: List[Tuple[str, Set[str]]] = []
        recv_cases: List[str] = []
        
        for proc in self.model.processes:
            by_source: Dict[str, List[IRTransition]] = defaultdict(list)
            for t in proc.transitions:
                by_source[t. source].append(t)
            
            for state, trans_list in by_source.items():
                expanded_trans:  List[IRTransition] = []
                for t in trans_list:
                    expanded = self._expand_transition_for_mtype(t)
                    for exp_t, _ in expanded: 
                        expanded_trans.append(exp_t)
                
                trans_with_cond = [(t, analyze_transition(t)) for t in expanded_trans]
                
                for t, cond in trans_with_cond:
                    if cond. is_timeout or cond.is_unconditional: 
                        continue
                    
                    send = t.get_send()
                    recv = t.get_recv()
                    
                    if send and send.channel == ch:
                        cond_parts = [
                            f"turn = P_{proc.name}",
                            f"{proc.name}_s = {state}",
                            f"{ch} = EMPTY"
                        ]
                        
                        if recv:
                            if recv.is_variable:
                                continue
                            cond_parts.append(f"{recv. channel} = {recv.message}")
                        
                        if cond. guard_expr:
                            guard = cond.get_smv_condition(proc.name, proc.local_vars)
                            guard_parts = [p for p in guard. split(' & ')
                                        if not any(c in p for c in self. model.channels)]
                            cond_parts.extend(guard_parts)
                        
                        full_cond = " & ".join(cond_parts)
                        
                        send_msg = send.message
                        if send.is_variable:
                            continue
                        
                        has_no_send_alt = False
                        for other_t, other_cond in trans_with_cond:
                            if other_t is t:
                                continue
                            other_send = other_t.get_send()
                            if other_send is None or other_send.channel != ch:
                                if cond.can_coexist_with(other_cond):
                                    has_no_send_alt = True
                                    break
                        
                        if not has_no_send_alt: 
                            has_no_send_alt = any(c.is_unconditional for _, c in trans_with_cond)
                        
                        found = False
                        for i, (existing_cond, msgs) in enumerate(send_cases):
                            if existing_cond == full_cond:
                                msgs. add(send_msg)
                                if has_no_send_alt:
                                    msgs.add("EMPTY")
                                found = True
                                break
                        
                        if not found:
                            msgs = {send_msg}
                            if has_no_send_alt:
                                msgs.add("EMPTY")
                            send_cases. append((full_cond, msgs))
                    
                    if recv and recv.channel == ch:
                        if recv.is_variable:
                            continue
                        
                        cond_parts = [
                            f"turn = P_{proc.name}",
                            f"{proc.name}_s = {state}",
                            f"{ch} = {recv.message}"
                        ]
                        
                        if send:
                            if send.is_variable:
                                continue
                            cond_parts.append(f"{send.channel} = EMPTY")
                        
                        if cond.guard_expr:
                            guard = cond.get_smv_condition(proc.name, proc.local_vars)
                            guard_parts = [p for p in guard. split(' & ')
                                        if not any(c in p for c in self. model.channels)]
                            cond_parts.extend(guard_parts)
                        
                        full_cond = " & ".join(cond_parts)
                        recv_cases.append(full_cond)
        
        for cond, msgs in send_cases:
            msg_str = self._format_targets(msgs)
            self.lines. append(f"{self.indent}{self. indent}{cond} : {msg_str};")
        
        for cond in recv_cases:
            self.lines.append(f"{self.indent}{self.indent}{cond} :  EMPTY;")
        
        self.lines.append(f"{self.indent}{self.indent}TRUE :  {ch};")
        self.lines. append(f"{self.indent}esac;")
        self.lines.append("")
    
    def _add_fairness(self):
        self.lines.append("-- Fairness constraints")
        for proc in self.model.processes:
            self. lines.append(f"FAIRNESS turn = P_{proc.name}")
        self.lines.append("")
    
    def _add_properties(self):
        self.lines.append("-- ============================================================")
        self.lines.append("-- Properties")
        self.lines.append("-- ============================================================")
        self.lines.append("")
        
        # CTL Properties
        self.lines.append("-- CTL Properties")
        dccp_procs = [p for p in self.model.processes if 'DCCP' in p.name. upper()]
        if len(dccp_procs) >= 2:
            p1, p2 = dccp_procs[0]. name, dccp_procs[1]. name
            if 'OPEN' in dccp_procs[0].states: 
                self.lines.append(f"CTLSPEC EF ({p1}_s = OPEN & {p2}_s = OPEN)")
        
        for proc in dccp_procs: 
            if 'OPEN' in proc.states:
                self.lines.append(f"CTLSPEC EF ({proc.name}_s = OPEN)")
        
        for proc in self.model.processes:
            if 'I_am_active' in proc.local_vars and 'CLOSEREQ' in proc. states:
                self. lines.append(
                    f"CTLSPEC AG ({proc.name}_s = CLOSEREQ -> {proc.name}_I_am_active = TRUE)"
                )
        
        self.lines.append("")


# ============================================================
# 辅助函数
# ============================================================

def pml_to_smv(pml_code: str, debug: bool = False) -> str:
    program = parse_pml(pml_code, silent=not debug, debug=debug)
    converter = PMLToIRConverter(program)
    ir_model = converter.convert()
    generator = SMVGenerator(ir_model)
    return generator.generate()


def pml_to_json(pml_code: str, protocol_name: str = None, debug: bool = False) -> str:
    """将PML代码转换为规范化的JSON格式"""
    program = parse_pml(pml_code, silent=not debug, debug=debug)
    converter = PMLToIRConverter(program)
    ir_model = converter.convert(protocol_name=protocol_name)
    return ir_model.to_json(indent=2)


def print_ir_model(ir_model: IRModel):
    print("=" * 70)
    print("Intermediate Representation (IR)")
    print("=" * 70)
    
    print(f"\nProtocol: {ir_model.protocol_name}")
    print(f"\nMType: {ir_model.mtype}")
    print(f"\nChannels: {ir_model.channels}")
    
    if ir_model.global_variables:
        print(f"\nGlobal Variables ({len(ir_model.global_variables)}):")
        for var in ir_model.global_variables:
            arr_str = f"[{var.get('size', '')}]" if var.get('is_array') else ""
            print(f"  {var['type']} {var['name']}{arr_str}")
    
    print(f"\nProcesses ({len(ir_model.processes)}):")
    for proc in ir_model. processes:
        print(f"\n  Process: {proc.name}")
        print(f"    States:  {proc.states}")
        print(f"    Initial State: {proc.initial_state}")
        
        if proc.local_vars:
            print(f"    Local Variables:  {proc.local_vars}")
        
        if proc.parameter_vars:
            print(f"    Parameter Variables:")
            for var_name, var_info in proc.parameter_vars.items():
                print(f"      {var_info. get('type', '? ')} {var_name} = {var_info.get('value', '?')}")
        
        if proc.state_entry_assignments:
            print(f"    State Entry Assignments:")
            for state, assigns in proc.state_entry_assignments.items():
                assign_str = ", ".join(f"{k}={v}" for k, v in assigns.items())
                print(f"      {state}:  {{{assign_str}}}")
        
        print(f"    Transitions ({len(proc.transitions)}):")
        for t in proc. transitions:
            cond = analyze_transition(t)
            guard_str = f" [{t.guard}]" if t.guard else ""
            if t.is_timeout:
                guard_str = " [timeout]"
            
            # 显示 triggers
            trigger_strs = []
            for trigger in t. triggers:
                if trigger.action_type == 'send':
                    msgs = trigger.messages or [trigger.message]
                    trigger_strs.append(f"{trigger.channel}!  {','.join(str(m) for m in msgs if m)}")
                elif trigger.action_type == 'receive': 
                    vars_list = trigger.variables or [trigger.message]
                    trigger_strs.append(f"{trigger. channel}?  {','.join(str(v) for v in vars_list if v)}")
            
            # 显示 actions
            action_strs = []
            for action in t. actions:
                if isinstance(action, IRAssignAction):
                    action_strs.append(f"{action. target} = {action.value}")
                elif isinstance(action, IRSelectAction):
                    action_strs. append(f"select({action.target}:  {action.min_val}..{action. max_val})")
            
            triggers = "; ".join(trigger_strs) if trigger_strs else ""
            actions = "; ".join(action_strs) if action_strs else "ε"
            
            markers = []
            if cond.is_timeout:
                markers. append("timeout")
            if cond. is_unconditional:
                markers. append("unconditional")
            marker_str = f" ({', '.join(markers)})" if markers else ""
            
            if triggers: 
                print(f"      {t. source} -> {t.target}{guard_str}")
                print(f"        triggers: [{triggers}]")
                print(f"        actions:   [{actions}]{marker_str}")
            else:
                print(f"      {t.source} -> {t.target}{guard_str}")
                print(f"        actions:  [{actions}]{marker_str}")


# ============================================================
# 命令行接口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description='Convert Promela (PML) to NuSMV (SMV) or JSON',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples: 
  python pml2smv_ir.py input.pml                    # 输出SMV到stdout
  python pml2smv_ir.py input.pml -o output.smv      # 输出SMV到文件
  python pml2smv_ir.py input.pml --json             # 输出JSON到stdout
  python pml2smv_ir.py input.pml --json -o out.json # 输出JSON到文件
  python pml2smv_ir.py input.pml --debug            # 显示调试信息
  python pml2smv_ir.py input.pml --ir               # 显示中间表示
  python pml2smv_ir.py --test                       # 运行内置测试
  python pml2smv_ir.py --test --json                # 测试JSON输出
        """
    )
    
    parser. add_argument('input', nargs='?', help='Input PML file')
    parser.add_argument('-o', '--output', help='Output file (SMV or JSON)')
    parser.add_argument('--json', action='store_true', help='Output as JSON instead of SMV')
    parser.add_argument('--protocol', help='Protocol name for JSON output')
    parser.add_argument('--debug', action='store_true', help='Show debug information')
    parser.add_argument('--ir', action='store_true', help='Print intermediate representation')
    parser.add_argument('--test', action='store_true', help='Run built-in test')
    
    args = parser.parse_args()
    
    if args.test:
        run_test(output_json=args.json)
        return
    
    if not args.input:
        parser.print_help()
        return
    
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            pml_code = f.read()
        
        program = parse_pml(pml_code, silent=not args.debug, debug=args.debug)
        
        converter = PMLToIRConverter(program)
        ir_model = converter. convert(protocol_name=args.protocol)
        
        if args. ir:
            print_ir_model(ir_model)
            print()
        
        if args.json:
            output_code = ir_model.to_json(indent=2)
        else:
            generator = SMVGenerator(ir_model)
            output_code = generator.generate()
        
        if args.output:
            with open(args. output, 'w', encoding='utf-8') as f:
                f.write(output_code)
            file_type = "JSON" if args. json else "SMV"
            print(f"{file_type} code written to:  {args.output}", file=sys.stderr)
        else:
            print(output_code)
    
    except FileNotFoundError: 
        print(f"Error: File not found: {args. input}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def run_test(output_json:  bool = False):
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
    ::  goto LISTEN; /* passive open */
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
    print("PML to SMV/JSON Converter - Test")
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
        ir_model = converter.convert(protocol_name="DCCP")
        print(f"  Converted successfully!")
        
        print("\n" + "-" * 70)
        print_ir_model(ir_model)
        
        if output_json: 
            print("\n" + "=" * 70)
            print("Generated JSON:")
            print("=" * 70)
            json_code = ir_model. to_json(indent=2)
            print(json_code)
            
            output_file = r"C:\Users\10544\Desktop\毕业论文\pml_ir_smv\ir_test.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(json_code)
            print(f"\n-- JSON output written to {output_file}", file=sys.stderr)
        else:
            print("\n" + "-" * 70)
            print("\nStep 3: Generating SMV...")
            generator = SMVGenerator(ir_model)
            smv_code = generator.generate()
            print(f"  Generated {len(smv_code. splitlines())} lines of SMV code")
            
            print("\n" + "=" * 70)
            print("Generated SMV Code:")
            print("=" * 70)
            print(smv_code)
            
            output_file = "dccp_auto.smv"
            with open(output_file, 'w') as f:
                f.write(smv_code)
            print(f"\n-- Output written to {output_file}", file=sys.stderr)
        
    except Exception as e: 
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__": 
    main()

