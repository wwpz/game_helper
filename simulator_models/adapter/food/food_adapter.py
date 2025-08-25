from simulator_models.adapter.game_adapter import GameAdapter
from log.log_factory import get_logger


class FoodAdapter(GameAdapter):
    def __init__(self, port, icon, account):
        self.port = port
        self.icon = icon
        self.account = account
        self.log = get_logger("FoodAdapter", account)

        self.log.info("创建适配器实例: 适配器=%s, 账号=%s, 端口=%d", self.__class__.__name__, self.account, self.port)

    def launcher_simulator_game(self):
        self.log.info("正在执行launcher_game方法...")
        print('ok')
        self.log.info("launcher_game方法执行成功")

    def login_game(self):
        self.log.info("正在执行login方法...")
        print('ok')
        self.log.info("login方法执行成功")

    def execute_task(self, task_name):
        self.log.info(f"正在执行execute_task方法，任务名称: {task_name}...")
        print('ok')
        self.log.info(f"execute_task方法执行成功，任务名称: {task_name}")
