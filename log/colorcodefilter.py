import re
import logging

class ColorCodeFilter(logging.Formatter):
    """
    修改后的颜色代码过滤器，正确处理参数化日志
    """
    color_pattern = re.compile(r'\033\[[0-9;]+m')

    def format(self, record) -> str:
        # 父类先处理参数化消息生成
        formatted = super().format(record)
        # 移除最终字符串中的颜色代码
        return self.color_pattern.sub('', formatted)
