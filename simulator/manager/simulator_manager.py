import threading
from typing import Dict

from simulator.manager.simulator_instance import SimulatorInstance


class SimulatorManager:
    """模拟器实例管理器，线程安全"""

    _instances: Dict[str, 'SimulatorInstance'] = {}
    _lock = threading.Lock()

    @classmethod
    def get_simulator_instance(cls, port: int, account: str, simulator_type: str) -> 'SimulatorInstance':
        """获取模拟器实例"""
        thread_id = threading.get_ident()
        key = f"{port}_{thread_id}_{account}"

        with cls._lock:
            if key not in cls._instances:
                cls._instances[key] = SimulatorInstance(port, account, simulator_type)
            return cls._instances[key]

    @classmethod
    def release_simulator_instance(cls, port: int, account: str = ""):
        """释放模拟器实例"""
        thread_id = threading.get_ident()
        key = f"{port}_{thread_id}_{account}"

        with cls._lock:
            if key in cls._instances:
                # 清理资源
                cls._instances[key].cleanup()
                del cls._instances[key]
