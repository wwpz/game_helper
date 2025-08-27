# StarRailHelper 游戏脚本管理器设计方案

## 1. 项目概述

StarRailHelper 是一个用于《星穹铁道》游戏自动化的辅助工具，旨在帮助玩家自动化执行游戏中的重复任务。本设计方案提供一个游戏脚本管理器，用于自动化执行各种游戏任务，并具备完善的错误处理机制。

### 1.1 核心需求

- 自动化执行游戏中的重复性任务（日常任务、战斗、培养等）
- 完善的错误处理机制，确保程序在遇到问题时不会崩溃
- 多账户支持，可同时处理多个游戏账户
- 模块化设计，便于功能扩展和维护
- 支持多种模拟器（MuMu、蓝叠等）

## 2. 技术架构

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                          脚本管理器                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐    │
│  │   任务调度器    │  │   错误处理器    │  │   日志系统      │    │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘    │
│           │                    │                    │              │
│           ▼                    ▼                    ▼              │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    插件化任务系统                           │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │   │
│  │  │  日常任务   │  │  战斗任务   │  │  培养任务   │  ...     │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│                              ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    模拟器操作层                              │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │   │
│  │  │   ADB控制   │  │  图像识别   │  │   OCR引擎   │          │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│                              ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    模拟器实例管理                            │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │   │
│  │  │  MuMu模拟器 │  │  蓝叠模拟器 │  │  其他模拟器 │  ...     │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘          │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```


### 2.2 技术选型

- **编程语言**: Python 3.x
- **OCR引擎**: PPOCR_api（基于paddleOCR）
- **图像处理**: OpenCV, Pillow
- **自动化控制**: PyAutoGUI, PyScreeze, PyGetWindow
- **日志系统**: colorama, 自定义日志模块
- **多线程**: threading
- **模拟器支持**: 蓝叠、MuMu等

## 3. 核心组件设计

### 3.1 模拟器实例管理器

```python
# core/simulator/manager/simulator_manager.py
import threading
from typing import Dict
from core.simulator.instance.simulator_instance import SimulatorInstance

class SimulatorManager:
    """模拟器实例管理器，确保线程安全"""
    
    _instances: Dict[str, SimulatorInstance] = {}
    _lock = threading.Lock()
    
    @classmethod
    def get_instance(cls, port: int, account: str, simulator_type: str) -> SimulatorInstance:
        """
        获取模拟器实例，确保线程安全
        
        Args:
            port: 模拟器端口号
            account: 账号名称
            simulator_type: 模拟器类型
            
        Returns:
            SimulatorInstance: 模拟器实例
        """
        thread_id = threading.get_ident()
        key = f"{port}_{thread_id}_{account}"
        
        with cls._lock:
            if key not in cls._instances:
                cls._instances[key] = SimulatorInstance(port, account, simulator_type)
            return cls._instances[key]
    
    @classmethod
    def release_instance(cls, port: int, account: str) -> None:
        """
        释放模拟器实例
        
        Args:
            port: 模拟器端口号
            account: 账号名称
        """
        thread_id = threading.get_ident()
        key = f"{port}_{thread_id}_{account}"
        
        with cls._lock:
            if key in cls._instances:
                cls._instances[key].cleanup()
                del cls._instances[key]
```


### 3.2 模拟器实例

```python
# core/simulator/instance/simulator_instance.py
from core.simulator.controller.adb_controller import ADBController
from core.simulator.controller.image_controller import ImageController
from core.ocr.ocr_engine import OCREngine

class SimulatorInstance:
    """模拟器实例，封装所有操作接口"""
    
    def __init__(self, port: int, account: str, simulator_type: str):
        self.port = port
        self.account = account
        self.simulator_type = simulator_type
        
        # 初始化控制器
        self.adb = ADBController(port, account, simulator_type)
        self.image = ImageController(port, account, simulator_type)
        self.ocr = OCREngine()
        
        # 连接模拟器
        self.adb.connect()
    
    def cleanup(self) -> None:
        """清理资源"""
        self.adb.disconnect()
    
    def take_screenshot(self) -> bytes:
        """截图"""
        return self.adb.screenshot()
    
    def find_element(self, template_path: str, threshold: float = 0.8) -> tuple:
        """
        查找图像元素
        
        Args:
            template_path: 模板图像路径
            threshold: 匹配阈值
            
        Returns:
            tuple: (x, y, confidence) 或 None
        """
        screenshot = self.take_screenshot()
        return self.image.find_template(screenshot, template_path, threshold)
    
    def click_element(self, template_path: str, threshold: float = 0.8) -> bool:
        """
        点击图像元素
        
        Args:
            template_path: 模板图像路径
            threshold: 匹配阈值
            
        Returns:
            bool: 是否成功点击
        """
        element = self.find_element(template_path, threshold)
        if element:
            x, y, confidence = element
            self.adb.click(x, y)
            return True
        return False
    
    def ocr_recognize(self, image_bytes: bytes) -> dict:
        """
        OCR识别
        
        Args:
            image_bytes: 图像数据
            
        Returns:
            dict: OCR识别结果
        """
        return self.ocr.recognize(image_bytes)
```


## 4. 任务系统设计

### 4.1 任务基类

```python
# core/tasks/task_base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from core.simulator.instance.simulator_instance import SimulatorInstance
from core.logger.logger_factory import LoggerFactory

class TaskBase(ABC):
    """任务基类"""
    
    def __init__(self, simulator: SimulatorInstance, config: Dict[str, Any] = None):
        self.simulator = simulator
        self.config = config or {}
        self.logger = LoggerFactory.get_logger(self.__class__.__name__)
        self.is_running = False
        self.is_paused = False
    
    @property
    @abstractmethod
    def name(self) -> str:
        """任务名称"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """任务描述"""
        pass
    
    @abstractmethod
    def execute(self) -> Dict[str, Any]:
        """
        执行任务
        
        Returns:
            Dict[str, Any]: 执行结果
        """
        pass
    
    def pause(self) -> None:
        """暂停任务"""
        self.is_paused = True
        self.logger.info(f"任务 {self.name} 已暂停")
    
    def resume(self) -> None:
        """恢复任务"""
        self.is_paused = False
        self.logger.info(f"任务 {self.name} 已恢复")
    
    def stop(self) -> None:
        """停止任务"""
        self.is_running = False
        self.logger.info(f"任务 {self.name} 已停止")
    
    def wait_if_paused(self) -> None:
        """如果任务被暂停则等待"""
        import time
        while self.is_paused and self.is_running:
            time.sleep(0.1)
```


### 4.2 错误处理机制

```python
# core/exceptions/task_exceptions.py
class TaskError(Exception):
    """任务执行错误基类"""
    def __init__(self, message: str, task_name: str = None, details: Dict = None):
        super().__init__(message)
        self.task_name = task_name
        self.details = details or {}

class ElementNotFoundError(TaskError):
    """元素未找到错误"""
    pass

class ExecutionTimeoutError(TaskError):
    """执行超时错误"""
    pass

class ImageRecognitionError(TaskError):
    """图像识别错误"""
    pass

# core/error_handler/error_handler.py
from enum import Enum
from typing import Callable, Optional
from core.exceptions.task_exceptions import TaskError

class ErrorHandlingStrategy(Enum):
    """错误处理策略"""
    WAIT = "wait"          # 等待用户处理
    SKIP = "skip"          # 跳过当前步骤
    RETRY = "retry"        # 重试
    STOP = "stop"          # 停止任务

class ErrorHandler:
    """错误处理器"""
    
    def __init__(self):
        self.handlers = {}
        self.default_strategy = ErrorHandlingStrategy.WAIT
    
    def register_handler(self, error_type: type, handler: Callable):
        """注册错误处理器"""
        self.handlers[error_type] = handler
    
    def handle_error(self, error: Exception, context: Dict) -> ErrorHandlingStrategy:
        """
        处理错误
        
        Args:
            error: 发生的错误
            context: 错误上下文信息
            
        Returns:
            ErrorHandlingStrategy: 错误处理策略
        """
        # 查找特定错误类型的处理器
        handler = self.handlers.get(type(error))
        if handler:
            return handler(error, context)
        
        # 使用默认策略
        return self._handle_with_default_strategy(error, context)
    
    def _handle_with_default_strategy(self, error: Exception, context: Dict) -> ErrorHandlingStrategy:
        """使用默认策略处理错误"""
        import tkinter as tk
        from tkinter import messagebox
        
        # 创建错误对话框
        root = tk.Tk()
        root.withdraw()  # 隐藏主窗口
        
        error_msg = f"任务执行出错:\n{str(error)}\n\n请选择处理方式:"
        result = messagebox.askyesnocancel(
            "错误处理",
            error_msg,
            icon=messagebox.ERROR,
            default=messagebox.YES
        )
        
        root.destroy()
        
        if result is True:  # 是 - 跳过
            return ErrorHandlingStrategy.SKIP
        elif result is False:  # 否 - 重试
            return ErrorHandlingStrategy.RETRY
        else:  # 取消 - 停止
            return ErrorHandlingStrategy.STOP
```


### 4.3 具体任务实现示例

```python
# core/tasks/daily/entrust_task.py
from core.tasks.task_base import TaskBase
from core.exceptions.task_exceptions import ElementNotFoundError

class EntrustTask(TaskBase):
    """委托任务"""
    
    @property
    def name(self) -> str:
        return "daily_entrust"
    
    @property
    def description(self) -> str:
        return "执行日常委托任务"
    
    def execute(self) -> Dict[str, Any]:
        """执行委托任务"""
        self.is_running = True
        result = {
            "status": "success",
            "task_name": self.name,
            "details": {}
        }
        
        try:
            self.logger.info("开始执行委托任务")
            
            # 1. 打开手机界面
            if not self._open_phone():
                raise ElementNotFoundError("无法打开手机界面", self.name)
            
            # 2. 点击委托按钮
            if not self._click_entrust():
                raise ElementNotFoundError("无法找到委托按钮", self.name)
            
            # 3. 领取委托奖励
            self._collect_rewards()
            
            # 4. 重新派遣委托
            self._reassign_entrust()
            
            # 5. 关闭界面
            self._close_interface()
            
            self.logger.info("委托任务执行完成")
            
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            self.logger.error(f"委托任务执行失败: {str(e)}")
        finally:
            self.is_running = False
            
        return result
    
    def _open_phone(self) -> bool:
        """打开手机界面"""
        self.wait_if_paused()
        return self.simulator.click_element("./res/images/daily_task/phone.png")
    
    def _click_entrust(self) -> bool:
        """点击委托按钮"""
        self.wait_if_paused()
        screenshot = self.simulator.take_screenshot()
        ocr_result = self.simulator.ocr_recognize(screenshot)
        
        # OCR查找委托文本
        for item in ocr_result.get("items", []):
            if "委托" in item["text"]:
                x, y = item["center"]
                self.simulator.adb.click(x, y)
                return True
        return False
    
    def _collect_rewards(self) -> None:
        """领取委托奖励"""
        self.wait_if_paused()
        self.simulator.click_element("./res/images/daily_task/entrust_receive_award.png")
    
    def _reassign_entrust(self) -> None:
        """重新派遣委托"""
        self.wait_if_paused()
        self.simulator.click_element("./res/images/daily_task/entrust_again.png")
    
    def _close_interface(self) -> None:
        """关闭界面"""
        self.wait_if_paused()
        self.simulator.click_element("./res/images/daily_task/entrust_close.png")
```


## 5. 任务调度器

```python
# core/scheduler/task_scheduler.py
import threading
import time
from typing import List, Dict, Any
from core.tasks.task_base import TaskBase
from core.error_handler.error_handler import ErrorHandler, ErrorHandlingStrategy
from core.exceptions.task_exceptions import TaskError

class TaskScheduler:
    """任务调度器"""
    
    def __init__(self):
        self.tasks: List[TaskBase] = []
        self.is_running = False
        self.current_task = None
        self.error_handler = ErrorHandler()
        self._lock = threading.Lock()
    
    def add_task(self, task: TaskBase) -> None:
        """添加任务"""
        with self._lock:
            self.tasks.append(task)
    
    def remove_task(self, task: TaskBase) -> None:
        """移除任务"""
        with self._lock:
            if task in self.tasks:
                self.tasks.remove(task)
    
    def start(self) -> None:
        """开始执行所有任务"""
        if self.is_running:
            return
            
        self.is_running = True
        thread = threading.Thread(target=self._execute_tasks)
        thread.daemon = True
        thread.start()
    
    def stop(self) -> None:
        """停止执行"""
        self.is_running = False
        if self.current_task:
            self.current_task.stop()
    
    def _execute_tasks(self) -> None:
        """执行所有任务"""
        for task in self.tasks:
            if not self.is_running:
                break
                
            self.current_task = task
            try:
                result = task.execute()
                # 处理任务结果
                self._handle_task_result(task, result)
            except TaskError as e:
                # 处理任务错误
                strategy = self.error_handler.handle_error(e, {
                    "task": task,
                    "error": e
                })
                self._handle_error_strategy(strategy, task)
            except Exception as e:
                # 处理未预期错误
                strategy = self.error_handler.handle_error(e, {
                    "task": task,
                    "error": e
                })
                self._handle_error_strategy(strategy, task)
    
    def _handle_task_result(self, task: TaskBase, result: Dict[str, Any]) -> None:
        """处理任务结果"""
        if result.get("status") == "success":
            print(f"任务 {task.name} 执行成功")
        else:
            print(f"任务 {task.name} 执行失败: {result.get('error')}")
    
    def _handle_error_strategy(self, strategy: ErrorHandlingStrategy, task: TaskBase) -> None:
        """处理错误策略"""
        if strategy == ErrorHandlingStrategy.SKIP:
            print(f"跳过任务 {task.name}")
        elif strategy == ErrorHandlingStrategy.RETRY:
            print(f"重试任务 {task.name}")
            # 重新执行任务
            try:
                result = task.execute()
                self._handle_task_result(task, result)
            except Exception as e:
                print(f"重试任务 {task.name} 失败: {str(e)}")
        elif strategy == ErrorHandlingStrategy.STOP:
            print(f"停止所有任务")
            self.stop()
```


## 6. 配置管理系统

```python
# core/config/config_manager.py
import json
import os
from typing import Dict, Any

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: str = "config/app_config.json"):
        self.config_file = config_file
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载配置文件失败: {e}")
                return self._create_default_config()
        else:
            return self._create_default_config()
    
    def _create_default_config(self) -> Dict[str, Any]:
        """创建默认配置"""
        default_config = {
            "simulator": {
                "default_type": "mumu",
                "adb_path": "adb",
                "timeout": 30
            },
            "tasks": {
                "daily": {
                    "enabled": True,
                    "order": ["entrust", "mail", "liveness"]
                },
                "battle": {
                    "enabled": True,
                    "max_retries": 3
                }
            },
            "error_handling": {
                "default_strategy": "wait",
                "auto_retry_count": 3
            }
        }
        
        # 保存默认配置
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
            
        return default_config
    
    def get(self, key: str, default=None) -> Any:
        """获取配置项"""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def set(self, key: str, value: Any) -> None:
        """设置配置项"""
        keys = key.split('.')
        config = self.config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
        
        # 保存配置
        self._save_config()
    
    def _save_config(self) -> None:
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置文件失败: {e}")
```


## 7. 插件化架构

### 7.1 插件基类

```python
# core/plugins/plugin_base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class PluginBase(ABC):
    """插件基类，所有插件都需要继承此类"""
    
    def __init__(self, adapter):
        """
        初始化插件
        
        Args:
            adapter: 适配器实例，提供上下文信息和资源访问
        """
        self.adapter = adapter
        self.log = adapter.log
        self.account = adapter.account
        self.port = adapter.port
        
    @property
    @abstractmethod
    def name(self) -> str:
        """插件名称，必须唯一"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """插件描述"""
        pass
    
    @property
    def version(self) -> str:
        """插件版本"""
        return "1.0.0"
    
    @property
    def priority(self) -> int:
        """插件优先级，数值越小优先级越高"""
        return 100
    
    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """
        执行插件功能
        
        Args:
            **kwargs: 执行参数
            
        Returns:
            执行结果
        """
        pass
    
    def can_execute(self, **kwargs) -> bool:
        """
        检查插件是否可以执行
        
        Args:
            **kwargs: 检查条件参数
            
        Returns:
            bool: 是否可以执行
        """
        return True
    
    def setup(self) -> None:
        """插件初始化，在加载时调用"""
        pass
    
    def teardown(self) -> None:
        """插件清理，在卸载时调用"""
        pass
```


### 7.2 插件管理器

```python
# core/plugins/plugin_manager.py
import os
import importlib.util
import threading
from typing import Dict, List, Optional, Type
from core.plugins.plugin_base import PluginBase

class PluginManager:
    """插件管理器，负责插件的加载、管理和执行"""
    
    def __init__(self, adapter):
        self.adapter = adapter
        self.log = adapter.log
        self._plugins: Dict[str, PluginBase] = {}
        self._lock = threading.Lock()
        self._loaded_modules = set()
        
    def load_plugins(self, plugin_paths: List[str] = None) -> None:
        """
        加载插件
        
        Args:
            plugin_paths: 插件路径列表，如果为None则加载默认路径下的所有插件
        """
        if plugin_paths is None:
            # 默认从 plugins 目录加载
            plugin_paths = ["plugins"]
            
        for path in plugin_paths:
            if os.path.isfile(path) and path.endswith('.py'):
                self._load_plugin_from_file(path)
            elif os.path.isdir(path):
                self._load_plugins_from_directory(path)
    
    def _load_plugins_from_directory(self, directory: str) -> None:
        """从目录加载插件"""
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('_plugin.py'):
                    file_path = os.path.join(root, file)
                    self._load_plugin_from_file(file_path)
    
    def _load_plugin_from_file(self, file_path: str) -> None:
        """从文件加载插件"""
        try:
            # 检查是否已加载
            abs_path = os.path.abspath(file_path)
            if abs_path in self._loaded_modules:
                return
                
            # 动态导入模块
            spec = importlib.util.spec_from_file_location(
                f"plugin_{len(self._loaded_modules)}", 
                file_path
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self._loaded_modules.add(abs_path)
            
            # 查找并实例化插件类
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, PluginBase) and 
                    attr != PluginBase):
                    self._register_plugin(attr)
                    
        except Exception as e:
            self.log.error(f"加载插件文件 {file_path} 失败: {str(e)}")
    
    def _register_plugin(self, plugin_class: Type[PluginBase]) -> None:
        """注册插件类"""
        try:
            plugin_instance = plugin_class(self.adapter)
            plugin_name = plugin_instance.name
            
            with self._lock:
                if plugin_name in self._plugins:
                    self.log.warning(f"插件 {plugin_name} 已存在，将被覆盖")
                
                # 初始化插件
                plugin_instance.setup()
                self._plugins[plugin_name] = plugin_instance
                self.log.info(f"插件 {plugin_name} 注册成功")
                
        except Exception as e:
            self.log.error(f"注册插件 {plugin_class.__name__} 失败: {str(e)}")
    
    def get_plugin(self, name: str) -> Optional[PluginBase]:
        """
        获取插件实例
        
        Args:
            name: 插件名称
            
        Returns:
            PluginBase: 插件实例，如果不存在返回None
        """
        return self._plugins.get(name)
    
    def list_plugins(self) -> List[Dict[str, str]]:
        """
        列出所有插件信息
        
        Returns:
            List[Dict[str, str]]: 插件信息列表
        """
        with self._lock:
            return [
                {
                    "name": plugin.name,
                    "description": plugin.description,
                    "version": plugin.version,
                    "priority": str(plugin.priority)
                }
                for plugin in sorted(self._plugins.values(), key=lambda p: p.priority)
            ]
    
    def execute_plugin(self, name: str, **kwargs) -> Any:
        """
        执行插件
        
        Args:
            name: 插件名称
            **kwargs: 执行参数
            
        Returns:
            执行结果
            
        Raises:
            ValueError: 插件不存在或无法执行
        """
        plugin = self.get_plugin(name)
        if not plugin:
            raise ValueError(f"插件 {name} 不存在")
            
        if not plugin.can_execute(**kwargs):
            raise ValueError(f"插件 {name} 当前无法执行")
            
        try:
            self.log.info(f"开始执行插件: {name}")
            result = plugin.execute(**kwargs)
            self.log.info(f"插件 {name} 执行完成")
            return result
        except Exception as e:
            self.log.error(f"执行插件 {name} 时发生错误: {str(e)}")
            raise
    
    def execute_plugins_by_priority(self, plugin_names: List[str], **kwargs) -> Dict[str, Any]:
        """
        按优先级顺序执行多个插件
        
        Args:
            plugin_names: 插件名称列表
            **kwargs: 执行参数
            
        Returns:
            Dict[str, Any]: 各插件执行结果
        """
        # 获取并排序插件
        plugins_to_execute = []
        for name in plugin_names:
            plugin = self.get_plugin(name)
            if plugin:
                plugins_to_execute.append(plugin)
        
        plugins_to_execute.sort(key=lambda p: p.priority)
        
        # 依次执行
        results = {}
        for plugin in plugins_to_execute:
            try:
                results[plugin.name] = self.execute_plugin(plugin.name, **kwargs)
            except Exception as e:
                self.log.error(f"执行插件 {plugin.name} 失败: {str(e)}")
                results[plugin.name] = {"error": str(e)}
                
        return results
    
    def unload_plugin(self, name: str) -> bool:
        """
        卸载插件
        
        Args:
            name: 插件名称
            
        Returns:
            bool: 是否卸载成功
        """
        with self._lock:
            if name in self._plugins:
                try:
                    # 执行清理
                    self._plugins[name].teardown()
                    del self._plugins[name]
                    self.log.info(f"插件 {name} 卸载成功")
                    return True
                except Exception as e:
                    self.log.error(f"卸载插件 {name} 时发生错误: {str(e)}")
                    return False
            else:
                self.log.warning(f"插件 {name} 不存在")
                return False
    
    def unload_all_plugins(self) -> None:
        """卸载所有插件"""
        with self._lock:
            plugin_names = list(self._plugins.keys())
            for name in plugin_names:
                self.unload_plugin(name)
```


## 8. 错误处理与用户交互

### 8.1 图形化错误处理界面

```python
# core/ui/error_dialog.py
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional
from core.error_handler.error_handler import ErrorHandlingStrategy

class ErrorDialog:
    """错误对话框"""
    
    def __init__(self, parent=None):
        self.parent = parent
        self.result = None
    
    def show_error(self, title: str, message: str, details: str = None) -> ErrorHandlingStrategy:
        """
        显示错误对话框
        
        Args:
            title: 对话框标题
            message: 错误消息
            details: 详细信息
            
        Returns:
            ErrorHandlingStrategy: 用户选择的处理策略
        """
        dialog = tk.Toplevel(self.parent) if self.parent else tk.Tk()
        dialog.title(title)
        dialog.geometry("400x200")
        dialog.resizable(False, False)
        
        # 居中显示
        dialog.transient(self.parent)
        dialog.grab_set()
        
        # 错误图标
        icon_label = ttk.Label(dialog, text="⚠️", font=("Arial", 24))
        icon_label.pack(pady=10)
        
        # 错误消息
        msg_label = ttk.Label(dialog, text=message, wraplength=350)
        msg_label.pack(pady=5)
        
        # 详细信息（如果有）
        if details:
            details_text = tk.Text(dialog, height=4, width=40)
            details_text.insert("1.0", details)
            details_text.config(state="disabled")
            details_text.pack(pady=5)
        
        # 按钮框架
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        
        # 按钮变量
        self.result = tk.StringVar(value="wait")
        
        # 等待按钮
        wait_btn = ttk.Button(
            button_frame, 
            text="等待处理", 
            command=lambda: self._set_result(dialog, "wait")
        )
        wait_btn.pack(side="left", padx=5)
        
        # 跳过按钮
        skip_btn = ttk.Button(
            button_frame, 
            text="跳过", 
            command=lambda: self._set_result(dialog, "skip")
        )
        skip_btn.pack(side="left", padx=5)
        
        # 重试按钮
        retry_btn = ttk.Button(
            button_frame, 
            text="重试", 
            command=lambda: self._set_result(dialog, "retry")
        )
        retry_btn.pack(side="left", padx=5)
        
        # 停止按钮
        stop_btn = ttk.Button(
            button_frame, 
            text="停止", 
            command=lambda: self._set_result(dialog, "stop")
        )
        stop_btn.pack(side="left", padx=5)
        
        # 等待用户选择
        dialog.wait_window(dialog)
        
        # 转换结果
        strategy_map = {
            "wait": ErrorHandlingStrategy.WAIT,
            "skip": ErrorHandlingStrategy.SKIP,
            "retry": ErrorHandlingStrategy.RETRY,
            "stop": ErrorHandlingStrategy.STOP
        }
        
        return strategy_map.get(self.result.get(), ErrorHandlingStrategy.WAIT)
    
    def _set_result(self, dialog, result: str) -> None:
        """设置结果并关闭对话框"""
        self.result.set(result)
        dialog.destroy()
```


## 9. 系统特性

### 9.1 完善的错误处理机制

1. **错误分类**：对不同类型的错误进行分类处理
2. **用户交互**：遇到错误时弹出对话框供用户选择处理方式
3. **自动重试**：支持配置自动重试次数
4. **日志记录**：详细记录错误信息便于调试

### 9.2 多线程支持

1. **线程安全**：确保模拟器实例在多线程环境下的安全访问
2. **资源隔离**：每个线程拥有独立的模拟器实例
3. **任务并发**：支持多个账号任务并发执行

### 9.3 插件化架构

1. **模块化设计**：每个任务独立封装为模块
2. **易于扩展**：添加新任务只需实现PluginBase接口
3. **动态加载**：支持运行时加载和卸载任务模块

### 9.4 配置驱动

1. **灵活配置**：通过配置文件控制系统行为
2. **默认值**：提供合理的默认配置
3. **持久化**：配置更改自动保存到文件

## 10. 部署与使用

### 10.1 环境要求

1. Python 3.7+
2. ADB工具
3. 支持的模拟器（MuMu、蓝叠等）
4. 相关Python依赖包

### 10.2 使用流程

1. 配置模拟器和账号信息
2. 启动模拟器并运行游戏
3. 运行脚本管理器
4. 系统自动执行配置的任务
5. 遇到错误时根据提示进行处理

### 10.3 扩展开发

1. 实现新的插件类继承PluginBase
2. 在配置文件中启用新插件
3. 提供相应的图像资源和OCR识别规则

## 11. 总结

本设计方案提供了一个完整的游戏脚本管理器架构，具有以下特点：

1. **模块化设计**：采用插件化架构，便于功能扩展和维护
2. **完善的错误处理**：提供多种错误处理策略，确保程序稳定性
3. **多线程支持**：支持多账号并发执行，提高效率
4. **配置驱动**：通过配置文件灵活控制系统行为
5. **易于扩展**：提供清晰的接口和规范，便于添加新功能

该架构能够满足StarRailHelper项目的需求，为自动化游戏任务执行提供稳定、可靠的技术基础。