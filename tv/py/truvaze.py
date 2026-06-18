#!/usr/bin/python
# -*- coding: utf-8 -*-
import json, requests, time
from datetime import datetime, timezone
from urllib.parse import quote, urljoin
from base.spider import Spider

class Spider(Spider):
    def getName(self): return "Truvaze"
    def init(self, extend=""):
        self.host = "https://truvaze.com"
        self.api = self.host + "/api/media"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.7444.235 Safari/537.36",
            "Referer": self.host + "/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
            "TE": "trailers",
            "Sec-Ch-Ua": "\"Not A(Brand\";v=\"99\", \"Google Chrome\";v=\"142\", \"Chromium\";v=\"142\"",
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": "\"Windows\""
        }
        self.categories = [
            {"type_id": "daily", "type_name": "每日"},
            {"type_id": "weekly", "type_name": "每周"},
            {"type_id": "monthly", "type_name": "每月"},
            {"type_id": "all", "type_name": "所有时间"}
        ]
        # 图片代理：解决 Twitter 图床在国内无法访问的问题
        self.use_image_proxy = True   # 改为 False 则直连原图

    # ==================== 工具函数 ====================
    def _pic_url(self, path):
        if not path:
            return ""
        raw_url = urljoin(self.host, path)
        if self.use_image_proxy and raw_url.startswith("http"):
            return f"https://images.weserv.nl/?url={quote(raw_url, safe='')}"
        return raw_url

    def _get_api(self, params):
        try:
            for retry in range(3):
                try:
                    r = requests.get(self.api, params=params, headers=self.headers, timeout=30, verify=False)
                    return r.json()
                except requests.exceptions.RequestException:
                    if retry == 2:
                        return {"items": [], "currentPage": 1, "lastPage": 1, "total": 0, "perPage": 50}
        except:
            return {"items": [], "currentPage": 1, "lastPage": 1, "total": 0, "perPage": 50}

    def _format_time(self, seconds):
        """将秒数转换为 时:分:秒"""
        if not seconds:
            return "0:00"
        try:
            seconds = int(seconds)
        except:
            return str(seconds)
        h, m = divmod(seconds, 3600)
        m, s = divmod(m, 60)
        return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

    def _format_count(self, count):
        """数字转 1.2k / 3.4w"""
        if not count:
            return "0"
        try:
            count = int(count)
        except:
            return str(count)
        if count >= 10000:
            return f"{count/10000:.1f}w"
        if count >= 1000:
            return f"{count/1000:.1f}k"
        return str(count)

    def _relative_time(self, timestamp):
        """将 ISO 时间字符串或 Unix 时间戳转为 相对时间"""
        if not timestamp:
            return ""
        try:
            # 处理 Unix 时间戳（秒）
            if isinstance(timestamp, (int, float)):
                ts = int(timestamp)
            else:
                # 处理 ISO 8601 字符串
                ts_str = str(timestamp).strip()
                # 兼容 Z 结尾
                if ts_str.endswith('Z'):
                    ts_str = ts_str[:-1] + '+00:00'
                dt = datetime.fromisoformat(ts_str)
                ts = int(dt.timestamp())
        except:
            # 无法解析时返回原始字符串，方便调试
            return str(timestamp)

        now = int(time.time())
        diff = now - ts
        if diff < 0:
            return "刚刚"
        if diff < 60:
            return "刚刚"
        if diff < 3600:
            return f"{diff // 60}分钟前"
        if diff < 86400:
            return f"{diff // 3600}小时前"
        if diff < 2592000:
            return f"{diff // 86400}天前"
        if diff < 31536000:
            return f"{diff // 2592000}个月前"
        return f"{diff // 31536000}年前"

    def _get_extra_info(self, item):
        """
        拼接备注信息：时长 + 播放次数 + 上传时间
        可根据实际 API 字段调整 'views' 等键名
        """
        # 1. 作品时长（秒）
        duration = item.get('time', 0)
        time_str = self._format_time(duration)

        # 2. 播放量（尝试多种常见字段名，若无则为空）
        views = (item.get('views') or item.get('play_count') or item.get('view_count')
                 or item.get('favorite_count') or item.get('like_count'))
        view_str = f"👁 {self._format_count(views)}" if views else ""

        # 3. 上传时间（优先 timestamp，其次 created_at/publish_date）
        upload = (item.get('timestamp') or item.get('created_at') or item.get('publish_date'))
        upload_str = self._relative_time(upload) if upload else ""

        # 组装：时长始终显示，播放量和上传时间可选
        parts = [f"⏱ {time_str}"]
        if view_str:
            parts.append(view_str)
        if upload_str:
            parts.append(upload_str)
        return " · ".join(parts)

    # ==================== 页面接口 ====================
    def homeContent(self, filter):
        params = {"range": "", "page": 1, "per_page": 50, "category": "", "ids": "",
                  "isAnimeOnly": 0, "sort": "favorite"}
        data = self._get_api(params)
        items = []
        # 如果仍然看不到上传时间，请取消下一行注释，查看日志第一条数据的完整字段
        # print(json.dumps(data.get("items", [])[0], ensure_ascii=False, indent=2))
        for item in data.get("items", []):
            account = item.get('tweet_account') or "未知用户"
            thumbnail = item.get('thumbnail') or ""
            items.append({
                "vod_id": str(item.get("id")),
                "vod_name": f"{account} - {self._format_time(item.get('time', 0))}",
                "vod_pic": self._pic_url(thumbnail),
                "vod_remarks": self._get_extra_info(item)
            })
        return {"class": self.categories, "list": items, "filters": {}}

    def categoryContent(self, tid, pg, filter, extend):
        range_map = {"daily": "daily", "weekly": "weekly", "monthly": "monthly", "all": "all"}
        params = {
            "range": range_map.get(tid, ""),
            "page": pg,
            "per_page": 50,
            "category": "",
            "ids": "",
            "isAnimeOnly": 0,
            "sort": "favorite"
        }
        data = self._get_api(params)
        items = []
        for item in data.get("items", []):
            account = item.get('tweet_account') or "未知用户"
            thumbnail = item.get('thumbnail') or ""
            items.append({
                "vod_id": str(item.get("id")),
                "vod_name": f"{account} - {self._format_time(item.get('time', 0))}",
                "vod_pic": self._pic_url(thumbnail),
                "vod_remarks": self._get_extra_info(item)
            })
        return {
            "page": int(pg),
            "pagecount": data.get("lastPage", 1),
            "limit": data.get("perPage", 50),
            "total": data.get("total", 0),
            "list": items
        }

    def detailContent(self, ids):
        result = {"list": []}
        for vid in ids:
            try:
                params = {"ids": vid}
                data = self._get_api(params)
                if not data.get("items"):
                    continue
                item = data.get("items")[0]
                account = item.get('tweet_account') or "未知用户"
                name = f"{account} - {self._format_time(item.get('time', 0))}"
                thumbnail = item.get('thumbnail') or ""
                video_url = item.get("url", "")
                result["list"].append({
                    "vod_id": vid,
                    "vod_name": name,
                    "vod_pic": self._pic_url(thumbnail),
                    "vod_play_from": "默认",
                    "vod_play_url": f"播放${video_url}",
                    "vod_remarks": self._get_extra_info(item)
                })
            except:
                continue
        return result

    def searchContent(self, key, quick, pg="1"):
        return {"list": [], "page": int(pg)}

    def playerContent(self, flag, id, vipFlags):
        return {"parse": 0, "url": str(id) if id else ""}