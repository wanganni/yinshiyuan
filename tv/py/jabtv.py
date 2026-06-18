import time
import os
import json
import sqlite3
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
# 核心升级：替换原生 requests，使用带有指纹伪装功能的 curl_cffi
from curl_cffi import requests

# --- 核心配置 ---
BASE_URL = "https://jable.tv"
# 模拟最新的 Chrome 浏览器 Header
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://jable.tv/",
}
MAX_WORKERS = 8 # 线程数，配合 curl_cffi 建议不要太高，稳定第一

# 路径自动管理
SAVE_DIR = os.path.expanduser("~/storage/shared/Download/Jable_Ultra_Data")
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

DB_PATH = os.path.join(SAVE_DIR, "jable_master.db")
JSON_PATH = os.path.join(SAVE_DIR, "jable_master.json")
M3U_PATH = os.path.join(SAVE_DIR, "jable_master.m3u")
TXT_PATH = os.path.join(SAVE_DIR, "jable_master.txt")
PROGRESS_FILE = os.path.join(SAVE_DIR, "spider_status.json")

class UltraSpider:
    def __init__(self):
        self.scanned_ids = set()
        self.last_tag_url = ""
        # 使用 check_same_thread=False 允许在多线程中操作同一个 DB 连接
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self._init_db()
        self.load_checkpoint()

    def _init_db(self):
        cursor = self.conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS videos 
                          (id TEXT PRIMARY KEY, title TEXT, category TEXT, poster TEXT, m3u8 TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
        self.conn.commit()

    def load_checkpoint(self):
        if os.path.exists(PROGRESS_FILE):
            try:
                with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.last_tag_url = data.get("last_tag_url", "")
            except: pass
        
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM videos")
        self.scanned_ids = set(row[0] for row in cursor.fetchall())
        print(f"✅ 已载入数据库记录: {len(self.scanned_ids)} 条")

    def safe_request(self, url):
        """核心防护：断网自动暂停，模拟 Chrome 指纹请求"""
        while True:
            try:
                # impersonate="chrome120" 是关键，它模拟了真实的浏览器 TLS 指纹
                res = requests.get(url, headers=HEADERS, timeout=15, impersonate="chrome120")
                if res.status_code == 200:
                    return res
                elif res.status_code == 404:
                    return None
                else:
                    print(f"\n⚠️ 触发限制 (Code: {res.status_code})，休眠 20 秒...")
                    time.sleep(20)
            except Exception:
                print(f"\r🔌 网络异常或已断开，挂机等待中... ", end="", flush=True)
                time.sleep(5)

    def save_item(self, data):
        """多格式同步保存"""
        # 1. 存入数据库 (DB)
        cursor = self.conn.cursor()
        try:
            cursor.execute("INSERT OR IGNORE INTO videos (id, title, category, poster, m3u8) VALUES (?,?,?,?,?)", 
                           (data['id'], data['title'], data['cat'], data['poster'], data['m3u8']))
            self.conn.commit()
        except: pass

        # 2. 追加到 M3U 和 TXT
        content = f'#EXTINF:-1, [{data["cat"]}] {data["title"]}\n{data["poster"]}\n{data["m3u8"]}\n'
        with open(M3U_PATH, "a", encoding="utf-8") as f: f.write(content)
        with open(TXT_PATH, "a", encoding="utf-8") as f: f.write(content)

    def get_video_m3u8(self, page_url):
        res = self.safe_request(page_url)
        if res:
            match = re.search(r"https?://[^\s'\" ]+\.m3u8", res.text)
            return match.group(0) if match else None
        return None

    def process_box(self, box, cat_name):
        try:
            a_tag = box.find("h6", class_="title").find("a")
            v_url = a_tag["href"]
            v_id = v_url.strip('/').split('/')[-1]
            
            if v_id in self.scanned_ids: return None
            
            m3u8 = self.get_video_m3u8(v_url)
            if not m3u8: return None
            
            img_tag = box.find("div", class_="img-box").find("img")
            poster = img_tag.get('data-src') or img_tag.get('src')
            
            result = {'id': v_id, 'title': a_tag.get_text(strip=True), 'cat': cat_name, 'poster': poster, 'm3u8': m3u8}
            self.scanned_ids.add(v_id)
            return result
        except: return None

    def start(self):
        print(f"🚀 终极防封爬虫已启动！")
        print(f"📂 存储目录: {SAVE_DIR}")
        
        entry_res = self.safe_request(BASE_URL)
        soup = BeautifulSoup(entry_res.text, "html.parser")
        tags = [{"name": t.get_text(strip=True), "url": t['href']} for t in soup.find_all("a", class_="tag")]

        is_skipping = True if self.last_tag_url else False
        
        for tag in tags:
            if is_skipping:
                if tag['url'] == self.last_tag_url: is_skipping = False
                else: continue

            print(f"\n📁 分类扫描: 【{tag['name']}】")
            page = 1
            while True:
                p_url = f"{tag['url']}{page}/" if page > 1 else tag['url']
                print(f"  📄 页面 {page} | 当前库总量: {len(self.scanned_ids)} ... ", end="\r", flush=True)
                
                resp = self.safe_request(p_url)
                if not resp: break # 404 说明分类结束
                
                soup_page = BeautifulSoup(resp.text, "html.parser")
                boxes = soup_page.find_all("div", class_="video-img-box")
                if not boxes: break

                with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                    futures = [executor.submit(self.process_box, b, tag['name']) for b in boxes]
                    for f in as_completed(futures):
                        item = f.result()
                        if item: self.save_item(item)

                # 记录分类进度
                with open(PROGRESS_FILE, 'w') as f:
                    json.dump({"last_tag_url": tag['url']}, f)
                
                page += 1
                time.sleep(0.5)
            
            # 分类结束导出全量 JSON
            self.export_to_json()

    def export_to_json(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM videos")
        rows = cursor.fetchall()
        data = [{"id": r[0], "title": r[1], "category": r[2], "poster": r[3], "m3u8": r[4]} for r in rows]
        with open(JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    spider = UltraSpider()
    try:
        spider.start()
    except KeyboardInterrupt:
        print("\n\n🛑 用户中止，进度已保存。")
    finally:
        spider.conn.close()