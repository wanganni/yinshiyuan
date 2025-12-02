import re
import sys
import urllib.parse
import requests
import json
from pyquery import PyQuery as pq
import time
import random

sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def __init__(self):
        self.name = '91pron[密]'
        self.host = 'https://0601.9p47p.com'
        self.candidate_hosts = ['https://0601.9p47p.com']
        self.ev_hosts = ['https://91.9p9.xyz', 'https://0601.9p47p.com']
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://duckduckgo.com/'
        }
        self.cookies = {'language': 'cn_CN', 'over18': '1'}
        self.class_map = {
            '91原创': 'ori', '当前最热': 'hot', '本月最热': 'top',
            '非付费': 'nonpaid', '10分钟以上': 'long', '20分钟以上': 'longer',
            '本月收藏': 'tf', '最近加精': 'rf', '高清': 'hd',
            '本月讨论': 'md', '收藏最多': 'mf'
        }

    def getName(self):
        return self.name

    def init(self, extend=""):
        self.host = self._pick_working_host()
        self.headers['Referer'] = self.host

    def isVideoFormat(self, url):
        return any(ext in (url or '') for ext in ['.m3u8', '.mp4', '.ts'])

    def manualVideoCheck(self):
        return False

    def _pick_working_host(self):
        for h in self.candidate_hosts:
            try:
                r = requests.get(f"{h}/v.php?category=ori&viewtype=basic&page=1", 
                                 headers=self.headers, cookies=self.cookies, timeout=6)
                if r.status_code == 200 and 'page=' in r.text:
                    return h
            except:
                pass
        return self.candidate_hosts[0]

    def _abs_href(self, href):
        if not href:
            return ''
        if href.startswith('http'):
            return re.sub(r'^https?://[^/]+', self.host, href)
        return f"{self.host.rstrip('/')}/{href.lstrip('/')}"

    def _parse_video_items(self, data):
        vlist = []
        for item in data('.col-xs-12').items():
            try:
                title = item('.video-title').text().strip()
                if not title:
                    continue
                pic = item('.img-responsive').attr('src') or ''
                pic = f"{self.host.rstrip('/')}/{pic.lstrip('/')}" if pic and not pic.startswith('http') else pic
                href = self._abs_href(item('a').attr('href'))
                if href:
                    vlist.append({
                        'vod_id': href,
                        'vod_name': title,
                        'vod_pic': pic,
                        'vod_remarks': item('.duration').text().strip() or '未知'
                    })
            except:
                continue
        return vlist

    def _parse_pagecount(self, data):
        try:
            nums = [int(m.group(1)) for a in data('a').items() 
                    if (m := re.search(r'[?&]page=(\d+)', a.attr('href') or ''))]
            if nums:
                return max(nums)
            page_nums = [int(a.text().strip()) 
                         for a in data('.pagination li a').items() 
                         if a.text().strip().isdigit()]
            return max(page_nums) if page_nums else 1
        except:
            return 1

    def _extract_tags(self, html):
        tags, data = [], pq(html)
        keywords = data('meta[name="keywords"]').attr('content') or ''
        if keywords:
            tags.extend(t.strip() for t in keywords.split(',') if t.strip())
        for link in data('a').items():
            href, text = link.attr('href') or '', link.text().strip()
            if any(p in href for p in ['category=', 'tag=', 'keyword=', '/tags/', '/category/']) and text and len(text) < 50:
                tags.append(text)
        for container in data('[class*="tag"], [class*="label"], [class*="category"]').items():
            text = container.text().strip()
            if text and len(text) < 50:
                tags.append(text)
        return list(dict.fromkeys(tags))

    def homeContent(self, filter):
        result = {'class': [{'type_name': k, 'type_id': v} for k, v in self.class_map.items()]}
        try:
            html = self._fetch(f"{self.host}/v.php?category=ori&viewtype=basic&page=1&cn_CN=cn_CN").text
            result['list'] = self._parse_video_items(pq(html))
        except:
            result['list'] = []
        return result

    def homeVideoContent(self):
        return []

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        try:
            if tid.startswith('author:'):
                uid = tid.split(':', 1)[1].strip()
                if not uid:
                    raise ValueError("无效作者UID")
                html = self._fetch(f"{self.host}/uvideos.php", params={'UID': uid, 'type': 'public', 'page': pg}).text
            else:
                html = self._fetch(f"{self.host}/v.php?category={tid}&viewtype=basic&page={pg}&cn_CN=cn_CN").text
            data = pq(html)
            return {
                'list': self._parse_video_items(data),
                'page': pg,
                'pagecount': self._parse_pagecount(data),
                'limit': 6,
                'total': 999999
            }
        except:
            return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 0, 'total': 0}

    def _extract_vid(self, text):
        patterns = [
            r'viewkey=([a-zA-Z0-9]+)',
            r'/viewvideo\.php\?.*viewkey=([a-zA-Z0-9]+)',
            r'VID["\']?\s*[:=]\s*["\']?([a-zA-Z0-9]+)',
            r'/ev\.php\?VID=([a-zA-Z0-9]+)'
        ]
        for pattern in patterns:
            if m := re.search(pattern, text):
                return m.group(1)
        return None

    def _get_ev_url(self, html, detail_url):
        if m := re.search(r'<textarea[^>]*>\s*(https?://[^<]+/ev\.php\?VID=[^<\s]+)', html, re.I):
            return m.group(1).strip()
        if matches := re.findall(r'(https?://[^"\'\s<>]+/ev\.php\?VID=[a-zA-Z0-9]+)', html, re.I):
            return matches[0]
        if vid := self._extract_vid(html) or self._extract_vid(detail_url):
            return f"{self.ev_hosts[0]}/ev.php?VID={vid}"
        return None

    def _get_mp4_url(self, ev_url):
        try:
            resp = self._fetch(ev_url, headers={**self.headers, 'Referer': self.host}, timeout=10)
            if resp.status_code != 200:
                return None
            html = resp.text
            if m := re.search(r'<source\s+src="([^"]+)"\s+type="video/mp4"', html, re.I):
                return m.group(1).strip().replace('&amp;', '&')
            if matches := re.findall(r'https?://[^"\'\s<>]*cdn77[^"\'\s<>]*\.mp4\?secure=[^"\'\s<>&]+', html):
                return matches[0].replace('&amp;', '&')
            if all_mp4 := re.findall(r'https?://[^"\'\s<>]+\.mp4[^"\'\s<>]*', html):
                for url in sorted(all_mp4, key=len, reverse=True):
                    if 'cdn77' in url and 'secure=' in url and len(url) > 150:
                        return url.replace('&amp;', '&')
                for url in all_mp4:
                    if 'cdn77' in url and len(url) > 100:
                        return url.replace('&amp;', '&')
            return None
        except:
            return None

    def detailContent(self, ids):
        if not ids or not ids[0]:
            return {'list': []}
        vod_id = ids[0].strip()
        detail_url = vod_id if vod_id.startswith('http') else f"{self.host}/{vod_id.lstrip('/')}"
        try:
            html = self._fetch(detail_url).text
        except:
            return {'list': []}
        ev_url = self._get_ev_url(html, detail_url)
        mp4_url = self._get_mp4_url(ev_url) if ev_url else None
        video_url = mp4_url if (mp4_url and 'secure=' in mp4_url) else (ev_url or detail_url)
        data = pq(html)
        title = data('title').text().strip().split('Chinese homemade video')[0].strip() or '未知标题'
        pic = (data('meta[property="og:image"]').attr('content') or
               data('.video-pic img, img.img-responsive').attr('src') or '')
        pic = f"{self.host.rstrip('/')}/{pic.lstrip('/')}" if pic and not pic.startswith('http') else pic
        director = '未知'
        author_link = data('.title-yakov').find('a[href*="uprofile.php"]')
        if author_link:
            name = author_link.find('.title').text().strip() or author_link.text().strip()
            if m := re.search(r'UID=([^&\'"]+)', author_link.attr('href') or ''):
                director = f'[a=cr:{json.dumps({"id": f"author:{m.group(1)}", "name": name})}/]{name}[/a]'
        duration = views = '未知'
        for span in data('span.info').items():
            if '热度' in span.text() or '观看' in span.text():
                if m := re.search(r'[\d]+', span.parent().text().strip()):
                    views = m.group(0)
        if duration_elem := data('.duration'):
            if durations := re.findall(r'\d{2}:\d{2}:\d{2}|\d{2}:\d{2}', duration_elem.text()):
                duration = ' '.join(durations)
        remarks = f"{duration} | 观看:{views}" if views != '未知' else duration
        return {'list': [{
            'vod_id': vod_id,
            'vod_name': title,
            'vod_pic': pic,
            'vod_play_from': '默认线路',
            'vod_play_url': f'正片${video_url}',
            'vod_director': director,
            'vod_tag': '|'.join(self._extract_tags(html)),
            'vod_remarks': remarks
        }]}

    def _search_from_categories(self, keyword, page=1):
        try:
            keyword_lower = keyword.lower()
            categories = ['hot', 'ori', 'rf']
            all_results = []
            for cat in categories:
                html = self._fetch(f"{self.host}/v.php?category={cat}&viewtype=basic&page={page}&cn_CN=cn_CN").text
                videos = self._parse_video_items(pq(html))
                filtered = [v for v in videos if keyword_lower in v['vod_name'].lower()]
                all_results.extend(filtered)
                if len(all_results) >= 10:
                    break
            seen = set()
            unique = [v for v in all_results if v['vod_id'] not in seen and not seen.add(v['vod_id'])]
            return unique[:10]
        except:
            return []

    def _search_via_duckduckgo(self, keyword, page=1):
        try:
            query = f"site:0601.9p47p.com OR site:9p47p.com OR site:9p9.xyz {keyword}"
            url = f"https://duckduckgo.com/html/?q={urllib.parse.quote(query)}&s={(page-1)*30}"
            time.sleep(random.uniform(0.5, 1.5))
            resp = requests.get(url, headers=self.headers, timeout=10)
            if resp.status_code != 200:
                return []
            data = pq(resp.text)
            vlist = []
            for item in data('div.result, .result__body').items():
                link_elem = item('a.result__a, .result__title a')
                if not link_elem:
                    continue
                title = link_elem.text().strip()
                href = link_elem.attr('href')
                if not title or not href or 'viewkey=' not in href:
                    continue
                if href.startswith('//duckduckgo.com/l/'):
                    parsed = urllib.parse.urlparse('https:' + href if href.startswith('//') else href)
                    params = urllib.parse.parse_qs(parsed.query)
                    href = urllib.parse.unquote(params.get('uddg', [''])[0])
                href = self._abs_href(href)
                snippet = item('.result__snippet, a.result__snippet').text().strip() or ''
                vlist.append({
                    'vod_id': href,
                    'vod_name': title,
                    'vod_pic': '',
                    'vod_remarks': f'DuckDuckGo搜索 | {snippet[:50]}...' if snippet else 'DuckDuckGo搜索'
                })
                if len(vlist) >= 10:
                    break
            return vlist
        except:
            return []

    def searchContent(self, key, quick, pg=1):
        pg = int(pg or 1)
        if not key or not key.strip():
            return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 0, 'total': 0}
        try:
            vlist = self._search_from_categories(key.strip(), pg) or self._search_via_duckduckgo(key.strip(), pg)
            if not vlist:
                return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 0, 'total': 0}
            return {
                'list': vlist,
                'page': pg,
                'pagecount': 20,
                'limit': len(vlist),
                'total': len(vlist) * 20
            }
        except:
            return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 0, 'total': 0}

    def playerContent(self, flag, id, vipFlags):
        parsed = urllib.parse.urlparse(id if id.startswith('http') else self.host)
        headers = {
            **self.headers,
            'Origin': f"{parsed.scheme}://{parsed.netloc}",
            'Referer': self.host
        }
        return {
            'parse': 0 if self.isVideoFormat(id) else 1,
            'url': id,
            'header': headers
        }

    def localProxy(self, param):
        try:
            if param.get('type') == 'img':
                url = param.get('url', '')
                url = f"{self.host.rstrip('/')}/{url.lstrip('/')}" if url and not url.startswith(('http://', 'https://')) else url
                headers = {**self.headers, 'Accept': 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8'}
                res = self._fetch(url, headers=headers)
                return [200, res.headers.get('Content-Type', 'image/jpeg'), res.content]
            return [404, 'text/plain', '']
        except:
            return [500, 'text/plain', '']

    def _fetch(self, url, params=None, headers=None, timeout=8):
        for i in range(2):
            try:
                resp = requests.get(
                    url,
                    headers=headers or self.headers,
                    cookies=self.cookies,
                    timeout=timeout,
                    allow_redirects=True,
                    params=params or {}
                )
                if resp.status_code in (200, 301, 302):
                    resp.encoding = resp.apparent_encoding or 'utf-8'
                    return resp
            except:
                if i < 1:
                    time.sleep(0.5)
        return type('obj', (object,), {
            'text': '', 'status_code': 404, 'headers': {},
            'content': b'', 'url': url, 'json': lambda: {}
        })()