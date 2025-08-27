# 关于任务执行插件的详细设计与实现

## 为什么使用新的插件架构而不是之前的方案

在之前的对话中，我提供了多种架构方案，包括服务类模式和插件化模式。现在我们选择插件化架构有以下几个重要原因：

### 1. 更好的模块化和解耦
插件化架构可以将每个功能模块完全独立，插件之间没有直接依赖关系，更容易维护和扩展。

### 2. 动态加载能力
插件可以在运行时动态加载和卸载，这为系统提供了更大的灵活性，可以根据需要加载特定功能。

### 3. 更容易的第三方扩展
插件架构使得第三方开发者可以更容易地为系统添加新功能，而无需修改核心代码。

### 4. 配置驱动的执行
通过配置文件可以灵活控制哪些插件被加载和执行，以及它们的执行顺序。

## 详细的任务执行插件设计

### 1. 插件基类设计

```python
# core/plugins/base/plugin_base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import threading

class PluginBase(ABC):
    """插件基类，所有任务插件都需要继承此类"""
    
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
        self._lock = threading.Lock()
        self._is_running = False
        self._is_paused = False
        
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
    
    @property
    def category(self) -> str:
        """插件分类，如'daily', 'battle', 'cultivate'等"""
        return "general"
    
    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        执行插件功能
        
        Args:
            **kwargs: 执行参数
            
        Returns:
            Dict[str, Any]: 执行结果
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
        # 检查模拟器是否可用
        try:
            simulator = self.adapter.get_simulator()
            return simulator is not None
        except:
            return False
    
    def setup(self) -> None:
        """插件初始化，在加载时调用"""
        self.log.debug(f"插件 {self.name} 初始化")
    
    def teardown(self) -> None:
        """插件清理，在卸载时调用"""
        self.log.debug(f"插件 {self.name} 清理")
    
    def pause(self) -> None:
        """暂停插件执行"""
        with self._lock:
            self._is_paused = True
        self.log.info(f"插件 {self.name} 已暂停")
    
    def resume(self) -> None:
        """恢复插件执行"""
        with self._lock:
            self._is_paused = False
        self.log.info(f"插件 {self.name} 已恢复")
    
    def stop(self) -> None:
        """停止插件执行"""
        with self._lock:
            self._is_running = False
        self.log.info(f"插件 {self.name} 已停止")
    
    def is_running(self) -> bool:
        """检查插件是否正在运行"""
        with self._lock:
            return self._is_running
    
    def is_paused(self) -> bool:
        """检查插件是否已暂停"""
        with self._lock:
            return self._is_paused
    
    def wait_if_paused(self) -> None:
        """如果插件被暂停则等待"""
        import time
        while self.is_paused() and self.is_running():
            time.sleep(0.1)
```


### 2. 任务插件管理器

```python
# core/plugins/manager/plugin_manager.py
import os
import importlib.util
import threading
import json
from typing import Dict, List, Optional, Type, Set
from core.plugins.base.plugin_base import PluginBase
from core.plugins.exceptions.plugin_exceptions import PluginLoadError, PluginExecutionError

class PluginManager:
    """插件管理器，负责插件的加载、管理和执行"""
    
    def __init__(self, adapter):
        self.adapter = adapter
        self.log = adapter.log
        self._plugins: Dict[str, PluginBase] = {}
        self._lock = threading.RLock()  # 使用RLock支持重入
        self._loaded_modules: Set[str] = set()
        self._config = self._load_config()
        
    def _load_config(self) -> Dict:
        """加载插件配置"""
        config_file = "config/plugins.json"
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.log.warning(f"加载插件配置失败: {e}")
        
        # 返回默认配置
        return {
            "plugin_paths": ["plugins"],
            "enabled_plugins": [],
            "plugin_settings": {}
        }
    
    def load_plugins(self, plugin_paths: List[str] = None) -> None:
        """
        加载插件
        
        Args:
            plugin_paths: 插件路径列表，如果为None则使用配置文件中的路径
        """
        if plugin_paths is None:
            plugin_paths = self._config.get("plugin_paths", ["plugins"])
            
        self.log.info(f"开始加载插件，路径: {plugin_paths}")
        
        for path in plugin_paths:
            if os.path.isfile(path) and path.endswith('.py'):
                self._load_plugin_from_file(path)
            elif os.path.isdir(path):
                self._load_plugins_from_directory(path)
    
    def _load_plugins_from_directory(self, directory: str) -> None:
        """从目录加载插件"""
        self.log.debug(f"从目录加载插件: {directory}")
        try:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if file.endswith('_plugin.py'):
                        file_path = os.path.join(root, file)
                        self._load_plugin_from_file(file_path)
        except Exception as e:
            self.log.error(f"从目录 {directory} 加载插件时出错: {e}")
    
    def _load_plugin_from_file(self, file_path: str) -> None:
        """从文件加载插件"""
        try:
            # 检查是否已加载
            abs_path = os.path.abspath(file_path)
            if abs_path in self._loaded_modules:
                self.log.debug(f"插件文件已加载，跳过: {file_path}")
                return
            
            self.log.debug(f"加载插件文件: {file_path}")
            
            # 动态导入模块
            spec = importlib.util.spec_from_file_location(
                f"plugin_{len(self._loaded_modules)}", 
                file_path
            )
            if spec is None:
                raise PluginLoadError(f"无法创建模块规范: {file_path}")
                
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
                    
        except PluginLoadError:
            raise
        except Exception as e:
            self.log.error(f"加载插件文件 {file_path} 失败: {str(e)}")
            raise PluginLoadError(f"加载插件文件失败: {file_path}") from e
    
    def _register_plugin(self, plugin_class: Type[PluginBase]) -> None:
        """注册插件类"""
        try:
            plugin_instance = plugin_class(self.adapter)
            plugin_name = plugin_instance.name
            
            with self._lock:
                if plugin_name in self._plugins:
                    self.log.warning(f"插件 {plugin_name} 已存在，将被覆盖")
                
                # 检查插件是否启用
                enabled_plugins = self._config.get("enabled_plugins", [])
                if enabled_plugins and plugin_name not in enabled_plugins:
                    self.log.info(f"插件 {plugin_name} 未启用，跳过初始化")
                    return
                
                # 初始化插件
                try:
                    plugin_instance.setup()
                    self._plugins[plugin_name] = plugin_instance
                    self.log.info(f"插件 {plugin_name} 注册成功 (版本: {plugin_instance.version})")
                except Exception as e:
                    self.log.error(f"插件 {plugin_name} 初始化失败: {str(e)}")
                    raise PluginLoadError(f"插件初始化失败: {plugin_name}") from e
                
        except PluginLoadError:
            raise
        except Exception as e:
            self.log.error(f"注册插件 {plugin_class.__name__} 失败: {str(e)}")
            raise PluginLoadError(f"注册插件失败: {plugin_class.__name__}") from e
    
    def get_plugin(self, name: str) -> Optional[PluginBase]:
        """
        获取插件实例
        
        Args:
            name: 插件名称
            
        Returns:
            PluginBase: 插件实例，如果不存在返回None
        """
        with self._lock:
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
                    "category": plugin.category,
                    "priority": str(plugin.priority)
                }
                for plugin in sorted(self._plugins.values(), key=lambda p: p.priority)
            ]
    
    def execute_plugin(self, name: str, **kwargs) -> Dict[str, Any]:
        """
        执行插件
        
        Args:
            name: 插件名称
            **kwargs: 执行参数
            
        Returns:
            Dict[str, Any]: 执行结果
            
        Raises:
            ValueError: 插件不存在或无法执行
            PluginExecutionError: 插件执行出错
        """
        plugin = self.get_plugin(name)
        if not plugin:
            raise ValueError(f"插件 {name} 不存在")
            
        if not plugin.can_execute(**kwargs):
            raise ValueError(f"插件 {name} 当前无法执行")
            
        try:
            self.log.info(f"开始执行插件: {name}")
            with plugin._lock:
                plugin._is_running = True
            
            result = plugin.execute(**kwargs)
            self.log.info(f"插件 {name} 执行完成")
            return result
        except Exception as e:
            self.log.error(f"执行插件 {name} 时发生错误: {str(e)}")
            raise PluginExecutionError(f"插件执行失败: {name}") from e
        finally:
            with plugin._lock:
                plugin._is_running = False
    
    def execute_plugins_by_category(self, category: str, **kwargs) -> Dict[str, Any]:
        """
        执行指定分类的所有插件
        
        Args:
            category: 插件分类
            **kwargs: 执行参数
            
        Returns:
            Dict[str, Any]: 各插件执行结果
        """
        plugins_in_category = [
            plugin for plugin in self._plugins.values() 
            if plugin.category == category
        ]
        
        # 按优先级排序
        plugins_in_category.sort(key=lambda p: p.priority)
        
        results = {}
        for plugin in plugins_in_category:
            try:
                results[plugin.name] = self.execute_plugin(plugin.name, **kwargs)
            except Exception as e:
                self.log.error(f"执行插件 {plugin.name} 失败: {str(e)}")
                results[plugin.name] = {"status": "error", "error": str(e)}
                
        return results
    
    def execute_plugins_by_priority(self, plugin_names: List[str] = None, **kwargs) -> Dict[str, Any]:
        """
        按优先级顺序执行插件
        
        Args:
            plugin_names: 插件名称列表，如果为None则执行所有插件
            **kwargs: 执行参数
            
        Returns:
            Dict[str, Any]: 各插件执行结果
        """
        if plugin_names is None:
            # 执行所有插件
            plugins_to_execute = list(self._plugins.values())
        else:
            # 执行指定插件
            plugins_to_execute = []
            for name in plugin_names:
                plugin = self.get_plugin(name)
                if plugin:
                    plugins_to_execute.append(plugin)
        
        # 按优先级排序
        plugins_to_execute.sort(key=lambda p: p.priority)
        
        results = {}
        for plugin in plugins_to_execute:
            try:
                results[plugin.name] = self.execute_plugin(plugin.name, **kwargs)
            except Exception as e:
                self.log.error(f"执行插件 {plugin.name} 失败: {str(e)}")
                results[plugin.name] = {"status": "error", "error": str(e)}
                
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
                    # 停止插件执行
                    plugin = self._plugins[name]
                    plugin.stop()
                    
                    # 执行清理
                    plugin.teardown()
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


### 3. 具体任务插件示例

```python
# plugins/daily/entrust_plugin.py
from core.plugins.base.plugin_base import PluginBase
from core.plugins.exceptions.plugin_exceptions import PluginExecutionError

class EntrustPlugin(PluginBase):
    """委托任务插件"""
    
    @property
    def name(self) -> str:
        return "daily_entrust"
    
    @property
    def description(self) -> str:
        return "执行日常委托任务"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def priority(self) -> int:
        return 10
    
    @property
    def category(self) -> str:
        return "daily"
    
    def execute(self, **kwargs) -> dict:
        """执行委托任务"""
        try:
            self.log.info(f"账号 {self.account} 开始执行委托任务")
            
            # 获取模拟器实例
            simulator = self.adapter.get_simulator()
            if not simulator:
                raise PluginExecutionError("无法获取模拟器实例")
            
            # 执行委托任务步骤
            result = {
                "status": "success",
                "plugin": self.name,
                "account": self.account,
                "steps": []
            }
            
            # 步骤1: 打开手机界面
            self.wait_if_paused()
            step_result = self._open_phone(simulator)
            result["steps"].append({"name": "open_phone", "result": step_result})
            
            if not step_result["success"]:
                raise PluginExecutionError("无法打开手机界面")
            
            # 步骤2: 点击委托按钮
            self.wait_if_paused()
            step_result = self._click_entrust(simulator)
            result["steps"].append({"name": "click_entrust", "result": step_result})
            
            if not step_result["success"]:
                raise PluginExecutionError("无法找到委托按钮")
            
            # 步骤3: 领取委托奖励
            self.wait_if_paused()
            step_result = self._collect_rewards(simulator)
            result["steps"].append({"name": "collect_rewards", "result": step_result})
            
            # 步骤4: 重新派遣委托
            self.wait_if_paused()
            step_result = self._reassign_entrust(simulator)
            result["steps"].append({"name": "reassign_entrust", "result": step_result})
            
            # 步骤5: 关闭界面
            self.wait_if_paused()
            step_result = self._close_interface(simulator)
            result["steps"].append({"name": "close_interface", "result": step_result})
            
            self.log.info(f"账号 {self.account} 委托任务执行完成")
            return result
            
        except Exception as e:
            self.log.error(f"执行委托任务时发生错误: {str(e)}")
            return {
                "status": "error",
                "plugin": self.name,
                "account": self.account,
                "error": str(e)
            }
    
    def _open_phone(self, simulator) -> dict:
        """打开手机界面"""
        try:
            success = simulator.click_element("./res/images/daily_task/phone.png")
            return {"success": success, "element": "phone"}
        except Exception as e:
            return {"success": False, "element": "phone", "error": str(e)}
    
    def _click_entrust(self, simulator) -> dict:
        """点击委托按钮"""
        try:
            screenshot = simulator.take_screenshot()
            ocr_result = simulator.ocr_recognize(screenshot)
            
            # OCR查找委托文本
            for item in ocr_result.get("items", []):
                if "委托" in item["text"]:
                    x, y = item["center"]
                    simulator.adb.click(x, y)
                    return {"success": True, "element": "entrust", "found_by": "ocr"}
            
            # 如果OCR找不到，尝试图像识别
            success = simulator.click_element("./res/images/daily_task/entrust_button.png")
            return {"success": success, "element": "entrust", "found_by": "image"}
        except Exception as e:
            return {"success": False, "element": "entrust", "error": str(e)}
    
    def _collect_rewards(self, simulator) -> dict:
        """领取委托奖励"""
        try:
            success = simulator.click_element("./res/images/daily_task/entrust_receive_award.png")
            return {"success": success, "element": "receive_award"}
        except Exception as e:
            return {"success": False, "element": "receive_award", "error": str(e)}
    
    def _reassign_entrust(self, simulator) -> dict:
        """重新派遣委托"""
        try:
            success = simulator.click_element("./res/images/daily_task/entrust_again.png")
            return {"success": success, "element": "reassign"}
        except Exception as e:
            return {"success": False, "element": "reassign", "error": str(e)}
    
    def _close_interface(self, simulator) -> dict:
        """关闭界面"""
        try:
            success = simulator.click_element("./res/images/daily_task/entrust_close.png")
            return {"success": success, "element": "close"}
        except Exception as e:
            return {"success": False, "element": "close", "error": str(e)}
```


### 4. 插件异常处理

```python
# core/plugins/exceptions/plugin_exceptions.py
class PluginError(Exception):
    """插件相关错误基类"""
    pass

class PluginLoadError(PluginError):
    """插件加载错误"""
    pass

class PluginExecutionError(PluginError):
    """插件执行错误"""
    pass

class PluginNotEnabledError(PluginError):
    """插件未启用错误"""
    pass
```


### 5. 插件配置文件示例

```json
{
  "plugin_paths": [
    "plugins",
    "plugins/daily",
    "plugins/battle",
    "plugins/cultivate"
  ],
  "enabled_plugins": [
    "daily_entrust",
    "daily_mail",
    "daily_liveness",
    "battle_prepare",
    "battle_execute",
    "battle_finish"
  ],
  "plugin_settings": {
    "daily_entrust": {
      "priority": 10,
      "retry_count": 3
    },
    "daily_mail": {
      "priority": 20,
      "retry_count": 2
    }
  }
}
```


## 插件架构的优势

### 1. 高度模块化
每个插件都是一个独立的模块，可以单独开发、测试和维护。

### 2. 动态加载
插件可以在运行时动态加载和卸载，提高了系统的灵活性。

### 3. 配置驱动
通过配置文件可以灵活控制插件的加载和执行行为。

### 4. 异常隔离
单个插件的错误不会影响其他插件或整个系统的运行。

### 5. 易于扩展
添加新功能只需要实现新的插件类，无需修改核心代码。

### 6. 优先级控制
支持按优先级顺序执行插件，满足不同任务的执行顺序要求。

这种插件化架构比之前的服务类模式更加灵活和可扩展，更适合复杂的自动化任务管理系统。