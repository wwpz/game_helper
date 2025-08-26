from simulator.simulator_manager import SimulatorManager
from simulator_models.adapter.game_adapter import GameAdapter
from log.log_factory import get_logger


class StarRailAdapter(GameAdapter):
    def __init__(self, port: int, account: str, simulator_type: str):
        self.port = port
        self.account = account
        self.logger = get_logger(self.__class__.__name__, port, account, simulator_type)
        self.simulator = SimulatorManager.get_simulator_instance(port, account,simulator_type)
        self.logger.info("创建适配器实例: 适配器=%s, 账号=%s, 端口=%s, 模拟器=%s", self.__class__.__name__, self.account, self.port, simulator_type)

    def login_game(self):
        self.logger.hr("登录游戏----开始", level=3)


        self.logger.hr("登录游戏----结束", level=3)