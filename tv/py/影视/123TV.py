# coding=utf-8
"""
目标站: A123TV  首页: https://a123tv.com
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
        self.site_url = "https://a123tv.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': self.site_url,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
        }

        self.categories = [
            {"type_id": "10", "type_name": "电影"},
            {"type_id": "11", "type_name": "连续剧"},
            {"type_id": "12", "type_name": "综艺"},
            {"type_id": "13", "type_name": "动漫"},
            {"type_id": "15", "type_name": "福利"}
        ]

        # ========== 预定义所有分类的筛选 ==========
        self.filters = {
            "10": [{"key": "subtype", "name": "类型", "value": [
                {"n": "全部", "v": ""},
                {"n": "动作片", "v": "1001"},
                {"n": "喜剧片", "v": "1002"},
                {"n": "爱情片", "v": "1003"},
                {"n": "科幻片", "v": "1004"},
                {"n": "恐怖片", "v": "1005"},
                {"n": "剧情片", "v": "1006"},
                {"n": "战争片", "v": "1007"},
                {"n": "纪录片", "v": "1008"},
                {"n": "动漫电影", "v": "1009"},
                {"n": "奇幻片", "v": "1010"},
                {"n": "动画片", "v": "1011"},
                {"n": "犯罪片", "v": "1012"},
                {"n": "悬疑片", "v": "1013"},
                {"n": "邵氏电影", "v": "1014"},
                {"n": "歌舞片", "v": "1015"},
                {"n": "家庭片", "v": "1016"},
                {"n": "古装片", "v": "1017"},
                {"n": "历史片", "v": "1018"},
                {"n": "4K电影", "v": "1019"}
            ]}],
            "11": [{"key": "subtype", "name": "类型", "value": [
                {"n": "全部", "v": ""},
                {"n": "国产剧", "v": "1101"},
                {"n": "香港剧", "v": "1102"},
                {"n": "韩国剧", "v": "1103"},
                {"n": "欧美剧", "v": "1104"},
                {"n": "台湾剧", "v": "1105"},
                {"n": "日本剧", "v": "1106"},
                {"n": "海外剧", "v": "1107"},
                {"n": "泰国剧", "v": "1108"},
                {"n": "港台剧", "v": "1110"},
                {"n": "日韩剧", "v": "1111"}
            ]}],
            "12": [{"key": "subtype", "name": "类型", "value": [
                {"n": "全部", "v": ""},
                {"n": "内地综艺", "v": "1201"},
                {"n": "港台综艺", "v": "1202"},
                {"n": "日韩综艺", "v": "1203"},
                {"n": "欧美综艺", "v": "1204"}
            ]}],
            "13": [{"key": "subtype", "name": "类型", "value": [
                {"n": "全部", "v": ""},
                {"n": "国产动漫", "v": "1301"},
                {"n": "日韩动漫", "v": "1302"},
                {"n": "欧美动漫", "v": "1303"}
            ]}],
            "15": [{"key": "subtype", "name": "类型", "value": [
                {"n": "全部", "v": ""},
                {"n": "韩国情色片", "v": "1501"},
                {"n": "日本情色片", "v": "1502"}
            ]}]
        }
        # =========================================

    def homeContent(self, filter):
        url = self.site_url + "/"
        resp = self.fetch(url, headers=self.headers)
        video_list = []
        
        if resp:
            soup = BeautifulSoup(resp.text, 'html.parser')
            containers = soup.select('main > div')
            if len(containers) >= 2:
                home_block = containers[1]
                cards = home_block.select('a.w4-item[href^="/v/"]')
                for a in cards[:20]:
                    href = a.get('href', '')
                    slug = href.replace('/v/', '').replace('.html', '').strip()
                    if not slug:
                        continue
                    title_tag = a.select_one('.w4-item-info .t')
                    vod_name = title_tag.get_text(strip=True) if title_tag else ''
                    if not vod_name:
                        vod_name = title_tag.get('title', '') if title_tag else ''
                    remark_tag = a.select_one('.w4-item-info .i')
                    vod_remarks = remark_tag.get_text(strip=True) if remark_tag else ''
                    img = a.select_one('figure img')
                    vod_pic = ''
                    if img:
                        src = img.get('data-src', '') or img.get('src', '')
                        if src:
                            vod_pic = src if src.startswith('http') else 'https:' + src
                    if vod_name:
                        video_list.append({
                            "vod_id": slug,
                            "vod_name": vod_name,
                            "vod_pic": vod_pic,
                            "vod_remarks": vod_remarks
                        })
        
        return {"class": self.categories, "list": video_list, "filters": self.filters}

    def homeVideoContent(self):
        return self.homeContent(False)

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg else 1
        
        # 如果筛选传入了 subtype，覆盖 tid
        if extend and 'subtype' in extend and extend['subtype']:
            tid = extend['subtype']
        
        if page == 1:
            url = f"{self.site_url}/t/{tid}.html"
        else:
            url = f"{self.site_url}/t/{tid}/p{page}.html"
        
        resp = self.fetch(url, headers=self.headers)
        if not resp:
            return {"list": [], "page": page, "pagecount": 1, "limit": 24, "total": 0}
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        video_list = []
        list_block = soup.select_one('div.w4-list')
        if not list_block:
            return {"list": [], "page": page, "pagecount": 1, "limit": 24, "total": 0}
        
        cards = list_block.select('a.w4-item[href^="/v/"]')
        for a in cards:
            href = a.get('href', '')
            slug = href.replace('/v/', '').replace('.html', '').strip()
            if not slug:
                continue
            title_tag = a.select_one('.w4-item-info .t')
            vod_name = title_tag.get_text(strip=True) if title_tag else ''
            if not vod_name:
                vod_name = title_tag.get('title', '') if title_tag else ''
            remark_tag = a.select_one('.w4-item-info .i')
            vod_remarks = remark_tag.get_text(strip=True) if remark_tag else ''
            img = a.select_one('figure img')
            vod_pic = ''
            if img:
                src = img.get('data-src', '') or img.get('src', '')
                if src:
                    vod_pic = src if src.startswith('http') else 'https:' + src
            if vod_name:
                video_list.append({
                    "vod_id": slug,
                    "vod_name": vod_name,
                    "vod_pic": vod_pic,
                    "vod_remarks": vod_remarks
                })
        
        # 分页
        pagecount = 1
        page_block = soup.select_one('div.w4-page')
        if page_block:
            page_links = page_block.select('a')
            for a_tag in page_links:
                text = a_tag.get_text(strip=True)
                if text.isdigit():
                    pagecount = max(pagecount, int(text))
                elif '下页' in text or '下一页' in text:
                    pagecount = page + 1
        
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
        url = f"{self.site_url}/v/{vod_id}.html"
        resp = self.fetch(url, headers=self.headers)
        if not resp or resp.status_code != 200:
            return {"list": []}
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 标题
        title_elem = soup.select_one('h1') or soup.select_one('h2') or soup.select_one('h3.t')
        vod_name = title_elem.get_text(strip=True) if title_elem else vod_id
        
        # 图片
        vod_pic = ''
        player_div = soup.select_one('#awp1')
        if player_div and player_div.get('data-poster'):
            vod_pic = player_div.get('data-poster')
            if vod_pic.startswith('//'):
                vod_pic = 'https:' + vod_pic
        if not vod_pic:
            img_elem = soup.select_one('div.w4-video img') or soup.select_one('main img')
            if img_elem:
                src = img_elem.get('data-src', '') or img_elem.get('src', '')
                if src:
                    vod_pic = src if src.startswith('http') else ('https:' + src)
        
        # 从 meta description 提取详细字段
        vod_content = ''
        vod_area = ''
        vod_actor = ''
        vod_director = ''
        vod_year = ''
        meta_desc = soup.select_one('meta[name="description"]')
        if meta_desc:
            desc_text = meta_desc.get('content', '')
            area_match = re.search(r'地区：([^。]+)', desc_text)
            if area_match:
                vod_area = area_match.group(1).strip()
            actor_match = re.search(r'演员：([^。]+)', desc_text)
            if actor_match:
                vod_actor = actor_match.group(1).strip()
            director_match = re.search(r'导演：([^。]+)', desc_text)
            if director_match:
                vod_director = director_match.group(1).strip()
            plot_match = re.search(r'剧情：(.+)', desc_text)
            if plot_match:
                vod_content = plot_match.group(1).strip()
            else:
                vod_content = desc_text
        
        if not vod_content:
            desc_elem = soup.select_one('.detail-desc') or soup.select_one('.text-muted')
            if desc_elem:
                vod_content = desc_elem.get_text(strip=True)
        
        # 播放列表
        play_from_list = []
        play_url_list = []
        pp_match = re.search(r'var\s+pp\s*=\s*({.*?});', resp.text, re.DOTALL)
        if pp_match:
            try:
                pp = json.loads(pp_match.group(1))
                la_list = pp.get('la', [])
                for item in la_list:
                    line_id = item[0]
                    line_name = item[1]
                    total = item[2]
                    episodes = []
                    for i in range(total):
                        ep_url = f"/v/{vod_id}/{line_id}z{i}.html"
                        ep_name = f"第{i+1:02d}集" if total > 1 else line_name
                        episodes.append(f"{ep_name}${ep_url}")
                    if episodes:
                        play_from_list.append(line_name)
                        play_url_list.append('#'.join(episodes))
            except Exception:
                pass
        
        if not play_url_list:
            line_items = soup.select('div.w4-line a.w4-line-item')
            if line_items:
                for a in line_items:
                    name_tag = a.select_one('.w4-line-info .r')
                    source_name = name_tag.get_text(strip=True) if name_tag else '未知线路'
                    href = a.get('href', '')
                    if href:
                        play_from_list.append(source_name)
                        play_url_list.append(f"{source_name}${href}")
            if not play_url_list:
                ep_links = soup.select('div.w4-episode-list a')
                if ep_links:
                    episodes = []
                    for a in ep_links:
                        name = a.get_text(strip=True)
                        href = a.get('href', '')
                        if name and href:
                            episodes.append(f"{name}${href}")
                    if episodes:
                        play_from_list.append('默认线路')
                        play_url_list.append('#'.join(episodes))
        
        vod_play_from = '$$$'.join(play_from_list) if play_from_list else '默认线路'
        vod_play_url = '$$$'.join(play_url_list) if play_url_list else ''
        
        result = [{
            "vod_id": vod_id,
            "vod_name": vod_name,
            "vod_pic": vod_pic,
            "vod_content": vod_content,
            "vod_actor": vod_actor,
            "vod_director": vod_director,
            "vod_area": vod_area,
            "vod_year": vod_year,
            "vod_play_from": vod_play_from,
            "vod_play_url": vod_play_url
        }]
        return {"list": result}

    def searchContent(self, key, quick, pg="1"):
        page = int(pg) if pg else 1
        url = f"{self.site_url}/s/?wd={urllib.parse.quote(key)}"
        if page > 1:
            url += f"&page={page}"
        
        resp = self.fetch(url, headers=self.headers)
        if not resp:
            return {"list": [], "page": page, "pagecount": 1}
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        video_list = []
        list_block = soup.select_one('div.w4-list')
        if list_block:
            cards = list_block.select('a.w4-item[href^="/v/"]')
        else:
            cards = soup.select('a[href^="/v/"]')
        
        for a in cards[:20]:
            href = a.get('href', '')
            slug = href.replace('/v/', '').replace('.html', '').strip()
            if not slug:
                continue
            title_tag = a.select_one('.w4-item-info .t')
            vod_name = title_tag.get_text(strip=True) if title_tag else ''
            if not vod_name:
                vod_name = title_tag.get('title', '') if title_tag else ''
            remark_tag = a.select_one('.w4-item-info .i')
            vod_remarks = remark_tag.get_text(strip=True) if remark_tag else ''
            img = a.select_one('figure img')
            vod_pic = ''
            if img:
                src = img.get('data-src', '') or img.get('src', '')
                if src:
                    vod_pic = src if src.startswith('http') else 'https:' + src
            if vod_name:
                video_list.append({
                    "vod_id": slug,
                    "vod_name": vod_name,
                    "vod_pic": vod_pic,
                    "vod_remarks": vod_remarks
                })
        
        return {"list": video_list, "page": page, "pagecount": 1}

    def playerContent(self, flag, id, vipFlags):
        if not id.startswith('http'):
            url = self.site_url + id
        else:
            url = id
        
        return {"parse": 1, "url": url, "header": self.headers}