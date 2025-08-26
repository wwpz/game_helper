from abc import ABC, abstractmethod


class GameAdapter(ABC):

    @abstractmethod
    def login_game(self) -> bool:
        """
        从启动游戏后 ---- 进到游戏内容首界面为 login_game 部分
        :return: True or False
        """
        pass
