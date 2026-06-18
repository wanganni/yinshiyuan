# coding=utf-8
#!/usr/bin/python
import re
import sys
import json
import html
import time
import requests
from urllib.parse import quote
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def getName(self):
        return "YouTube视频"

    def init(self, extend):
        try:
            self.extendDict = json.loads(extend)
        except:
            self.extendDict = {}
        self.proxies = self.extendDict.get('proxy', {})
        self.proxy_str = self.extendDict.get('proxy_str', None)
        # 使用最稳健的 UA，配合动态 Referer 处理
        self.header = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
        }
        self.channel_cache = {}

    def homeContent(self, filter):
        return {
            'class': [
                {'type_id': '虎妞小叨叨', 'type_name': '虎妞小叨叨'},
                {'type_id': '温城鲤', 'type_name': '温城鲤'},
                {'type_id': '阿奇讲电影', 'type_name': '阿奇讲电影'},
                {'type_id': '哇萨比抓马', 'type_name': '哇萨比抓马'}
            ]
        }

    def homeVideoContent(self):
        return self.categoryContent("华语音乐", 1, {}, {})

    def categoryContent(self, cid, page, filter, ext):
        url = f"https://www.youtube.com/results?search_query={quote(cid)}&sp=EgIQAQ%3D%3D"
        try:
            # 响应截断：只获取前 64KB，防止阻塞导致的异常时长
            r = requests.get(url, headers=self.header, timeout=8, proxies=self.proxies, stream=True)
            html_content = r.raw.read(64 * 1024).decode('utf-8', 'ignore')
            r.close()
            
            videos = self._extract_videos(html_content, 50)
            self.channel_cache["current"] = videos
            return {'list': videos, 'page': 1, 'pagecount': 1, 'limit': len(videos), 'total': len(videos)}
        except:
            return {'list': []}

    def searchContent(self, key, quick, pg=1):
        return self.categoryContent(key, pg, {}, {})

    def detailContent(self, did):
        vid = did[0]
        # 优化：从内存读取标题，避免重复网络请求
        cache = self.channel_cache.get("current", [])
        video_item = next((v for v in cache if v['vod_id'] == vid), None)
        title = video_item['vod_name'] if video_item else self._get_title(vid)
        
        episode_list = [f"{self._safe(v['vod_name'])}${v['vod_id']}" for v in cache]
        
        vod = {
            "vod_id": vid,
            "vod_name": title,
            "vod_pic": f"https://img.youtube.com/vi/{vid}/hqdefault.jpg",
            "vod_play_from": "YouTube直连",
            "vod_play_url": f"{self._safe(title)}${vid}"
        }
        if episode_list:
            vod["vod_play_url"] += "#" + "#".join(episode_list)
        return {'list': [vod]}

    def playerContent(self, flag, pid, vipFlags):
        vid = pid.split('$')[-1]
        # 核心优化：动态时间戳 + 动态 Referer，强力击穿壳子缓存与 YouTube 鉴权校验
        return {
            "parse": 1,
            "url": f"https://www.youtube.com/watch?v={vid}&t={int(time.time())}",
            "header": {
                "User-Agent": self.header["User-Agent"],
                "Referer": f"https://www.youtube.com/watch?v={vid}"
            },
            "proxy": self.proxy_str
        }

    def _extract_videos(self, html_content, limit=30):
        videos = []
        m = re.search(r'var ytInitialData\s*=\s*({.*?});', html_content, re.S)
        if not m: return []
        try:
            data = json.loads(m.group(1))
            items = data.get("contents", {}).get("twoColumnSearchResultsRenderer", {}).get("primaryContents", {}).get("sectionListRenderer", {}).get("contents", [])
            for section in items:
                vids = section.get("itemSectionRenderer", {}).get("contents", [])
                for item in vids:
                    r = item.get("videoRenderer")
                    if r and "videoId" in r:
                        videos.append({
                            "vod_id": r["videoId"],
                            "vod_name": r.get("title", {}).get("runs", [{}])[0].get("text", "未知"),
                            "vod_pic": f"https://img.youtube.com/vi/{r['videoId']}/hqdefault.jpg"
                        })
                        if len(videos) >= limit: break
        except: pass
        return videos

    def _get_title(self, vid):
        try:
            r = requests.get(f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={vid}&format=json", timeout=3, proxies=self.proxies)
            return r.json().get("title", "YouTube视频")
        except: return "YouTube视频"

    def _safe(self, t):
        return "".join([c if c.isalnum() or c in "· " else "·" for c in t])[:80]

    def destroy(self): pass