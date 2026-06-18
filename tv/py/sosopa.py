#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import re
import time
import random
import sqlite3
from curl_cffi import requests

class SosopaCrawler:
    def __init__(self):
        self.host = "https://www.sosopa.cc"
        self.save_dir = "./sosopa_records"
        self.db_path = os.path.join(self.save_dir, "master_data.db")
        self.m3u_path = os.path.join(self.save_dir, "playlist.m3u")
        self.txt_path = os.path.join(self.save_dir, "movies.txt")
        
        # 完整浏览器请求头（模仿 Chrome 120）
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': self.host,
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }

    def init(self):
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("PRAGMA synchronous = OFF")
        c.execute("PRAGMA journal_mode = WAL")
        c.execute("""CREATE TABLE IF NOT EXISTS videos
                     (vod_id TEXT PRIMARY KEY,
                      name TEXT,
                      url TEXT,
                      genre TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS progress
                     (tid TEXT PRIMARY KEY,
                      last_pg INTEGER)""")
        conn.commit()
        conn.close()

    def _get_last_pg(self, tid):
        conn = sqlite3.connect(self.db_path)
        res = conn.execute("SELECT last_pg FROM progress WHERE tid=?", (tid,)).fetchone()
        conn.close()
        return res[0] if res else 1

    def _update_progress(self, tid, pg):
        conn = sqlite3.connect(self.db_path)
        conn.execute("INSERT OR REPLACE INTO progress VALUES (?, ?)", (tid, pg))
        conn.commit()
        conn.close()

    def _save_video(self, vid, name, url, genre):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO videos VALUES (?,?,?,?)", (vid, name, url, genre))
        if c.rowcount > 0:   # 新记录才写入文件
            with open(self.txt_path, "a", encoding="utf-8") as f:
                f.write(f"{name},{genre}\n")
            with open(self.m3u_path, "a", encoding="utf-8") as f:
                f.write(f"#EXTINF:-1,{name}\n{url}\n")
        conn.commit()
        conn.close()
        return c.rowcount > 0

    def fetch(self, url, retry=2):
        """使用 curl_cffi 模拟真实浏览器，支持重试"""
        time.sleep(random.uniform(3, 6))  # 随机延时防封
        try:
            # 模拟 Chrome 120 的 TLS 指纹
            resp = requests.get(
                url,
                headers=self.headers,
                impersonate="chrome120",
                timeout=20
            )
            if resp.status_code == 200:
                return resp.text
            elif resp.status_code == 403 and retry > 0:
                print(f"  ⚠️ 403 Forbidden，{3}秒后重试...")
                time.sleep(3)
                return self.fetch(url, retry - 1)
            else:
                print(f"  ❌ HTTP {resp.status_code}: {url}")
                return ""
        except Exception as e:
            if retry > 0:
                print(f"  ⚠️ 请求异常: {e}，重试...")
                time.sleep(3)
                return self.fetch(url, retry - 1)
            else:
                print(f"  ❌ 请求失败: {e}")
                return ""

    def get_all_category_ids(self, html):
        tids = re.findall(r'/index.php/vod/type/id/(\d+).html', html)
        return list(dict.fromkeys(tids))

    def get_total_pages(self, tid):
        url = f"{self.host}/index.php/vod/type/id/{tid}/page/1.html"
        html = self.fetch(url)
        if not html:
            return 30000
        match = re.search(r'共(\d+)页', html)
        if match:
            return int(match.group(1))
        # 备选规则
        match2 = re.search(r'/(\d+)\.html.*?尾页', html)
        if match2:
            return int(match2.group(1))
        return 30000

    def crawl_category(self, tid, start_page, total_pages):
        for page in range(start_page, total_pages + 1):
            url = f"{self.host}/index.php/vod/type/id/{tid}/page/{page}.html"
            print(f"  正在爬取: 第 {page}/{total_pages} 页 - {url}")
            html = self.fetch(url)
            if not html or len(html) < 500:
                print(f"  ⚠️ 第 {page} 页内容过短，可能已无数据，跳过")
                continue

            ids = re.findall(r'/index.php/vod/detail/id/(\d+).html', html)
            if not ids:
                print(f"  ⏹️ 第 {page} 页没有视频，停止翻页")
                break

            new_count = 0
            for vid in set(ids):
                v_name = f"DATA_{vid}"
                v_url = f"{self.host}/index.php/vod/detail/id/{vid}.html"
                genre = f"CAT_{tid}"
                if self._save_video(vid, v_name, v_url, genre):
                    new_count += 1
                time.sleep(random.uniform(0.5, 1.2))

            self._update_progress(tid, page)
            print(f"  ✅ 第 {page} 页完成，新增 {new_count} 条记录")

    def run(self):
        self.init()
        print("=" * 50)
        print("搜搜啪爬虫 (curl_cffi 浏览器指纹模拟版)")
        print(f"数据保存目录: {self.save_dir}")
        print(f"M3U文件: {self.m3u_path}")
        print("=" * 50)

        print("\n[1] 获取首页分类列表...")
        index_html = self.fetch(self.host)
        if not index_html:
            print("❌ 无法访问首页，请检查网络或网站状态")
            return
        tids = self.get_all_category_ids(index_html)
        if not tids:
            print("❌ 未提取到任何分类ID，可能网站结构已变更")
            return
        print(f"[✔] 共发现 {len(tids)} 个分类: {tids}")

        for tid in tids:
            print(f"\n[2] 开始处理分类: {tid}")
            last_page = self._get_last_pg(tid)
            total_pages = self.get_total_pages(tid)
            print(f"    进度: 已爬取到第 {last_page} 页，总页数约 {total_pages} 页")
            if last_page > total_pages:
                print(f"    该分类已完成，跳过")
                continue
            self.crawl_category(tid, last_page, total_pages)

        print("\n🎉 全部任务执行完毕！")
        print(f"播放列表已保存至: {self.m3u_path}")

if __name__ == "__main__":
    crawler = SosopaCrawler()
    crawler.run()