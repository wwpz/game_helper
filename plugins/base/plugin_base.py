from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class PluginBase(ABC):
    """插件基类，所有插件都需要继承此类"""

    def __init__(self, adapter):
        """
        初始化插件

        Args:
            adapter: 适配器实例，提供上下文信息和资源访问
        """
        self.adapter = adapter
        self.log = adapter.log
        self.account = adapter.account
        self.port = adapter.port

    @property
    @abstractmethod
    def name(self) -> str:
        """插件名称，必须唯一"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """插件描述"""
        pass

    @property
    def version(self) -> str:
        """插件版本"""
        return "1.0.0"

    @property
    def priority(self) -> int:
        """插件优先级，数值越小优先级越高"""
        return 100

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """
        执行插件功能

        Args:
            **kwargs: 执行参数

        Returns:
            执行结果
        """
        pass

    def can_execute(self, **kwargs) -> bool:
        """
        检查插件是否可以执行

        Args:
            **kwargs: 检查条件参数

        Returns:
            bool: 是否可以执行
        """
        return True

    def setup(self) -> None:
        """插件初始化，在加载时调用"""
        pass

    def teardown(self) -> None:
        """插件清理，在卸载时调用"""
        pass