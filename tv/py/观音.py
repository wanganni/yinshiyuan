#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from queue import Queue, Empty

import requests
from pyquery import PyQuery as pq

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Referer": "https://avgood32t9s3.com/"
}

CLASSES = [
    {"type_name": "有码", "type_id": "511"},
    {"type_name": "无码", "type_id": "512"},
    {"type_name": "欧美", "type_id": "513"}
]

class AvGoodCrawler:
    def __init__(self, page_workers=4, video_workers=16): 
        self.host = "https://avgood32t9s3.com"
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

        self.page_q = Queue()
        self.video_q = Queue()

        self.output_file = "avgood_magnets.txt"
        self.lock = threading.RLock()
        self.batch_buffer = [] 
        
        # 全局去重，防止一张网页里多个链接指向同一视频
        self.visited_videos = set()
        self.visited_pages = set()
        
        with open(self.output_file, "w", encoding="utf-8") as f:
            f.write("=== AvGood 磁力链接提取 ===\n\n")

        self.page_counter = 0
        self.video_counter = 0

        self.page_pool = ThreadPoolExecutor(max_workers=page_workers)
        self.video_pool = ThreadPoolExecutor(max_workers=video_workers)

    def full(self, url: str) -> str:
        if not url:
            return ""
        if url.startswith("http"):
            return url
        if url.startswith("//"):
            return "https:" + url
        return self.host.rstrip("/") + url

    def fetch(self, url: str, retry=3) -> str:
        for _ in range(retry):
            try:
                r = self.session.get(url, timeout=10)
                if r.status_code == 200:
                    r.encoding = 'utf-8' 
                    return r.text
            except Exception:
                time.sleep(1)
        return ""

    def update_progress(self, is_page: bool):
        with self.lock:
            if is_page:
                self.page_counter += 1
                # 每扫描 5 页在终端打印一次提示，避免刷屏卡顿
                if self.page_counter % 5 == 0:
                    print(f"⏳ 进度: 已扫描 {self.page_counter} 个列表页...")
            else:
                self.video_counter += 1
                # 每解析 10 部在终端打印一次提示
                if self.video_counter % 10 == 0:
                    print(f"⏳ 进度: 已解析 {self.video_counter} 部视频磁力链...")

    def commit_batch(self):
        with self.lock:
            if len(self.batch_buffer) >= 30:
                with open(self.output_file, "a", encoding="utf-8") as f:
                    for item in self.batch_buffer:
                        f.write(item + "\n")
                self.batch_buffer.clear()

    def scan_page(self, cate: dict, url: str, page: int):
        html = self.fetch(url)
        if not html:
            return
            
        root = pq(html)
        links = root('a')
        videos_found = 0
        
        for a in links.items():
            href = a.attr('href')
            if href and re.search(r'/c/\d+\.html$', href):
                full_url = self.full(href)
                # 去重判定
                with self.lock:
                    if full_url in self.visited_videos:
                        continue
                    self.visited_videos.add(full_url)
                    
                self.video_q.put((cate, full_url))
                videos_found += 1
                
        self.update_progress(True)

        # 限制每个分类最多爬 50 页（防止无限爬取导致资源耗尽）
        if page >= 50:
            return

        # 动态寻找“下一页”链接
        next_page_url = None
        for a in links.items():
            text = a.text().strip()
            # 兼容各种写法的下一页
            if text in ['下一页', '下一頁', 'Next', 'next']:
                href = a.attr('href')
                if href and href != '#':
                    next_page_url = self.full(href)
                    break
        
        # 如果找到了下一页，且没访问过，则加入队列
        if next_page_url:
            with self.lock:
                if next_page_url not in self.visited_pages:
                    self.visited_pages.add(next_page_url)
                    self.page_q.put((cate, next_page_url, page + 1))
            
        time.sleep(0.5)

    def parse_video(self, cate: dict, url: str):
        html = self.fetch(url)
        if not html:
            self.update_progress(False)
            return
            
        root = pq(html)
        title = root('h1').text() or root('title').text()
        title = title.replace('_磁力链接_BT种子_迅雷下载_AvGood', '').strip()
        
        magnets = []
        for a in root('a[href^="magnet:"]').items():
            magnet_url = a.attr('href')
            if magnet_url and magnet_url not in magnets:
                magnets.append(magnet_url)
                
        if magnets:
            magnet_str = "\n".join(magnets)
            result_text = f"【{cate['type_name']}】{title}\n{magnet_str}\n----------------------------------------"
            
            with self.lock:
                self.batch_buffer.append(result_text)
                self.commit_batch()
                
        self.update_progress(False)

    def run(self):
        print(f"开始爬取，数据将实时保存至：{self.output_file}")
        
        # 初始第一页
        for cate in CLASSES:
            first_url = f"{self.host}/c/{cate['type_id']}/"
            self.visited_pages.add(first_url)
            self.page_q.put((cate, first_url, 1))

        for _ in range(self.page_pool._max_workers):
            self.page_pool.submit(self.page_worker)
            
        for _ in range(self.video_pool._max_workers):
            self.video_pool.submit(self.video_worker)

        self.page_pool.shutdown(wait=True)
        self.video_pool.shutdown(wait=True)
        
        if self.batch_buffer:
            with self.lock:
                with open(self.output_file, "a", encoding="utf-8") as f:
                    for item in self.batch_buffer:
                        f.write(item + "\n")
                self.batch_buffer.clear()
        
        print(f"\n爬取完成！共扫描 {self.page_counter} 个列表页，成功保存了 {self.video_counter} 个视频的磁力链接。")

    def page_worker(self):
        while True:
            try:
                cate, url, page = self.page_q.get(timeout=20) 
            except Empty:
                return
            self.scan_page(cate, url, page)
            self.page_q.task_done()

    def video_worker(self):
        while True:
            try:
                cate, href = self.video_q.get(timeout=25)
            except Empty:
                return
            self.parse_video(cate, href)
            self.video_q.task_done()

if __name__ == "__main__":
    crawler = AvGoodCrawler(page_workers=4, video_workers=16) 
    crawler.run()
