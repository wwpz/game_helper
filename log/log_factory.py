import os
import logging
import unicodedata
import threading
from datetime import datetime
from typing import Literal, Dict
from logging.handlers import RotatingFileHandler
from log.coloredformatter import ColoredFormatter
from log.colorcodefilter import ColorCodeFilter


class LogFactory:
    """日志工厂类，负责创建和管理不同组件和账号的日志实例"""
    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._loggers: Dict[str, logging.Logger] = {}  # 存储日志器实例
        self._log_handlers: Dict[str, Dict[str, logging.Handler]] = {}  # 存储日志处理器
        self._config = {
            "log_format": "%(asctime)s | %(levelname)s | %(message)s",
            "title_log_format": "%(message)s",
            "max_bytes": 10 * 1024 * 1024,  # 10MB
            "backup_count": 5
        }

    def configure(self, **kwargs):
        """配置日志工厂"""
        with self._lock:
            self._config.update(kwargs)

    def get_logger(self, port: int, account: str, simulator_type: str, level: str) -> logging.Logger:
        """获取或创建日志器实例
        
        Args:
            port: 端口号
            account: 账号名称
            simulator_type: 模拟器类型
            level: 日志级别
        """
        logger_key = f"logger_{account}" if account else "logger_default"

        with self._lock:
            if logger_key not in self._loggers:
                # 创建日志器
                logger = logging.getLogger(logger_key)
                logger.propagate = False
                logger.setLevel(logging.DEBUG)

                # 确保日志目录存在
                self._ensure_log_directory_exists(simulator_type, port, account)

                # 添加控制台处理器
                console_handler = self._create_console_handler(level)
                logger.addHandler(console_handler)

                # 添加文件处理器
                file_handler = self._create_file_handler(simulator_type, port, account)
                logger.addHandler(file_handler)

                # 存储日志器和处理器
                self._loggers[logger_key] = logger
                self._log_handlers[logger_key] = {
                    "console": console_handler,
                    "file": file_handler
                }
            else:
                logger = self._loggers[logger_key]
                # 更新日志级别
                self._update_handler_levels(logger_key, level)

            return logger

    def get_title_logger(self, port: int, account: str, simulator_type: str, level: str) -> logging.Logger:
        """获取或创建标题日志器实例
        
        Args:
            port: 端口号
            account: 账号名称
            simulator_type: 模拟器类型
            level: 日志级别
        """
        title_logger_key = f"title_logger_{account}" if account else "title_logger_default"

        with self._lock:
            if title_logger_key not in self._loggers:
                # 创建标题日志器
                title_logger = logging.getLogger(title_logger_key)
                title_logger.propagate = False
                title_logger.setLevel(logging.DEBUG)

                # 确保日志目录存在
                self._ensure_log_directory_exists(simulator_type, port, account)

                # 添加控制台处理器
                console_handler = logging.StreamHandler()
                console_formatter = logging.Formatter(self._config["title_log_format"])
                console_handler.setFormatter(console_formatter)
                console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
                title_logger.addHandler(console_handler)

                # 添加文件处理器
                log_file_path = self._get_log_file_path(simulator_type, port, account)
                file_handler = RotatingFileHandler(
                    log_file_path,
                    encoding="utf-8",
                    maxBytes=self._config["max_bytes"],
                    backupCount=self._config["backup_count"]
                )
                file_formatter = logging.Formatter(self._config["title_log_format"])
                file_handler.setFormatter(file_formatter)
                file_handler.setLevel(logging.DEBUG)
                title_logger.addHandler(file_handler)

                # 存储日志器和处理器
                self._loggers[title_logger_key] = title_logger
                self._log_handlers[title_logger_key] = {
                    "console": console_handler,
                    "file": file_handler
                }
            else:
                title_logger = self._loggers[title_logger_key]
                # 更新日志级别
                self._update_handler_levels(title_logger_key, level)

            return title_logger

    def remove_logger(self, account: str) -> bool:
        """移除日志器实例"""
        logger_key = f"logger_{account}" if account else "logger_default"
        title_logger_key = f"title_logger_{account}" if account else "title_logger_default"

        with self._lock:
            removed = False

            # 移除普通日志器
            if logger_key in self._loggers:
                logger = self._loggers[logger_key]
                # 移除所有处理器
                for handler in list(logger.handlers):
                    handler.close()
                    logger.removeHandler(handler)
                del self._loggers[logger_key]
                if logger_key in self._log_handlers:
                    del self._log_handlers[logger_key]
                removed = True

            # 移除标题日志器
            if title_logger_key in self._loggers:
                title_logger = self._loggers[title_logger_key]
                # 移除所有处理器
                for handler in list(title_logger.handlers):
                    handler.close()
                    title_logger.removeHandler(handler)
                del self._loggers[title_logger_key]
                if title_logger_key in self._log_handlers:
                    del self._log_handlers[title_logger_key]
                removed = True

            return removed

    def _create_console_handler(self, level: str) -> logging.Handler:
        """创建控制台日志处理器"""
        console_handler = logging.StreamHandler()
        console_formatter = ColoredFormatter(self._config["log_format"])
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(getattr(logging, level.upper(), logging.DEBUG))
        return console_handler

    def _create_file_handler(self, simulator_type: str, port: int, account: str) -> logging.Handler:
        """创建文件日志处理器"""
        log_file_path = self._get_log_file_path(simulator_type, port, account)
        file_handler = RotatingFileHandler(
            log_file_path,
            encoding="utf-8",
            maxBytes=self._config["max_bytes"],
            backupCount=self._config["backup_count"]
        )
        file_formatter = ColorCodeFilter(self._config["log_format"])
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.DEBUG)
        return file_handler

    def _get_log_file_path(self, simulator_type: str, port: int, account: str) -> str:
        """获取日志文件路径，格式为 logs/日期/模拟器类型/端口号和账号.log"""
        current_date = datetime.now().strftime("%Y-%m-%d")
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))

        # 构建日志目录结构: logs/日期/模拟器类型/端口号和账号.log
        log_base_dir = os.path.join(project_root, "logs")
        date_dir = os.path.join(log_base_dir, current_date)

        # 如果提供了模拟器类型，则按模拟器类型组织目录
        if simulator_type:
            simulator_dir = os.path.join(date_dir, simulator_type)

            # 构建端口号和账号部分
            if port and account:
                file_name = f"{port}-{account}.log"
            elif port:
                file_name = f"{port}.log"
            elif account:
                file_name = f"{account}.log"
            else:
                file_name = "default.log"

            # 确保目录存在
            os.makedirs(simulator_dir, exist_ok=True)

            # 返回日志文件路径
            return os.path.join(simulator_dir, file_name)
        else:
            # 如果没有模拟器类型，使用默认结构
            default_dir = os.path.join(date_dir, "system")
            os.makedirs(default_dir, exist_ok=True)
            return os.path.join(default_dir, "system.log")

    def _ensure_log_directory_exists(self, simulator_type: str, port: int, account: str) -> None:
        """确保日志目录存在"""
        log_file_path = self._get_log_file_path(simulator_type, port, account)
        log_dir = os.path.dirname(log_file_path)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

    def _update_handler_levels(self, logger_key: str, level: str) -> None:
        """更新日志处理器的级别"""
        level_const = getattr(logging, level.upper(), logging.INFO)
        if logger_key in self._log_handlers:
            handlers = self._log_handlers[logger_key]
            if "console" in handlers:
                handlers["console"].setLevel(level_const)


class LogWrapper:
    """日志包装类，提供友好的日志接口"""

    def __init__(self, component_name: str, port: int, account: str, simulator_type: str, level: str):
        """初始化日志包装器
        
        Args:
            component_name: 组件名称（用于在日志中标识模块）
            account: 账号名称
            simulator_type: 模拟器类型
            port: 端口号
            level: 日志级别
        """
        self.component_name = component_name
        self.account = account
        self.simulator_type = simulator_type
        self.port = port
        self.log_factory = LogFactory()
        self.logger = self.log_factory.get_logger(port, account, simulator_type, level)
        self.title_logger = self.log_factory.get_title_logger(port, account, simulator_type, level)

    def info(self, format_str: str, *args):
        """记录信息日志"""
        message = f"[{self.component_name}] {format_str}"
        self.logger.info(message, *args)

    def debug(self, format_str: str, *args):
        """记录调试日志"""
        message = f"[{self.component_name}] {format_str}"
        self.logger.debug(message, *args)

    def warning(self, format_str: str, *args):
        """记录警告日志"""
        message = f"[{self.component_name}] {format_str}"
        self.logger.warning(message, *args)

    def error(self, format_str: str, *args):
        """记录错误日志"""
        message = f"[{self.component_name}] {format_str}"
        self.logger.error(message, *args)

    def critical(self, format_str: str, *args):
        """记录关键错误"""
        message = f"[{self.component_name}] {format_str}"
        self.logger.critical(message, *args)

    def hr(self, title: str, level: Literal[0, 1, 2, 3, 4] = 0, write: bool = True, style: str = 'default'):
        """格式化标题并打印或写入文件

        参数:
            title: 标题文本
            level: 标题级别(0-4)
            write: 是否写入日志
            style: 样式('default', 'rounded', 'double', 'solid')
        """
        if not title:
            return

        try:
            # 在标题前添加组件名称标识
            titled_title = f"[{self.component_name}] {title}"

            title_lines = titled_title.split('\n')
            max_title_length = max(self._custom_len(line) for line in title_lines)
            separator_length = max_title_length + 4

            # 定义不同样式的边框字符
            styles = {
                'default': {'corner': '+', 'hline': '-', 'vline': '|'},
                'rounded': {'corner': '*', 'hline': '-', 'vline': '|'},
                'double': {'corner': '+', 'hline': '=', 'vline': '||'},
                'solid': {'corner': '#', 'hline': '#', 'vline': '#'}
            }
            style = style.lower() if style in styles else 'default'
            corner, hline, vline = styles[style].values()

            # 初始化formatted_title变量
            formatted_title = titled_title

            if level == 0:
                # 带边框的标题框
                separator = corner + hline * separator_length + corner
                formatted_title_lines = []

                for line in title_lines:
                    title_length = self._custom_len(line)
                    padding_left = (separator_length - title_length) // 2
                    padding_right = separator_length - title_length - padding_left

                    formatted_title_line = vline + ' ' * padding_left + line + ' ' * padding_right + vline
                    formatted_title_lines.append(formatted_title_line)

                formatted_title = f"{separator}\n" + "\n".join(formatted_title_lines) + f"\n{separator}"
            elif level == 1:
                # 粗标题（上下有分隔线）
                line_sep = hline * (separator_length + 2)
                padding = (separator_length - self._custom_len(titled_title)) // 2
                formatted_title = f"{line_sep}\n{vline} {' ' * padding}{titled_title}{' ' * padding} {vline}\n{line_sep}"
            elif level == 2:
                # 简单包围标题
                padding = (separator_length - self._custom_len(titled_title)) // 2
                formatted_title = f"{corner}{hline * padding} {titled_title} {hline * padding}{corner}"
            elif level == 3:
                # 标题带前缀标记
                marker = '▶' if level == 3 else '✓'
                formatted_title = f"{marker} [{self.component_name}] {title}"
            elif level == 4:
                # 下划线标题
                formatted_title = f"[{self.component_name}] {title}\n{'-' * self._custom_len(f'[{self.component_name}] {title}')}"

            if write:
                self.title_logger.info(formatted_title)
            else:
                print(formatted_title)
        except Exception as e:
            self.error(f"格式化标题时出错: {e}")

    def _custom_len(self, text: str) -> int:
        """计算字符串的自定义长度，考虑到某些字符可能占用更多的显示宽度"""
        if text is None:
            return 0
        return sum(2 if unicodedata.east_asian_width(c) in 'WF' else 1 for c in text)

    def __del__(self):
        """析构函数，清理资源"""
        try:
            self.log_factory.remove_logger(self.account)
        except:
            pass


# 提供全局访问接口
log_factory = LogFactory()


def get_logger(component_name: str, port: int, account: str, simulator_type: str, level: str = "DEBUG") -> LogWrapper:
    """全局函数，获取日志包装器实例
    
    Args:
        component_name: 组件名称（用于在日志中标识模块）
        account: 账号名称
        level: 日志级别
        simulator_type: 模拟器类型
        port: 端口号
    """
    return LogWrapper(component_name, port, account, simulator_type, level)
