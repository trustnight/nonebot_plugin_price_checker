"""
crawler.py
----------
负责爬取不同平台的银价信息，并更新和存储历史数据。
在此版本中，我们将数字保留 3 位小数。
"""
import sqlite3
import json
import aiohttp
import asyncio
from datetime import datetime
from bs4 import BeautifulSoup
from nonebot.log import logger
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pathlib import Path
from .config import config

# 数据库存放位置：/root/nonebot2/data/price_checker/prices_data.db
DATABASE_DIR = Path(__file__).resolve().parents[3] / "data" / "price_checker"
DATABASE_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_PATH = DATABASE_DIR / "prices_data.db"
TO_HTML_PATH = DATABASE_DIR / "to_html.json"

def init_db():
    """
    初始化数据库，创建表格，添加必要的字段。
    """
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # 创建 prices 表（存储当天和历史记录）
    cursor.execute('''CREATE TABLE IF NOT EXISTS prices (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        platform TEXT NOT NULL,
                        current_dates TEXT,  -- 存储当天日期，确保是标准的 DATETIME 格式
                        current_lowest REAL,
                        trend_dates TEXT,  -- 存储历史日期（当 `current_dates` 更新时，迁移旧数据到这里）
                        trend_prices TEXT  -- 存储历史最低价（对应于 `trend_dates`）
                    )''')

    conn.commit()
    conn.close()
def insert_price_data(platform, current_date, current_lowest, trend_dates, trend_prices):
    """
    插入银价数据到数据库，如果日期变化则迁移数据。
    """
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # 查询当前是否已有该平台的记录
    cursor.execute('''SELECT * FROM prices WHERE platform = ? AND current_dates = ? ORDER BY current_dates DESC LIMIT 1''', (platform, current_date))
    existing_record = cursor.fetchone()

    if existing_record:
        logger.debug(f"已有记录：{existing_record}")
        
        # 如果已有记录且当前银价低于记录中的最低银价，则更新最低银价
        if float(current_lowest) < float(existing_record[3]):  # Compare current_lowest and existing lowest price
            # 更新最低价
            cursor.execute('''UPDATE prices 
                              SET current_lowest = ?, trend_dates = ?, trend_prices = ?
                              WHERE platform = ? AND current_dates = ?''', 
                           (current_lowest, trend_dates, trend_prices, platform, current_date))
    else:
        # 插入新的记录（首次记录或日期不同）
        cursor.execute('''INSERT INTO prices (platform, current_lowest, current_dates, trend_dates, trend_prices) 
                          VALUES (?, ?, ?, ?, ?)''', 
                       (platform, current_lowest, current_date, trend_dates, trend_prices))

    conn.commit()
    conn.close()

async def get_dd373_prices(url: str, headers: dict) -> list:
    """
    异步爬取 DD373 平台的银价信息，提取前 10 个报价。
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status != 200:
                    logger.error(f"错误：无法获取 {url}，状态码：{response.status}")
                    return None
                text = await response.text()
                soup = BeautifulSoup(text, "lxml")
                price_tags = soup.find_all("p", class_="font12 color666 m-t5")
                prices = []
                for tag in price_tags[:10]:
                    text = tag.text.strip()
                    try:
                        price = float(text.split('=')[1].replace('元', ''))
                        prices.append(price)
                    except (IndexError, ValueError):
                        continue
                if prices:
                    return prices
                else:
                    logger.warning(f"警告：未能找到有效的银价数据，URL: {url}")
                    return None              
    except Exception as e:
        logger.exception(f"异常：在获取 {url} 时发生错误：{e}")
        return None
async def get_7881_prices(url: str) -> list:
    """
    异步爬取 7881 平台的银价信息，使用 Selenium 提取前 10 个报价。
    """
    loop = asyncio.get_event_loop()
    prices = await loop.run_in_executor(None, fetch_7881_prices, url)
    return prices
def fetch_7881_prices(url: str) -> list:
    """
    使用 Selenium 爬取 7881 平台的银价信息。
    """
    service = Service(config.chromedriver_path)
    options = Options()
    options.binary_location = config.chromium_binary_path
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.list-item-default"))
        )
        price_elements = driver.find_elements(By.CSS_SELECTOR, "div.list-item-default div.price-unit p")

        prices = []
        match_count = 0
        for element in price_elements:
            if "元/万银" in element.text:
                try:
                    price_text = element.text.split("元/万银")[0].strip()
                    prices.append(float(price_text))
                    match_count += 1
                    if match_count == 10:
                        break
                except ValueError:
                    continue
        return prices if prices else None

    except Exception:
        logger.exception(f"异常：在获取 {url} 时发生错误")
        return None
    finally:
        driver.quit()
async def get_uu898_prices(url: str, headers: dict) -> list:
    """
    异步爬取 UU898 平台的银价信息，提取前 10 个报价。
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status != 200:
                    logger.error(f"错误：无法获取 {url}，状态码：{response.status}")
                    return None
                soup = BeautifulSoup(await response.text(), "lxml")
                price_tags = soup.select("li.sp_li1 h6 span:last-child")
                prices = []

                for tag in price_tags[:10]:
                    text = tag.text.strip()
                    try:
                        price = float(text.split("元/万银")[0])
                        prices.append(price)
                    except (IndexError, ValueError):
                        continue

                return prices if prices else None
    except Exception as e:
        logger.exception(f"异常：在获取 {url} 时发生错误：{e}")
        return None
def fetch_recent_data(platform: str, count: int = 1):
    """
    查询数据库中某个平台最近 count 条记录，返回最近存储的 current_lowest 值。
    """
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT current_dates, current_lowest
        FROM prices
        WHERE platform = ?
        ORDER BY current_dates DESC
        LIMIT ?
    ''', (platform, count))

    rows = cursor.fetchall()
    conn.close()
    return rows

async def get_all_prices() -> dict:
    """
    1. 爬取各平台银价并计算平均价
    2. 查询数据库，比较 avg_value 是否小于 current_lowest
    3. 如果 avg_value < current_lowest，则更新数据库
    4. 返回最终的银价数据
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        )
    }

    all_prices = {}

    with open(config.json_file_path, 'r') as file:
        platforms = json.load(file)

    for platform, urls in platforms.items():
        # logger.info(f"开始爬取 {platform}，URL 列表: {urls}")  # 确保 3 个平台都被遍历
        platform_prices = []
        for url in urls:
            if platform == "DD373":
                prices = await get_dd373_prices(url, headers)
                logger.info(f"爬取到 {url} 的银价数据：{prices}")
            elif platform == "7881":
                prices = await get_7881_prices(url)
                logger.info(f"爬取到 {url} 的银价数据：{prices}")
            elif platform == "UU898":
                prices = await get_uu898_prices(url, headers)
                logger.info(f"爬取到 {url} 的银价数据：{prices}")
            else:
                prices = None

            if prices:
                platform_prices.extend(prices)

        if platform_prices:
            # 限制 avg_value 保留 3 位小数
            avg_value = round(sum(platform_prices) / len(platform_prices), 3)  # 计算当天的平均值并限制精度
            current_date = datetime.now().strftime("%Y-%m-%d")
            logger.debug(f"最新情报:{current_date}：{avg_value}")
            # 查询数据库中该平台的最新最低价
            recent_data = fetch_recent_data(platform, 1)
            if recent_data:
                try:
                    # 访问数据
                    last_date = recent_data[0][0]  # 获取最近存储的日期
                    last_lowest = recent_data[0][1]  # 获取最近存储的最低值

                except IndexError as e:
                    logger.error(f"IndexError: 访问 recent_data 发生错误 - {e}")
                    logger.error(f"recent_data 结构: {recent_data}")
                    return
                # 如果今天的日期与上次存储的日期不同
                if current_date != last_date:
                    # 迁移当前数据到历史数据
                    insert_price_data(
                        platform=platform,
                        current_date=current_date,  # 新的日期
                        current_lowest=avg_value,   # 当前最低价
                        trend_dates=last_date,      # 上次存储的日期迁移到 trend_dates
                        trend_prices=last_lowest    # 上次存储的最低价格迁移到 trend_prices
                    )
                else:
                    # 如果日期相同，比较新计算的 avg_value 和 last_lowest
                    if avg_value < last_lowest:
                        # 如果新爬取的 avg_value 小于 last_lowest，更新 current_lowest
                        insert_price_data(
                            platform=platform,
                            current_date=current_date,  # 更新日期
                            current_lowest=avg_value,   # 更新 current_lowest
                            trend_dates="",             # 传递空值，表示不更新历史数据
                            trend_prices=""             # 传递空值，表示不更新历史数据
                        )
                    else:
                        # 如果 avg_value >= last_lowest，只更新 current_avg
                        # 将 avg_value 直接传递给前端进行渲染
                        all_prices[platform] = {
                            "current_avg": f"{avg_value:.3f} 元/万银",  # 更新 avg_value
                            "current_lowest": f"{last_lowest:.3f} 元/万银",
                        }
            else:
                # 如果数据库没有记录，首次存入 avg_value 作为 current_lowest
                insert_price_data(
                    platform=platform,
                    current_date=current_date,
                    current_lowest=avg_value,
                    trend_dates="",  # 没有历史数据时，trend_dates 和 trend_prices 为空
                    trend_prices=""
                )
                last_lowest = avg_value  # 如果没有历史记录，使用 avg_value 作为 last_lowest
            # 获取最近 3 条数据来生成趋势数据
            rows = fetch_recent_data(platform, 3)
            trend_dates = []
            trend_lowest_prices = []

            for row in rows:
                trend_dates_str = row[0]  # 获取 trend_dates
                trend_lowest_price = row[1]  # 获取 trend_prices

                trend_dates.append(trend_dates_str)
                trend_lowest_prices.append(trend_lowest_price)

            trend_data = {
                "dates": trend_dates,
                "lowest_prices": trend_lowest_prices
            }

            # 确保有 trend 数据
            if trend_data["dates"]:
                all_prices[platform] = {
                    "current_avg": f"{avg_value:.3f} 元/万银",
                    "current_lowest": f"{avg_value:.3f} 元/万银",  # 更新显示为 avg_value
                    "trend": trend_data
                }
            else:
                # 如果没有趋势数据，则使用默认值
                all_prices[platform] = {
                    "current_avg": f"{avg_value:.3f} 元/万银",
                    "current_lowest": f"{last_lowest:.3f} 元/万银"
                }
    return all_prices

# 初始化数据库（在模块加载时执行一次）
init_db()
