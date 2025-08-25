from log.log_factory import get_logger
from simulator.simulator_factory import SimulatorFactory
from simulator_models.adapter.adapter_factory import AdapterFactory

if __name__ == "__main__":
    try:
        logger = get_logger("system", 16384, "test", "mumu")

        # 定义参数字典
        simulator_kwargs = {
            "window_name": "MuMu模拟器12",
            "window_class": "Qt5156QWindowIcon",
            "simulator_path": "E:/MuMu Player 12/shell/MuMuPlayer.exe",
            "simulator_type": "mumu",
            "port": 16384,
            "account": "test"
        }
        adapter_kwargs = {
            "port": 16384,
            "account": "test",
            "simulator_type": "mumu",
            "icon": "食物语"
        }

        # 使用 ** 解包传递参数
        simulator = SimulatorFactory.create_simulator("mumu", **simulator_kwargs)
        logger.info("模拟器实例创建成功: %s", type(simulator).__name__)
        if simulator.run():
            adapter = AdapterFactory.create_adapter("star_rail", **adapter_kwargs)
            logger.info("适配器实例创建成功: %s", type(adapter).__name__)
            adapter.launcher_game()

    except Exception as e:
        print(f"创建模拟器时出错: {e}")
