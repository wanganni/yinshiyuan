# coding=utf-8
"""
目标站: Jable.TV  适配 TVBox (Py 引擎)
修复：分类「按主题」「按女优」无数据
"""
import re
import sys
import urllib.parse
from bs4 import BeautifulSoup

sys.path.append('..')
from base.spider import Spider

class Spider(Spider):

    def init(self, extend=""):
        self.site_url = "https://jable.tv"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
        }

    def homeContent(self, filter):
        url = self.site_url + "/"
        resp = self.fetch(url, headers=self.headers)
        categories = []
        if resp:
            soup = BeautifulSoup(resp.text, 'html.parser')
            nav_links = soup.select('nav.app-nav a')
            for a in nav_links:
                href = a.get('href', '').strip()
                name = a.get_text(strip=True)
                if not href or 'javascript' in href or name == '':
                    continue
                if href.startswith(self.site_url) or href.startswith('/'):
                    path = href if href.startswith('/') else href.replace(self.site_url, '')
                    path = path.strip('/')
                    if path.startswith('c') and len(path) > 2 and path[1].isdigit():
                        continue
                    categories.append({"type_id": path, "type_name": name})
        seen = set()
        unique_cat = []
        for c in categories:
            if c['type_id'] not in seen:
                seen.add(c['type_id'])
                unique_cat.append(c)
        video_list = self._parse_video_list(resp) if resp else []
        return {"class": unique_cat, "list": video_list[:20], "filters": {}}

    def homeVideoContent(self):
        return self.homeContent(False)

    # ---------- 分类列表（支持子类目解析） ----------
    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg else 1
        # 特殊处理：按主题(categories) 和按女优(models) 的首页是子类目列表
        if tid in ('categories', 'models'):
            return self._sub_category_list(tid)
        
        # 普通视频列表分类
        base = f"{self.site_url}/{tid}/"
        params = {}
        if page > 1:
            params['page'] = page
        if extend:
            for k, v in extend.items():
                if v:
                    params[k] = v
        query = urllib.parse.urlencode(params)
        url = base if not query else f"{base}?{query}"

        resp = self.fetch(url, headers=self.headers)
        if not resp:
            return {"list": [], "page": page, "pagecount": 1, "limit": 24, "total": 0}

        soup = BeautifulSoup(resp.text, 'html.parser')
        video_list = self._parse_video_list(resp)
        limit = 24
        pagecount = self._get_pagecount(soup, page, limit, len(video_list))

        return {
            "list": video_list,
            "page": page,
            "pagecount": pagecount,
            "limit": limit,
            "total": pagecount * limit
        }

    # 解析子类目列表（categories 或 models）
    def _sub_category_list(self, tid):
        url = f"{self.site_url}/{tid}/"
        resp = self.fetch(url, headers=self.headers)
        if not resp:
            return {"list": [], "page": 1, "pagecount": 1, "limit": 100, "total": 0}
        soup = BeautifulSoup(resp.text, 'html.parser')
        items = []
        # 尝试匹配常见的分类卡片结构
        # 主题页通常都是 <a> 包含图片和名称，链接到 /categories/xxx/
        # 女优页类似
        cards = soup.select('.category-grid a, .model-grid a, .grid-item a, a[href*="/categories/"], a[href*="/models/"]')
        seen = set()
        for a in cards:
            href = a.get('href', '').strip()
            if not href:
                continue
            # 确保是子分类/女优的链接
            if f'/{tid}/' not in href:
                continue
            # 提取相对路径作为 vod_id
            sub_id = href.replace(self.site_url, '').strip('/')
            if sub_id in seen:
                continue
            seen.add(sub_id)
            # 名称
            name_elem = a.select_one('.title, .name, h6, .model-name')
            name = name_elem.get_text(strip=True) if name_elem else a.get_text(strip=True)
            # 图片
            img_elem = a.select_one('img')
            pic = ''
            if img_elem:
                pic = img_elem.get('data-src') or img_elem.get('src') or ''
            items.append({
                "vod_id": sub_id,          # 将子类目路径作为 id，下次点击会进入视频列表
                "vod_name": name,
                "vod_pic": pic,
                "vod_remarks": ''
            })
        return {
            "list": items,
            "page": 1,
            "pagecount": 1,
            "limit": len(items),
            "total": len(items)
        }

    def _get_pagecount(self, soup, current_page, limit, current_count):
        total_text = ''
        total_elem = soup.select_one('.showing, .total, .result-count')
        if total_elem:
            total_text = total_elem.get_text()
        if total_text:
            nums = re.findall(r'(\d[\d,]*)', total_text)
            if nums:
                total_num = int(nums[-1].replace(',', ''))
                if total_num > 0:
                    return max(1, -(-total_num // limit))
        pager = soup.select('.pagination a, .pagination span')
        max_page = 1
        for elem in pager:
            t = elem.get_text(strip=True)
            if t.isdigit():
                max_page = max(max_page, int(t))
        if max_page > 1:
            return max_page
        next_links = [a for a in pager if '下一頁' in a.get_text() or 'next' in a.get_text().lower()]
        if next_links and current_count >= limit:
            return current_page + 1
        if current_count < limit:
            return current_page
        return current_page

    # ---------- 列表解析（标题修复） ----------
    def _parse_video_list(self, resp):
        soup = BeautifulSoup(resp.text, 'html.parser')
        video_list = []
        cards = soup.select('div.video-img-box')
        if not cards:
            cards = soup.select('#site-content .container .row .col .row .video-img-box')
        for card in cards:
            img_box_a = card.select_one('div.img-box > a')
            if not img_box_a:
                continue
            href = img_box_a.get('href', '')
            match = re.search(r'/videos/([^/]+)', href)
            if not match:
                continue
            vod_id = match.group(1)
            title_elem = card.select_one('div.detail h6.title') or card.select_one('h6.title') or card.select_one('div.detail h6') or card.select_one('.title')
            vod_name = title_elem.get_text(strip=True) if title_elem else '未知标题'
            img_elem = img_box_a.select_one('img.lazyload')
            vod_pic = ''
            if img_elem:
                vod_pic = img_elem.get('data-src') or img_elem.get('src') or ''
            video_list.append({
                "vod_id": vod_id,
                "vod_name": vod_name,
                "vod_pic": vod_pic,
                "vod_remarks": ''
            })
        return video_list

    # ---------- 详情页 ----------
    def detailContent(self, ids):
        if not ids:
            return {"list": []}
        vod_id = ids[0]
        url = f"{self.site_url}/videos/{vod_id}/"
        resp = self.fetch(url, headers=self.headers)
        if not resp:
            return {"list": []}

        soup = BeautifulSoup(resp.text, 'html.parser')
        vod_name = ''
        name_elem = soup.select_one('h1.title') or soup.select_one('h4') or soup.select_one('.video-title')
        if name_elem:
            vod_name = name_elem.get_text(strip=True)

        vod_pic = ''
        img_elem = soup.select_one('div.video-thumbnail img') or soup.select_one('img.lazyload')
        if img_elem:
            vod_pic = img_elem.get('data-src') or img_elem.get('src') or ''

        vod_content = ''
        desc_elem = soup.select_one('.description') or soup.select_one('meta[name="description"]')
        if desc_elem:
            if desc_elem.name == 'meta':
                vod_content = desc_elem.get('content', '')
            else:
                vod_content = desc_elem.get_text(strip=True)

        actor_elems = soup.select('a[href*="/models/"]')
        actors = [a.get_text(strip=True) for a in actor_elems if a.get_text(strip=True)]
        vod_actor = ', '.join(actors) if actors else ''
        director_elem = soup.select_one('a[href*="/director/"]')
        vod_director = director_elem.get_text(strip=True) if director_elem else ''

        m3u8_link = self._extract_m3u8(resp.text, soup)

        vod_play_from = '高清'
        vod_play_url = ''
        if m3u8_link:
            vod_play_url = f'高清${m3u8_link}'
        else:
            vod_play_url = f'解析${url}'

        result = [{
            "vod_id": vod_id,
            "vod_name": vod_name,
            "vod_pic": vod_pic,
            "vod_content": vod_content,
            "vod_actor": vod_actor,
            "vod_director": vod_director,
            "vod_play_from": vod_play_from,
            "vod_play_url": vod_play_url
        }]
        return {"list": result}

    def _extract_m3u8(self, html_text, soup):
        candidates = set()
        script_texts = []
        for script in soup.select('script'):
            if script.string:
                script_texts.append(script.string)
        full_js = '\n'.join(script_texts)

        patterns = [
            r'(?:videoSource|source|src|file|hlsUrl|url)\s*[:=]\s*["\']([^"\']+\.m3u8[^"\']*)',
            r'["\']([^"\']+\.m3u8)["\']',
        ]
        for pat in patterns:
            for m in re.finditer(pat, full_js, re.IGNORECASE):
                link = m.group(1)
                if any(s in link.lower() for s in ['google', 'facebook', 'analytics', 'pixel']):
                    continue
                candidates.add(link)

        if not candidates:
            for m in re.finditer(r'["\']([^"\']+\.m3u8)["\']', html_text, re.IGNORECASE):
                link = m.group(1)
                if any(s in link.lower() for s in ['google', 'facebook', 'analytics', 'pixel']):
                    continue
                candidates.add(link)

        for link in candidates:
            if link.startswith('//'):
                link = 'https:' + link
            elif link.startswith('/'):
                link = self.site_url + link
            if link.startswith('http') and '.m3u8' in link:
                return link
        return None

    # ---------- 搜索 ----------
    def searchContent(self, key, quick, pg="1"):
        page = int(pg) if pg else 1
        encoded_key = urllib.parse.quote(key)
        url = f"{self.site_url}/search/?keyword={encoded_key}"
        if page > 1:
            url += f"&page={page}"
        resp = self.fetch(url, headers=self.headers)
        if not resp:
            return {"list": [], "page": page, "pagecount": 1}
        video_list = self._parse_video_list(resp)
        return {
            "list": video_list,
            "page": page,
            "pagecount": 1,
            "limit": 24,
            "total": len(video_list)
        }

    def playerContent(self, flag, id, vipFlags):
        if id.startswith('http') and '.m3u8' in id:
            return {"parse": 0, "url": id, "header": self.headers}
        return {"parse": 1, "url": id, "header": self.headers}