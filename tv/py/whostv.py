# coding=utf-8
"""
目标站: whos.tv 帧探索
首页: https://whos.tv/frames
"""
import re
import sys
from bs4 import BeautifulSoup

sys.path.append('..')
from base.spider import Spider

class Spider(Spider):

    def init(self, extend=""):
        self.site_url = "https://whos.tv"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': self.site_url,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
        }
        self.categories = []
        self.filters = {}

    def homeContent(self, filter):
        url = self.site_url + "/frames"
        resp = self.fetch(url, headers=self.headers)
        categories = []
        video_list = []
        if resp:
            soup = BeautifulSoup(resp.text, 'html.parser')
            # 提取主分类
            nav = soup.select_one('nav#frame-explore-categories')
            if nav:
                for a in nav.select('a'):
                    href = a.get('href', '')
                    name_span = a.select_one('span.flex-1')
                    name = name_span.get_text(strip=True) if name_span else a.get_text(strip=True)
                    if href and name:
                        parts = href.strip('/').split('/')
                        tid = parts[-1] if parts else name
                        categories.append({"type_id": tid, "type_name": name})
            # 首页列表
            video_list = self._parse_list(soup)
        return {"class": categories, "list": video_list, "filters": self.filters}

    def homeVideoContent(self):
        return self.homeContent(False)

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg else 1
        sub_tid = tid
        if extend and 'subtype' in extend and extend['subtype']:
            sub_tid = extend['subtype']
        url = f"{self.site_url}/frames/{sub_tid}"
        if page > 1:
            url = f"{self.site_url}/frames/page-{page}"
        resp = self.fetch(url, headers=self.headers)
        if not resp:
            return {"list": [], "page": page, "pagecount": 1, "limit": 24, "total": 0}
        soup = BeautifulSoup(resp.text, 'html.parser')
        video_list = self._parse_list(soup)
        # 分页
        pagecount = 1
        pagination = soup.select('a[href*="/page-"]')
        if pagination:
            nums = []
            for a in pagination:
                m = re.search(r'page-(\d+)', a.get('href', ''))
                if m:
                    nums.append(int(m.group(1)))
            if nums:
                pagecount = max(nums)
        total = len(video_list) * pagecount
        return {
            "list": video_list,
            "page": page,
            "pagecount": pagecount,
            "limit": 24,
            "total": total
        }

    def _parse_list(self, soup):
        """解析网格列表，提取帧ID和图片"""
        video_list = []
        if not soup:
            return video_list
        cards = soup.select('a.frame-card[href^="/frames/"]')
        if not cards:
            grid = soup.select_one('div.grid')
            if grid:
                cards = grid.select('a[href^="/frames/"]')
        for a in cards:
            href = a.get('href', '')
            m = re.search(r'/frames/(\d+)', href)
            if not m:
                continue
            vod_id = m.group(1)
            img = a.select_one('img.w-full')
            if not img:
                continue
            vod_pic = img.get('src') or img.get('data-src', '')
            if vod_pic.startswith('//'):
                vod_pic = 'https:' + vod_pic
            elif vod_pic.startswith('/'):
                vod_pic = self.site_url + vod_pic
            vod_remarks = img.get('alt', '') or ''
            video_list.append({
                "vod_id": vod_id,
                "vod_name": vod_id,
                "vod_pic": vod_pic,
                "vod_remarks": vod_remarks
            })
        return video_list

    def detailContent(self, ids):
        if not ids:
            return {"list": []}
        vod_id = ids[0]
        url = f"{self.site_url}/frames/{vod_id}"
        resp = self.fetch(url, headers=self.headers)
        if not resp or resp.status_code != 200:
            return {"list": []}
        soup = BeautifulSoup(resp.text, 'html.parser')

        # 标题：meta title 提取番号和时间
        title_tag = soup.select_one('title')
        vod_name = vod_id
        if title_tag:
            full_title = title_tag.get_text(strip=True)
            # 取 | 之前的部分作为名称
            vod_name = full_title.split('|')[0].strip()

        # 主图：优先大图
        main_img = soup.select_one('img.max-h-screen, img[src*="hisav.me"]')
        if not main_img:
            main_img = soup.select_one('main img')
        vod_pic = ''
        if main_img:
            vod_pic = main_img.get('src') or main_img.get('data-src', '')
            if vod_pic.startswith('//'):
                vod_pic = 'https:' + vod_pic
            elif vod_pic.startswith('/'):
                vod_pic = self.site_url + vod_pic

        # 描述
        vod_content = ''
        meta_desc = soup.select_one('meta[name="description"]')
        if meta_desc:
            vod_content = meta_desc.get('content', '')

        # 演员：从视频卡片提取
        vod_actor = ''
        actress_tag = soup.select_one('a[href*="/actresses/"]')
        if not actress_tag:
            # 备用：从文本中搜索“女优”
            text = soup.get_text()
            m = re.search(r'女优\[([^\]]+)\]', text)
            if m:
                vod_actor = m.group(1)
        else:
            vod_actor = actress_tag.get_text(strip=True)

        # 播放链接：提取“从此帧播放”或“播放影片”的链接
        vod_play_from = 'whos.tv'
        play_url = None
        play_link = soup.select_one('a[href^="/videos/"]')  # 第一个包含视频链接的a
        if play_link:
            play_url = self.site_url + play_link.get('href')
        if not play_url:
            # 回退，构造标准链接
            # 从标题提取番号
            m = re.search(r'([a-zA-Z]+-\d+)', vod_name)
            if m:
                play_url = self.site_url + '/videos/' + m.group(1)

        vod_play_url = ''
        if play_url:
            vod_play_url = f"播放${play_url}"

        result = [{
            "vod_id": vod_id,
            "vod_name": vod_name,
            "vod_pic": vod_pic,
            "vod_content": vod_content,
            "vod_actor": vod_actor,
            "vod_director": '',
            "vod_area": '',
            "vod_year": '',
            "vod_play_from": vod_play_from,
            "vod_play_url": vod_play_url
        }]
        return {"list": result}

    def searchContent(self, key, quick, pg="1"):
        # 无搜索接口
        return {"list": [], "page": 1, "pagecount": 1}

    def playerContent(self, flag, id, vipFlags):
        # id 是视频链接，交由解析器处理
        if not id.startswith('http'):
            id = self.site_url + id
        return {"parse": 1, "url": id, "header": self.headers}