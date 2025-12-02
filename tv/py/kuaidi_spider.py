# coding=utf-8
#!/usr/bin/env python3
import requests
import json
import urllib.parse
import re
import os
import time
from urllib3.exceptions import InsecureRequestWarning

# 禁用SSL警告
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

class KuaidiSpider:
    def __init__(self):
        self.host = "https://www.xjjkdfw.sbs"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 11; M2007J3SC Build/RKQ1.200826.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/77.0.3865.120 MQQBrowser/6.2 TBS/045713 Mobile Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Referer': self.host
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.session.verify = False
        print("快递🔞爬虫初始化完成")

    def fetch(self, url, headers=None, retry=3):
        """请求网页"""
        for i in range(retry):
            try:
                if headers:
                    response = self.session.get(url, headers=headers, timeout=30)
                else:
                    response = self.session.get(url, timeout=30)
                response.encoding = 'utf-8'
                return response
            except Exception as e:
                print(f"请求失败 {i+1}/{retry}: {str(e)}")
                time.sleep(2)
        return None

    def log(self, message):
        """日志输出"""
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}")

    def get_categories(self):
        """获取全部分类"""
        self.log("开始获取分类...")
        try:
            rsp = self.fetch(self.host)
            if not rsp:
                return []
                
            html = rsp.text
            categories = []
            pattern = r'<a href="/vodtype/(\d+)\.html"[^>]*>([^<]+)</a>'
            matches = re.findall(pattern, html)
            
            seen = set()
            for tid, name in matches:
                if name.strip() and tid not in seen:
                    seen.add(tid)
                    categories.append({'type_id': tid, 'type_name': name.strip()})
            
            self.log(f"找到 {len(categories)} 个分类")
            return categories
        except Exception as e:
            self.log(f"获取分类出错: {str(e)}")
            return []

    def get_category_pages(self, tid):
        """获取分类的总页数"""
        try:
            url = f"{self.host}/vodtype/{tid}.html"
            rsp = self.fetch(url)
            if not rsp:
                return 1
                
            html = rsp.text
            page_links = re.findall(r'<a href="/vodtype/{}/page/(\d+)\.html"'.format(tid), html)
            if page_links:
                pagecount = max([int(p) for p in page_links if p.isdigit()])
                return pagecount
            return 1
        except:
            return 1

    def get_videos_from_page(self, tid, pg):
        """从分类页面获取视频列表"""
        try:
            if pg == 1:
                url = f"{self.host}/vodtype/{tid}.html"
            else:
                url = f"{self.host}/vodtype/{tid}/page/{pg}.html"
            
            self.log(f"获取分类 {tid} 第 {pg} 页: {url}")
            rsp = self.fetch(url)
            if not rsp:
                return []
                
            html = rsp.text
            videos = self._get_videos(html)
            return videos
        except Exception as e:
            self.log(f"获取视频列表失败: {str(e)}")
            return []

    def _get_videos(self, html):
        """从HTML中提取视频列表"""
        videos = []
        
        pattern = r'<a\s+class="thumbnail"[^>]*href="(/vodplay/(\d+)-\d+-\d+\.html)"[^>]*>.*?data-original="([^"]+)".*?</a>.*?<a\s+href="/voddetail/\d+\.html"[^>]*>([^<]+)</a>.*?<p\s+class="vodtitle">([^<]+?)\s*-\s*<span\s+class="title">([^<]+)</span>'
        
        matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
        
        for full_play_link, vid, pic, title, category, date in matches:
            if not pic.startswith('http'):
                pic = self.host + pic if pic.startswith('/') else 'https:' + pic if pic.startswith('//') else pic
            
            video = {
                'vod_id': vid,
                'vod_name': title.strip(),
                'vod_pic': pic,
                'vod_remarks': f"{category.strip()} | {date.strip()}",
                'play_url': f"{self.host}/vodplay/{vid}-1-1.html"
            }
            videos.append(video)
        
        return videos

    def get_video_detail(self, vid):
        """获取视频详情和播放链接"""
        try:
            detail_url = f"{self.host}/voddetail/{vid}.html"
            self.log(f"获取视频详情: {detail_url}")
            
            rsp = self.fetch(detail_url)
            if not rsp:
                return None
                
            html = rsp.text
   