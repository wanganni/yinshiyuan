#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
import requests
from urllib.parse import unquote

# 目标地址
HOST = "https://www.sehumt203.vip:9527"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Mobile Safari/537.36",
    "Referer": HOST
}

class SehuSpider:
    def get_classes(self):
        # 严格按照你提供的分类 ID 对应表
        return [
            {"type_name": "国产视频", "type_id": "1"},
            {"type_name": "传媒精品", "type_id": "2"},
            {"type_name": "无码专区", "type_id": "3/1"},
            {"type_name": "破解无码", "type_id": "3/2"},
            {"type_name": "有码专区", "type_id": "3/3"},
            {"type_name": "日韩精品", "type_id": "4"},
            {"type_name": "欧美大片", "type_id": "5"},
            {"type_name": "动漫专区", "type_id": "6"},
            {"type_name": "AI 换脸", "type_id": "7"},
            {"type_name": "同性专区", "type_id": "8"},
            {"type_name": "解说视频", "type_id": "9"},
            {"type_name": "三级伦理", "type_id": "10"}
        ]

    def get_list(self, tid, pg=1):
        # 关键：SPA 站点的列表数据通常可以通过带页码的路径获取
        # 适配你提供的规律：type/3/1-1-0-1 (最后四个数通常是：页码-排序-筛选-筛选)
        url = f"{HOST}/type/{tid}/{pg}-0-0-1" if "/" not in str(tid) else f"{HOST}/type/{tid}-{pg}-0-0-1"
        
        try:
            # verify=False 解决 9527 端口常见的证书报错
            r = requests.get(url, headers=HEADERS, timeout=10, verify=False)
            html = r.text
            
            vod_list = []
            # 兼容模式：如果 HTML 里有 JSON 数据块（SPA 常态），则解析 JSON
            json_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', html)
            if json_match:
                data = json.loads(json_match.group(1))
                # 这里的路径需根据实际返回的 JSON 结构微调
                items = data.get('vodList', [])
                for item in items:
                    vod_list.append({
                        "vod_id": item.get('id'),
                        "vod_name": item.get('name'),
                        "vod_pic": item.get('pic'),
                        "vod_remarks": item.get('remarks')
                    })
            
            # 兜底模式：如果 JSON 解析失败，强制正则抓取 HTML 标签
            if not vod_list:
                pattern = re.compile(r'href="/detail/(\d+)".*?src="(.*?)".*?title">(.*?)<', re.S)
                matches = pattern.findall(html)
                for vid, pic, title in matches:
                    vod_list.append({
                        "vod_id": vid,
                        "vod_name": title.strip(),
                        "vod_pic": pic if pic.startswith('http') else HOST + pic,
                        "vod_remarks": "🔥立即观看"
                    })
            return vod_list
        except:
            return []

    def get_detail(self, vid):
        # 播放页通常包含 m3u8
        url = f"{HOST}/detail/{vid}"
        try:
            r = requests.get(url, headers=HEADERS, timeout=10, verify=False)
            # 匹配页面中的 m3u8 链接
            m3u8 = re.search(r'https?://[^\s"\'<>]+?\.m3u8', r.text)
            return m3u8.group(0) if m3u8 else ""
        except:
            return ""

# --- OK 影视标准主接口 ---
def main(event):
    params = event.get("queryStringParameters", {})
    ac = params.get("ac", "list")
    spider = SehuSpider()

    if ac == "list":
        tid = params.get("t")
        pg = params.get("pg", "1")
        if not tid:
            return {"class": spider.get_classes()}
        return {"list": spider.get_list(tid, pg)}

    if ac == "detail":
        vid = params.get("ids")
        play_url = spider.get_detail(vid)
        return {
            "list": [{
                "vod_id": vid,
                "vod_play_from": "色虎专用线",
                "vod_play_url": f"全速播放${play_url}"
            }]
        }