import os
import threading
import traceback
import xml.etree.ElementTree as ET

from log.log_factory import get_logger
from simulator_models.adb.adb_controller import ADBController


class ImageController:
    """图片处理控制器，线程安全"""

    _instances = {}
    _lock = threading.Lock()

    def __init__(self, port: int, account: str, simulator_type: str):
        self.port = port
        self.account = account
        self._connection_lock = threading.Lock()
        self.adb = ADBController.get_instance(port, account, simulator_type)
        self.logger = get_logger(self.__class__.__name__, port, account, simulator_type)
        self.xml_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "res", "xml", "window_dump.xml")

    @classmethod
    def get_instance(cls, port: int, account: str, simulator_type: str):
        """获取image控制器实例（单例模式）"""
        key = f"{port}:{account}"
        with cls._lock:
            if key not in cls._instances:
                cls._instances[key] = cls(port, account, simulator_type)
            return cls._instances[key]
    def get_simulator_ui_bounds(self, search_value, search_by='text'):
        """
        根据指定属性获取UI元素的bounds坐标
        参数：
        search_value: 要匹配的属性值
        search_by: 搜索属性类型（默认text，可选resource-id/class等）
        """
        try:
            # 使用端口号和账号构建唯一文件名，避免多实例冲突
            xml_dir = os.path.dirname(self.xml_path)
            base_name = os.path.splitext(os.path.basename(self.xml_path))[0]
            ext = os.path.splitext(self.xml_path)[1]

            # 构建基于端口和账号的唯一文件名
            unique_filename = f"{base_name}_{self.port}_{self.account}{ext}"
            unique_xml_path = os.path.join(xml_dir, unique_filename)

            # 确保目标目录存在
            if not os.path.exists(xml_dir):
                os.makedirs(xml_dir)

            # 下载XML文件
            if not self.adb.download_window_dump(unique_xml_path):
                self.logger.error("下载模拟器布局文件失败")
                return None
            else:
                self.logger.info(f"正在获取模拟器布局文件{search_by}='{search_value}'的节点")
                # 解析指定路径的 XML 文件
                tree = ET.parse(unique_xml_path)
                root = tree.getroot()
                # 遍历所有节点
                for node in root.findall('.//node'):
                    current_value = node.get(search_by)
                    if current_value and current_value == search_value:
                        bounds = node.get('bounds')
                        if bounds:
                            # 解析 bounds 字符串获取坐标
                            left, top, right, bottom = map(int, bounds.replace("[", "").replace("]", ",").split(",")[:-1])
                            # 计算中心点坐标
                            center_x = (left + right) // 2
                            center_y = (top + bottom) // 2
                            self.logger.debug(f"{search_by}='{search_value}'的节点坐标为: ({center_x}, {center_y})")
                            return center_x, center_y
                self.logger.debug(f"未找到{search_by}='{search_value}'的节点")
                # 删除临时文件
                try:
                    os.remove(unique_xml_path)
                except Exception as e:
                    self.logger.warning(f"删除临时文件失败: {e}")
                return None
        except FileNotFoundError:
            self.logger.error("错误: 确保XML路径存在")
        except Exception as e:
            self.logger.error(f"运行根据指定属性获取UI元素的bounds坐标异常: {str(e)}")
            traceback.format_exc()
            return None
    def check_resolution_ratio(self, target_width: int, target_height: int) -> bool:
        """检查分辨率"""
        self.logger.info("进入分辨率检测")
        # 获取当前逻辑分辨率
        resolution = self.adb.get_current_display_resolution()
        if not resolution:
            raise Exception("模拟器分辨率获取失败")
        current_width, current_height = resolution
        # 计算目标比例（强制使用横屏比例标准）
        target_ratio = max(target_width, target_height) / min(target_width, target_height)
        current_ratio = max(current_width, current_height) / min(current_width, current_height)
        # 检查分辨率绝对值
        if (current_width < target_width and current_height < target_height) or \
                (current_width < target_height and current_height < target_width):  # 兼容竖屏目标
            self.logger.error(
                f"当前分辨率 {current_width}x{current_height} 小于目标 {target_width}x{target_height}\n"
                "请调整模拟器分辨率至推荐值")
        # 检查比例容错（1% 误差）
        elif abs(current_ratio - target_ratio) > 0.01:
            self.logger.error(
                f"屏幕比例异常 当前 {current_width}x{current_height} (≈{current_ratio:.2f}:1)\n"
                f"需要接近 {target_ratio:.2f}:1 (基于 {target_width}x{target_height})")
        # 宽高顺序不匹配时的警告（如竖屏模式符合比例但方向不符）
        elif (current_width < current_height) != (target_width < target_height):
            self.logger.warning(
                f"方向不匹配 当前 {current_width}x{current_height} (竖屏)\n"
                f"需使用横屏 {max(target_width, target_height)}x{min(target_width, target_height)}")
        else:
            self.logger.debug(f"分辨率验证通过: {current_width}x{current_height}")
            return True