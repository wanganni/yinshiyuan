# -*- coding: utf-8 -*-
#Kyle
import json, sys, re
from base64 import b64decode, b64encode
from urllib.parse import urljoin
from requests import Session
from pyquery import PyQuery as pq
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def init(self, extend=""):
        self.proxies = {}
        try:
            p = json.loads(extend) if extend else {}
            if isinstance(p, dict) and 'proxy' in p: p = p['proxy']
            self.proxies = {k: f'http://{v}' if isinstance(v, str) and not v.startswith('http') else v for k, v in p.items()}
        except: pass
        self.headers = {
    'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 10; SM-G975F Build/QP1A.190711.020) okhttp/5.0.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
}
        self.host = b64decode("aHR0cHM6Ly9tb3R2LmFwcA==").decode('utf-8')
        self.session = Session()
        self.session.headers.update(self.headers)
        self.session.proxies.update(self.proxies)

    def getName(self): return "MOTV"
    def isVideoFormat(self, url): return '.m3u8' in url or '.mp4' in url
    def manualVideoCheck(self): return True
    def destroy(self): pass

    def getpq(self, path=''):
        url = path if path.startswith('http') else self.host + path
        try:
            resp = self.session.get(url, timeout=15)
            resp.encoding = 'utf-8'
            return pq(resp.text)
        except Exception as e: return pq("")

    def getlist(self, selector):
        vlist = []
        for i in selector.items():
            try:
                vod_name = i('.movie-title').text().strip()
                vod_url = i('a').attr('href')
                if not vod_url or not vod_name: continue
                img_elem = i('.movie-post-lazyload')
                vod_pic = img_elem.attr('data-original')
                if not vod_pic:
                    style_attr = img_elem.attr('style') or ''
                    match = re.search(r"background-image:\s*url\('([^']+)'\)", style_attr)
                    vod_pic = match.group(1) if match else img_elem.attr('src')
                if vod_pic:
                    if vod_pic.startswith('//'): vod_pic = 'https:' + vod_pic
                    elif not vod_pic.startswith('http'): vod_pic = urljoin(self.host, vod_pic)
                vod_remarks = f"评分:{i('.movie-rating').text().strip()}" if i('.movie-rating').text().strip() else ""
                if vod_url and not vod_url.startswith('http'): vod_url = self.host + vod_url
                vlist.append({'vod_id': b64encode(vod_url.encode('utf-8')).decode('utf-8'), 'vod_name': vod_name, 'vod_pic': vod_pic, 'vod_remarks': vod_remarks, 'style': {'ratio': 1.78, 'type': 'rect'}})
            except Exception as e: pass
        return vlist

    def homeContent(self, filter):
        classes = [{'type_name': n, 'type_id': i} for n, i in [('精选HD日本破解无码', 'vodshow/51'), ('精选HD欧美质量爽片', 'vodshow/52'), ('日本無碼', 'vodshow/50'), ('日本有碼', 'vodshow/20'), ('歐美风情', 'vodshow/25'), ('國產原創', 'vodshow/41'), ('水果短视频AV解说', 'vodshow/35'), ('色情雜燴(字幕不全)', 'vodshow/30'), ('三级电影', 'vodshow/53'), ('经典剧情四级电影', 'vodshow/47')]]
        vlist = self.getlist(self.getpq('/label/new/')('.movie-list-item'))
        return {'class': classes, 'filters': self.getFilters(), 'list': vlist}

    def getFilters(self):
        jp_class = [{"n": n, "v": v} for v, n in [("", "全部"), ("偶像系", "偶像系"), ("空姐 ", "空姐+"), ("教师", "教师"), ("女高中生", "女高中生"), ("女仆", "女仆"), ("兔女郎", "兔女郎"), ("護士", "護士"), ("乳液", "乳液"), ("潮吹", "潮吹"), ("按摩", "按摩"), ("美腿", "美腿"), ("微乳", "微乳"), ("美乳", "美乳"), ("少女", "少女"), ("痴女", "痴女"), ("荡妇", "荡妇"), ("熟女", "熟女"), ("捆绑", "捆绑"), ("中出", "中出"), ("颜射", "颜射"), ("调教", "调教"), ("母乳", "母乳"), ("肛交", "肛交"), ("另类", "另类"), ("剧情", "剧情"), ("綜藝", "綜藝"), ("情趣吊带", "情趣吊带"), ("连裤袜", "连裤袜"), ("白丝", "白丝"), ("絲襪 ", "絲襪+"), ("巨乳 ", "巨乳+"), ("苗条", "苗条"), ("多P", "多P"), ("肉食系 ", "肉食系+"), ("制服", "制服"), ("道具", "道具"), ("凌辱", "凌辱"), ("角色扮演", "角色扮演"), ("办公室", "办公室"), ("洗浴場 ", "洗浴場+"), ("校园", "校园"), ("電車 ", "電車+"), ("场景", "场景"), ("單體作品", "單體作品")]]
        om_class = [{"n": n, "v": v} for v, n in [("", "全部"), ("巨乳", "巨乳"), ("美乳", "美乳"), ("美臀", "美臀"), ("美腿", "美腿"), ("金发", "金发"), ("黑发", "黑发"), ("红发", "红发"), (" blonde", " blonde"), (" brunette", " brunette"), (" redhead", " redhead"), ("少女", "少女"), ("熟女", "熟女"), ("学生", "学生"), ("教师", "教师"), ("护士", "护士"), ("秘书", "秘书"), ("模特", "模特"), ("明星", "明星"), ("素人", "素人"), ("黑人", "黑人"), ("拉丁", "拉丁"), ("亚洲", "亚洲"), ("白人", "白人"), ("混血", "混血"), ("中出", "中出"), ("口交", "口交"), ("肛交", "肛交"), ("群交", "群交"), ("女同", "女同"), ("SM", "SM"), ("角色扮演", "角色扮演"), ("制服", "制服"), ("户外", "户外"), ("车内", "车内"), ("办公室", "办公室"), ("学校", "学校"), ("医院", "医院"), ("酒店", "酒店"), ("家庭", "家庭"), ("派对", "派对")]]
        sort_by = [{"n": "全部", "v": ""}, {"n": "时间", "v": "time"}, {"n": "人气", "v": "hits"}, {"n": "评分", "v": "score"}]
        filters_map = {"class": {"name": "分类", "value": []}, "by": {"name": "排序", "value": sort_by}}
        filters = {}
        for tid in ["vodshow/51", "vodshow/50", "vodshow/20"]: filters[tid] = [{"key": "class", "name": "分类", "value": jp_class}, {"key": "by", "name": "排序", "value": sort_by}]
        filters["vodshow/52"] = [{"key": "class", "name": "分类", "value": om_class}, {"key": "by", "name": "排序", "value": sort_by}]
        return filters

    def categoryContent(self, tid, pg, filter, extend):
        by = extend.get('by', '') if extend else ''
        cls = extend.get('class', '') if extend else ''
        url = f"{self.host}/{tid}--{by}-{cls}-----{pg}---/"
        vlist = self.getlist(self.getpq(url)('.movie-list-item'))
        return {'page': pg, 'pagecount': 9999, 'limit': 90, 'total': 999999, 'list': vlist}

    def searchContent(self, key, quick, pg="1"):
        try:
            url = f"https://motv.app/index.php/ajax/suggest?mid=1&wd={key}"
            data = self.session.get(url, timeout=15).json()
            vlist = []
            for item in data.get('list', []):
                vod_url = f"https://motv.app/vodplay/{item['id']}-1-1/"
                vod_pic = item.get('pic', '')
                if vod_pic and not vod_pic.startswith('http'): vod_pic = urljoin(self.host, vod_pic)
                vlist.append({'vod_id': b64encode(vod_url.encode('utf-8')).decode('utf-8'), 'vod_name': item.get('name', ''), 'vod_pic': vod_pic, 'vod_remarks': '', 'style': {'ratio': 1.78, 'type': 'rect'}})
            return {'list': vlist, 'page': pg}
        except Exception as e: return {'list': [], 'page': pg}

    def detailContent(self, ids):
        detail_url = b64decode(ids[0]).decode('utf-8')
        data = self.getpq(detail_url)
        title, actors, play_from, play_url = data('h1').text().strip(), [a.text().strip() for a in data('.starLink a').items()], [], []
        sources = data('.play_source_tab .titleName')
        if sources:
            for source in sources.items():
                play_from.append("MOTV")
                episodes = [f"{e('a').text().strip()}${b64encode((self.host + e('a').attr('href')).encode('utf-8')).decode('utf-8')}" for e in data('#tagContent .play_list_box .content_playlist li').items() if e('a').attr('href')]
                play_url.append('#'.join(episodes))
        if not play_from:
            playlist = data('.play_list_box')
            if playlist:
                play_from = ['MOTV']
                episodes = [f"{e('a').text().strip()}${b64encode((self.host + e('a').attr('href')).encode('utf-8')).decode('utf-8')}" for e in playlist('.content_playlist li').items() if e('a').attr('href')]
                if episodes: play_url.append('#'.join(episodes))
        if not play_from: play_from, play_url = ['MOTV'], [f"第1集${b64encode(detail_url.encode('utf-8')).decode('utf-8')}"]
        vod = {'vod_name': title, 'vod_actor': ' '.join(actors), 'vod_play_from': '$$$'.join(play_from), 'vod_play_url': '$$$'.join(play_url)}
        return {'list': [vod]}

    def _extract_direct_url(self, html):
        m = re.search(r"var\s+player_[a-zA-Z0-9_]*\s*=\s*(\{.*?\});", html, re.S)
        if m:
            block, url = m.group(1), ''
            try: url = json.loads(block).get('url') or ''
            except Exception as e:
                murl = re.search(r'"url"\s*:\s*"([^\"]+)"', block)
                if murl: url = murl.group(1)
            if url:
                url = url.replace('\\/', '/')
                if url.startswith('//'): url = 'https:' + url
                return url
        m1 = re.search(r'https?:\\/\\/[^"\'\s]+\.(?:m3u8|mp4)', html)
        if m1: return m1.group(0).replace('\\/', '/')
        m2 = re.search(r'https?://[^"\'\s]+\.(?:m3u8|mp4)', html)
        if m2: return m2.group(0)
        return ''

    def playerContent(self, flag, id, vipFlags):
        detail_url = b64decode(id.encode('utf-8')).decode('utf-8')
        try:
            resp = self.session.get(detail_url, timeout=15)
            resp.encoding = 'utf-8'
            html = resp.text
        except Exception as e: html = ''
        direct = self._extract_direct_url(html) or detail_url
        headers = {'User-Agent': self.headers.get('User-Agent', ''), 'Referer': detail_url, 'Origin': self.host, 'Range': 'bytes=0-'}
        return {'parse': 0, 'playUrl': '', 'url': direct, 'header': headers}