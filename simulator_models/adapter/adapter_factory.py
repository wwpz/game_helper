from typing import Dict, Type
from simulator_models.adapter.game_adapter import GameAdapter
from simulator_models.adapter.star_rail.star_rail_adapter import StarRailAdapter
from simulator_models.adapter.food.food_adapter import FoodAdapter


class AdapterFactory:
    """游戏适配器工厂类"""

    # 注册支持的适配器类型
    _adapter_types: Dict[str, Type[GameAdapter]] = {
        "star_rail": StarRailAdapter,
        "food": FoodAdapter
    }

    @classmethod
    def register_adapter_type(cls, name: str, adapter_class: Type[GameAdapter]):
        """注册新的适配器类型"""
        cls._adapter_types[name] = adapter_class

    @classmethod
    def create_adapter(cls, adapter_type: str, **kwargs) -> GameAdapter:
        """创建适配器实例"""
        if adapter_type not in cls._adapter_types:
            raise ValueError(f"不支持的适配器类型: {adapter_type}")

        adapter_class = cls._adapter_types[adapter_type]
        return adapter_class(**kwargs)

    @classmethod
    def get_supported_types(cls) -> list:
        """获取支持的适配器类型列表"""
        return list(cls._adapter_types.keys())