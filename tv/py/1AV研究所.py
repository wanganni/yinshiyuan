# -*- coding: utf-8 -*-
import re
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
requests.packages.urllib3.disable_warnings()
import base64
from urllib.parse import urljoin, unquote

from base.spider import Spider


class Spider(Spider):
    def getName(self):
        return "AV研究所"

    def init(self, extend=""):
        super().init(extend)
        self.site_url = "https://xn--cdn0428-1yjs01cc-rf0zn60cta5031amw9i.yanjiusuo0046.top"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Mobile Safari/537.36",
            "Referer": self.site_url,
            "Accept-Language": "zh-CN,zh;q=0.9"
        }
        self.sess = requests.Session()
        retry = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        self.sess.mount("https://", HTTPAdapter(max_retries=retry))
        self.sess.mount("http://", HTTPAdapter(max_retries=retry))
        self.page_size = 20
        self.total = 9999

    def fetch(self, url, timeout=10):
        try:
            return self.sess.get(url, headers=self.headers, timeout=timeout, verify=False)
        except Exception:
            return None

    def _abs(self, u):
        if not u:
            return ""
        if u.startswith("//"):
            return "https:" + u
        if u.startswith(("http://", "https://")):
            return u
        return self.site_url + (u if u.startswith("/") else "/" + u)

    def _clean(self, s):
        if not s:
            return ""
        s = re.sub(r"<[^>]+>", "", s, flags=re.S)
        return re.sub(r"\s+", " ", s).strip()

    def homeContent(self, filter):
        # 可按你的站点改成动态抓取；这里先给固定分类
        cate_list = [
            {"type_name": "最新", "type_id": "latest-insert"},
            {"type_name": "最近发布", "type_id": "recent-release"},
            {"type_name": "评分榜", "type_id": "top-rating"},
            {"type_name": "收藏榜", "type_id": "top-favorites"},
        ]
        return {"class": cate_list}

    def _parse_video_list(self, html):
        video_list = []
        # 匹配 <dl> ... <dt><a href=...><img data-src=...><i>日期</i> ... <h3>标题</h3>
        dls = re.findall(r"<dl>([\s\S]*?)</dl>", html, flags=re.S)
        for item in dls:
            m_href = re.search(r'<dt>\s*<a[^>]+href=["\']([^"\']+)["\']', item, flags=re.S)
            m_pic = re.search(r'<img[^>]+(?:data-src|src)=["\']([^"\']+)["\']', item, flags=re.S)
            m_date = re.search(r"<i>([^<]+)</i>", item, flags=re.S)
            m_name = re.search(r"<h3>([\s\S]*?)</h3>", item, flags=re.S)

            if not (m_href and m_pic and m_name):
                continue

            video_list.append({
                "vod_id": self._abs(m_href.group(1).strip()),
                "vod_name": self._clean(m_name.group(1)),
                "vod_pic": self._abs(m_pic.group(1).strip()),
                "vod_remarks": self._clean(m_date.group(1)) if m_date else "",
                "style": {"type": "rect", "ratio": 1.33}
            })
        return video_list

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg) if str(pg).isdigit() else 1

        # 兼容两种分页：
        # /list/AvDB/latest-insert.html
        # /list/AvDB/latest-insert/2.html
        if pg == 1:
            list_url = f"{self.site_url}/list/AvDB/{tid}.html"
        else:
            list_url = f"{self.site_url}/list/AvDB/{tid}/{pg}.html"

        res = self.fetch(list_url)
        video_list = self._parse_video_list(res.text) if (res and res.ok) else []

        pagecount = pg + 1 if len(video_list) else pg
        return {
            "list": video_list,
            "page": pg,
            "pagecount": pagecount,
            "limit": self.page_size,
            "total": self.total
        }

    def searchContent(self, key, quick, pg=1):
        pg = int(pg) if str(pg).isdigit() else 1
        # 页面结构里的搜索参数是 GET: /?m=search&u=AvDB&p=1&k=关键词
        search_url = f"{self.site_url}/?m=search&u=AvDB&p={pg}&k={requests.utils.quote(key)}"
        res = self.fetch(search_url)
        video_list = self._parse_video_list(res.text) if (res and res.ok) else []

        pagecount = pg + 1 if len(video_list) else pg
        return {
            "list": video_list,
            "page": pg,
            "pagecount": pagecount,
            "limit": self.page_size,
            "total": len(video_list) if len(video_list) < self.total else self.total
        }


    def detailContent(self, ids):
        vod_id = ids[0] if ids else ""
        if not vod_id:
            return {"list": [{"vod_name": "视频ID为空"}]}
    
        res = self.fetch(vod_id)
        if not (res and res.ok):
            return {"list": [{"vod_id": vod_id, "vod_name": "视频详情解析失败"}]}
    
        html = res.text
    
        # 标题
        m_name = re.search(r"<h1>([\s\S]*?)</h1>", html, re.S)
        vod_name = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m_name.group(1))).strip() if m_name else "未知名称"
    
        # 封面（详情页通常没有主封面，兜底从猜你喜欢首图拿）
        m_pic = re.search(r'<img[^>]+(?:data-src|src)=["\']([^"\']+)["\']', html, re.I)
        vod_pic = ""
        if m_pic:
            p = m_pic.group(1).strip()
            if p.startswith("//"):
                vod_pic = "https:" + p
            elif p.startswith(("http://", "https://")):
                vod_pic = p
            else:
                vod_pic = self.site_url + (p if p.startswith("/") else "/" + p)
    
        # 关键：提取 iframe 播放页地址
        m_iframe = re.search(
            r'<iframe[^>]*class=["\']player-iframe["\'][^>]*src=["\']([^"\']+)["\']',
            html, re.I | re.S
        )
        play_entry = ""
        if m_iframe:
            iframe_src = m_iframe.group(1).strip()
            if iframe_src.startswith("//"):
                iframe_src = "https:" + iframe_src
            elif not iframe_src.startswith(("http://", "https://")):
                iframe_src = self.site_url + (iframe_src if iframe_src.startswith("/") else "/" + iframe_src)
    
            # !!! 必须是 名称$地址
            play_entry = f"在线播放${iframe_src}"
        else:
            # 兜底：给详情页，让 playerContent 再二次提 iframe
            play_entry = f"在线播放${vod_id}"
    
        detail_info = {
            "vod_id": vod_id,
            "vod_name": vod_name,
            "vod_pic": vod_pic,
            "vod_remarks": "",
            "type_name": "",
            "vod_play_from": "主线路",
            "vod_play_url": play_entry
        }
        return {"list": [detail_info]}
    
    
    def playerContent(self, flag, id, vipFlags):
        import re
        import json
        from urllib.parse import urljoin, urlparse, parse_qsl, urlencode, urlunparse, unquote
    
        def force_m_stream(u):
            """强制线路为 M原版：src=missav，移除 variant"""
            pr = urlparse(u)
            q = dict(parse_qsl(pr.query, keep_blank_values=True))
            q["res"] = "720P"
            q["src"] = "missav"
            q.pop("variant", None)
            new_query = urlencode(q, doseq=True)
            return urlunparse((pr.scheme, pr.netloc, pr.path, pr.params, new_query, pr.fragment))
    
        def abs_url(u, base):
            if u.startswith("//"):
                return "https:" + u
            if u.startswith(("http://", "https://")):
                return u
            return urljoin(base, u)
    
        play_url = id.split("$", 1)[1] if "$" in id else id
        if not play_url:
            return {"parse": 0, "url": "", "header": self.headers}
    
        play_url = abs_url(play_url, self.site_url)
    
        # 直链直接返回
        if re.search(r"\.(m3u8|mp4|flv)(\?|$)", play_url, re.I):
            return {"parse": 0, "url": play_url, "header": self.headers}
    
        # 先请求当前地址（可能是详情页，也可能是 iframe 页）
        try:
            h = dict(self.headers)
            h["Referer"] = self.site_url
            r = self.sess.get(play_url, headers=h, timeout=10, verify=False)
            if not (r and r.ok):
                return {"parse": 1, "url": play_url, "header": self.headers}
            html = r.text
        except Exception:
            return {"parse": 1, "url": play_url, "header": self.headers}
    
        # 若是详情页，先提取 iframe
        m_iframe = re.search(
            r'<iframe[^>]*class=["\']player-iframe["\'][^>]*src=["\']([^"\']+)["\']',
            html, re.I | re.S
        )
        if m_iframe:
            iframe_url = abs_url(m_iframe.group(1).strip(), play_url)
        else:
            iframe_url = play_url
    
        # 强制 M原版
        iframe_url = force_m_stream(iframe_url)
    
        # 请求 iframe 页面
        try:
            h2 = dict(self.headers)
            h2["Referer"] = play_url
            r2 = self.sess.get(iframe_url, headers=h2, timeout=10, verify=False)
            if not (r2 and r2.ok):
                return {"parse": 1, "url": iframe_url, "header": self.headers}
            ihtml = r2.text
        except Exception:
            return {"parse": 1, "url": iframe_url, "header": self.headers}
    
        final_url = ""
    
        # 主解析：var playurls = [...]
        m = re.search(r"var\s+playurls\s*=\s*(\[[\s\S]*?\])\s*;", ihtml, re.I)
        if m:
            try:
                arr = json.loads(m.group(1))
                if isinstance(arr, list) and arr:
                    # playurls 通常已是当前线路的结果，取 auto 或第一个
                    target = None
                    for it in arr:
                        if isinstance(it, dict) and str(it.get("name", "")).lower() == "auto" and it.get("url"):
                            target = it
                            break
                    if target is None:
                        target = arr[0]
    
                    if isinstance(target, dict):
                        u = str(target.get("url", "")).strip().replace("\\/", "/")
                        u = unquote(u)
                        final_url = abs_url(u, iframe_url)
            except Exception:
                pass
    
        # 兜底正则
        if not final_url:
            mm = re.search(r'https?://[^\s"\'<>]+?\.(?:m3u8|mp4|flv)(?:\?[^\s"\'<>]*)?', ihtml, re.I)
            if mm:
                final_url = mm.group(0).strip()
    
        if final_url:
            return {
                "parse": 0,
                "url": final_url,
                "header": {
                    "User-Agent": self.headers.get("User-Agent", ""),
                    "Referer": iframe_url
                }
            }
    
        return {"parse": 1, "url": iframe_url, "header": self.headers} 
