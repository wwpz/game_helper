from abc import ABC, abstractmethod


class GameAdapter(ABC):

    @abstractmethod
    def launcher_game(self) -> bool:
        """
        从启动模拟器后 ---- 到点击启动游戏icon为 launcher_simulator_game 部分
        :return: True or False
        """
        pass

    @abstractmethod
    def login_game(self) -> bool:
        """
        从启动游戏后 ---- 进到游戏内容首界面为 login_game 部分
        :return: True or False
        """
        pass

    @abstractmethod
    def execute_task(self, task_name: str) -> bool:
        # 执行指定任务
        pass
