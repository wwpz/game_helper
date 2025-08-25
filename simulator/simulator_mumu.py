import os
import time
import win32gui
import subprocess
from log.log_factory import get_logger
from simulator_models.adb.adb_controller import ADBController
from simulator_models.base.simulator_base import SimulatorBase
from simulator_models.image.image_controller import ImageController


class MuMuSimulator(SimulatorBase):
    """
    MuMu模拟器实现类
    """

    def __init__(self, window_name: str, window_class: str, simulator_path: str, simulator_type: str, port: int, account: str):
        """
        初始化MuMu模拟器

        Args:
            window_name: 模拟器窗口名称
            window_class: 模拟器窗口类名
            simulator_path: 模拟器可执行文件路径
            port: 模拟器端口号
            account: 账号
        """
        self.port = port
        self.xml_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "res", "xml", "window_dump.xml")
        self.window_name = window_name
        self.window_class = window_class
        self.simulator_path = os.path.normpath(simulator_path)
        self.adb = ADBController.get_instance(port, account, simulator_type)
        self.image = ImageController.get_instance(port, account, simulator_type)
        self.logger = get_logger(self.__class__.__name__, port, account, simulator_type)

    def run(self) -> bool:
        result = False
        self.logger.hr("启动模拟器----开始", level=3)
        try:
            if self.is_running_simulator():
                self.logger.info("MuMu模拟器启动成功")
                if self.connect_simulator():
                    self.logger.info("成功连接到MuMu模拟器")
                    if self.check_init():
                        result = True
                else:
                    self.logger.error("连接到MuMu模拟器失败")
            else:
                self.logger.info(f"当前模拟器未启动,将启动模拟器...")
                if self.start_simulator():
                    self.logger.info("MuMu模拟器启动成功")
                    if self.connect_simulator():
                        self.logger.info("成功连接到MuMu模拟器")
                        if self.check_init():
                            result = True
                    else:
                        self.logger.error("连接到MuMu模拟器失败")
                else:
                    self.logger.error("MuMu模拟器启动失败")
        finally:
            self.logger.hr("启动模拟器----结束", level=3)
        return result

    def check_init(self) -> bool:
        self.logger.hr("启动成功模拟器后的检测流程----开始", level=3)
        if self.image.check_resolution_ratio(1920, 1080):
            return self._close_simulator_Ad()
        self.logger.hr("启动成功模拟器后的检测流程----结束", level=3)

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
            disconnect_result = self.adb.disconnect(self.port)
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
        result = self.adb.connect(self.port)
        return result

    def disconnect_simulator(self) -> bool:
        """
        断开与MuMu模拟器的连接

        Returns:
            bool: 断开连接成功返回True，否则返回False
        """
        self.logger.info("正在断开与MuMu模拟器的连接...")
        try:
            result = self.adb.disconnect(self.port)
            if result:
                self.logger.info("成功断开与MuMu模拟器的连接")
            else:
                self.logger.error("断开与MuMu模拟器的连接失败")
            return result
        except Exception as e:
            self.logger.error(f"断开与MuMu模拟器连接时发生错误: {e}")
            return False

    def _close_simulator_Ad(self) -> bool:
        self.logger.info("正在检测启动模拟器后的广告 -X-")
        # 由于download_window_dump现在会生成带时间戳的唯一文件名，我们需要获取实际的文件名
        # 先提取基础路径和目录
        xml_dir = os.path.dirname(self.xml_path)
        base_name = os.path.splitext(os.path.basename(self.xml_path))[0]
        ext = os.path.splitext(self.xml_path)[1]
        
        # 调用下载方法，它会生成带时间戳的唯一文件
        if self.adb.download_window_dump(self.xml_path):
            # 查找最新生成的文件（基于时间戳）
            latest_file = None
            latest_time = 0
            
            # 列出目录中的所有匹配文件
            if os.path.exists(xml_dir):
                for file in os.listdir(xml_dir):
                    if file.startswith(base_name) and file.endswith(ext):
                        file_path = os.path.join(xml_dir, file)
                        file_time = os.path.getmtime(file_path)
                        if file_time > latest_time:
                            latest_time = file_time
                            latest_file = file_path
            
            # 使用最新生成的文件进行处理
            if latest_file:
                bounds = self.image.get_simulator_ui_bounds(latest_file, "com.mumu.launcher:id/close", "resource-id")
                if bounds is not None:
                    self.adb.click(bounds[0], bounds[1])
                    self.logger.info("成功关闭启动模拟器后的广告")
                    # 处理完后删除临时文件
                    os.remove(latest_file)
                else:
                    self.logger.info("未找到启动模拟器后的广告")
                    os.remove(latest_file)
                return True
            else:
                self.logger.warning("未找到下载的布局文件")
        else:
            self.logger.error("下载模拟器布局文件失败")
