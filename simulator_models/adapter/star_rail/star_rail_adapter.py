import os
import re
from lxml import etree
from simulator_models.adapter.game_adapter import GameAdapter
from log.log_factory import get_logger
from simulator_models.adb.adb_controller import ADBController
from simulator_models.image.image_controller import ImageController


class StarRailAdapter(GameAdapter):
    def __init__(self, port: int, account: str, simulator_type: str, icon: str):
        self.icon = icon
        self.port = port
        self.page = 0
        self.count = 0
        self.game_package = "com.miHoYo.hkrpg"
        self.account = account
        self.adb = ADBController.get_instance(port, account, simulator_type)
        self.image = ImageController.get_instance(port, account, simulator_type)
        self.logger = get_logger(self.__class__.__name__, port, account, simulator_type)
        self.xml_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "res", "xml", "window_dump.xml")
        self.logger.info("创建适配器实例: 适配器=%s, 账号=%s, 端口=%s, 模拟器=%s", self.__class__.__name__, self.account, self.port, simulator_type)

    def launcher_game(self):
        self.logger.hr("启动游戏----开始", level=3)
        # TODO 关闭游戏前需判断在能识别的首页时则不进行关闭应用,直接返回成功
        if self.adb.close_simulator_game(self.game_package):
            self._refresh_screen()
        # 首次尝试直接定位
        if self._try_launch():
            return True


        self.logger.hr("启动游戏----结束", level=3)

    def login_game(self):
        self.logger.hr("登录游戏----开始", level=3)

        self.logger.hr("登录游戏----结束", level=3)

    def execute_task(self, task_name):
        self.logger.info(f"正在执行execute_task方法，任务名称: {task_name}...")
        self.logger.info(f"execute_task方法执行成功，任务名称: {task_name}")

    def _refresh_screen(self):
        self.logger.info("刷新当前模拟器屏幕数据...")
        if self._get_simulator_screen_info():
            self.logger.info("屏幕数据已刷新")

    def _try_launch(self):
        self.logger.info("正在尝试定位并启动游戏...")
        bounds = self.image.get_simulator_ui_bounds(self.icon)
        if bounds is not None:
            self.logger.debug(f"已定位游戏图标坐标: {bounds}")
            self.adb.click(bounds[0], bounds[1])
            return True
        else:
            self.logger.debug("当前屏幕未检测到游戏图标")
            return False



    def _get_simulator_screen_info(self):
        """
        获取模拟器当前屏幕信息（当前屏号和总屏数）

        Returns:
            str: 格式化的屏幕信息字符串，如"当前所在屏幕：第1屏，共2屏"
            None: 解析失败时返回None
        """
        try:
            self.logger.info("正在解析当前模拟器屏幕数据...")
            tree = etree.parse(self.xml_path)
            root = tree.getroot()

            # 定位页面指示器节点
            target_nodes = root.xpath('//node[@resource-id="com.mumu.launcher:id/page_indicator"]')
            if not target_nodes:
                self.logger.error("未找到页面指示器节点")
                return False

            content_desc = target_nodes[0].get("content-desc", "")
            if not content_desc:
                self.logger.error("content-desc 属性为空")
                return False

            # 提取关键信息
            parts = content_desc.split("：")
            if len(parts) < 2:
                self.logger.error("content-desc 格式不符合预期")
                return False

            screen_info = parts[1].split(",")[0].strip()  # "第1屏，共2屏"

            # 正则提取当前屏和总屏数
            match = re.search(r'第(\d+)屏，共(\d+)屏', screen_info)
            if not match:
                self.logger.error("无法解析屏幕信息")
                return False
            else:
                # 赋值给实例变量
                self.count = int(match.group(1))  # 当前所在屏
                self.page = int(match.group(2))  # 总屏数
                # 保持原有返回格式
                self.logger.info("解析成功...")
                formatted_result = f"当前所在屏幕：{screen_info}"
                self.logger.info(formatted_result)
                return True
        except Exception as e:
            self.logger.debug(f"解析异常: {str(e)}")
            return False