#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
参数空间定义
NeuroTrade Nexus (NTN) - Parameter Space

核心功能：
1. 定义优化参数的搜索空间
2. 参数类型和范围管理
3. 参数验证和约束
"""

import random
from dataclasses import dataclass
from typing import Any, Dict, List, Union


@dataclass
class ParameterRange:
    """参数范围定义"""

    min_value: Union[int, float]
    max_value: Union[int, float]
    param_type: str  # 'int' or 'float'
    step: Union[int, float] = None

    def __post_init__(self):
        if self.step is None:
            if self.param_type == "int":
                self.step = 1
            else:
                self.step = (self.max_value - self.min_value) / 100

    def random_value(self) -> Union[int, float]:
        """生成随机值"""
        if self.param_type == "int":
            return random.randint(int(self.min_value), int(self.max_value))
        else:
            return random.uniform(self.min_value, self.max_value)

    def validate(self, value: Union[int, float]) -> bool:
        """验证值是否在范围内"""
        return self.min_value <= value <= self.max_value


class ParameterSpace:
    """参数空间管理器"""

    def __init__(
        self,
        parameters: Union[Dict[str, ParameterRange], Dict[str, Dict[str, Any]]] = None,
    ):
        self.parameters = {}
        if parameters:
            if isinstance(list(parameters.values())[0], ParameterRange):
                # 如果已经是ParameterRange对象
                self.parameters = parameters
            else:
                # 如果是字典格式，转换为ParameterRange对象
                for name, param_info in parameters.items():
                    param_range = ParameterRange(
                        min_value=param_info["min"],
                        max_value=param_info["max"],
                        param_type=param_info["type"],
                        step=param_info.get("step"),
                    )
                    self.parameters[name] = param_range

    def add_parameter(self, name: str, param_range: ParameterRange):
        """添加参数"""
        self.parameters[name] = param_range

    def add_int_parameter(self, name: str, min_val: int, max_val: int, step: int = 1):
        """添加整数参数"""
        self.parameters[name] = ParameterRange(min_val, max_val, "int", step)

    def add_float_parameter(
        self, name: str, min_val: float, max_val: float, step: float = None
    ):
        """添加浮点参数"""
        self.parameters[name] = ParameterRange(min_val, max_val, "float", step)

    def random_sample(self) -> Dict[str, Union[int, float]]:
        """随机采样参数组合"""
        return {
            name: param_range.random_value()
            for name, param_range in self.parameters.items()
        }

    def validate_parameters(self, params: Dict[str, Union[int, float]]) -> bool:
        """验证参数组合"""
        for name, value in params.items():
            if name not in self.parameters:
                return False
            if not self.parameters[name].validate(value):
                return False
        return True

    def get_parameter_names(self) -> List[str]:
        """获取参数名列表"""
        return list(self.parameters.keys())

    def get_dimension(self) -> int:
        """获取参数空间维度"""
        return len(self.parameters)

    def keys(self):
        """获取参数名称（兼容字典接口）"""
        return self.parameters.keys()

    def items(self):
        """获取参数项（兼容字典接口）"""
        return self.parameters.items()

    def __getitem__(self, key):
        """支持索引访问"""
        return self.parameters[key]

    def __contains__(self, key):
        """支持in操作符"""
        return key in self.parameters

    def sample_parameter(self, param_name: str) -> Union[int, float]:
        """采样单个参数"""
        if param_name in self.parameters:
            return self.parameters[param_name].random_value()
        raise KeyError(f"Parameter {param_name} not found in parameter space")

    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        """转换为字典格式"""
        result = {}
        for name, param_range in self.parameters.items():
            result[name] = {
                "min": param_range.min_value,
                "max": param_range.max_value,
                "type": param_range.param_type,
                "step": param_range.step,
            }
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Dict[str, Any]]) -> "ParameterSpace":
        """从字典创建参数空间"""
        space = cls()
        for name, param_info in data.items():
            param_range = ParameterRange(
                min_value=param_info["min"],
                max_value=param_info["max"],
                param_type=param_info["type"],
                step=param_info.get("step"),
            )
            space.add_parameter(name, param_range)
        return space


# 预定义的策略参数空间
STRATEGY_PARAMETER_SPACES = {
    "grid_v1.2": ParameterSpace(
        {
            "grid_num": ParameterRange(5, 50, "int"),
            "profit_ratio": ParameterRange(0.005, 0.05, "float"),
            "stop_loss": ParameterRange(0.02, 0.1, "float"),
        }
    ),
    "ma_cross_v1.0": ParameterSpace(
        {
            "fast_period": ParameterRange(3, 50, "int"),
            "slow_period": ParameterRange(20, 200, "int"),
            "signal_threshold": ParameterRange(0.01, 0.05, "float"),
        }
    ),
}
