# -*- coding: utf-8 -*-
import sys
import re
import requests
from urllib.parse import urljoin
from pyquery import PyQuery as pq
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

sys.path.append('..')
from base.spider import Spider

requests.packages.urllib3.disable_warnings()


class Spider(Spider):
    def __init__(self):
        super().__init__()
        # 网站基础地址（无需重定向，直接使用）
        self.siteUrl = "https://aidjst.cc/888"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": self.siteUrl + "/"
        }
        self.session = self._create_session()
        self.debug = False  # 关闭调试输出，提高速度

    def _create_session(self):
        session = requests.Session()
        adapter = HTTPAdapter(pool_connections=20, pool_maxsize=50, max_retries=Retry(total=2))
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        session.headers.update(self.headers)
        return session

    def getName(self):
        return "AI顶级涩图极简版"

    def init(self, extend=""):
        pass

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def destroy(self):
        self.session.close()

    def homeContent(self, filter):
        """
        返回分类列表（自定义一个“AI图片”分类）
        """
        classes = [
            {"type_id": "ai_tu", "type_name": "🤖 AI图片"}
        ]
        return {"class": classes, "filters": {}}

    def categoryContent(self, tid, pg, filter, extend):
        """
        获取分类页内容（实际是首页，按页码翻页）
        tid 暂时忽略，因为只有一个分类
        pg: 页码，从1开始
        首页第1页：https://aidjst.cc/888/
        第2页：https://aidjst.cc/888/index.php/page/2/
        第3页：https://aidjst.cc/888/index.php/page/3/
        """
        pg = int(pg)
        if pg == 1:
            url = self.siteUrl
        else:
            url = f"{self.siteUrl}/index.php/page/{pg}"
        return self._parse_list(url, pg)

    def searchContent(self, key, quick, pg="1"):
        # 此网站没有公开搜索接口，暂不支持
        return {"list": []}

    def _parse_list(self, url, pg):
        """解析列表页（首页/分类页），提取每个图集的链接、标题、封面"""
        try:
            resp = self.session.get(url, timeout=10)
            if resp.status_code != 200:
                return {"list": []}
            doc = pq(resp.text)

            videos = []
            # 每个图集在 article.post 容器中（根据分类页源码）
            for article in doc('article.post').items():
                # 详情页链接
                link = article('.entry-title a')
                href = link.attr('href')
                if not href:
                    continue
                # 标题
                title = link.text().strip()
                # 封面图（post-thumbnail 中的 img）
                img = article('.post-thumbnail img')
                img_url = img.attr('src')
                if not img_url:
                    # 如果没有找到，尝试其他选择器
                    img = article('img')
                    img_url = img.attr('src')
                if img_url and img_url.startswith('//'):
                    img_url = 'https:' + img_url
                # 副标题（图片数量，标题中可能包含 [xxP]）
                remarks = ""
                match = re.search(r'\[(\d+)P\]', title)
                if match:
                    remarks = f"{match.group(1)}P"
                else:
                    remarks = "AI套图"
                # 构造 vod_id（存储详情页 URL）
                vod_id = f"{href}@@@{title}@@@{img_url}"
                videos.append({
                    "vod_id": vod_id,
                    "vod_name": title,
                    "vod_pic": img_url,
                    "vod_remarks": remarks
                })

            # 不获取最大页数，固定返回 999 页
            page_count = 999

            return {
                "list": videos,
                "page": pg,
                "pagecount": page_count,
                "limit": len(videos),
                "total": 999999
            }
        except Exception as e:
            return {"list": []}

    def detailContent(self, ids):
        """获取详情页中的所有图片"""
        try:
            if not ids:
                return {"list": []}
            parts = ids[0].split("@@@")
            url = parts[0]
            title = parts[1] if len(parts) > 1 else ""
            cover = parts[2] if len(parts) > 2 else ""

            resp = self.session.get(url, timeout=10)
            if resp.status_code != 200:
                return {"list": []}
            doc = pq(resp.text)

            # 提取文章内容中的所有图片（.entry-content 下的 figure.wp-block-image img）
            image_urls = []
            for img in doc('.entry-content img').items():
                src = img.attr('src')
                if not src:
                    continue
                # 处理协议相对路径
                if src.startswith('//'):
                    src = 'https:' + src
                elif src.startswith('/'):
                    src = urljoin(self.siteUrl, src)
                # 过滤掉 gif 广告图（可选）
                if src.endswith('.gif'):
                    continue
                image_urls.append(src)

            # 去重
            image_urls = list(dict.fromkeys(image_urls))

            # 构建播放 URL（直接返回图片地址列表，无代理）
            play_url = "pics://" + "&&".join(image_urls) if image_urls else ""

            return {
                "list": [{
                    "vod_id": ids[0],
                    "vod_name": title,
                    "vod_pic": cover,
                    "type_name": "AI高清套图",
                    "vod_actor": "AI顶级涩图",
                    "vod_director": "AI生成",
                    "vod_content": f"共 {len(image_urls)} 张图片",
                    "vod_play_from": "图片阅览",
                    "vod_play_url": f"全集浏览${play_url}"
                }]
            }
        except Exception as e:
            return {"list": []}

    def playerContent(self, flag, id, vipFlags):
        if id.startswith("pics://"):
            return {"parse": 0, "playUrl": "", "url": id, "header": ""}
        return {"parse": 0, "url": "", "header": ""}

    def localProxy(self, param):
        return [404, "text/plain", b"Proxy not needed"]