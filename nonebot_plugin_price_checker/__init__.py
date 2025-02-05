"""
插件项目名：nonebot_plugin_price_checker
---------------------------
这是一个用于查询多个平台银价的 NoneBot 插件。
---------------------------
初始化文件：__init__.py
"""

from nonebot import on_command
from nonebot.adapters.onebot.v11 import MessageSegment
from nonebot.log import logger
from .crawler import get_all_prices
from .renderer import render_image

# 定义命令触发词，如：/银价 或 /查银价 或 /价格
price_checker = on_command("银价", aliases={"查银价", "价格"}, priority=5, block=True)

@price_checker.handle()
async def handle_price():
    """
    处理查询银价的命令流程：
    1. 从各平台爬取最新银价并进行计算。
    2. 将数据渲染为截图。
    3. 发送截图给用户。
    """
    try:
        logger.info("开始处理银价查询命令...")

        # 1. 获取各平台的银价数据
        prices = await get_all_prices()
        if not prices:
            logger.warning("未获取到银价信息")
            await price_checker.finish("未获取到银价信息，请稍后重试。")
            return

        logger.info(f"获取到银价数据：{prices}")

         # 2. 渲染截图为 Base64
        logger.info("开始渲染图片...")
        try:
            image_base64 = await render_image(prices)
            logger.info("图片渲染成功")
        except Exception as e:
            logger.error(f"图片渲染失败：{e}")
            await price_checker.finish(f"图片渲染失败：{e}")
            return

        # 3. 发送 Base64 图片
        logger.info("开始发送图片...")
        try:
            await price_checker.send(MessageSegment.image(f"base64://{image_base64}"))
            logger.info("图片发送成功")
        except Exception as e:
            logger.error(f"发送图片失败：{e}")
            await price_checker.finish(f"发送图片失败：{e}")
            return

    except Exception as e:
        logger.error(f"生成银价图片失败：{e}")
        await price_checker.finish(f"生成银价图片失败：{e}")
