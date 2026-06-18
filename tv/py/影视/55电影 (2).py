# coding=utf-8
"""
目标站: 555电影 首页: https://www.55dy9.com
修复Netflix与福利分类无数据问题
"""
import re
import sys
import urllib.parse
from bs4 import BeautifulSoup

sys.path.append('..')
from base.spider import Spider

class Spider(Spider):

    def init(self, extend=""):
        self.site_url = "https://www.55dy9.com"
        self.limit = 24
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': self.site_url,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
        }
        self.categories = [
            {"type_id": "1", "type_name": "电影"},
            {"type_id": "2", "type_name": "连续剧"},
            {"type_id": "4", "type_name": "动漫"},
            {"type_id": "3", "type_name": "综艺纪录"},
            {"type_id": "126", "type_name": "擦边短剧"},
            {"type_id": "label/netflix", "type_name": "Netflix"},
            {"type_id": "124", "type_name": "福利"}   # 修改为本站内部数字ID，对应 /vodshow/124-----------.html
        ]
        self.filters = {
            "1": [
                {"key": "剧情", "name": "剧情", "value": [  
                    {"n": "全部", "v": "/vodshow/1-----------.html"},
                    {"n": "Netflix", "v": "/vodshow/1---Netflix--------.html"},
                    {"n": "动作", "v": "/vodshow/1---动作--------.html"},
                    {"n": "喜剧", "v": "/vodshow/1---喜剧--------.html"},
                    {"n": "爱情", "v": "/vodshow/1---爱情--------.html"},
                    {"n": "科幻", "v": "/vodshow/1---科幻--------.html"},
                    {"n": "恐怖", "v": "/vodshow/1---恐怖--------.html"},
                    {"n": "剧情", "v": "/vodshow/1---剧情--------.html"},
                    {"n": "战争", "v": "/vodshow/1---战争--------.html"}
                ]},
                {"key": "地区", "name": "地区", "value": [
                    {"n": "全部", "v": "/vodshow/1-----------.html"},
                    {"n": "大陆", "v": "/vodshow/1-大陆----------.html"},
                    {"n": "香港", "v": "/vodshow/1-香港----------.html"},
                    {"n": "台湾", "v": "/vodshow/1-台湾----------.html"},
                    {"n": "美国", "v": "/vodshow/1-美国----------.html"},
                    {"n": "日本", "v": "/vodshow/1-日本----------.html"},
                    {"n": "韩国", "v": "/vodshow/1-韩国----------.html"}
                ]},
                {"key": "年份", "name": "年份", "value": [
                    {"n": "全部", "v": "/vodshow/1-----------.html"},
                    {"n": "2026", "v": "/vodshow/1-----------2026.html"},
                    {"n": "2025", "v": "/vodshow/1-----------2025.html"},
                    {"n": "2024", "v": "/vodshow/1-----------2024.html"},
                    {"n": "2023", "v": "/vodshow/1-----------2023.html"}
                ]},
                {"key": "排序", "name": "排序", "value": [
                    {"n": "时间排序", "v": "/vodshow/1--time---------.html"},
                    {"n": "人气排序", "v": "/vodshow/1--hits---------.html"},
                    {"n": "评分排序", "v": "/vodshow/1--score---------.html"}
                ]}
            ],
            "2": [
                {"key": "类型", "name": "类型", "value": [
                    {"n": "全部", "v": "/vodshow/2-----------.html"},
                    {"n": "热门连续剧", "v": "/vodshow/13-----------.html"},
                    {"n": "港台剧", "v": "/vodshow/15-----------.html"},
                    {"n": "日韩剧", "v": "/vodshow/44-----------.html"},
                    {"n": "欧美剧", "v": "/vodshow/45-----------.html"},
                    {"n": "短剧", "v": "/vodshow/125-----------.html"}
                ]},
                {"key": "剧情", "name": "剧情", "value": [
                    {"n": "全部", "v": "/vodshow/2-----------.html"},
                    {"n": "Netflix", "v": "/vodshow/2---Netflix--------.html"},
                    {"n": "短剧", "v": "/vodshow/2---短剧--------.html"},
                    {"n": "仙侠", "v": "/vodshow/2---仙侠--------.html"},
                    {"n": "科幻", "v": "/vodshow/2---科幻--------.html"},
                    {"n": "动作", "v": "/vodshow/2---动作--------.html"},
                    {"n": "喜剧", "v": "/vodshow/2---喜剧--------.html"},
                    {"n": "爱情", "v": "/vodshow/2---爱情--------.html"}
                ]},
                {"key": "地区", "name": "地区", "value": [
                    {"n": "全部", "v": "/vodshow/2-----------.html"},
                    {"n": "大陆", "v": "/vodshow/2-大陆----------.html"},
                    {"n": "香港", "v": "/vodshow/2-香港----------.html"},
                    {"n": "韩国", "v": "/vodshow/2-韩国----------.html"},
                    {"n": "美国", "v": "/vodshow/2-美国----------.html"},
                    {"n": "日本", "v": "/vodshow/2-日本----------.html"}
                ]},
                {"key": "年份", "name": "年份", "value": [
                    {"n": "全部", "v": "/vodshow/2-----------.html"},
                    {"n": "2026", "v": "/vodshow/2-----------2026.html"},
                    {"n": "2025", "v": "/vodshow/2-----------2025.html"},
                    {"n": "2024", "v": "/vodshow/2-----------2024.html"},
                    {"n": "2023", "v": "/vodshow/2-----------2023.html"}
                ]},
                {"key": "排序", "name": "排序", "value": [
                    {"n": "时间排序", "v": "/vodshow/2--time---------.html"},
                    {"n": "人气排序", "v": "/vodshow/2--hits---------.html"},
                    {"n": "评分排序", "v": "/vodshow/2--score---------.html"}
                ]}
            ]
        }

    def _parse_video_card(self, card):
        link_elem = card.select_one('a')
        if not link_elem:
            link_elem = card
        href = link_elem.get('href', '')
        match = re.search(r'/voddetail/(\d+)\.html', href)
        if not match:
            return None
        vod_id = match.group(1)
        title_elem = card.select_one('.module-item-title') or card.select_one('.module-poster-item-title')
        vod_name = title_elem.get_text(strip=True) if title_elem else ''
        img_elem = card.select_one('img')
        vod_pic = ''
        if img_elem:
            vod_pic = img_elem.get('data-original', '') or img_elem.get('data-src', '') or img_elem.get('src', '')
        tag_elem = card.select_one('.module-item-note') or card.select_one('.module-item-text')
        vod_remarks = tag_elem.get_text(strip=True) if tag_elem else ''
        return {"vod_id": vod_id, "vod_name": vod_name, "vod_pic": vod_pic, "vod_remarks": vod_remarks}

    def homeContent(self, filter):
        url = f"{self.site_url}/index/home.html"
        resp = self.fetch(url, headers=self.headers)
        video_list = []
        if resp:
            soup = BeautifulSoup(resp.text, 'html.parser')
            cards = soup.select('.module-items .module-item')
            if not cards:
                cards = soup.select('.module-items a.module-poster-item')
            for card in cards[:24]:
                item = self._parse_video_card(card)
                if item:
                    video_list.append(item)
        return {"class": self.categories, "list": video_list, "filters": self.filters}

    def homeVideoContent(self):
        return self.homeContent(False)

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg else 1

        # ----- 修复：统一生成相对路径base_url，方便拼接 -----
        if tid.startswith('http'):
            base_url = tid  # 保留绝对URL作后备
        elif tid.startswith('label/'):
            base_url = f"/{tid}.html"   # 例如 /label/netflix.html
        elif extend:
            base_url = None
            for key, val in extend.items():
                if val:
                    base_url = val
                    break
            if not base_url:
                base_url = f"/vodshow/{tid}-----------.html"
        else:
            base_url = f"/vodshow/{tid}-----------.html"

        # ----- 修复：分页URL构造，区分绝对路径与相对路径 -----
        def make_page_url(base, pg_num):
            # 如果已是绝对URL（http开头），直接在其基础上修改
            if base.startswith('http'):
                if pg_num == 1:
                    return base
                # 尝试替换 .html 为 -页码.html （常见格式）
                return base.replace('.html', f'-{pg_num}.html')
            # 相对路径，补全域名
            if pg_num == 1:
                return self.site_url + base
            # 处理 /vodshow/xxx-----------.html 这种默认全部链接
            if re.match(r'/vodshow/\d+-----------\.html$', base):
                tid_match = re.search(r'/vodshow/(\d+)', base)
                if tid_match:
                    return f"{self.site_url}/vodshow/{tid_match.group(1)}--------{pg_num}---.html"
                else:
                    return self.site_url + base.replace('.html', f'{pg_num}---.html')
            else:
                # 其他格式（如 label/netflix.html），简单的页码替换
                return self.site_url + base.replace('.html', f'-{pg_num}.html')

        url = make_page_url(base_url, page)

        resp = self.fetch(url, headers=self.headers)
        if not resp:
            return {"list": [], "page": page, "pagecount": 1, "limit": self.limit, "total": 0}

        soup = BeautifulSoup(resp.text, 'html.parser')
        video_list = []
        cards = soup.select('.module-items .module-item') or soup.select('.module-items a.module-poster-item')
        if not cards:
            cards = soup.select('.module-page .module-item')
        for card in cards:
            item = self._parse_video_card(card)
            if item:
                video_list.append(item)

        # 分页总数
        pagecount = 1
        pagination = soup.select('.page-link') or soup.select('.pagination a')
        for a in pagination:
            text = a.get_text(strip=True)
            if text.isdigit():
                pagecount = max(pagecount, int(text))
        if pagecount == 1 and len(video_list) >= self.limit:
            pagecount = 999

        return {
            "list": video_list,
            "page": page,
            "pagecount": pagecount,
            "limit": self.limit,
            "total": 0
        }

    def detailContent(self, ids):
        if not ids:
            return {"list": []}
        vod_id = ids[0]
        url = f"{self.site_url}/voddetail/{vod_id}.html"
        resp = self.fetch(url, headers=self.headers)
        if not resp or resp.status_code != 200:
            return {"list": []}

        soup = BeautifulSoup(resp.text, 'html.parser')
        vod_name = ''
        title_tag = soup.select_one('.module-info-heading h1')
        if title_tag:
            vod_name = title_tag.get_text(strip=True)

        vod_pic = ''
        img_elem = soup.select_one('.module-info-poster img')
        if img_elem:
            vod_pic = img_elem.get('data-original', '') or img_elem.get('src', '')

        vod_content = ''
        desc_elem = soup.select_one('.module-info-introduction-content p') or soup.select_one('.show-desc p')
        if desc_elem:
            vod_content = desc_elem.get_text(strip=True)

        vod_director = ''
        vod_actor = ''
        for item in soup.select('.module-info-item'):
            title_span = item.select_one('.module-info-item-title')
            if not title_span:
                continue
            label = title_span.get_text(strip=True)
            content_div = item.select_one('.module-info-item-content')
            if not content_div:
                continue
            if '导演' in label:
                vod_director = content_div.get_text(strip=True)
            if '主演' in label:
                vod_actor = content_div.get_text(strip=True)

        tab_items = soup.select('.module-tab-item')
        play_containers = soup.select('.module-list.sort-list.tab-list')
        play_from_list = []
        play_url_list = []

        if tab_items and play_containers and len(tab_items) == len(play_containers):
            for idx, tab in enumerate(tab_items):
                source_name = tab.get('data-dropdown-value', '') or tab.get_text(strip=True)
                container = play_containers[idx]
                episodes = []
                for a in container.select('a.module-play-list-link'):
                    ep_name = a.get_text(strip=True)
                    ep_link = a.get('href', '')
                    if ep_link:
                        episodes.append(f"{ep_name}${ep_link}")
                if episodes:
                    play_from_list.append(source_name)
                    play_url_list.append('#'.join(episodes))
        else:
            all_items = soup.select('.module-play-list-content a.module-play-list-link')
            if all_items:
                episodes = []
                for a in all_items:
                    ep_name = a.get_text(strip=True)
                    ep_link = a.get('href', '')
                    if ep_link:
                        episodes.append(f"{ep_name}${ep_link}")
                if episodes:
                    play_from_list.append('默认线路')
                    play_url_list.append('#'.join(episodes))

        vod_play_from = '$$$'.join(play_from_list) if play_from_list else ''
        vod_play_url = '$$$'.join(play_url_list) if play_url_list else ''

        return {"list": [{
            "vod_id": vod_id,
            "vod_name": vod_name,
            "vod_pic": vod_pic,
            "vod_content": vod_content,
            "vod_director": vod_director,
            "vod_actor": vod_actor,
            "vod_play_from": vod_play_from,
            "vod_play_url": vod_play_url
        }]}

    def searchContent(self, key, quick, pg="1"):
        page = int(pg) if pg else 1
        if page > 1:
            url = f"{self.site_url}/vodsearch/{urllib.parse.quote(key)}----------{page}---.html"
        else:
            url = f"{self.site_url}/vodsearch/{urllib.parse.quote(key)}-------------.html"
        resp = self.fetch(url, headers=self.headers)
        if not resp:
            return {"list": [], "page": page, "pagecount": 1}
        soup = BeautifulSoup(resp.text, 'html.parser')
        video_list = []
        cards = soup.select('.module-items .module-item') or soup.select('.module-items a.module-poster-item')
        for card in cards:
            item = self._parse_video_card(card)
            if item:
                video_list.append(item)
        return {"list": video_list, "page": page, "pagecount": 1}

    def playerContent(self, flag, id, vipFlags):
        if not id.startswith('http'):
            url = self.site_url + id
        else:
            url = id
        return {"parse": 1, "url": url, "header": self.headers}