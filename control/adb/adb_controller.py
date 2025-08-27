import random
import re
import subprocess
import threading
import time
import os

from log.log_factory import get_logger


class ADBController:
    """ADB控制器，线程安全"""

    _instances = {}
    _lock = threading.Lock()

    def __init__(self, port: int, account: str, simulator_type: str, host: str = "127.0.0.1"):
        self.host = host
        self.port = port
        self._connection_lock = threading.Lock()
        self.logger = get_logger(self.__class__.__name__, port, account, simulator_type)

    @classmethod
    def get_instance(cls, port: int, account: str, simulator_type: str, host: str = "127.0.0.1"):
        """获取ADB控制器实例（单例模式）"""
        key = f"{host}:{port}"
        with cls._lock:
            if key not in cls._instances:
                cls._instances[key] = cls(port, account, simulator_type, host)
            return cls._instances[key]

    def connect(self, port) -> bool:
        """连接到模拟器"""
        with self._connection_lock:
            # 构建完整连接命令（便于异常时排查）
            connect_cmd = f"{self.host}:{port}"
            adb_cmd = ["adb", "connect", connect_cmd]

            try:
                self.logger.info(f"正在尝试连接到模拟器: {connect_cmd}")
                self.logger.debug(f"执行ADB命令: {' '.join(adb_cmd)}")  # 打印完整命令

                # 执行ADB命令
                result = subprocess.run(
                    adb_cmd,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    encoding='utf-8',
                    errors='ignore'
                )

                # 处理命令输出（区分不同情况）
                stdout = result.stdout.strip() if result.stdout else "无输出"

                # 判断连接结果
                if "connected" in stdout.lower() or "already" in stdout.lower():
                    self.logger.info(f"成功连接到模拟器: {connect_cmd}")
                    return True
                else:
                    self.logger.error(
                        f"连接模拟器失败: 命令返回非预期结果\n"
                        f"返回码: {result.returncode}\n"
                        f"输出信息: {stdout}"
                    )
                    return False

            except FileNotFoundError:
                # 专门处理ADB文件找不到的错误（最常见问题）
                self.logger.error(
                    f"连接模拟器失败: 未找到ADB工具\n"
                    f"请检查ADB是否已安装并配置到环境变量，或在代码中指定正确路径\n"
                    f"执行的命令: {' '.join(adb_cmd)}"
                )
                return False

            except subprocess.TimeoutExpired:
                # 超时错误单独处理
                self.logger.error(
                    f"连接模拟器超时: 命令执行超过{10}秒未响应\n"
                    f"目标地址: {connect_cmd}\n"
                    f"执行的命令: {' '.join(adb_cmd)}"
                )
                return False

            except PermissionError:
                # 权限错误（如无执行ADB的权限）
                self.logger.error(
                    f"连接模拟器失败: 没有执行ADB命令的权限\n"
                    f"请检查ADB文件权限或尝试以管理员身份运行\n"
                    f"执行的命令: {' '.join(adb_cmd)}"
                )
                return False

            except Exception as e:
                # 其他未知异常
                self.logger.error(
                    f"连接模拟器时发生未知异常\n"
                    f"目标地址: {connect_cmd}\n"
                    f"执行的命令: {' '.join(adb_cmd)}\n"
                    f"异常类型: {type(e).__name__}\n"
                    f"异常信息: {str(e)}"
                )
                return False

    def disconnect(self, port: int) -> bool:
        """断开模拟器"""
        try:
            self.logger.info(f"正在尝试断开模拟器 地址:{self.host} 端口: {self.port}...")
            cmd = ["adb", "disconnect", f"{self.host}:{port}"]
            subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return True
        except Exception as e:
            self.logger.error(f"断开模拟器失败: {str(e)}")
            return False

    def get_current_display_resolution(self) -> tuple[int, int] | None:
        """通过 dumpsys 获取当前界面实际分辨率（自动适应旋转）"""
        try:
            result = subprocess.run(
                ["adb", "shell", "dumpsys", "window", "displays"],
                capture_output=True, text=True, check=True, timeout=5
            )
            # 解析类似 cur=1080x1920 的当前分辨率
            match = re.search(r"cur=(\d+)x(\d+)", result.stdout)
            if not match:
                raise ValueError("未找到当前分辨率")
            return int(match[1]), int(match[2])  # (width, height)
        except Exception as e:
            self.logger.error(f"获取当前分辨率失败: {str(e)}")
            return None

    def download_window_dump(self, xml_path):
        """
        下载模拟器的UI布局文件(window_dump.xml)
        
        Args:
            xml_path (str): 保存XML文件的路径
            
        Returns:
            bool: 下载是否成功
        """
        try:
            self.logger.info(f"正在尝试下载模拟器布局文件...")
            # 确保目标路径的目录存在
            xml_dir = os.path.dirname(xml_path)
            if xml_dir and not os.path.exists(xml_dir):
                os.makedirs(xml_dir)
                
            # 执行 uiautomator dump 命令获取 UI 布局信息，捕获标准输出和错误输出并忽略
            subprocess.run(["adb", "shell", "uiautomator", "dump", "/sdcard/window_dump.xml"],
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL,
                           check=True)
            # 将布局文件从设备复制到本地，捕获标准输出和错误输出并忽略
            subprocess.run(["adb", "pull", "/sdcard/window_dump.xml", xml_path],
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL,
                           check=True)
            self.logger.info(f"下载模拟器布局文件成功: {xml_path}")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"错误: 命令执行失败: {e}")
            return False
        except FileNotFoundError:
            self.logger.error("错误: 未找到 adb 命令，请确认 adb 已安装并添加到环境变量")
            return False
        except Exception as e:
            self.logger.error(f"未知错误: {str(e)}")
            return False

    def click(
            self,
            base_x: float,
            base_y: float,
            max_offset: int = 10,
            min_delay: float = 0.1,
            max_delay: float = 0.5,
            before_sleep: bool = False,
            after_sleep: bool = True,
            before_sleep_delay: int = 2,
            after_sleep_delay: int = 2,
    ) -> bool:
        """
        增强版模拟点击（带随机扰动和防护机制）

        :param base_x: 基准X坐标
        :param base_y: 基准Y坐标
        :param max_offset: 最大随机偏移量（默认10像素）
        :param min_delay: 最小延迟秒数（默认0.1）
        :param max_delay: 最大延迟秒数（默认0.5）
        :param before_sleep: 在执行程序之前等待
        :param after_sleep: 在执行程序之后等待
        :param before_sleep_delay: 在执行程序之前等待秒数（默认2秒）
        :param after_sleep_delay: 在执行程序之后等待（默认2秒）
        :return: 操作是否成功
        """
        try:
            if before_sleep:
                time.sleep(before_sleep_delay)
            # ==================== 随机延迟 ====================
            delay_seconds = random.uniform(min_delay, max_delay)
            time.sleep(delay_seconds)

            # ==================== 坐标扰动 ====================
            offset_x = random.randint(-max_offset, max_offset)
            offset_y = random.randint(-max_offset, max_offset)

            actual_x = base_x + offset_x
            actual_y = base_y + offset_y

            # 记录坐标调整信息
            coord_info = {
                "original": (base_x, base_y),
                "offset": (offset_x, offset_y),
                "final": (actual_x, actual_y)
            }

            # ==================== 执行点击 ====================
            subprocess.run(
                ["adb", "shell", "input", "tap",
                 str(actual_x), str(actual_y)],
                check=True,
                timeout=5,
                capture_output=True
            )

            # ==================== 日志记录 ====================
            self.logger.debug(
                "点击操作成功 | "
                f"延迟: {delay_seconds:.2f}s | "
                f"基准坐标: {base_x},{base_y} | "
                f"最终坐标: {actual_x},{actual_y} | "
                f"坐标演变: {coord_info}"
            )
            if after_sleep:
                time.sleep(after_sleep_delay)
            return True

        except subprocess.TimeoutExpired:
            self.logger.error("ADB命令执行超时，建议检查设备连接")
        except subprocess.CalledProcessError as e:
            self.logger.error(
                f"ADB命令执行失败 [状态码:{e.returncode}]\n"
                f"错误输出: {e.stderr.decode().strip()}"
            )
        except Exception as e:
            self.logger.error(f"点击发生异常: {str(e)}")
        return False

    def swipe(
            self,
            base_x1: int,
            base_y1: int,
            base_x2: int,
            base_y2: int,
            duration: int = 900,
            max_offset: int = 5,
            min_delay: float = 0.1,
            max_delay: float = 0.5
    ) -> bool:
        """
        增强版模拟滑动（带随机扰动和防护机制）

        :param base_x1: 起点基准X坐标
        :param base_y1: 起点基准Y坐标
        :param base_x2: 终点基准X坐标
        :param base_y2: 终点基准Y坐标
        :param duration: 滑动持续时间（毫秒，默认900ms）
        :param max_offset: 最大随机偏移量（默认5像素）
        :param min_delay: 最小延迟秒数（默认0.1）
        :param max_delay: 最大延迟秒数（默认0.5）
        :return: 操作是否成功
        """
        try:
            # ==================== 随机延迟 ====================
            delay_seconds = random.uniform(min_delay, max_delay)
            time.sleep(delay_seconds)

            # ==================== 坐标扰动 ====================
            offset_x1 = random.randint(-max_offset, max_offset)
            offset_y1 = random.randint(-max_offset, max_offset)
            offset_x2 = random.randint(-max_offset, max_offset)
            offset_y2 = random.randint(-max_offset, max_offset)

            actual_x1 = base_x1 + offset_x1
            actual_y1 = base_y1 + offset_y1
            actual_x2 = base_x2 + offset_x2
            actual_y2 = base_y2 + offset_y2

            # 记录坐标调整信息
            coord_info = {
                "original_start": (base_x1, base_y1),
                "original_end": (base_x2, base_y2),
                "offset_start": (offset_x1, offset_y1),
                "offset_end": (offset_x2, offset_y2),
                "final_start": (actual_x1, actual_y1),
                "final_end": (actual_x2, actual_y2)
            }

            # ==================== 执行滑动 ====================
            subprocess.run(
                ["adb", "shell", "input", "swipe",
                 str(actual_x1), str(actual_y1),
                 str(actual_x2), str(actual_y2),
                 str(duration)],
                check=True,
                timeout=5,
                capture_output=True
            )

            # ==================== 日志记录 ====================
            self.logger.debug(
                "滑动操作成功 | "
                f"延迟: {delay_seconds:.2f}s | "
                f"基准坐标: ({base_x1},{base_y1})→({base_x2},{base_y2}) | "
                f"最终坐标: ({actual_x1},{actual_y1})→({actual_x2},{actual_y2}) | "
                f"持续时间: {duration}ms | "
                f"坐标演变: {coord_info}"
            )
            return True

        except subprocess.TimeoutExpired:
            self.logger.error("ADB命令执行超时，建议检查设备连接")
        except subprocess.CalledProcessError as e:
            self.logger.error(
                f"ADB命令执行失败 [状态码:{e.returncode}]\n"
                f"错误输出: {e.stderr.decode().strip()}"
            )
        except Exception as e:
            self.logger.error(f"发生未预期的异常 {e}")
        return False

    def close_simulator_game(self, package_name) -> bool:
        """
        通过ADB命令强制停止指定包名的应用程序
        Args:
            package_name (str): 要关闭的应用程序包名
        Returns:
            bool: 关闭操作是否成功
                True: 成功发送关闭命令
                False: 执行过程中出现异常
        """
        import subprocess
        try:
            # 发送 ADB 关闭命令
            cmd = f"adb shell am force-stop {package_name}"
            subprocess.run(cmd, shell=True, check=True)
            self.logger.info(f"将关闭应用,应用包名: {package_name}")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"关闭失败: {str(e)}")
            return False

    def swipe_left(self):
        """向左滑动（从右向左滑动手势）"""
        self.swipe(480, 540, 1440, 540)
        self.logger.debug("执行向左滑动")

    def swipe_right(self):
        """向右滑动（从左向右滑动手势）"""
        self.swipe(1440, 540, 480, 540)
        self.logger.debug("执行向右滑动")
