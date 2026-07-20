# coding=utf-8
import re
import sys
import time
import random
from urllib.parse import quote, urljoin

from base.spider import Spider as BaseSpider

sys.path.append("..")


class Spider(BaseSpider):
    def __init__(self):
        self.name = "琉璃神社"
        self.host = "https://www.hacg.icu"
        self.backend_parse = True
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.6261.95 Safari/537.36"
            ),
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Cookie": "existmag=mag; dv=1; age=verified",
        }
        # 分类列表（对应顶部导航）
        self.categories = [
            {"type_id": "latest", "type_name": "最新更新"},
            {"type_id": "anime", "type_name": "动画"},
            {"type_id": "comic", "type_name": "漫画"},
            {"type_id": "game", "type_name": "游戏"},
            {"type_id": "other", "type_name": "其他"},
            {"type_id": "goods", "type_name": "周边"},
            {"type_id": "op", "type_name": "音乐"},
            {"type_id": "book", "type_name": "轻小说"},
        ]
        # 分类 URL 映射
        self.category_paths = {
            "latest": "/wp/",
            "anime": "/wp/anime.html",
            "comic": "/wp/comic.html",
            "game": "/wp/game.html",
            "other": "/wp/other.html",
            "goods": "/wp/goods.html",
            "op": "/wp/op.html",
            "book": "/wp/book.html",
        }

    # ---------- 工具方法 ----------
    @staticmethod
    def _clean(s):
        return re.sub(r"\s+", " ", str(s or "")).strip()

    def _build_url(self, path):
        if not path:
            return self.host
        if str(path).startswith("http"):
            return path
        return urljoin(self.host.rstrip("/") + "/", str(path).strip().lstrip("/"))

    @staticmethod
    def _extract_hash(text):
        if not text:
            return None
        match = re.search(r'([a-fA-F0-9]{40})', text, re.I)
        return match.group(1).lower() if match else None

    @staticmethod
    def _extract_file_size(text):
        if not text:
            return ""
        match = re.search(r'([\d.]+)\s*(TB|GB|MB|KB)', text, re.I)
        return f"{match.group(1)}{match.group(2).upper()}" if match else ""

    @staticmethod
    def _parse_size_bytes(size_str):
        if not size_str:
            return 0
        match = re.search(r'([\d.]+)\s*(TB|GB|MB|KB)', size_str, re.I)
        if not match:
            return 0
        val = float(match.group(1))
        unit = match.group(2).upper()
        multipliers = {"KB": 1024, "MB": 1048576, "GB": 1073741824, "TB": 1099511627776}
        return int(val * multipliers.get(unit, 1))

    # ---------- HTTP 请求 ----------
    def _request(self, url):
        target = self._build_url(url)
        try:
            rsp = self.fetch(target, headers=self.headers, timeout=15, verify=False, allow_redirects=True)
            return rsp.text or ""
        except Exception:
            return ""

    # ---------- 解析列表（带封面图） ----------
    def _parse_article_list(self, html):
        if not html:
            return []
        root = self.html(html)
        if root is None:
            return []

        items = []
        seen = set()

        for article in root.xpath("//article"):
            # 标题 & 链接
            title_node = article.xpath(".//h1[@class='entry-title']/a | .//h1[contains(@class,'entry-title')]/a")
            if not title_node:
                continue
            link = self._clean("".join(title_node[0].xpath("./@href")))
            title = self._clean("".join(title_node[0].xpath(".//text()")))
            if not link or not title:
                continue

            vid = link.strip("/").split("/")[-1].replace(".html", "")
            if not vid or vid in seen:
                continue
            seen.add(vid)

            # 封面图：从 entry-content 中取第一张图
            pic = ""
            img_nodes = article.xpath(".//div[@class='entry-content']//img[1]/@src")
            if not img_nodes:
                img_nodes = article.xpath(".//img[1]/@src")
            if img_nodes:
                pic = self._build_url(self._clean(img_nodes[0]))

            # 摘要
            excerpt = ""
            content_div = article.xpath(".//div[@class='entry-content']")
            if content_div:
                excerpt = self._clean("".join(content_div[0].xpath(".//text()")))[:100]

            # 评论数
            comments = article.xpath(".//div[@class='comments-link']/a/text()")
            comment_count = self._clean("".join(comments)) if comments else ""

            items.append({
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": comment_count,
                "vod_content": excerpt,
            })

        return items

    def _has_next_page(self, html):
        if not html:
            return False
        return bool(re.search(r'<a[^>]*class="nextpostslink"[^>]*>', html)) or \
               bool(re.search(r'<a[^>]*rel="next"[^>]*>', html))

    def _get_page_url(self, base_path, page):
        if page <= 1:
            return base_path
        # 处理分页格式
        if base_path.endswith(".html"):
            base = base_path[:-5]  # 去掉 .html
        else:
            base = base_path.rstrip("/")
        return f"{base}/page/{page}"

    # ---------- 接口方法 ----------
    def init(self, extend=""):
        return None

    def getName(self):
        return self.name

    def danmaku(self):
        return False

    def homeContent(self, filter):
        return {"class": self.categories}

    def homeVideoContent(self):
        try:
            html = self._request("/wp/")
            items = self._parse_article_list(html)[:24]
        except Exception:
            items = []
        return {"list": items}

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) or 1
        base_path = self.category_paths.get(tid, "/wp/")
        url = self._build_url(self._get_page_url(base_path, page))
        html = self._request(url)
        items = self._parse_article_list(html) if html else []
        has_next = self._has_next_page(html) if html else False

        return {
            "page": page,
            "pagecount": page + 1 if has_next else page,
            "limit": len(items),
            "total": 9999,
            "list": items,
        }

    def searchContent(self, key, quick, pg=1, category=""):
        keyword = self._clean(key)
        if not keyword:
            return {"list": [], "page": 1, "pagecount": 1, "total": 0}

        page = int(pg) or 1
        if page <= 1:
            url = self._build_url(f"/wp/?s={quote(keyword)}")
        else:
            url = self._build_url(f"/wp/page/{page}?s={quote(keyword)}")

        html = self._request(url)
        items = self._parse_article_list(html) if html else []
        has_next = self._has_next_page(html) if html else False

        return {
            "list": items,
            "page": page,
            "pagecount": page + 1 if has_next else page,
            "total": 9999,
        }

    def detailContent(self, ids):
        result = {"list": []}

        for raw_id in ids:
            vid = str(raw_id or "").strip()
            if not vid:
                continue

            if vid.endswith(".html"):
                detail_url = self._build_url(f"/wp/{vid}")
            else:
                detail_url = self._build_url(f"/wp/{vid}.html")

            html = self._request(detail_url)
            if not html:
                continue

            root = self.html(html)
            if root is None:
                continue

            # 标题
            title = vid
            title_nodes = root.xpath("//h1[@class='entry-title']//text()")
            if title_nodes:
                title = self._clean("".join(title_nodes))

            # 封面图
            pic = ""
            img_nodes = root.xpath("//div[@class='entry-content']//img[1]/@src")
            if img_nodes:
                pic = self._build_url(self._clean(img_nodes[0]))

            # 正文内容（用于提取哈希和大小）
            content = ""
            content_div = root.xpath("//div[@class='entry-content']")
            if content_div:
                content = self._clean(content_div[0].xpath("string(.)"))

            # === 提取磁力链（40位哈希） ===
            magnets = []
            seen_hashes = set()

            # 提取所有40位hex
            all_hashes = re.findall(r'([a-fA-F0-9]{40})', content, re.I)
            for h in all_hashes:
                h_lower = h.lower()
                if h_lower in seen_hashes:
                    continue
                seen_hashes.add(h_lower)
                size_str = self._extract_file_size(content)
                magnet_url = f"magnet:?xt=urn:btih:{h_lower}"
                magnets.append({
                    "magnet": magnet_url,
                    "hash": h_lower,
                    "size": self._parse_size_bytes(size_str),
                    "size_label": size_str,
                })

            # 按大小排序（大的在前）
            magnets.sort(key=lambda x: x["size"], reverse=True)

            # 构建播放列表
            play_from = []
            play_url = []
            for idx, mag in enumerate(magnets[:50]):
                label = mag["hash"][:8] + "..."
                if mag["size_label"]:
                    label += f" [{mag['size_label']}]"
                play_from.append(label)
                play_url.append(f"{label}${mag['magnet']}")

            if not magnets:
                play_from = ["无磁力链接"]
                play_url = ["无磁力链接$"]

            result["list"].append({
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": pic,
                "type_name": "琉璃神社",
                "vod_content": content[:500] if content else title,
                "vod_play_from": "$$$".join(play_from),
                "vod_play_url": "$$$".join(play_url),
            })

        return result

    def playerContent(self, flag, id, vipFlags):
        url = str(id or "").strip()
        if url.startswith("magnet:?"):
            return {"parse": 0, "jx": 0, "playUrl": "", "url": url, "header": {}}
        if url.startswith("http"):
            return {"parse": 0, "jx": 0, "playUrl": "", "url": url, "header": {}}
        return {"parse": 0, "jx": 0, "playUrl": "", "url": "", "header": {}}