from simulator_models.adb.adb_controller import ADBController
from simulator_models.image.image_controller import ImageController


class SimulatorInstance:
    """模拟器实例，每个线程独立"""

    def __init__(self, port: int, account: str, simulator_type: str):
        self.port = port
        self.account = account
        self.adb = ADBController.get_instance(port, account, simulator_type)
        self.image = ImageController.get_instance(port, account, simulator_type)
        self.ocr = None  # 需要外部注入

    def cleanup(self):
        """清理资源"""
        self.adb.disconnect(self.port)
