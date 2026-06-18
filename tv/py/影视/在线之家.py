# coding=utf-8
"""
目标站: 在线之家  首页: https://www.zxzjhd.com/
基于 TVBox 兼容标准改造
"""
import re
import sys
import urllib.parse
from bs4 import BeautifulSoup

sys.path.append('..')
from base.spider import Spider

class Spider(Spider):

    def init(self, extend=""):
        self.site_url = "https://www.zxzjhd.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': self.site_url,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
        }

    def homeContent(self, filter):
        categories = [
            {"type_id": "1", "type_name": "电影"},
            {"type_id": "2", "type_name": "美剧"},
            {"type_id": "3", "type_name": "韩剧"},
            {"type_id": "4", "type_name": "日剧"},
            {"type_id": "5", "type_name": "泰剧"}
        ]
        
        url = f"{self.site_url}/"
        resp = self.fetch(url, headers=self.headers)
        if not resp:
            return {"class": categories, "list": [], "filters": {}}
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        video_list = []
        cards = soup.select('.stui-vodlist__box')
        
        for card in cards[:20]:
            link_elem = card.select_one('a.stui-vodlist__thumb')
            if not link_elem:
                continue
            
            href = link_elem.get('href', '')
            match = re.search(r'/voddetail/([^/]+)\.html', href)
            if match:
                vod_id = match.group(1)
            else:
                continue
            
            title_elem = card.select_one('h4.title') or link_elem
            vod_name = title_elem.get('title') or title_elem.get_text(strip=True) if title_elem else ''
            
            # stui 模板通常图片在 a 标签的 data-original 或内部 img 中
            vod_pic = link_elem.get('data-original', '')
            if not vod_pic:
                img_elem = link_elem.select_one('img')
                if img_elem:
                    vod_pic = img_elem.get('data-original') or img_elem.get('src', '')
            
            tag_elem = card.select_one('.pic-text')
            vod_remarks = tag_elem.get_text(strip=True) if tag_elem else ''
            
            if vod_name:
                video_list.append({
                    "vod_id": vod_id,
                    "vod_name": vod_name,
                    "vod_pic": vod_pic,
                    "vod_remarks": vod_remarks
                })
        
        # 由于目标站未提供复杂筛选项结构，这里保持空 filters 避免出错
        filters = {}
        
        return {"class": categories, "list": video_list, "filters": filters}

    def homeVideoContent(self):
        return self.homeContent(False)

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg else 1
        
        # 构建基础 URL: /vodtype/{tid}-{page}.html
        url = f"{self.site_url}/vodtype/{tid}-{page}.html"
        
        resp = self.fetch(url, headers=self.headers)
        if not resp:
            return {"list": [], "page": page, "pagecount": 1, "limit": 24, "total": 0}
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        video_list = []
        cards = soup.select('.stui-vodlist__box')
        
        for card in cards:
            link_elem = card.select_one('a.stui-vodlist__thumb')
            if not link_elem:
                continue
            
            href = link_elem.get('href', '')
            match = re.search(r'/voddetail/([^/]+)\.html', href)
            if match:
                vod_id = match.group(1)
            else:
                continue
            
            title_elem = card.select_one('h4.title') or link_elem
            vod_name = title_elem.get('title') or title_elem.get_text(strip=True) if title_elem else ''
            
            vod_pic = link_elem.get('data-original', '')
            if not vod_pic:
                img_elem = link_elem.select_one('img')
                if img_elem:
                    vod_pic = img_elem.get('data-original') or img_elem.get('src', '')
            
            tag_elem = card.select_one('.pic-text')
            vod_remarks = tag_elem.get_text(strip=True) if tag_elem else ''
            
            if vod_name:
                video_list.append({
                    "vod_id": vod_id,
                    "vod_name": vod_name,
                    "vod_pic": vod_pic,
                    "vod_remarks": vod_remarks
                })
        
        pagecount = page
        pagination = soup.select('.stui-page__item a')
        for a in pagination:
            if '下一页' in a.get_text(strip=True):
                pagecount = page + 1
                break
        
        return {
            "list": video_list,
            "page": page,
            "pagecount": pagecount,
            "limit": 24,
            "total": len(video_list) * pagecount
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
        
        detail = soup.select_one('.stui-content__detail')
        vod_name = ''
        if detail:
            name_elem = detail.select_one('h1.title') or detail.select_one('h3.title')
            vod_name = name_elem.get_text(strip=True) if name_elem else ''
        
        vod_pic = ''
        img_elem = soup.select_one('a.pic img.lazyload') or soup.select_one('.stui-vodlist__thumb img')
        if img_elem:
            vod_pic = img_elem.get('data-original') or img_elem.get('src', '')
        
        vod_content = ''
        vod_director = ''
        vod_actor = ''
        vod_year = ''
        vod_area = ''
        
        if detail:
            for p in detail.select('p.data'):
                text = p.get_text(strip=True)
                if '导演：' in text:
                    vod_director = text.replace('导演：', '').strip()
                elif '主演：' in text:
                    vod_actor = text.replace('主演：', '').strip()
                elif '类型：' in text:
                    # 分割提取 年份/地区/类型 (根据目标站格式: 类型：... / 地区：... / 年份：...)
                    parts = text.split('/')
                    for part in parts:
                        if '年份：' in part:
                            vod_year = part.replace('年份：', '').strip()
                        elif '地区：' in part:
                            vod_area = part.replace('地区：', '').strip()
            
            desc_elem = soup.select_one('span.detail-content') or soup.select_one('.desc.detail')
            if desc_elem:
                vod_content = desc_elem.get_text(strip=True).replace('简介：', '').strip()
        
        play_from_list = []
        play_url_list = []
        
        # 提取播放源名称 (stui 模板通常在面板头部)
        play_source_tabs = soup.select('.stui-pannel__hd h3.title')
        for tab in play_source_tabs:
            tab_text = tab.get_text(strip=True)
            if '播放' in tab_text or '线路' in tab_text or '云' in tab_text:
                source_name = tab_text.replace('播放', '').replace('线路', '').strip()
                if not source_name:
                    source_name = tab_text
                play_from_list.append(source_name)
        
        # 提取播放列表
        play_lists = soup.select('ul.stui-content__playlist')
        for idx, pl in enumerate(play_lists):
            episodes = []
            for a in pl.select('li a'):
                ep_name = a.get_text(strip=True)
                ep_link = a.get('href', '')
                if ep_link:
                    episodes.append(f"{ep_name}${ep_link}")
            
            if episodes:
                play_url_list.append('#'.join(episodes))
        
        # 如果解析的名称数量与列表数量不匹配，兜底处理
        if not play_from_list or len(play_from_list) != len(play_url_list):
            play_from_list = [f"播放源{i+1}" for i in range(len(play_url_list))]
            
        vod_play_from = '$$$'.join(play_from_list) if play_from_list else '默认线路'
        vod_play_url = '$$$'.join(play_url_list) if play_url_list else ''
        
        result = [{
            "vod_id": vod_id,
            "vod_name": vod_name,
            "vod_pic": vod_pic,
            "vod_year": vod_year,
            "vod_area": vod_area,
            "vod_director": vod_director,
            "vod_actor": vod_actor,
            "vod_content": vod_content,
            "vod_play_from": vod_play_from,
            "vod_play_url": vod_play_url
        }]
        
        return {"list": result}

    def searchContent(self, key, quick, pg="1"):
        page = int(pg) if pg else 1
        # 适配 MacCMS 标准搜索路径
        url = f"{self.site_url}/vodsearch/{urllib.parse.quote(key)}----------{page}---.html"
        
        resp = self.fetch(url, headers=self.headers)
        if not resp:
            return {"list": [], "page": page, "pagecount": 1}
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        video_list = []
        cards = soup.select('.stui-vodlist__box')
        
        for card in cards:
            link_elem = card.select_one('a.stui-vodlist__thumb')
            if not link_elem:
                continue
            
            href = link_elem.get('href', '')
            match = re.search(r'/voddetail/([^/]+)\.html', href)
            if match:
                vod_id = match.group(1)
            else:
                continue
            
            title_elem = card.select_one('h4.title') or link_elem
            vod_name = title_elem.get('title') or title_elem.get_text(strip=True) if title_elem else ''
            
            vod_pic = link_elem.get('data-original', '')
            if not vod_pic:
                img_elem = link_elem.select_one('img')
                if img_elem:
                    vod_pic = img_elem.get('data-original') or img_elem.get('src', '')
            
            tag_elem = card.select_one('.pic-text')
            vod_remarks = tag_elem.get_text(strip=True) if tag_elem else ''
            
            if vod_name:
                video_list.append({
                    "vod_id": vod_id,
                    "vod_name": vod_name,
                    "vod_pic": vod_pic,
                    "vod_remarks": vod_remarks
                })
        
        pagecount = page
        pagination = soup.select('.stui-page__item a')
        for a in pagination:
            if '下一页' in a.get_text(strip=True):
                pagecount = page + 1
                break
                
        return {"list": video_list, "page": page, "pagecount": pagecount}

    def playerContent(self, flag, id, vipFlags):
        if not id.startswith('http'):
            url = self.site_url + id
        else:
            url = id
        
        return {"parse": 1, "url": url, "header": self.headers}
