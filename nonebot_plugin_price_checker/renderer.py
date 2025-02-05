"""
renderer.py
-----------
利用 Playwright 渲染 HTML 模板并截图，返回 Base64 编码。
在此版本中，我们使用 `page.add_style_tag` 和 `page.add_script_tag` 来注入外部 CSS / JS。
"""
"""
renderer.py
-----------
利用 Playwright 渲染 HTML 模板并截图，返回 Base64 编码。
"""
import json
import base64
from pathlib import Path
from playwright.async_api import async_playwright

# 关键：引入 NoneBot 自带的日志器
from nonebot.log import logger

HTML_TEMPLATE_PATH = Path(__file__).parent / "templates" / "index.html"
CSS_FILE_PATH = Path(__file__).parent / "templates" / "css" / "price.css"
CHART_JS_FILE_PATH = Path(__file__).parent / "templates" / "js" / "chart.js"

# 获取数据库文件所在目录，确保文件保存路径正确
DATABASE_DIR = Path(__file__).resolve().parents[3] / "data" / "price_checker"
TO_HTML_PATH = DATABASE_DIR / "to_html.json"

async def render_image(prices: dict) -> str:
    """
    使用 Playwright 渲染 HTML 并返回截图的 Base64 编码。
    """
    try:
        
        # 读取 HTML 模板内容
        html_template = HTML_TEMPLATE_PATH.read_text(encoding="utf-8")
    except Exception as e:
        raise RuntimeError(f"读取模板文件失败: {e}")
    # 获取当前最低的银价数据
    display_prices = {}
    for platform, data in prices.items():
        current_avg = float(data["current_avg"].split()[0])
    
        # 获取昨日和前日的最低价
        trend = data["trend"]
        trend_lowest_prices = trend["lowest_prices"]

        # 获取前三天的最低银价
        last_three_days = trend_lowest_prices[:3]

        # 选择今日最低，昨日最低，前日最低
        display_prices[platform] = {
            "current_avg": f"{current_avg:.3f} 元/万银",
            "today_lowest": f"{last_three_days[0]:.3f} 元/万银",
            "yesterday_lowest": f"{last_three_days[1]:.3f} 元/万银" if len(last_three_days) > 1 else "N/A",
            "pre_yesterday_lowest": f"{last_three_days[2]:.3f} 元/万银" if len(last_three_days) > 2 else "N/A"
        }
    # 将爬取的数据保存为 to_html.json 文件
    with open(TO_HTML_PATH, 'w', encoding='utf-8') as file:
        json.dump(display_prices, file, ensure_ascii=False, indent=4)
    # logger.info(f"银价数据已保存到 {TO_HTML_PATH}")
    # 将爬取的银价数据传递给前端模板
    prices_json = json.dumps(display_prices, ensure_ascii=False)
    
    # 日志 1：打印将要替换的 JSON 数据
    # logger.info(f"即将替换到模板中的 prices JSON 数据: {prices_json}")

    # 在模板中替换占位符 {DD373_data} 为真实的 JSON
    html_content = html_template.replace("{DD373_data}", prices_json)

    async with async_playwright() as playwright:
         # 创建一个移动设备配置
        mobile_viewport = {
            "viewport": {"width": 375, "height": 812},  # iPhone X 尺寸
            "device_scale_factor": 3,                   # 屏幕比例
            "is_mobile": True,                          # 启用移动设备模式
            "has_touch": True,                          # 启用触摸事件
        }
         # PC端视口配置（横向三平台布局）
        pc_viewport = {
            "viewport": {"width": 1280, "height": 800},  # PC端适配的宽高
            "device_scale_factor": 1,  # 屏幕比例
            "is_mobile": False,        # 禁用移动设备模式
            "has_touch": False         # 禁用触摸事件
        }
        browser = await playwright.chromium.launch(headless=True)
        # 指定使用上海时区，UTC+8
        context = await browser.new_context(**mobile_viewport, timezone_id="Asia/Shanghai" ) 
        # 监听 context 或 page 的 console 事件
        # context.on("console", lambda msg: logger.info(f"[PAGE CONSOLE] {msg.type}: {msg.text}"))
        
        page = await context.new_page()
        # 在你 renderer.py 的 render_image 里，和 console 监听相似：
        # page.on("pageerror", lambda exc: logger.error(f"[PAGE ERROR] {exc.message}"))
        # 在将 HTML 设置到页面前，再输出一条日志
        # logger.info("即将调用 page.set_content() 进行渲染...")
         # 1. 设置页面内容（仅包含我们的 index.html, 不包含外部链接）
        await page.set_content(html_content, wait_until="domcontentloaded")
        # 2. 注入 CSS
        await page.add_style_tag(path=str(CSS_FILE_PATH))
        # 3. 注入 chart.js
        await page.add_script_tag(path=str(CHART_JS_FILE_PATH))
        # 4. 等待 .platform-card 出现（前端 JS 渲染逻辑生效后才会有此元素）
        await page.wait_for_selector(".platform-card", timeout=10000)
        # 5. 截图
        screenshot_bytes = await page.screenshot(full_page=True)
        await browser.close()
    # 6. 返回 Base64 编码的图片
    return base64.b64encode(screenshot_bytes).decode("utf-8")
