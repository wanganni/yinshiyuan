# coding=utf-8
"""
目标站: JAVXX  首页: https://javxx.com
修复 pagecount 始终为 1 的问题，改用 href 提取总页数
"""
import re
import sys
import json
import urllib.parse
from bs4 import BeautifulSoup

sys.path.append('..')
from base.spider import Spider

class Spider(Spider):

    def init(self, extend=""):
        self.site_url = "https://javxx.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': self.site_url,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
        }

        self.categories = [
            {"type_id": "new", "type_name": "最新"},
            {"type_id": "hot", "type_name": "热门"},
            {"type_id": "recent", "type_name": "最近"},
            {"type_id": "today", "type_name": "今日"},
            {"type_id": "weekly", "type_name": "每周"}
        ]

        self.filters = {
            "new": [{"key": "type", "name": "类型", "value": [
                {"n": "全部", "v": ""},
                {"n": "无码", "v": "uncensored"},
                {"n": "无码泄露", "v": "uncensored-leaked"},
                {"n": "VR", "v": "vr"},
                {"n": "有码", "v": "censored"}
            ]}]
        }

    def _parse_cards(self, soup, max_items=0):
        seen = set()
        video_list = []
        containers = soup.select('main div.container section div.body div.vid-items')
        if not containers:
            containers = soup.select('div.vid-items')
        for block in containers:
            for a in block.select('a.poster[href^="/cn/v/"]'):
                href = a.get('href', '').strip()
                if not href:
                    continue
                slug = href.replace('/cn/v/', '')
                if slug in seen:
                    continue
                seen.add(slug)
                parent = a.find_parent('div', class_='item')
                title_tag = parent.select_one('.info a.title') if parent else None
                vod_name = title_tag.get_text(strip=True) if title_tag else a.get('title', slug)
                img_tag = a.select_one('div.image img') or a.select_one('img')
                vod_pic = ''
                if img_tag:
                    src = img_tag.get('data-src', '') or img_tag.get('src', '')
                    if src:
                        vod_pic = src if src.startswith('http') else 'https:' + src
                video_list.append({
                    "vod_id": slug,
                    "vod_name": vod_name,
                    "vod_pic": vod_pic,
                    "vod_remarks": ""
                })
                if max_items and len(video_list) >= max_items:
                    break
            if max_items and len(video_list) >= max_items:
                break
        return video_list

    def homeContent(self, filter):
        try:
            resp = self.fetch(self.site_url + "/cn", headers=self.headers)
            video_list = self._parse_cards(BeautifulSoup(resp.text, 'html.parser'), 20) if resp else []
        except:
            video_list = []
        return {"class": self.categories, "list": video_list, "filters": self.filters}

    def homeVideoContent(self):
        return self.homeContent(False)

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg else 1
        type_val = extend.get('type', '') if extend else ''

        # 构造基础 URL
        if tid == "new":
            base = f"{self.site_url}/cn/new"
            if type_val:
                base += f"?type={type_val}"
        elif tid == "today":
            base = f"{self.site_url}/cn/all?sort=today_views"
        elif tid == "weekly":
            base = f"{self.site_url}/cn/all?sort=weekly_views"
        elif tid == "hot":
            base = f"{self.site_url}/cn/hot"
        elif tid == "recent":
            base = f"{self.site_url}/cn/recent"
        else:
            base = f"{self.site_url}/cn"

        if page > 1:
            url = base + ("&" if "?" in base else "?") + f"page={page}"
        else:
            url = base

        try:
            resp = self.fetch(url, headers=self.headers)
            if not resp:
                return {"list": [], "page": page, "pagecount": 1, "limit": 24, "total": 0}

            soup = BeautifulSoup(resp.text, 'html.parser')
            video_list = self._parse_cards(soup)

            # ===== 改进的分页计算 =====
            pagecount = 1
            nav = soup.select_one('nav.simple')
            if nav:
                # 1) 从所有链接的 href 中提取 page= 参数，取最大值
                max_page = 1
                for a in nav.select('a'):
                    href = a.get('href', '')
                    match = re.search(r'page=(\d+)', href)
                    if match:
                        max_page = max(max_page, int(match.group(1)))
                if max_page > 1:
                    pagecount = max_page
                else:
                    # 2) 没有数字页码链接，看是否有“下一页”按钮（可根据实际调整）
                    next_btn = nav.select_one('a:contains("下页"), a:contains("下一页"), a[rel="next"]')
                    if next_btn:
                        pagecount = page + 1 if len(video_list) >= 24 else page
                    else:
                        pagecount = page
            else:
                # 无导航栏时，根据数据量推测
                if len(video_list) >= 24:
                    pagecount = page + 1
                else:
                    pagecount = page

            # 若当前页无数据且页码 >1，修正为前一页
            if not video_list and page > 1:
                pagecount = page - 1
            # 保证不小于当前页
            if pagecount < page:
                pagecount = page

        except:
            video_list = []
            pagecount = page

        return {
            "list": video_list,
            "page": page,
            "pagecount": pagecount,
            "limit": 24,
            "total": len(video_list) * pagecount,
        }

    def detailContent(self, ids):
        if not ids:
            return {"list": []}
        vod_id = ids[0]
        url = f"{self.site_url}/cn/v/{vod_id}"
        try:
            resp = self.fetch(url, headers=self.headers)
            if not resp or resp.status_code != 200:
                return {"list": []}
            soup = BeautifulSoup(resp.text, 'html.parser')

            title_elem = soup.select_one('h1.title') or soup.select_one('#video-info h1.title')
            vod_name = title_elem.get_text(strip=True) if title_elem else vod_id

            vod_pic = ''
            og = soup.select_one('meta[property="og:image"]')
            if og:
                vod_pic = og.get('content', '')
            if not vod_pic:
                poster = soup.select_one('div.video-poster img') or soup.select_one('div.poster img')
                if poster:
                    src = poster.get('data-src', '') or poster.get('src', '')
                    if src:
                        vod_pic = src if src.startswith('http') else 'https:' + src

            vod_content = ''
            desc = soup.select_one('#video-details d-tag.desc') or soup.select_one('meta[name="description"]')
            if desc:
                vod_content = desc.get('content', '') if desc.name == 'meta' else desc.get_text(strip=True)

            vod_actor = ''
            kw = soup.select_one('meta[name="keywords"]')
            if kw:
                vod_actor = kw.get('content', '')

            vod_play_from = '默认线路'
            vod_play_url = f"视频${url}"

            return {"list": [{
                "vod_id": vod_id,
                "vod_name": vod_name,
                "vod_pic": vod_pic,
                "vod_content": vod_content,
                "vod_actor": vod_actor,
                "vod_director": '',
                "vod_area": '',
                "vod_year": '',
                "vod_play_from": vod_play_from,
                "vod_play_url": vod_play_url,
            }]}
        except:
            return {"list": []}

    def searchContent(self, key, quick, pg="1"):
        page = int(pg) if pg else 1
        url = f"{self.site_url}/cn/search?q={urllib.parse.quote(key)}"
        if page > 1:
            url += f"&page={page}"
        try:
            resp = self.fetch(url, headers=self.headers)
            video_list = self._parse_cards(BeautifulSoup(resp.text, 'html.parser'), 20) if resp else []
        except:
            video_list = []
        return {"list": video_list, "page": page, "pagecount": 1}

    def playerContent(self, flag, id, vipFlags):
        if not id.startswith('http'):
            url = self.site_url + id
        else:
            url = id
        return {"parse": 1, "url": url, "header": self.headers}