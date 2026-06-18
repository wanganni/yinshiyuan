# coding=utf-8
import sys
import json
import requests
import re
from urllib.parse import urljoin, quote
from pyquery import PyQuery as pq
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def getName(self):
        return "600老司机"

    def init(self, extend=""):
        # 目标站最新域名
        self.siteUrl = "https://lsj6305.600gc.top" 
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": self.siteUrl
        }
        self.session = requests.Session()

    def homeContent(self, filter):
        r = self.session.get(self.siteUrl, headers=self.headers, timeout=15)
        doc = pq(r.text)
        classes = []
        for item in doc(".nav-list.swiper-slide a").items():
            name = item.text().strip()
            href = item.attr("href")
            if href and "/vodtype/" in href:
                tid = re.search(r'(\d+)', href).group(1)
                classes.append({"type_name": name, "type_id": tid})
        return {"class": classes, "list": []}

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg else 1
        url = urljoin(self.siteUrl, f"/vodtype/{tid}-{page}.html")
        r = self.session.get(url, headers=self.headers, timeout=15)
        doc = pq(r.text)
        videos = []
        for item in doc("li article").items():
            vod = self.parseVodItem(item)
            if vod:
                videos.append(vod)
        return {"list": videos, "page": page, "pagecount": 999, "limit": 30}

    def detailContent(self, ids):
        vid = ids[0]
        url = urljoin(self.siteUrl, vid)
        r = self.session.get(url, headers=self.headers, timeout=15)
        r.encoding = 'utf-8'
        
        doc = pq(r.text)
        vod = {
            "vod_id": vid,
            "vod_name": doc("title").text().split('-')[0].strip(),
            "vod_pic": "",
            "vod_play_from": "600资源",
            "vod_play_url": "",
            "vod_actor": "",
            "type_name": "",
            "vod_content": doc('meta[name="description"]').attr("content") or ""
        }

        # 提取 player_aaaa 数据
        pattern = r'var\s+player_aaaa\s*=\s*(\{.*?\})</script>'
        match = re.search(pattern, r.text)
        if match:
            try:
                data = json.loads(match.group(1))
                v_data = data.get("vod_data", {})
                vod["vod_name"] = v_data.get("vod_name", vod["vod_name"])
                vod["vod_actor"] = v_data.get("vod_actor", "")
                vod["type_name"] = v_data.get("vod_class", "")
                
                share_url = data.get("url", "").replace('\\', '')
                vod["vod_play_url"] = f"小鸡炖蘑菇${share_url}"
                vod["vod_play_from"] = data.get("from", "hsckyun")
            except:
                pass

        # 补全图片
        og_img = doc('meta[property="og:image"]').attr("content")
        if og_img:
            vod["vod_pic"] = urljoin(self.siteUrl, og_img)
        else:
            vod["vod_pic"] = urljoin(self.siteUrl, doc("article .cover img").attr("src") or "")

        return {"list": [vod]}

    def searchContent(self, key, quick, pg="1"):
        url = f"{self.siteUrl}/vodsearch/{quote(key)}----------{pg}---.html"
        r = self.session.get(url, headers=self.headers, timeout=15)
        doc = pq(r.text)
        videos = []

        for item in doc("ul.list li").items():
            if not item("a.cover"): continue
            vod = self.parseVodItem(item)
            if vod:
                videos.append(vod)
        return {"list": videos}

    def playerContent(self, flag, id, vipFlags):
        share_url = id
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": self.siteUrl
        }
        real_url = ""
        try:
            # 1. 动态嗅探
            res = self.session.get(share_url, headers=headers, timeout=8)
            m3u8_match = re.search(r'var\s+(?:main|url|vurl|vid)\s*=\s*["\'](.*?\.m3u8.*?)["\']', res.text)
            if m3u8_match:
                temp_url = m3u8_match.group(1).replace('\\', '')
                real_url = urljoin(share_url, temp_url) if not temp_url.startswith("http") else temp_url
        except:
            pass

        # 2. 拼接兜底
        if not real_url or ".m3u8" not in real_url:
            if "/share/" in share_url:
                path_part = share_url.split("/share/")[1]
                real_url = f"https://hsm3.hwzcfz.com/{path_part}/index.m3u8"
            else:
                real_url = share_url

        return {
            "parse": 0, "url": real_url,
            "header": {"User-Agent": "Mozilla/5.0", "Referer": "https://hsckyun.yeffpe.com/"}
        }

    def parseVodItem(self, item):
        """精准适配搜索和分类两种源码结构"""
        try:
            a_cover = item("a.cover")
            href = a_cover.attr("href")
            if not href: return None
            
            img_el = a_cover("img")
            img = img_el.attr("src")
            # 优先取 img 的 title 或 alt，这是最准确的视频标题
            title = img_el.attr("title") or img_el.attr("alt") or item("h3 a").text() or item("h3 span").text()
            
            remark = item(".actress a").text() or item(".actress").text() or ""
            
            if img and not img.startswith("http"):
                img = urljoin(self.siteUrl, img)
                
            return {
                "vod_id": href,
                "vod_name": title.strip() if title else "未知视频",
                "vod_pic": img,
                "vod_remarks": remark.strip()
            }
        except:
            return None