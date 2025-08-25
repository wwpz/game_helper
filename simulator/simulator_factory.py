from typing import Dict, Type
from simulator_models.base.simulator_base import SimulatorBase
from simulator.simulator_mumu import MuMuSimulator


class SimulatorFactory:
    """
    模拟器工厂类
    用于根据配置创建不同类型的模拟器实例
    """

    # 注册支持的模拟器类型
    _simulator_types: Dict[str, Type[SimulatorBase]] = {
        "mumu": MuMuSimulator
    }

    @classmethod
    def register_simulator_type(cls, name: str, simulator_class: Type[SimulatorBase]):
        """
        注册新的模拟器类型
        
        Args:
            name: 模拟器类型名称
            simulator_class: 模拟器类
        """
        cls._simulator_types[name] = simulator_class

    @classmethod
    def create_simulator(cls, create_simulator_type: str, **kwargs) -> SimulatorBase:
        """
        创建模拟器实例
        
        Args:
            create_simulator_type: 模拟器类型名称
            **kwargs: 传递给模拟器构造函数的参数
            
        Returns:
            SimulatorBase: 模拟器实例
            
        Raises:
            ValueError: 不支持的模拟器类型
        """
        if create_simulator_type not in cls._simulator_types:
            raise ValueError(f"不支持的模拟器类型: {create_simulator_type}")

        simulator_class = cls._simulator_types[create_simulator_type]
        return simulator_class(**kwargs)

    @classmethod
    def get_supported_types(cls) -> list:
        """
        获取支持的模拟器类型列表
        
        Returns:
            list: 支持的模拟器类型列表
        """
        return list(cls._simulator_types.keys())
