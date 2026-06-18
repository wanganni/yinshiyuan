#故乡的原风景
import sys
import json
import re
import ssl
import urllib.request
import urllib.parse
import base64

sys.path.append('..')

try:
    from base.spider import Spider
except:
    class Spider:
        pass

class Spider(Spider):
    def __init__(self):
        self.siteUrl = "https://s_ae_ep_k.cha18c8.top"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Referer': self.siteUrl + '/',
            'Accept-Language': 'zh-CN,zh;q=0.9'
        }
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE

    def _get(self, url):
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, context=self.ctx, timeout=12) as r:
                return r.read().decode("utf-8", "ignore")
        except:
            return ""

    def getName(self):
        return "OK传媒_修正终极版"

    def init(self, extend=""):
        pass

    def homeContent(self, filter):
        html = self._get(self.siteUrl)
        classes = []
        # 兼容匹配所有分类路径
        nav_reg = r'href=".*?/vod/type/id/(\d+)\.html"[^>]*>([^<]+)</a>'
        matches = re.findall(nav_reg, html)
        seen = set()
        for tid, name in matches:
            name = name.strip()
            if name not in ["首页", "留言", "传送门", "更多"] and tid not in seen:
                classes.append({"type_id": tid, "type_name": name})
                seen.add(tid)
        return {"class": classes, "list": self._list(html)}

    def _list(self, html):
        videos = []
        if not html: return videos
        # 针对该站列表块进行深度切割
        parts = html.split('class="vod"')
        if len(parts) < 2: parts = html.split('class="pack-ykpack"')
        
        for part in parts[1:]:
            # 1. 提取 ID
            m_id = re.search(r'href=".*?(?:detail/id/|/v/|/id/)(\d+)\.html"', part)
            if not m_id: continue
            
            # 2. 提取图片
            m_pic = re.search(r'data-original="([^"]+)"', part)
            pic = m_pic.group(1) if m_pic else ""
            if pic and pic.startswith('//'): pic = "https:" + pic

            # 3. 【核心修复】提取标题：采用多级探测逻辑
            name = ""
            # A. 优先尝试提取 a 标签的标题属性
            t_match = re.search(r'title="([^"]+)"', part)
            if t_match: name = t_match.group(1).strip()
            
            # B. 穿透 div 和 span 提取纯文本 (应对截图中“未知”的情况)
            if not name or name == "未知":
                # 匹配 vod-txt 或 vod-name 类名下的文字
                txt_match = re.search(r'vod-txt">.*?<a[^>]*>(.*?)</a>', part, re.S)
                if txt_match:
                    name = re.sub(r'<.*?>', '', txt_match.group(1)).strip()
            
            # C. 暴力正则提取：提取两个闭合标签之间的所有汉字
            if not name or name == "未知":
                hanzi_match = re.findall(r'[\u4e00-\u9fa5]{3,}', part) # 找连续3个汉字以上的文本
                if hanzi_match: name = hanzi_match[0]

            videos.append({
                "vod_id": m_id.group(1),
                "vod_name": name if name else "未知资源",
                "vod_pic": pic
            })
        return videos

    def categoryContent(self, tid, pg, filter, extend):
        url = f"{self.siteUrl}/index.php/vod/type/id/{tid}/page/{pg}.html"
        return {"page": pg, "pagecount": 999, "limit": 20, "list": self._list(self._get(url))}

    def detailContent(self, ids):
        vid = ids[0] if isinstance(ids, list) else ids
        # 详情页拿不到明文地址，强制请求播放页
        play_url = f"{self.siteUrl}/index.php/vod/play/id/{vid}/sid/1/nid/1.html"
        html = self._get(play_url)
        
        # 提取标题
        name = "视频详情"
        m_name = re.search(r'在线播放：([^<]+) -', html)
        if m_name: name = m_name.group(1).strip()

        # 提取 player_aaaa 里的地址
        final_url = ""
        m_json = re.search(r'var\s+player_aaaa\s*=\s*(\{.*?});', html, re.DOTALL)
        if m_json:
            try:
                data = json.loads(m_json.group(1))
                u = data.get("url", "")
                enc = str(data.get("encrypt", "0"))
                # 自动解密逻辑
                if enc == "2": u = base64.b64decode(u).decode('utf-8')
                elif enc == "1": u = urllib.parse.unquote(u)
                final_url = u.replace('\\/', '/')
            except: pass
            
        if not final_url: # 备用提取
            m_url = re.search(r'["\'](https?[:\\/]+[^"\']+\.m3u8[^"\']*)["\']', html)
            if m_url: final_url = m_url.group(1).replace('\\/', '/')

        if final_url and final_url.startswith('/'): final_url = self.siteUrl + final_url

        vod = {
            "vod_id": vid,
            "vod_name": name,
            "vod_play_from": "极速专线",
            "vod_play_url": "正片$" + final_url
        }
        return {"list": [vod]}

    def playerContent(self, flag, id, vipFlags):
        # 加入防盗链必备的 Origin 和 Referer
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Referer': self.siteUrl + '/',
            'Origin': self.siteUrl
        }
        return {"parse": 0, "url": id, "header": json.dumps(headers)}

    def searchContent(self, key, quick, pg="1"):
        url = f"{self.siteUrl}/index.php/vod/search.html?wd={urllib.parse.quote(key)}"
        return {"list": self._list(self._get(url))}

    def isVideoFormat(self, url):
        return ".m3u8" in url or ".mp4" in url

    def destroy(self):
        pass