# coding=utf-8
import sys
import json
import re
import requests
import base64
from bs4 import BeautifulSoup
from urllib.parse import unquote, urljoin

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider():
        def fetch(self, url, headers=None, timeout=10):
            try:
                res = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
                res.encoding = 'utf-8'
                return res
            except Exception as e:
                print(f"fetch error: {e}")
                return None

class Spider(BaseSpider):
    def getName(self):
        return "撸一天"

    def init(self, extend=""):
        self.host = "https://luyitian.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })

    def fetch(self, url, headers=None, timeout=10):
        try:
            req_headers = headers or self.session.headers
            res = self.session.get(url, headers=req_headers, timeout=timeout, allow_redirects=True)
            res.encoding = 'utf-8'
            return res
        except Exception as e:
            print(f"fetch error: {e}")
            return None

    # ---------- 分类首页 ----------
    def homeContent(self, filter):
        result = {}
        result['class'] = [
            {"type_name": "中文字幕", "type_id": "28"},
            {"type_name": "日本中字", "type_id": "51"},
            {"type_name": "日本无码", "type_id": "22"},
            {"type_name": "日本有码", "type_id": "21"},
            {"type_name": "国产精品", "type_id": "26"},
            {"type_name": "国产剧情", "type_id": "27"},
            {"type_name": "国产自拍", "type_id": "29"},
            {"type_name": "国产主播", "type_id": "35"},
            {"type_name": "欧美精品", "type_id": "104"},
            {"type_name": "动漫精品", "type_id": "103"},
            {"type_name": "韩国主播", "type_id": "37"},
            {"type_name": "Cosplay", "type_id": "106"},
            {"type_name": "人妻", "type_id": "31"},
            {"type_name": "素人", "type_id": "44"}
        ]
        result['list'] = []
        result['filters'] = {}
        return result

    # ---------- 分类列表 ----------
    def categoryContent(self, tid, pg, filter, extend):
        result = {"list": [], "page": int(pg), "pagecount": 999, "limit": 20, "total": 9999}
        url = f"{self.host}/vodtype/{tid}-{pg}/"
        res = self.fetch(url, headers={'Referer': self.host})
        if not res:
            return result

        soup = BeautifulSoup(res.text, 'html.parser')
        vod_list = []
        items = (soup.select('div#mdym > div') or
                 soup.select('.stui-vodlist__item') or
                 soup.select('.myui-vodlist__box') or
                 soup.select('.video-item') or
                 soup.select('.item') or
                 soup.select('.vodlist_item'))

        for item in items:
            a = item.select_one('a') or item.find('a')
            if not a:
                continue

            href = a.get('href', '')
            vid_match = re.search(r'/vodplay/(\d+)', href)
            vid = vid_match.group(1) if vid_match else href

            name = ""
            img = item.select_one('img')
            if img and img.get('alt'):
                name = img['alt']
            if not name and a.get('title'):
                name = a['title']
            if not name:
                title_elem = item.select_one('.title') or item.select_one('.name') or item.select_one('.text')
                if title_elem:
                    name = title_elem.get_text(strip=True)
            if not name:
                name = a.get_text(strip=True)
            if not name:
                name = "未知标题"

            pic = ""
            if img:
                pic = img.get('data-src') or img.get('src', '')
                if pic and not pic.startswith('http'):
                    pic = urljoin(self.host, pic)

            remark = ""
            remark_elem = item.select_one('.remarks') or item.select_one('.note') or item.select_one('.tag')
            if remark_elem:
                remark = remark_elem.get_text(strip=True)
            elif item.text.strip():
                lines = [l.strip() for l in item.text.split('\n') if l.strip()]
                if lines:
                    remark = lines[-1][:20]

            vod_list.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": pic,
                "vod_remarks": remark
            })

        result['list'] = vod_list
        page_elem = soup.select_one('.page .page-link, .pagination a')
        if page_elem:
            try:
                last_page = int(re.search(r'(\d+)', page_elem.get('href', '')).group(1)) if 'href' in page_elem.attrs else 1
                result['pagecount'] = max(last_page, 1)
            except:
                pass
        return result

    # ---------- 详情 ----------
    def detailContent(self, ids):
        vid = ids[0]
        url = f"{self.host}/vodplay/{vid}-1-1/"
        res = self.fetch(url, headers={'Referer': self.host})
        if not res:
            return {"list": []}

        soup = BeautifulSoup(res.text, 'html.parser')
        raw_title = soup.title.text.split('|')[0].replace('在线播放在线观看','').replace('《','').replace('》','').strip()

        vod = {
            "vod_id": vid,
            "vod_name": raw_title,
            "vod_type": "视频",
            "vod_content": "撸一天资源",
            "vod_play_from": "Luyitian",
            "vod_play_url": f"播放#{vid}-1-1"
        }
        return {"list": [vod]}

    # ---------- 搜索 ----------
    def searchContent(self, key, quick, pg=1):
        url = f"{self.host}/vodsearch/{key}----------{pg}---/"
        res = self.fetch(url, headers={'Referer': self.host})
        if not res:
            return {"list": []}

        soup = BeautifulSoup(res.text, 'html.parser')
        vod_list = []
        items = (soup.select('div#mdym > div') or
                 soup.select('.stui-vodlist__item') or
                 soup.select('.myui-vodlist__box') or
                 soup.select('.video-item'))

        for item in items:
            a = item.select_one('a') or item.find('a')
            if not a:
                continue

            href = a.get('href', '')
            vid_match = re.search(r'/vodplay/(\d+)', href)
            vid = vid_match.group(1) if vid_match else href

            name = ""
            img = item.select_one('img')
            if img and img.get('alt'):
                name = img['alt']
            if not name and a.get('title'):
                name = a['title']
            if not name:
                title_elem = item.select_one('.title') or item.select_one('.name')
                if title_elem:
                    name = title_elem.get_text(strip=True)
            if not name:
                name = a.get_text(strip=True)
            if not name:
                name = "搜索结果"

            pic = ""
            if img:
                pic = img.get('data-src') or img.get('src', '')

            vod_list.append({
                "vod_id": vid,
                "vod_name": name.strip(),
                "vod_pic": pic,
                "vod_remarks": ""
            })
        return {"list": vod_list}

    # ---------- JS 逆向解包（简化） ----------
    def _js_decode(self, js_str):
        """尝试解码常见的 JS 混淆字符串"""
        # base64
        b64_match = re.search(r'atob\s*\(\s*["\']([^"\']+)["\']\s*\)', js_str)
        if b64_match:
            try:
                decoded = base64.b64decode(b64_match.group(1)).decode('utf-8')
                return decoded
            except:
                pass
        # unescape
        unescape_match = re.search(r'unescape\s*\(\s*["\']([^"\']+)["\']\s*\)', js_str)
        if unescape_match:
            try:
                decoded = unquote(unescape_match.group(1))
                return decoded
            except:
                pass
        # 直接提取 m3u8
        url_match = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', js_str, re.I)
        if url_match:
            return url_match.group(1)
        return None

    # ---------- 嗅探 XHR ----------
    def _sniff_xhr(self, html, page_url):
        """从页面中嗅探可能的 XHR 请求，返回视频地址"""
        patterns = [
            r'fetch\s*\(\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'XMLHttpRequest.*?\.open\s*\(\s*["\']GET["\']\s*,\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'\.get\s*\(\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'url\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'src\s*=\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
        ]
        for pat in patterns:
            match = re.search(pat, html, re.I)
            if match:
                url = match.group(1)
                if not url.startswith('http'):
                    url = urljoin(page_url, url)
                return url
        # 从 script 中解包
        soup = BeautifulSoup(html, 'html.parser')
        for script in soup.find_all('script'):
            if script.string:
                found = self._js_decode(script.string)
                if found and '.m3u8' in found:
                    return found
        return None

    # ---------- 播放核心（最终回退） ----------
    def playerContent(self, flag, id, vipFlags):
        play_url = f"{self.host}/vodplay/{id}/"
        res = self.fetch(play_url, headers={'Referer': self.host})
        if not res:
            return {"parse": 1, "url": play_url}

        html = res.text
        m3u8_url = None

        # 1. 从 player_aaaa 提取
        match = re.search(r'var\s+player_aaaa\s*=\s*(\{.*?\});', html, re.DOTALL)
        if match:
            try:
                json_str = match.group(1).strip()
                if json_str.endswith(','):
                    json_str = json_str[:-1]
                config = json.loads(json_str)
                m3u8_url = config.get('url', '')
            except:
                pass

        # 2. JS 解包
        if not m3u8_url:
            m3u8_url = self._js_decode(html)

        # 3. 嗅探
        if not m3u8_url:
            m3u8_url = self._sniff_xhr(html, play_url)

        # 如果提取到地址，尝试测试，但即使测试失败也返回播放页
        if m3u8_url:
            m3u8_url = unquote(m3u8_url)
            if m3u8_url.startswith('//'):
                m3u8_url = 'https:' + m3u8_url
            elif not m3u8_url.startswith('http'):
                m3u8_url = urljoin(self.host, m3u8_url)

            # 尝试测试，若失败则返回播放页
            try:
                test_res = self.session.get(
                    m3u8_url,
                    headers={
                        'User-Agent': self.session.headers['User-Agent'],
                        'Referer': play_url,
                        'Origin': self.host,
                    },
                    timeout=5,
                    allow_redirects=True
                )
                if test_res.status_code == 200 and test_res.text.strip().startswith('#EXTM3U'):
                    # 有效，直接返回
                    return {
                        "parse": 0,
                        "playUrl": "",
                        "url": m3u8_url,
                        "header": {
                            "User-Agent": self.session.headers['User-Agent'],
                            "Referer": play_url,
                            "Origin": self.host,
                            "Accept": "*/*"
                        }
                    }
            except:
                pass

        # 所有尝试均无效或测试失败，返回播放页，让播放器自行解析（parse=1）
        return {"parse": 1, "url": play_url}