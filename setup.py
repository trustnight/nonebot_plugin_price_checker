from setuptools import setup, find_packages

setup(
    name="nonebot-plugin-price-checker",  # 包名，使用驼峰命名
    version="0.1.1",  # 初始版本，发布时可以调整
    packages=find_packages(),  # 自动查找所有模块
    install_requires=[
        "nonebot2",  # NoneBot 的依赖
        "pydantic",  # 用于配置文件
        "aiohttp",  # 异步 HTTP 请求库
        "beautifulsoup4",  # 用于解析 HTML
        "selenium",  # 用于爬取 7881 数据
        "playwright",  # 用于页面截图渲染
        "sqlite3",  # 用于数据库操作
        "chart.js",  # 用于图表渲染（前端依赖）
    ],
    entry_points={
        "nonebot.plugin": [
            "price_checker = nonebot_plugin_price_checker:main",  # 设置插件的入口
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',  # Python 版本要求
)
