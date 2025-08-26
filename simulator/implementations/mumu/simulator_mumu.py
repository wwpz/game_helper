import os
import re
import time
import win32gui
import subprocess
from lxml import etree
from log.log_factory import get_logger
from simulator.base.simulator_base import SimulatorBase
from simulator.manager.simulator_manager import SimulatorManager


class MuMuSimulator(SimulatorBase):
    """
    MuMu模拟器实现类
    """

    def __init__(self, window_name: str, window_class: str, simulator_path: str, simulator_type: str, port: int, account: str, icon: str):
        """
        初始化MuMu模拟器

        Args:
            window_name: 模拟器窗口名称
            window_class: 模拟器窗口类名
            simulator_path: 模拟器可执行文件路径
            port: 模拟器端口号
            account: 账号
            icon: 启动图标名称
        """
        self.page = 0
        self.count = 0
        self.icon = icon
        self.port = port
        self.window_name = window_name
        self.window_class = window_class
        self.game_package = "com.miHoYo.hkrpg"
        self.simulator_path = os.path.normpath(simulator_path)
        self.simulator = SimulatorManager.get_simulator_instance(port, account, simulator_type)
        self.logger = get_logger(self.__class__.__name__, port, account, simulator_type)
        self.xml_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "res", "xml", "window_dump.xml")

    def run(self) -> bool:
        result = False
        self.logger.hr("启动模拟器----开始", level=3)
        try:
            if self.is_running_simulator():
                self.logger.info("MuMu模拟器启动成功")
                if self.connect_simulator():
                    self.logger.info("成功连接到MuMu模拟器")
                    if self.check_init():
                        return self.launcher_simulator_game()
                else:
                    self.logger.error("连接到MuMu模拟器失败")
            else:
                self.logger.info(f"当前模拟器未启动,将启动模拟器...")
                if self.start_simulator():
                    self.logger.info("MuMu模拟器启动成功")
                    if self.connect_simulator():
                        self.logger.info("成功连接到MuMu模拟器")
                        if self.check_init():
                            return self.launcher_simulator_game()
                    else:
                        self.logger.error("连接到MuMu模拟器失败")
                else:
                    self.logger.error("MuMu模拟器启动失败")
        finally:
            self.logger.hr("启动模拟器----结束", level=3)
        return result

    def check_init(self) -> bool:
        self.logger.hr("模拟器检测流程----开始", level=3)
        if self.simulator.image.check_resolution_ratio(1920, 1080):
            return self._close_simulator_Ad()
        self.logger.hr("模拟器检测流程----结束", level=3)

    def start_simulator(self) -> bool:
        """
        启动MuMu模拟器

        Returns:
            bool: 启动成功返回True，否则返回False
        """
        try:
            self.logger.info("正在启动MuMu模拟器")

            # 检查模拟器路径是否存在
            if not os.path.exists(self.simulator_path):
                self.logger.error(f"模拟器路径不存在: {self.simulator_path}")
                return False
            # 获取游戏文件夹路径
            game_folder = os.path.dirname(self.simulator_path)
            # 启动模拟器
            process = subprocess.Popen(self.simulator_path, cwd=game_folder)
            # 等待一段时间确保模拟器启动
            time.sleep(20)
            # 再次检测是否启动
            result = self.is_running_simulator()
            return result
        except FileNotFoundError:
            self.logger.error("系统找不到cmd命令或模拟器路径配置错误")
            return False
        except Exception as e:
            self.logger.error(f"启动MuMu模拟器时发生错误: {e}")
            return False

    def stop_simulator(self) -> bool:
        """
        停止MuMu模拟器

        Returns:
            bool: 停止成功返回True，否则返回False
        """
        try:
            self.logger.info(f"正在停止MuMu模拟器: {self.window_name}")

            # 断开ADB连接
            self.logger.info("正在断开ADB连接...")
            disconnect_result = self.simulator.adb.disconnect(self.port)
            if disconnect_result:
                self.logger.info("ADB断开连接成功")
            else:
                self.logger.warning("ADB断开连接失败")

            # 通过ADB关闭模拟器
            cmd = ["adb", "kill-server"]
            subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            self.logger.info(f"MuMu模拟器停止成功: {self.window_name}")
            return True
        except Exception as e:
            self.logger.error(f"停止MuMu模拟器时发生错误: {e}")
            return False

    def is_running_simulator(self) -> bool:
        """
        检查MuMu模拟器是否运行中

        Returns:
            bool: 运行中返回True，否则返回False
        """
        try:
            self.logger.info("正在检查MuMu模拟器运行状态")
            # 通过窗口类名和窗口名称查找模拟器窗口
            hwnd = win32gui.FindWindow(self.window_class, self.window_name)
            return hwnd != 0
        except Exception as e:
            self.logger.error(f"检查模拟器运行状态时发生错误: {e}")
            return False

    def connect_simulator(self) -> bool:
        """
        连接到MuMu模拟器

        Returns:
            bool: 连接成功返回True，否则返回False
        """
        self.logger.info("正在连接到MuMu模拟器...")
        result = self.simulator.adb.connect(self.port)
        return result

    def disconnect_simulator(self) -> bool:
        """
        断开与MuMu模拟器的连接

        Returns:
            bool: 断开连接成功返回True，否则返回False
        """
        self.logger.info("正在断开与MuMu模拟器的连接...")
        try:
            result = self.simulator.adb.disconnect(self.port)
            if result:
                self.logger.info("成功断开与MuMu模拟器的连接")
            else:
                self.logger.error("断开与MuMu模拟器的连接失败")
            return result
        except Exception as e:
            self.logger.error(f"断开与MuMu模拟器连接时发生错误: {e}")
            return False

    def launcher_simulator_game(self):
        self.logger.hr("启动游戏----开始", level=3)
        # TODO 关闭游戏前需判断在能识别的首页时则不进行关闭应用,直接返回成功
        if self.simulator.adb.close_simulator_game(self.game_package):
            self._refresh_screen()
        # 首次尝试直接定位
        if self._try_launch():
            return True
        # 计算滑动策略
        self.logger.debug(f"开始循环滑动查找，最大尝试次数: {self.page}")
        for attempt in range(1, self.page + 1):
            # 动态判断滑动方向
            if self.count > 1:
                # 优先向左滑动查找
                self.simulator.adb.swipe_left() if attempt % 2 == 1 else self.simulator.adb.swipe_right()
            else:
                # 从首页直接向右滑动
                self.simulator.adb.swipe_right()
            self._refresh_screen()
            if self._try_launch():
                return True
        self.logger.hr("启动游戏----结束", level=3)
        return False

    def _refresh_screen(self):
        self.logger.info("刷新当前模拟器屏幕数据...")
        if self._get_simulator_screen_info():
            self.logger.info("屏幕数据已刷新")

    def _try_launch(self):
        self.logger.info("正在尝试定位并启动游戏...")
        bounds = self.simulator.image.get_simulator_ui_bounds(self.icon)
        if bounds is not None:
            self.logger.debug(f"已定位游戏图标坐标: {bounds}")
            self.simulator.adb.click(bounds[0], bounds[1])
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

    def _close_simulator_Ad(self) -> bool:
        """
        关闭模拟器启动后的广告
        通过端口号和账号来区分不同实例，避免文件名冲突
        """
        self.logger.info("正在检测启动模拟器后的广告 -X-")

        bounds = self.simulator.image.get_simulator_ui_bounds("com.mumu.launcher:id/close", "resource-id")
        if bounds is not None:
            self.simulator.adb.click(bounds[0], bounds[1])
            self.logger.info("成功关闭启动模拟器后的广告")
            return True
        else:
            self.logger.info("未找到启动模拟器后的广告")
            return True
