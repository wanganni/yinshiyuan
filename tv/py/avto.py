#!/usr/bin/env python3  
# -*- coding: utf-8 -*-  
  
"""  
AVToday 爬虫 for Termux  
功能：  
- 提取视频封面图片链接、标题、详情链接、日期、演员  
- 保存为 SQLite 数据库 (avtoday.db)  
- 保存为 TXT 文件 (videos.txt)  
- 生成 IPTV 格式的 M3U 播放列表 (playlist.m3u)  
- 多线程智能爬取所有分页  
- 数据保存在 /sdcard/avtoday_data/  
"""  
  
import os  
import re  
import time  
import sqlite3  
import threading  
from queue import Queue  
from urllib.parse import urljoin  
  
import requests  
from bs4 import BeautifulSoup  
  
# ========== 配置 ==========  
BASE_URL = "https://avtoday.io/chs/"          # 起始爬取页面（首页）  
HEADERS = {  
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",  
    "Accept-Language": "zh-CN,zh;q=0.9",  
}  
SAVE_DIR = "/sdcard/avtoday_data"              # 手机根目录下的文件夹  
THREAD_NUM = 5                                 # 并发线程数  
REQUEST_DELAY = 1                              # 每个请求间隔秒数（避免反爬）  
  
# 数据库和文件路径  
DB_PATH = os.path.join(SAVE_DIR, "avtoday.db")  
TXT_PATH = os.path.join(SAVE_DIR, "videos.txt")  
M3U_PATH = os.path.join(SAVE_DIR, "playlist.m3u")  
  
# 线程锁，用于安全写入文件  
db_lock = threading.Lock()  
txt_lock = threading.Lock()  
m3u_lock = threading.Lock()  
  
# 全局已处理 URL 集合（避免重复）  
seen_urls = set()  
url_lock = threading.Lock()  
  
# 待爬取队列  
page_queue = Queue()  
  
  
# ========== 辅助函数 ==========  
def init_save_dir():  
    """创建保存目录并初始化文件"""  
    os.makedirs(SAVE_DIR, exist_ok=True)  
    # 初始化数据库  
    conn = sqlite3.connect(DB_PATH)  
    c = conn.cursor()  
    c.execute('''  
        CREATE TABLE IF NOT EXISTS videos (  
            id INTEGER PRIMARY KEY AUTOINCREMENT,  
            title TEXT,  
            image_url TEXT,  
            detail_url TEXT UNIQUE,  
            date TEXT,  
            actor TEXT  
        )  
    ''')  
    conn.commit()  
    conn.close()  
    # 清空旧的 TXT 和 M3U 文件（重新运行会覆盖）  
    with open(TXT_PATH, 'w', encoding='utf-8') as f:  
        f.write("")  
    with open(M3U_PATH, 'w', encoding='utf-8') as f:  
        f.write("#EXTM3U\n")  
  
  
def save_to_db(title, image_url, detail_url, date, actor):  
    """线程安全地保存数据到 SQLite"""  
    with db_lock:  
        conn = sqlite3.connect(DB_PATH)  
        c = conn.cursor()  
        try:  
            c.execute('''  
                INSERT OR IGNORE INTO videos (title, image_url, detail_url, date, actor)  
                VALUES (?, ?, ?, ?, ?)  
            ''', (title, image_url, detail_url, date, actor))  
            conn.commit()  
        except Exception as e:  
            print(f"数据库写入错误: {e}")  
        finally:  
            conn.close()  
  
  
def save_to_txt(title, image_url, detail_url, date, actor):  
    """线程安全地追加到 TXT 文件（一行一条记录）"""  
    line = f"{title}\t{image_url}\t{detail_url}\t{date}\t{actor}\n"  
    with txt_lock:  
        with open(TXT_PATH, 'a', encoding='utf-8') as f:  
            f.write(line)  
  
  
def save_to_m3u(title, image_url, detail_url, date, actor):  
    """  
    生成 IPTV 格式 M3U 条目。  
    #EXTINF 参数简介：  
        tvg-logo="图片链接"  作为节目图标  
        group-title="分类"  可选，这里用日期作为分组  
    """  
    # 清理标题中的特殊字符  
    safe_title = title.replace('"', '\\"').strip()  
    # 使用日期作为分组名（若无则用 "未知"）  
    group = date if date else "未知日期"  
    extinf = f'#EXTINF:-1 tvg-logo="{image_url}" group-title="{group}",{safe_title}'  
    with m3u_lock:  
        with open(M3U_PATH, 'a', encoding='utf-8') as f:  
            f.write(extinf + "\n")  
            f.write(detail_url + "\n")  
  
  
def extract_image_from_style(style_str):  
    """从 style 字符串中提取 background-image 的 url"""  
    if not style_str:  
        return ""  
    match = re.search(r'url\([\'"]?([^\'"\)]+)[\'"]?\)', style_str)  
    if match:  
        url = match.group(1)  
        if url.startswith("//"):  
            url = "https:" + url  
        return url  
    return ""  
  
  
def parse_video_card(card):  
    """解析单个视频卡片，返回 (title, image_url, detail_url, date, actor)"""  
    try:  
        # 提取详情链接和标题  
        title_elem = card.find("div", class_="video-title")  
        if not title_elem:  
            return None  
        a_tag = title_elem.find("a")  
        if not a_tag:  
            return None  
        title = a_tag.get_text(strip=True)  
        detail_url = urljoin(BASE_URL, a_tag.get("href", ""))  
  
        # 提取图片链接：从 video 标签的 style 背景图中获取  
        video_card = card.find("div", class_="video-card")  
        video_tag = video_card.find("video") if video_card else None  
        image_url = ""  
        if video_tag and video_tag.get("style"):  
            image_url = extract_image_from_style(video_tag["style"])  
        else:  
            # 备用：通过 data-spcode 构造图片 URL（如果直接访问图片目录）  
            spcode = video_card.get("data-spcode") if video_card else ""  
            if spcode and not image_url:  
                # 网站封面图片路径一般是 /pic/年份/月份/番号-数字.jpg  
                # 无法精确构造，故仅当 style 提取失败时使用默认占位  
                image_url = ""  
  
        # 提取日期和演员  
        row = card.find("div", class_="row")  
        date = ""  
        actor = ""  
        if row:  
            date_div = row.find("div", class_="video-date")  
            if date_div:  
                date = date_div.get_text(strip=True)  
            actor_div = row.find("div", class_="video-actor")  
            if actor_div:  
                actor = actor_div.get_text(strip=True)  
  
        return (title, image_url, detail_url, date, actor)  
    except Exception as e:  
        print(f"解析卡片出错: {e}")  
        return None  
  
  
def parse_page(url):  
    """请求页面，解析所有视频卡片，返回下一页面 URL（若有）"""  
    try:  
        print(f"正在爬取: {url}")  
        resp = requests.get(url, headers=HEADERS, timeout=10)  
        resp.encoding = "utf-8"  
        if resp.status_code != 200:  
            print(f"请求失败，状态码 {resp.status_code}")  
            return None  
  
        soup = BeautifulSoup(resp.text, "html.parser")  
        # 查找所有视频卡片（根据实际结构）  
        cards = soup.find_all("div", class_="thumbnail")  
        if not cards:  
            # 备用选择器  
            cards = soup.find_all("div", class_="col", recursive=True)  
            cards = [c for c in cards if c.find("div", class_="video-card")]  
  
        new_items = 0  
        for card in cards:  
            # 过滤广告卡片（通常没有 real-card 类或包含 iframe）  
            if card.find("iframe"):  
                continue  
            data = parse_video_card(card)  
            if data:  
                title, image_url, detail_url, date, actor = data  
                # 去重  
                with url_lock:  
                    if detail_url in seen_urls:  
                        continue  
                    seen_urls.add(detail_url)  
                # 保存  
                save_to_db(title, image_url, detail_url, date, actor)  
                save_to_txt(title, image_url, detail_url, date, actor)  
                save_to_m3u(title, image_url, detail_url, date, actor)  
                new_items += 1  
                print(f"  ✓ {title}")  
  
        print(f"当前页面解析完成，新增 {new_items} 条记录")  
  
        # 查找“更多”按钮或下一页链接  
        more_block = soup.find("div", class_="more-block")  
        if more_block and more_block.get("data-src"):  
            next_url = more_block["data-src"]  
            if next_url.startswith("/"):  
                next_url = urljoin(BASE_URL, next_url)  
            return next_url  
        else:  
            # 尝试寻找分页链接（如页码按钮）  
            pagination = soup.find("ul", class_="pagination")  
            if pagination:  
                next_li = pagination.find("li", class_="next")  
                if next_li:  
                    a = next_li.find("a")  
                    if a and a.get("href"):  
                        return urljoin(url, a["href"])  
        return None  
    except Exception as e:  
        print(f"解析页面出错 {url}: {e}")  
        return None  
  
  
def worker():  
    """线程工作函数：从队列中取出 URL 进行爬取，并将新发现的 URL 加入队列"""  
    while True:  
        url = page_queue.get()  
        if url is None:  
            break  
        next_url = parse_page(url)  
        if next_url:  
            # 检查是否已加入队列或已爬取  
            with url_lock:  
                if next_url not in seen_urls:  
                    seen_urls.add(next_url)  
                    page_queue.put(next_url)  
        # 控制请求频率  
        time.sleep(REQUEST_DELAY)  
        page_queue.task_done()  
  
  
def main():  
    print("初始化...")  
    init_save_dir()  
    print(f"数据将保存到: {SAVE_DIR}")  
  
    # 起始页入队  
    page_queue.put(BASE_URL)  
    with url_lock:  
        seen_urls.add(BASE_URL)  
  
    # 启动线程  
    threads = []  
    for _ in range(THREAD_NUM):  
        t = threading.Thread(target=worker)  
        t.daemon = True  
        t.start()  
        threads.append(t)  
  
    # 等待所有任务完成  
    page_queue.join()  
    # 停止工作线程  
    for _ in range(THREAD_NUM):  
        page_queue.put(None)  
    for t in threads:  
        t.join()  
  
    print("\n爬取完成！")  
    print(f"SQLite 数据库: {DB_PATH}")  
    print(f"TXT 文件: {TXT_PATH}")  
    print(f"IPTV M3U 文件: {M3U_PATH}")  
  
  
if __name__ == "__main__":  
    main()  
