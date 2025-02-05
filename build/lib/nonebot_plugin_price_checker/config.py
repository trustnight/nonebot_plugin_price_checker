"""
config.py 文件使用了 pydantic 来定义配置类 Config，
并提供了几个配置项（如 chromedriver_path、chromium_binary_path 和 json_file_path）。
这些配置用于管理插件的执行环境和路径信息。
"""
import os
from pydantic import BaseSettings

class Config(BaseSettings):
    """
    统一管理插件所需的配置信息。
    Attributes:
        chromedriver_path: Chromedriver 可执行文件路径。
        chromium_binary_path: Chromium 或 Google Chrome 可执行文件路径，用于 Playwright 或 Selenium。
        json_file_path: urls.json 的绝对路径，用于管理各平台链接。
    """
    chromedriver_path: str = "/usr/bin/chromedriver"
    chromium_binary_path: str = "/root/.cache/ms-playwright/chromium-1148/chrome-linux/chrome"

    # 动态设置 urls.json 的路径
    json_file_path: str = os.path.join(os.path.dirname(__file__), "urls.json")

config = Config()

