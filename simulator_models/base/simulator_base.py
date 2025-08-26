from abc import ABC, abstractmethod


class SimulatorBase(ABC):
    """模拟器基类"""

    @abstractmethod
    def run(self) -> bool:
        """
        (检测、启动、连接)
        """
        pass

    def check_init(self) -> bool:
        """模拟器启动后需要检查初始化的一些操作"""
        pass

    @abstractmethod
    def start_simulator(self) -> bool:
        """启动模拟器"""
        pass

    @abstractmethod
    def stop_simulator(self) -> bool:
        """停止模拟器"""
        pass

    @abstractmethod
    def is_running_simulator(self) -> bool:
        """检查模拟器是否运行中"""
        pass

    @abstractmethod
    def connect_simulator(self) -> bool:
        """连接到模拟器"""
        pass

    @abstractmethod
    def disconnect_simulator(self) -> bool:
        """断开连接"""
        pass

    @abstractmethod
    def launcher_simulator_game(self) -> bool:
        """
        从启动模拟器后 ---- 到点击启动游戏icon为 launcher_simulator_game 部分
        :return: True or False
        """
        pass