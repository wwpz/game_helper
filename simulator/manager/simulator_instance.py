from control.adb.adb_controller import ADBController
from control.image.image_controller import ImageController
from control.ocr.ocr_controller import GetOcrApi
from log.log_factory import get_logger


class SimulatorInstance:
    """模拟器实例，每个线程独立"""

    def __init__(self, port: int, account: str, simulator_type: str):
        self.port = port
        self.account = account
        self.adb = ADBController.get_instance(port, account, simulator_type)
        self.image = ImageController.get_instance(port, account, simulator_type)
        self.ocr = GetOcrApi('control/ocr/PaddleOCR/PaddleOCR-json.exe', logger=get_logger("OCR-API", port, account, simulator_type))

    def cleanup(self):
        """清理资源"""
        self.adb.disconnect(self.port)