import os
import importlib.util
import threading
from typing import Dict, List, Optional, Type, Any
from .plugin_base import PluginBase


class PluginManager:
    """插件管理器，负责插件的加载、管理和执行"""

    def __init__(self, adapter):
        self.adapter = adapter
        self.log = adapter.log
        self._plugins: Dict[str, PluginBase] = {}
        self._lock = threading.Lock()
        self._loaded_modules = set()

    def load_plugins(self, plugin_paths: List[str] = None) -> None:
        """
        加载插件

        Args:
            plugin_paths: 插件路径列表，如果为None则加载默认路径下的所有插件
        """
        if plugin_paths is None:
            # 默认从 plugins 目录加载
            plugin_paths = ["plugins"]

        for path in plugin_paths:
            if os.path.isfile(path) and path.endswith('.py'):
                self._load_plugin_from_file(path)
            elif os.path.isdir(path):
                self._load_plugins_from_directory(path)

    def _load_plugins_from_directory(self, directory: str) -> None:
        """从目录加载插件"""
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('_plugin.py'):
                    file_path = os.path.join(root, file)
                    self._load_plugin_from_file(file_path)

    def _load_plugin_from_file(self, file_path: str) -> None:
        """从文件加载插件"""
        try:
            # 检查是否已加载
            abs_path = os.path.abspath(file_path)
            if abs_path in self._loaded_modules:
                return

            # 动态导入模块
            spec = importlib.util.spec_from_file_location(
                f"plugin_{len(self._loaded_modules)}",
                file_path
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self._loaded_modules.add(abs_path)

            # 查找并实例化插件类
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and
                        issubclass(attr, PluginBase) and
                        attr != PluginBase):
                    self._register_plugin(attr)

        except Exception as e:
            self.log.error(f"加载插件文件 {file_path} 失败: {str(e)}")

    def _register_plugin(self, plugin_class: Type[PluginBase]) -> None:
        """注册插件类"""
        try:
            plugin_instance = plugin_class(self.adapter)
            plugin_name = plugin_instance.name

            with self._lock:
                if plugin_name in self._plugins:
                    self.log.warning(f"插件 {plugin_name} 已存在，将被覆盖")

                # 初始化插件
                plugin_instance.setup()
                self._plugins[plugin_name] = plugin_instance
                self.log.info(f"插件 {plugin_name} 注册成功")

        except Exception as e:
            self.log.error(f"注册插件 {plugin_class.__name__} 失败: {str(e)}")

    def get_plugin(self, name: str) -> Optional[PluginBase]:
        """
        获取插件实例

        Args:
            name: 插件名称

        Returns:
            PluginBase: 插件实例，如果不存在返回None
        """
        return self._plugins.get(name)

    def list_plugins(self) -> List[Dict[str, str]]:
        """
        列出所有插件信息

        Returns:
            List[Dict[str, str]]: 插件信息列表
        """
        with self._lock:
            return [
                {
                    "name": plugin.name,
                    "description": plugin.description,
                    "version": plugin.version,
                    "priority": str(plugin.priority)
                }
                for plugin in sorted(self._plugins.values(), key=lambda p: p.priority)
            ]

    def execute_plugin(self, name: str, **kwargs) -> Any:
        """
        执行插件

        Args:
            name: 插件名称
            **kwargs: 执行参数

        Returns:
            执行结果

        Raises:
            ValueError: 插件不存在或无法执行
        """
        plugin = self.get_plugin(name)
        if not plugin:
            raise ValueError(f"插件 {name} 不存在")

        if not plugin.can_execute(**kwargs):
            raise ValueError(f"插件 {name} 当前无法执行")

        try:
            self.log.info(f"开始执行插件: {name}")
            result = plugin.execute(**kwargs)
            self.log.info(f"插件 {name} 执行完成")
            return result
        except Exception as e:
            self.log.error(f"执行插件 {name} 时发生错误: {str(e)}")
            raise

    def execute_plugins_by_priority(self, plugin_names: List[str], **kwargs) -> Dict[str, Any]:
        """
        按优先级顺序执行多个插件

        Args:
            plugin_names: 插件名称列表
            **kwargs: 执行参数

        Returns:
            Dict[str, Any]: 各插件执行结果
        """
        # 获取并排序插件
        plugins_to_execute = []
        for name in plugin_names:
            plugin = self.get_plugin(name)
            if plugin:
                plugins_to_execute.append(plugin)

        plugins_to_execute.sort(key=lambda p: p.priority)

        # 依次执行
        results = {}
        for plugin in plugins_to_execute:
            try:
                results[plugin.name] = self.execute_plugin(plugin.name, **kwargs)
            except Exception as e:
                self.log.error(f"执行插件 {plugin.name} 失败: {str(e)}")
                results[plugin.name] = {"error": str(e)}

        return results

    def unload_plugin(self, name: str) -> bool:
        """
        卸载插件

        Args:
            name: 插件名称

        Returns:
            bool: 是否卸载成功
        """
        with self._lock:
            if name in self._plugins:
                try:
                    # 执行清理
                    self._plugins[name].teardown()
                    del self._plugins[name]
                    self.log.info(f"插件 {name} 卸载成功")
                    return True
                except Exception as e:
                    self.log.error(f"卸载插件 {name} 时发生错误: {str(e)}")
                    return False
            else:
                self.log.warning(f"插件 {name} 不存在")
                return False

    def unload_all_plugins(self) -> None:
        """卸载所有插件"""
        with self._lock:
            plugin_names = list(self._plugins.keys())
            for name in plugin_names:
                self.unload_plugin(name)