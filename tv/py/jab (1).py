# coding=utf-8
"""
目标站: Jable.TV  完美多级分类，稳定不闪退，头像正常显示
已添加代理核心逻辑 & 图片海报增强提取
"""
import json
import re
import sys
import urllib.parse
from bs4 import BeautifulSoup
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def init(self, extend=""):
        # ----------------- 代理配置解析 -----------------
        self.proxies = {}
        if extend:
            try:
                config = json.loads(extend)
                self.proxies = config.get('proxy', {})
            except Exception as e:
                print(f"代理配置解析错误: {str(e)}")

        self.site_url = "https://jable.tv"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
        }

        # ----------------- 创建带重试和代理的会话 -----------------
        self.session = self._create_session()
        self.session.headers.update(self.headers)
        self.session.proxies = self.proxies

    def _create_session(self):
        """创建带重试机制的会话，优化连接稳定性"""
        session = Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.3,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def destroy(self):
        if hasattr(self, 'session'):
            self.session.close()

    def fetch(self, url, headers=None, **kwargs):
        """使用带代理的会话发起 GET 请求，保持与原 fetch 接口兼容"""
        merged_headers = self.headers.copy()
        if headers:
            merged_headers.update(headers)
        return self.session.get(url, headers=merged_headers, timeout=10, **kwargs)

    # ═══ 首页 ═══════════════════════════════════
    def homeContent(self, filter):
        try:
            url = self.site_url + "/"
            resp = self.fetch(url, headers=self.headers)
            cat_list = []
            if resp:
                soup = BeautifulSoup(resp.text, 'html.parser')
                for a in soup.select('nav.app-nav a'):
                    href = (a.get('href') or '').strip()
                    name = a.get_text(strip=True)
                    if not href or 'javascript' in href or not name:
                        continue
                    if href.startswith('/'):
                        type_id = href.strip('/')
                    elif href.startswith(self.site_url):
                        type_id = href.replace(self.site_url, '').strip('/')
                    else:
                        continue
                    if type_id and type_id.split('/')[0].startswith('c') and type_id[-1].isdigit():
                        continue
                    cat_list.append({"type_id": type_id, "type_name": name})

            vlist = self._parse_video_list(resp) if resp else []
            return {"class": cat_list, "list": vlist[:20], "filters": {}}
        except Exception:
            return {"class": [], "list": [], "filters": {}}

    def homeVideoContent(self):
        return self.homeContent(False)

    # ═══ 分类内容 ═══════════════════════════════
    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg else 1
        try:
            if tid in ("", "home", "latest-updates", "hot"):
                if tid in ("home", ""):
                    if page > 1:
                        return self._empty_result(page)
                    url = self.site_url + "/"
                else:
                    url = f"{self.site_url}/{tid}/"
                    if page > 1:
                        url += f"page/{page}/"
                resp = self.fetch(url, headers=self.headers)
                if not resp:
                    return self._empty_result(page)
                soup = BeautifulSoup(resp.text, 'html.parser')
                vlist = self._parse_video_list(resp)
                pc = self._get_pagecount(soup, page)
                return self._result_with_page(vlist, page, pc)

            elif tid == "models" and (not extend or "id" not in extend):
                url = f"{self.site_url}/models/"
                resp = self.fetch(url, headers=self.headers)
                if not resp:
                    return self._empty_result(1)
                items = self._parse_actor_list(resp.text)
                return {
                    "list": items,
                    "page": 1, "pagecount": 1,
                    "limit": len(items), "total": len(items)
                }

            elif tid == "models" and extend and "id" in extend:
                slug = extend["id"]
                base = f"{self.site_url}/models/{slug}/"
                url = base + (f"page/{page}/" if page > 1 else "")
                resp = self.fetch(url, headers=self.headers)
                if not resp:
                    return self._empty_result(page)
                soup = BeautifulSoup(resp.text, 'html.parser')
                vlist = self._parse_video_list(resp)
                pc = self._get_pagecount(soup, page)
                return self._result_with_page(vlist, page, pc)

            elif tid == "categories" and (not extend or "id" not in extend):
                url = f"{self.site_url}/categories/"
                resp = self.fetch(url, headers=self.headers)
                if not resp:
                    return self._empty_result(1)
                items = self._parse_category_list(resp.text)
                return {
                    "list": items,
                    "page": 1, "pagecount": 1,
                    "limit": len(items), "total": len(items)
                }

            elif tid == "categories" and extend and "id" in extend:
                slug = extend["id"]
                base = f"{self.site_url}/categories/{slug}/"
                url = base + (f"page/{page}/" if page > 1 else "")
                resp = self.fetch(url, headers=self.headers)
                if not resp:
                    return self._empty_result(page)
                soup = BeautifulSoup(resp.text, 'html.parser')
                vlist = self._parse_video_list(resp)
                pc = self._get_pagecount(soup, page)
                return self._result_with_page(vlist, page, pc)

            else:
                url = f"{self.site_url}/{tid}/"
                if page > 1:
                    url += f"page/{page}/"
                resp = self.fetch(url, headers=self.headers)
                if not resp:
                    return self._empty_result(page)
                soup = BeautifulSoup(resp.text, 'html.parser')
                vlist = self._parse_video_list(resp)
                pc = self._get_pagecount(soup, page)
                return self._result_with_page(vlist, page, pc)

        except Exception:
            return self._empty_result(page)

    # ═══ 详情页 ═══════════════════════════════
    def detailContent(self, ids):
        if not ids:
            return {"list": []}
        vod_id = ids[0]
        try:
            if vod_id.startswith("model_"):
                slug = vod_id.replace("model_", "", 1)
                return self._actor_detail(slug)
            elif vod_id.startswith("category_"):
                slug = vod_id.replace("category_", "", 1)
                return self._category_detail(slug)
            else:
                return self._video_detail(vod_id)
        except Exception:
            return {"list": [self._empty_video(vod_id)]}

    # ═══ 搜索 ══════════════════════════════════
    def searchContent(self, key, quick, pg="1"):
        page = int(pg) if pg else 1
        try:
            key_enc = urllib.parse.quote(key)
            url = f"{self.site_url}/search/?keyword={key_enc}"
            if page > 1:
                url += f"&page={page}"
            resp = self.fetch(url, headers=self.headers)
            if not resp:
                return {"list": [], "page": page, "pagecount": 1}
            vlist = self._parse_video_list(resp)
            return {"list": vlist, "page": page, "pagecount": 1, "limit": 24, "total": len(vlist)}
        except Exception:
            return {"list": [], "page": page, "pagecount": 1}

    # ═══ 播放器 ════════════════════════════════
    def playerContent(self, flag, id, vipFlags):
        try:
            if id.startswith('http'):
                if '.m3u8' in id:
                    return {"parse": 0, "url": id, "header": self.headers, "proxy": self.proxies}
                else:
                    return {"parse": 1, "url": id, "header": self.headers, "proxy": self.proxies}
            video_url = f"{self.site_url}/videos/{id}/"
            resp = self.fetch(video_url, headers=self.headers)
            if resp:
                soup = BeautifulSoup(resp.text, 'html.parser')
                m3u8 = self._extract_m3u8(resp.text, soup)
                if m3u8:
                    return {"parse": 0, "url": m3u8, "header": self.headers, "proxy": self.proxies}
                else:
                    return {"parse": 1, "url": video_url, "header": self.headers, "proxy": self.proxies}
            else:
                return {"parse": 1, "url": video_url, "header": self.headers, "proxy": self.proxies}
        except Exception:
            return {"parse": 1, "url": "", "header": self.headers, "proxy": self.proxies}

    # ═══════════════════════════════════════════
    # 内部工具方法
    # ═══════════════════════════════════════════

    def _fix_pic_url(self, pic):
        """补全图片为绝对路径"""
        if not pic:
            return pic
        if pic.startswith('//'):
            return 'https:' + pic
        elif pic.startswith('/'):
            return self.site_url.rstrip('/') + pic
        elif not pic.startswith('http'):
            pic = self.site_url.rstrip('/') + '/' + pic.lstrip('/')
        return pic

    def _parse_video_list(self, resp=None, soup=None):
        """
        解析视频卡片列表（能抓出所有视频，且标题正确）
        图片提取已增强：支持 data-src / noscript / background-image / 路径补全
        """
        if soup is None and resp is not None:
            soup = BeautifulSoup(resp.text, 'html.parser')
        if soup is None:
            return []
        vlist = []
        seen_ids = set()
        
        for a in soup.select('a[href*="/videos/"]'):
            try:
                href = a.get('href', '')
                m = re.search(r'/videos/([^/]+)', href)
                if not m:
                    continue
                vid = m.group(1)
                if vid in seen_ids:
                    continue
                seen_ids.add(vid)
                
                # 向上查找卡片容器（最多上溯5层，直到找到一个包含标题的 div）
                card = a
                for _ in range(5):
                    if card is None:
                        break
                    if card.name in ('div', 'article', 'li'):
                        if card.select_one('h6.title') or card.select_one('.detail'):
                            break
                    card = card.parent if card and card.parent else None
                if card is None or card.name not in ('div', 'article', 'li'):
                    card = a.parent if a and a.parent else None
                
                # --- 标题提取（不变）---
                title = '未知'
                if card:
                    h6 = (card.select_one('h6.title')
                          or card.select_one('h6')
                          or card.select_one('.detail h6'))
                    if h6:
                        title = h6.get_text(strip=True)
                if title == '未知':
                    txt_parts = []
                    for child in a.children:
                        if hasattr(child, 'get') and child.get('class') and 'duration' in child.get('class'):
                            continue
                        if hasattr(child, 'get_text'):
                            txt_parts.append(child.get_text(strip=True))
                        elif isinstance(child, str):
                            txt_parts.append(child.strip())
                    title = ' '.join(txt_parts).strip()
                if not title or title == '未知':
                    title = vid
                
                # ---------- 图片增强提取 ----------
                pic = ''
                img = None
                # 1. 从 a 或 card 中找 img 标签
                img = a.select_one('img')
                if not img and card:
                    img = card.select_one('img')

                if img:
                    pic = (img.get('data-src') or
                           img.get('data-original') or
                           img.get('data-lazy-src') or
                           img.get('src') or '')

                # 2. 如果为空，尝试从 noscript 中获取
                if not pic and card:
                    noscript_img = card.select_one('noscript img')
                    if noscript_img:
                        pic = noscript_img.get('src') or ''

                # 3. 如果还是空，检查 background-image 样式
                if not pic and card:
                    style = card.get('style') or ''
                    bg_match = re.search(r'url\(["\']?([^"\')]+)', style)
                    if bg_match:
                        pic = bg_match.group(1)

                # 4. 统一补全为绝对地址
                pic = self._fix_pic_url(pic)
                # ---------------------------------

                # --- 时长备注 ---
                remarks = ''
                duration_el = card.select_one('.duration') if card else None
                if duration_el:
                    remarks = duration_el.get_text(strip=True)
                
                vlist.append({
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": remarks
                })
            except Exception:
                continue
        return vlist if vlist else []

    def _parse_actor_list(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        items = []
        seen = set()
        for a in soup.select('a[href*="/models/"]'):
            try:
                href = a.get('href', '')
                if '/page/' in href or '#' in href or not href:
                    continue
                m = re.search(r'/models/([^/]+)/?$', href)
                if not m:
                    continue
                slug = m.group(1)
                if slug in seen:
                    continue
                seen.add(slug)
                name = ''
                img = a.select_one('img')
                if img and img.get('alt', '').strip():
                    name = img['alt'].strip()
                if not name:
                    name = a.get_text(strip=True)
                if not name or len(name) > 50:
                    name = slug.replace('-', ' ').title()
                pic = ''
                if img:
                    pic = (img.get('data-src')
                           or img.get('data-original')
                           or img.get('data-lazy-src')
                           or img.get('src')
                           or '')
                if not pic:
                    inner = a.select_one('[style*="background"]')
                    if inner:
                        style_val = inner.get('style', '')
                        bg = re.search(r'url\(["\']?([^"\')]+)', style_val)
                        if bg:
                            pic = bg.group(1)
                if not pic:
                    style_val = a.get('style', '')
                    bg = re.search(r'url\(["\']?([^"\')]+)', style_val)
                    if bg:
                        pic = bg.group(1)
                # 补全路径
                pic = self._fix_pic_url(pic)
                items.append({
                    "vod_id": f"model_{slug}",
                    "vod_name": name,
                    "vod_pic": pic,
                    "vod_remarks": ""
                })
            except Exception:
                continue
        return items

    def _parse_category_list(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        items = []
        seen = set()
        for a in soup.select('a[href*="/categories/"]'):
            try:
                href = a.get('href', '')
                if '/page/' in href or '#' in href:
                    continue
                m = re.search(r'/categories/([^/]+)', href)
                if not m:
                    continue
                slug = m.group(1)
                if slug in seen:
                    continue
                seen.add(slug)
                name = a.get_text(strip=True)
                if len(name) > 50:
                    inner = a.select_one('h3,h4,.name')
                    if inner:
                        name = inner.get_text(strip=True)
                if not name:
                    name = slug.replace('-', ' ').title()
                img = a.select_one('img')
                pic = ''
                if img:
                    pic = img.get('data-src') or img.get('src') or ''
                # 补全路径
                pic = self._fix_pic_url(pic)
                items.append({
                    "vod_id": f"category_{slug}",
                    "vod_name": name,
                    "vod_pic": pic,
                    "vod_remarks": ""
                })
            except Exception:
                continue
        return items

    def _actor_detail(self, slug):
        try:
            url = f"{self.site_url}/models/{slug}/"
            resp = self.fetch(url, headers=self.headers)
            if not resp:
                return {"list": [self._empty_video(f"model_{slug}", slug)]}
            soup = BeautifulSoup(resp.text, 'html.parser')
            name_el = (soup.select_one('.title-box h2')
                       or soup.select_one('h1')
                       or soup.select_one('h2')
                       or soup.select_one('h3'))
            name = name_el.get_text(strip=True) if name_el else slug.replace('-', ' ').title()
            avatar = (soup.select_one('img.avatar')
                      or soup.select_one('img.model-avatar')
                      or soup.select_one('img'))
            pic = ''
            if avatar:
                pic = (avatar.get('data-src')
                       or avatar.get('data-original')
                       or avatar.get('data-lazy-src')
                       or avatar.get('src')
                       or '')
            pic = self._fix_pic_url(pic)
            desc_el = soup.select_one('.description')
            content = desc_el.get_text(strip=True) if desc_el else ''
            all_videos = []
            for p in range(1, 3):
                if p == 1:
                    page_soup = soup
                else:
                    page_url = f"{url}page/{p}/"
                    r = self.fetch(page_url, headers=self.headers)
                    if not r:
                        break
                    page_soup = BeautifulSoup(r.text, 'html.parser')
                vlist = self._parse_video_list(soup=page_soup)
                all_videos.extend(vlist)
                if len(all_videos) >= 30:
                    break
            seen_ids = set()
            unique = []
            for v in all_videos:
                if v["vod_id"] not in seen_ids and len(unique) < 30:
                    seen_ids.add(v["vod_id"])
                    unique.append(v)
            play_from = [v.get("vod_name", "") for v in unique]
            play_url = [v.get("vod_id", "") for v in unique]
            return {"list": [{
                "vod_id": f"model_{slug}",
                "vod_name": name,
                "vod_pic": pic,
                "vod_content": content,
                "vod_actor": name,
                "vod_director": "",
                "vod_play_from": "$$$".join(play_from) if play_from else "无作品",
                "vod_play_url": "$$$".join(play_url) if play_url else ""
            }]}
        except Exception:
            return {"list": [self._empty_video(f"model_{slug}", slug)]}

    def _category_detail(self, slug):
        try:
            url = f"{self.site_url}/categories/{slug}/"
            resp = self.fetch(url, headers=self.headers)
            if not resp:
                return {"list": [self._empty_video(f"category_{slug}", slug)]}
            soup = BeautifulSoup(resp.text, 'html.parser')
            name_el = soup.select_one('h1') or soup.select_one('h2')
            name = name_el.get_text(strip=True) if name_el else slug.replace('-', ' ').title()
            desc_el = soup.select_one('.description')
            content = desc_el.get_text(strip=True) if desc_el else ''
            all_videos = []
            for p in range(1, 3):
                if p == 1:
                    page_soup = soup
                else:
                    page_url = f"{url}page/{p}/"
                    r = self.fetch(page_url, headers=self.headers)
                    if not r:
                        break
                    page_soup = BeautifulSoup(r.text, 'html.parser')
                vlist = self._parse_video_list(soup=page_soup)
                all_videos.extend(vlist)
                if len(all_videos) >= 30:
                    break
            seen_ids = set()
            unique = []
            for v in all_videos:
                if v["vod_id"] not in seen_ids and len(unique) < 30:
                    seen_ids.add(v["vod_id"])
                    unique.append(v)
            play_from = [v.get("vod_name", "") for v in unique]
            play_url = [v.get("vod_id", "") for v in unique]
            return {"list": [{
                "vod_id": f"category_{slug}",
                "vod_name": name,
                "vod_pic": "",
                "vod_content": content,
                "vod_actor": "",
                "vod_director": "",
                "vod_play_from": "$$$".join(play_from) if play_from else "无作品",
                "vod_play_url": "$$$".join(play_url) if play_url else ""
            }]}
        except Exception:
            return {"list": [self._empty_video(f"category_{slug}", slug)]}

    def _video_detail(self, vod_id):
        try:
            url = f"{self.site_url}/videos/{vod_id}/"
            resp = self.fetch(url, headers=self.headers)
            if not resp:
                return {"list": [self._empty_video(vod_id)]}
            soup = BeautifulSoup(resp.text, 'html.parser')
            name_el = soup.select_one('h1.title') or soup.select_one('h4') or soup.select_one('.video-title')
            name = name_el.get_text(strip=True) if name_el else vod_id

            # ---------- 详情页海报增强提取 ----------
            img = (soup.select_one('div.video-thumbnail img') or
                   soup.select_one('img.lazyload') or
                   soup.select_one('video[poster]'))
            pic = ''
            if img:
                if img.name == 'video':
                    pic = img.get('poster') or ''
                else:
                    pic = (img.get('data-src') or
                           img.get('data-original') or
                           img.get('data-lazy-src') or
                           img.get('src') or '')

            # 补充 noscript
            if not pic:
                noscript_img = soup.select_one('noscript img')
                if noscript_img:
                    pic = noscript_img.get('src') or ''

            pic = self._fix_pic_url(pic)
            # ------------------------------------

            desc = soup.select_one('.description') or soup.select_one('meta[name="description"]')
            content = ''
            if desc:
                if desc.name == 'meta':
                    content = desc.get('content', '')
                else:
                    content = desc.get_text(strip=True)
            actors = []
            for a in soup.select('a[href*="/models/"]'):
                act = a.get_text(strip=True)
                if act:
                    actors.append(act)
            vod_actor = ', '.join(actors) if actors else ''
            director_el = soup.select_one('a[href*="/director/"]')
            vod_director = director_el.get_text(strip=True) if director_el else ''
            m3u8 = self._extract_m3u8(resp.text, soup)
            play_from = "Jable"
            play_url = ""
            if m3u8:
                play_url = f"高清${m3u8}"
            else:
                play_url = f"解析${url}"
            return {"list": [{
                "vod_id": vod_id,
                "vod_name": name,
                "vod_pic": pic,
                "vod_content": content,
                "vod_actor": vod_actor,
                "vod_director": vod_director,
                "vod_play_from": play_from,
                "vod_play_url": play_url
            }]}
        except Exception:
            return {"list": [self._empty_video(vod_id)]}

    def _empty_video(self, vid, name=""):
        return {
            "vod_id": vid,
            "vod_name": name or vid,
            "vod_pic": "",
            "vod_content": "",
            "vod_actor": "",
            "vod_director": "",
            "vod_play_from": "无数据",
            "vod_play_url": ""
        }

    def _get_pagecount(self, soup, current_page):
        max_page = 1
        try:
            pager = soup.select('.pagination a')
            if pager:
                nums = []
                for a in pager:
                    t = a.get_text(strip=True)
                    if t.isdigit():
                        nums.append(int(t))
                if nums:
                    max_page = max(nums)
                elif any('下一頁' in a.get_text() for a in pager):
                    max_page = current_page + 1
        except Exception:
            pass
        return max_page

    def _extract_m3u8(self, html_text, soup):
        try:
            candidates = set()
            scripts = []
            for s in soup.select('script'):
                if s.string:
                    scripts.append(s.string)
            full_js = '\n'.join(scripts)
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
        except Exception:
            return None

    def _empty_result(self, page):
        return {"list": [], "page": page, "pagecount": 1, "limit": 24, "total": 0}

    def _result_with_page(self, vlist, page, pagecount):
        return {
            "list": vlist,
            "page": page,
            "pagecount": pagecount,
            "limit": 24,
            "total": len(vlist) * pagecount
        }