from abc import ABC, abstractmethod
from typing import Dict, Any
import threading
import time


class PluginBase(ABC):
    """插件基类，支持交互式错误处理"""

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
        self.error_handler = adapter.error_handler
        self._lock = threading.Lock()
        self._is_running = False
        self._is_paused = False

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

    @property
    def category(self) -> str:
        """插件分类"""
        return "general"

    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """执行插件功能"""
        pass

    def can_execute(self, **kwargs) -> bool:
        """检查插件是否可以执行"""
        try:
            simulator = self.adapter.get_simulator()
            return simulator is not None
        except:
            return False

    def setup(self) -> None:
        """插件初始化，在加载时调用"""
        self.log.debug(f"插件 {self.name} 初始化")

    def teardown(self) -> None:
        """插件清理，在卸载时调用"""
        self.log.debug(f"插件 {self.name} 清理")
        pass

    def pause(self) -> None:
        """暂停插件执行"""
        with self._lock:
            self._is_paused = True
        self.log.info(f"插件 {self.name} 已暂停")

    def resume(self) -> None:
        """恢复插件执行"""
        with self._lock:
            self._is_paused = False
        self.log.info(f"插件 {self.name} 已恢复")

    def stop(self) -> None:
        """停止插件执行"""
        with self._lock:
            self._is_running = False
        self.log.info(f"插件 {self.name} 已停止")

    def is_running(self) -> bool:
        """检查插件是否正在运行"""
        with self._lock:
            return self._is_running

    def is_paused(self) -> bool:
        """检查插件是否已暂停"""
        with self._lock:
            return self._is_paused

    def wait_if_paused(self) -> None:
        """如果插件被暂停则等待"""
        while self.is_paused() and self.is_running():
            time.sleep(0.1)

    def execute_with_error_handling(self, **kwargs) -> Dict[str, Any]:
        """带错误处理的插件执行"""
        try:
            self.log.info(f"开始执行插件: {self.name}")

            with self._lock:
                self._is_running = True

            # 执行插件逻辑
            result = self.execute(**kwargs)

            self.log.info(f"插件 {self.name} 执行完成")
            return result

        except Exception as e:
            self.log.error(f"执行插件 {self.name} 时发生错误: {str(e)}")

            # 使用交互式错误处理器处理错误
            resolution = self.error_handler.handle_error(
                plugin_name=self.name,
                error_message=str(e),
                error_details={
                    "account": self.account,
                    "plugin": self.name,
                    "category": self.category
                }
            )

            # 根据用户选择返回相应结果
            if resolution == "resolved":
                # 用户已解决问题，返回成功结果
                self.log.info(f"用户已解决 {self.name} 插件的问题，继续执行")
                return {
                    "status": "success",
                    "plugin": self.name,
                    "account": self.account,
                    "user_resolved": True
                }
            elif resolution == "retry":
                # 用户选择重试
                self.log.info(f"用户选择重试 {self.name} 插件")
                return self.execute_with_error_handling(**kwargs)
            elif resolution == "skip":
                # 用户选择跳过
                self.log.info(f"用户选择跳过 {self.name} 插件")
                return {
                    "status": "skipped",
                    "plugin": self.name,
                    "account": self.account,
                    "skipped": True
                }
            elif resolution == "stop":
                # 用户选择停止
                self.log.info(f"用户选择停止所有任务")
                raise Exception(f"用户手动停止任务: {self.name}")
            else:
                # 默认返回错误
                return {
                    "status": "error",
                    "plugin": self.name,
                    "account": self.account,
                    "error": str(e)
                }
        finally:
            with self._lock:
                self._is_running = False
