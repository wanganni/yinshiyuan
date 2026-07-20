#!/usr/bin/env python3
# coding=utf-8
import json
import os
import random
import re
import shutil
import sqlite3
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter

try:
    from base.spider import Spider as BaseSpider
except Exception:

    class BaseSpider:
        pass


# ====================== 【全局唯一输出根目录 按你要求修改】 ======================
BIND_OUTPUT_ROOT = "/storage/emulated/0/lz/wj/"
# 旧源目录
OLD_ROOT_DIR = "/storage/emulated/0/女优库"
# 迁移完成标记文件
MIGRATE_FLAG_FILE = os.path.join(BIND_OUTPUT_ROOT, ".migrate_success.flag")

# 自动拼接子文件夹：lz/wj/下面新建「女优库」
OUTPUT_DIR = os.path.join(BIND_OUTPUT_ROOT, "女优库")

# 路径自动派生
PROGRESS_FILE = os.path.join(OUTPUT_DIR, "crawl_progress.json")
GLOBAL_M3U_FILE = os.path.join(OUTPUT_DIR, "女优库全集.m3u")
DB_FILE = os.path.join(OUTPUT_DIR, "女优库汇总.db")

# ====================== 爬虫核心配置（完全不变） ======================
HOST = "https://whos.tv"
TIMEOUT = 45
MAX_RETRIES = 15
GLOBAL_THREADS = 20
REQUEST_DELAY = (1.0, 2.5)

# 兜底占位图
BACKUP_PIC = "https://img.icons8.com/fluency/300/000000/video.png"

# UA池
USER_AGENTS = [
    "Mozilla/5.0 (Linux; Android 15; Pixel 8 Pro) AppleWebKit/537.36 Chrome/124.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 Chrome/123.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 Chrome/122.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; SM-G998B) AppleWebKit/537.36 Chrome/121.0.0.0 Mobile Safari/537.36",
]

# ====================== 全局变量（不变） ======================
session = requests.Session()
session.mount(
    "https://", HTTPAdapter(pool_connections=100, pool_maxsize=200, max_retries=3)
)
session.mount(
    "http://", HTTPAdapter(pool_connections=100, pool_maxsize=200, max_retries=3)
)

file_lock = threading.Lock()
db_lock = threading.Lock()
start_time = time.time()
total_actor_pages = 0
current_actor_page = 0
total_actresses = 0
current_actress = 0


# ====================== 日志函数（原版无精简不变） ======================
def log(msg):
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def log_actor_list_full_progress():
    global current_actor_page, total_actor_pages, start_time
    if total_actor_pages == 0:
        return
    current_actor_page = min(current_actor_page, total_actor_pages)
    percent = round(current_actor_page / total_actor_pages * 100, 1)
    elapsed = time.time() - start_time
    speed = round(current_actor_page / elapsed, 2) if elapsed > 0 else 0
    remaining_pages = total_actor_pages - current_actor_page
    eta = int(remaining_pages / speed) if speed > 0 else 0
    eta_str = str(timedelta(seconds=eta)).split(".")[0]
    print(
        f"\r解析女优列表页码: {percent}% | {current_actor_page}/{total_actor_pages} 剩余:{eta_str} {speed}页/s",
        end="",
        flush=True,
    )


def log_actress_total_progress():
    global total_actresses, current_actress, start_time
    if total_actresses == 0:
        return
    percent = round(current_actress / total_actresses * 100, 1)
    elapsed = time.time() - start_time
    speed = round(current_actress / elapsed * 60, 2) if elapsed > 0 else 0
    remaining = total_actresses - current_actress
    eta = int(remaining / speed * 60) if speed > 0 else 0
    eta_str = str(timedelta(seconds=eta)).split(".")[0]
    log(f"预估剩余时间: {eta_str} | 抓取速度: {speed} 个/分钟")
    log("=" * 50)


# ====================== 【核心：严格顺序迁移模块】 ======================
def migrate_workspace_once():
    if os.path.exists(MIGRATE_FLAG_FILE):
        log("✅ 检测到迁移标记，跳过迁移流程")
        return

    log("🚀 首次运行，执行标准化迁移（顺序：记录文件 → 整文件夹）")
    os.makedirs(BIND_OUTPUT_ROOT, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 第一步：迁移进度记录文件
    old_progress = os.path.join(OLD_ROOT_DIR, "crawl_progress.json")
    new_progress = PROGRESS_FILE
    if os.path.exists(old_progress):
        if not os.path.exists(new_progress):
            try:
                shutil.copy2(old_progress, new_progress)
                log(f"📄 第一步：进度记录迁移完成")
            except Exception as e:
                log(f"⚠️ 进度文件迁移失败：{str(e)[:40]}，不影响主程序")
        else:
            log("ℹ️ 目标进度文件已存在，跳过")
    else:
        log("ℹ️ 旧目录无进度文件，跳过第一步")

    # 第二步：迁移整个女优库文件夹
    if os.path.exists(OLD_ROOT_DIR):
        if not any(os.listdir(OUTPUT_DIR)):
            try:
                for item in os.listdir(OLD_ROOT_DIR):
                    s_item = os.path.join(OLD_ROOT_DIR, item)
                    d_item = os.path.join(OUTPUT_DIR, item)
                    if not os.path.exists(d_item):
                        if os.path.isdir(s_item):
                            shutil.copytree(s_item, d_item, dirs_exist_ok=True)
                        else:
                            shutil.copy2(s_item, d_item)
                log(f"📁 第二步：旧女优库全部迁移至 /lz/wj/女优库/")
                try:
                    shutil.rmtree(OLD_ROOT_DIR)
                    log("🗑️ 旧根目录女优库已删除")
                except Exception:
                    log("ℹ️ 旧目录无法删除，不影响使用")
            except Exception as e:
                log(f"⚠️ 文件夹迁移失败：{str(e)[:40]}，继续运行")
        else:
            log("ℹ️ /lz/wj/女优库/已有数据，防止覆盖跳过迁移")
    else:
        log("ℹ️ 旧 /storage/emulated/0/女优库 不存在，跳过第二步")

    # 生成永久标记
    try:
        with open(MIGRATE_FLAG_FILE, "w", encoding="utf-8") as f:
            f.write(
                f"migrate:{datetime.now().isoformat()}\nold:{OLD_ROOT_DIR}\nnew:{OUTPUT_DIR}"
            )
        log("🔖 迁移标记已生成，后续永久不再迁移")
    except Exception:
        log("⚠️ 标记生成失败，下次启动重试")


# ====================== 工具函数（全部不变） ======================
def norm_url(url):
    if not url:
        return BACKUP_PIC
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return HOST + url
    return url


def get_random_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Referer": HOST,
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Connection": "keep-alive",
    }


def safe_get_soup(url):
    for attempt in range(MAX_RETRIES):
        try:
            time.sleep(random.uniform(*REQUEST_DELAY))
            resp = session.get(url, headers=get_random_headers(), timeout=TIMEOUT)
            resp.encoding = "utf-8"
            if resp.status_code == 200:
                return BeautifulSoup(resp.text, "html.parser")
            elif resp.status_code in [403, 429]:
                sleep_sec = 5 * (attempt + 1)
                log(
                    f"⚠️ 访问受限{resp.status_code}，休眠{sleep_sec}s 重试{attempt + 1}/{MAX_RETRIES}"
                )
                time.sleep(sleep_sec)
        except Exception as e:
            sleep_sec = 3 * (attempt + 1)
            log(
                f"⚠️ 网络异常[{str(e)[:35]}]，休眠{sleep_sec}s 重试{attempt + 1}/{MAX_RETRIES}"
            )
            time.sleep(sleep_sec)
    log(f"❌ {MAX_RETRIES}次重试全部失败: {url}")
    return None


# ====================== SQLite数据库（不变） ======================
def init_database():
    with db_lock:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS actress_info (
            id TEXT PRIMARY KEY,
            actress_name TEXT NOT NULL,
            total_video_num INTEGER DEFAULT 0,
            success_video_num INTEGER DEFAULT 0,
            crawl_time TEXT NOT NULL,
            status TEXT DEFAULT "pending"
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS video_detail (
            vid TEXT PRIMARY KEY,
            actress_id TEXT NOT NULL,
            vod_name TEXT NOT NULL,
            vod_pic TEXT NOT NULL,
            vod_tags TEXT,
            vod_content TEXT,
            vod_play_url TEXT,
            crawl_time TEXT NOT NULL,
            FOREIGN KEY (actress_id) REFERENCES actress_info(id)
        )
        """)
        conn.commit()
        conn.close()
    log(f"🗄️ 数据库初始化完成: {DB_FILE}")


def insert_actress_to_db(actress_id, actress_name, total_num, success_num):
    now_time = datetime.now().isoformat()
    with db_lock:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO actress_info VALUES (?,?,?,?,?,?)",
            (actress_id, actress_name, total_num, success_num, now_time, "completed"),
        )
        conn.commit()
        conn.close()


def insert_video_to_db(
    vid, actress_id, vod_name, vod_pic, vod_tags, vod_content, vod_play_url
):
    now_time = datetime.now().isoformat()
    tag_str = ",".join(vod_tags) if isinstance(vod_tags, list) else str(vod_tags)
    with db_lock:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO video_detail VALUES (?,?,?,?,?,?,?,?)",
            (
                vid,
                actress_id,
                vod_name,
                vod_pic,
                tag_str,
                vod_content,
                vod_play_url,
                now_time,
            ),
        )
        conn.commit()
        conn.close()


# ====================== 文件初始化 ======================
def init_all_folder_file():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with file_lock:
        if not os.path.exists(GLOBAL_M3U_FILE):
            with open(GLOBAL_M3U_FILE, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n#EXT-X-VERSION:3\n")
    init_database()
    log(f"📂 当前工作目录: {OUTPUT_DIR}")


class ProgressTracker:
    def __init__(self):
        self.data = {}
        if os.path.exists(PROGRESS_FILE):
            try:
                with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception:
                self.data = {}

    def save(self):
        with file_lock:
            with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)

    def is_actress_finished(self, aid):
        return aid in self.data

    def mark_actress_finished(self, aid, total=0, success=0):
        self.data[aid] = {
            "status": "finished",
            "total_video": total,
            "success_video": success,
            "update_time": datetime.now().isoformat(),
        }
        self.save()


pg_tracker = ProgressTracker()


# ====================== 爬虫业务逻辑【完全原样不动】 ======================
def crawl_actress_page(page_num):
    global total_actor_pages, current_actor_page
    url = f"{HOST}/actresses?page={page_num}" if page_num > 1 else f"{HOST}/actresses"
    soup = safe_get_soup(url)
    if not soup:
        current_actor_page += 1
        log_actor_list_full_progress()
        return []
    for a_tag in soup.find_all("a", href=True):
        match = re.search(r"page-(\d+)|page=(\d+)", a_tag["href"])
        if match:
            total_actor_pages = max(
                total_actor_pages, int(match.group(1) or match.group(2))
            )
    actress_list = []
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if (
            href.startswith("/actresses/")
            and href != "/actresses"
            and "page" not in href
        ):
            aid = href.split("/")[-1]
            if not pg_tracker.is_actress_finished(aid):
                img_tag = a_tag.find("img")
                name = img_tag.get("alt", aid).strip() if img_tag else aid
                actress_list.append({"aid": aid, "name": name})
    current_actor_page += 1
    log_actor_list_full_progress()
    return actress_list


def parse_video_full_info(video_url, video_title, actress_aid, actress_name):
    vid = video_url.split("/")[-1]
    soup = safe_get_soup(video_url)
    real_pic = ""
    if soup:
        cover_cls = soup.find(class_=re.compile("cover|preview|thumbnail|poster"))
        if cover_cls and cover_cls.get("src"):
            real_pic = cover_cls.get("src")
        else:
            og_img_meta = soup.find("meta", property="og:image")
            if og_img_meta and og_img_meta.get("content"):
                real_pic = og_img_meta.get("content")
    vod_pic = norm_url(real_pic)
    tag_list = []
    if soup:
        tag_tags = soup.find_all(class_=re.compile("tag|label|category|keyword|badge"))
        for t in tag_tags:
            tag_text = t.get_text(strip=True)
            if tag_text and len(tag_text) > 1 and tag_text not in tag_list:
                tag_list.append(tag_text)
    content_text = "暂无影片详细介绍"
    if soup:
        detail_box = soup.find(
            class_=re.compile("detail|intro|synopsis|description|full-content")
        )
        if detail_box:
            content_text = (
                detail_box.get_text(strip=True).replace("\n", " ").replace("\r", " ")
            )
    vod_content = f"<p>　　{content_text}</p>"
    m3u8_link = ""
    if soup:
        m_match = re.search(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', str(soup))
        if m_match:
            m3u8_link = norm_url(m_match.group(1))
    vod_play_url = f"高清${video_url}$$$高清${m3u8_link}"
    video_item = {
        "vod_id": vid,
        "vod_name": video_title,
        "vod_pic": vod_pic,
        "vod_actor": actress_name,
        "vod_director": "whos.tv",
        "vod_remarks": "HD高清",
        "vod_pubdate": datetime.now().strftime("%Y-%m-%d"),
        "vod_area": "日本",
        "vod_year": datetime.now().strftime("%Y"),
        "vod_tags": tag_list,
        "vod_content": vod_content,
        "vod_play_from": "dytt$$$dyttm3u8",
        "vod_play_url": vod_play_url,
        "type_name": "成人影片",
    }
    insert_video_to_db(
        vid, actress_aid, video_title, vod_pic, tag_list, vod_content, vod_play_url
    )
    return video_item


def append_to_m3u(video_item):
    play_link = video_item["vod_play_url"].split("$$$")[-1].split("$")[-1]
    line = f'#EXTINF:-1 tvg-logo="{video_item["vod_pic"]}" group-title="{video_item["vod_actor"]}",{video_item["vod_name"]}\n{play_link}\n'
    with file_lock:
        with open(GLOBAL_M3U_FILE, "a", encoding="utf-8") as f:
            f.write(line)


def crawl_single_actress_task(actress_data):
    global current_actress
    aid = actress_data["aid"]
    a_name = actress_data["name"]
    base_url = f"{HOST}/actresses/{aid}"
    home_soup = safe_get_soup(base_url)
    if not home_soup:
        log(f"❌ 【{a_name}】主页访问失败，跳过")
        pg_tracker.mark_actress_finished(aid, 0, 0)
        insert_actress_to_db(aid, a_name, 0, 0)
        current_actress += 1
        return
    max_video_page = 1
    for a_tag in home_soup.find_all("a", href=True):
        p_match = re.search(r"/page-(\d+)", a_tag["href"])
        if p_match:
            max_video_page = max(max_video_page, int(p_match.group(1)))
    log(f"📌 【{a_name}】作品总页数: {max_video_page} 页")
    all_video_source = []
    for page in range(1, max_video_page + 1):
        page_url = f"{base_url}/page-{page}" if page > 1 else base_url
        page_soup = safe_get_soup(page_url)
        if not page_soup:
            continue
        for box_a in page_soup.find_all("a", href=True):
            href = box_a["href"]
            if href.startswith("/videos/") and "page" not in href:
                img_tag = box_a.find("img")
                title = (
                    img_tag.get("alt", "未知作品").strip()
                    if img_tag
                    else href.split("/")[-1]
                )
                all_video_source.append({"url": norm_url(href), "title": title})
    if not all_video_source:
        log(f"📭 【{a_name}】无任何作品")
        pg_tracker.mark_actress_finished(aid, 0, 0)
        insert_actress_to_db(aid, a_name, 0, 0)
        current_actress += 1
        return
    log(f"🎞️ 【{a_name}】待解析视频: {len(all_video_source)} 个")
    success_count = 0
    video_json_list = []
    with ThreadPoolExecutor(max_workers=GLOBAL_THREADS) as executor:
        future_map = {
            executor.submit(parse_video_full_info, v["url"], v["title"], aid, a_name): v
            for v in all_video_source
        }
        for future in as_completed(future_map):
            try:
                item = future.result(timeout=60)
                video_json_list.append(item)
                append_to_m3u(item)
                success_count += 1
            except TimeoutError:
                log("⚠️ 单个视频超时跳过")
                continue
            except Exception as e:
                log(f"⚠️ 视频解析异常: {str(e)[:30]}")
                continue
    json_save_path = os.path.join(OUTPUT_DIR, f"{a_name}.json")
    with file_lock:
        with open(json_save_path, "w", encoding="utf-8") as f:
            json.dump({"list": video_json_list}, f, ensure_ascii=False, indent=2)
    insert_actress_to_db(aid, a_name, len(all_video_source), success_count)
    pg_tracker.mark_actress_finished(aid, len(all_video_source), success_count)
    current_actress += 1
    log(f"✅ 【{a_name}】完成 | 总数:{len(all_video_source)} 成功:{success_count}")
    log_actress_total_progress()


# ====================== TVBox / Hipy 插件入口 ======================
class Spider(BaseSpider):
    def init(self, extend=""):
        pass

    def getName(self):
        return "女优库"

    def homeContent(self, filter):
        return {"class": [{"type_id": "actresses", "type_name": "女优"}]}

    def homeVideoContent(self):
        return self.categoryContent("actresses", "1", False, {}).get("list", [])

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg or 1)
        if tid != "actresses":
            return {"list": [], "page": page, "pagecount": 1}

        url = f"{HOST}/actresses?page={page}" if page > 1 else f"{HOST}/actresses"
        soup = safe_get_soup(url)
        if not soup:
            return {"list": [], "page": page, "pagecount": 1}

        videos = []
        for item in self._parse_actresses(soup):
            videos.append(
                {
                    "vod_id": item["aid"],
                    "vod_name": item["name"],
                    "vod_pic": item.get("pic") or BACKUP_PIC,
                    "vod_remarks": "女优",
                }
            )

        return {
            "list": videos,
            "page": page,
            "pagecount": self._parse_pagecount(soup),
        }

    def detailContent(self, ids):
        aid = ids[0] if ids else ""
        if not aid:
            return {"list": []}

        soup = safe_get_soup(f"{HOST}/actresses/{aid}")
        if not soup:
            return {"list": []}

        name = self._parse_title(soup, aid)
        episodes = self._parse_videos(soup)
        if not episodes:
            return {"list": []}

        play_url = "#".join(f"{item['name']}${item['url']}" for item in episodes)
        return {
            "list": [
                {
                    "vod_id": aid,
                    "vod_name": name,
                    "vod_pic": self._parse_cover(soup),
                    "vod_actor": name,
                    "vod_director": "whos.tv",
                    "vod_content": f"<p>{name}</p>",
                    "vod_play_from": "whos",
                    "vod_play_url": play_url,
                }
            ]
        }

    def searchContent(self, key, quick, pg="1"):
        return {"list": [], "page": int(pg or 1)}

    def playerContent(self, flag, vid, vip_flags):
        play_url = self._parse_play_url(vid) or vid
        return {"jx": 0, "parse": 0, "url": play_url, "header": get_random_headers()}

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    def localProxy(self, param):
        pass

    def _parse_pagecount(self, soup):
        pagecount = 1
        for a_tag in soup.find_all("a", href=True):
            match = re.search(r"page-(\d+)|page=(\d+)", a_tag["href"])
            if match:
                pagecount = max(pagecount, int(match.group(1) or match.group(2)))
        return pagecount

    def _parse_actresses(self, soup):
        result = []
        seen = set()
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if not href.startswith("/actresses/") or href == "/actresses" or "page" in href:
                continue

            aid = href.rstrip("/").split("/")[-1]
            if not aid or aid in seen:
                continue

            seen.add(aid)
            img_tag = a_tag.find("img")
            name = img_tag.get("alt", aid).strip() if img_tag else a_tag.get_text(strip=True) or aid
            pic = BACKUP_PIC
            if img_tag:
                pic = norm_url(img_tag.get("src") or img_tag.get("data-src"))
            result.append({"aid": aid, "name": name, "pic": pic})
        return result

    def _parse_videos(self, soup):
        result = []
        seen = set()
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if not href.startswith("/videos/") or "page" in href:
                continue

            url = norm_url(href)
            if url in seen:
                continue

            seen.add(url)
            img_tag = a_tag.find("img")
            name = img_tag.get("alt", "").strip() if img_tag else ""
            if not name:
                name = a_tag.get_text(strip=True) or href.rstrip("/").split("/")[-1]
            result.append({"name": name, "url": url})
        return result

    def _parse_title(self, soup, fallback):
        for selector in ["h1", "title"]:
            tag = soup.find(selector)
            if tag and tag.get_text(strip=True):
                return tag.get_text(strip=True).replace(" - whos.tv", "")
        return fallback

    def _parse_cover(self, soup):
        img_tag = soup.find("img", src=True)
        if img_tag:
            return norm_url(img_tag.get("src"))
        return BACKUP_PIC

    def _parse_play_url(self, video_url):
        soup = safe_get_soup(video_url)
        if not soup:
            return ""
        match = re.search(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', str(soup))
        return norm_url(match.group(1)) if match else ""


# ====================== 主程序入口 ======================
def main():
    migrate_workspace_once()
    init_all_folder_file()

    log("=============================================")
    log("  20线程 | 重试15次 | 输出:/lz/wj/女优库/")
    log("=============================================")
    start_time = time.time()

    log("🔍 探测全站页码 & 解析女优列表...")
    crawl_actress_page(1)
    all_actress_pool = []
    with ThreadPoolExecutor(max_workers=GLOBAL_THREADS) as executor:
        futures_list = [
            executor.submit(crawl_actress_page, p)
            for p in range(1, total_actor_pages + 1)
        ]
        for ft in as_completed(futures_list):
            all_actress_pool.extend(ft.result() or [])
    unique_check = set()
    todo_actress_list = []
    for act in all_actress_pool:
        if act["aid"] not in unique_check:
            unique_check.add(act["aid"])
            todo_actress_list.append(act)
    total_actresses = len(todo_actress_list)
    current_actress = len(pg_tracker.data)
    log(f"\n📋 待抓取: {total_actresses} 位，已完成: {current_actress} 位")
    log_actress_total_progress()

    for idx, actress_item in enumerate(todo_actress_list, 1):
        log(f"\n>>>>>>>>>> {idx}/{total_actresses} : {actress_item['name']} <<<<<<<<<<")
        crawl_single_actress_task(actress_item)

    total_all_video = sum(v.get("total_video", 0) for v in pg_tracker.data.values())
    total_succ_video = sum(v.get("success_video", 0) for v in pg_tracker.data.values())
    total_use_min = round((time.time() - start_time) / 60, 2)
    log(
        "\n==================================== 任务结束 ================================"
    )
    log(f"运行时长: {total_use_min} 分钟 | 女优总数: {len(pg_tracker.data)}")
    log(f"解析视频: {total_all_video} 部 | 成功入库: {total_succ_video} 部")
    log(f"存储目录: {OUTPUT_DIR}")
    log(
        "=============================================================================="
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("\n🛑 手动中断，进度已保存，下次续爬不重跑")
        sys.exit(0)
    except Exception as e:
        log(f"\n❌ 程序异常: {str(e)[:60]}")
        sys.exit(1)
