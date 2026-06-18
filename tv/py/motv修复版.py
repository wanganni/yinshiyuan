# -*- coding: utf-8 -*-
# MOTV 爬虫修复版
import json, sys, re
from base64 import b64decode, b64encode
from urllib.parse import urljoin, quote
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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        self.host = "https://motv.app"
        self.session = Session()
        self.session.headers.update(self.headers)
        self.session.proxies.update(self.proxies)
        self.timeout = 20

    def getName(self): return "MOTV"
    def isVideoFormat(self, url): return '.m3u8' in url or '.mp4' in url
    def manualVideoCheck(self): return True
    def destroy(self): pass

    def getpq(self, url):
        if not url.startswith('http'):
            url = self.host + url
        try:
            resp = self.session.get(url, timeout=self.timeout)
            resp.encoding = 'utf-8'
            return pq(resp.text)
        except Exception as e:
            print(f"获取页面失败: {url}, 错误: {e}")
            return pq("")

    def getlist(self, selector):
        vlist = []
        for i in selector.items():
            try:
                # 获取标题
                title_elem = i('.movie-title, .title, h4')
                vod_name = title_elem.text().strip()
                if not vod_name:
                    vod_name = i.attr('title') or i('img').attr('alt') or ''
                
                # 获取链接
                link_elem = i('a')
                vod_url = link_elem.attr('href')
                if not vod_url:
                    vod_url = i.attr('href') or ''
                if not vod_url or not vod_name:
                    continue
                
                # 获取图片
                vod_pic = ''
                img_elem = i('.movie-post-lazyload, img')
                if img_elem:
                    vod_pic = img_elem.attr('data-original') or img_elem.attr('data-src') or img_elem.attr('src')
                    if not vod_pic:
                        style_attr = img_elem.attr('style') or ''
                        match = re.search(r"background-image:\s*url\(['\"]?([^'\")]+)['\"]?\)", style_attr)
                        vod_pic = match.group(1) if match else ''
                
                # 处理图片URL
                if vod_pic:
                    if vod_pic.startswith('//'):
                        vod_pic = 'https:' + vod_pic
                    elif not vod_pic.startswith('http'):
                        vod_pic = urljoin(self.host, vod_pic)
                
                # 获取评分
                rating_elem = i('.movie-rating, .rating, .score')
                vod_remarks = f"评分:{rating_elem.text().strip()}" if rating_elem and rating_elem.text().strip() else ""
                
                # 处理URL
                if vod_url and not vod_url.startswith('http'):
                    vod_url = urljoin(self.host, vod_url)
                
                # 添加到列表
                vlist.append({
                    'vod_id': b64encode(vod_url.encode('utf-8')).decode('utf-8'),
                    'vod_name': vod_name,
                    'vod_pic': vod_pic,
                    'vod_remarks': vod_remarks,
                    'style': {'ratio': 1.78, 'type': 'rect'}
                })
            except Exception as e:
                print(f"解析列表项失败: {e}")
                continue
        return vlist

    def homeContent(self, filter):
        classes = [
            {'type_name': '精选HD日本破解无码', 'type_id': 'vodshow/51'},
            {'type_name': '精选HD欧美质量爽片', 'type_id': 'vodshow/52'},
            {'type_name': '日本無碼', 'type_id': 'vodshow/50'},
            {'type_name': '日本有碼', 'type_id': 'vodshow/20'},
            {'type_name': '歐美风情', 'type_id': 'vodshow/25'},
            {'type_name': '國產原創', 'type_id': 'vodshow/41'},
            {'type_name': '水果短视频AV解说', 'type_id': 'vodshow/35'},
            {'type_name': '色情雜燴(字幕不全)', 'type_id': 'vodshow/30'},
            {'type_name': '三级电影', 'type_id': 'vodshow/53'},
            {'type_name': '经典剧情四级电影', 'type_id': 'vodshow/47'}
        ]
        
        # 获取首页内容
        doc = self.getpq('/')
        if not doc:
            # 尝试备用首页
            doc = self.getpq('/label/new/')
        
        if doc:
            # 尝试多种选择器
            items = doc('.movie-list-item, .vod-item, .item')
            if not items:
                items = doc('.row').find('.col-md-2, .col-sm-3, .col-xs-6')
            vlist = self.getlist(items)
        else:
            vlist = []
        
        return {'class': classes, 'filters': self.getFilters(), 'list': vlist}

    def getFilters(self):
        jp_class = [
            {"n": "全部", "v": ""},
            {"n": "偶像系", "v": "偶像系"},
            {"n": "空姐", "v": "空姐"},
            {"n": "教师", "v": "教师"},
            {"n": "女高中生", "v": "女高中生"},
            {"n": "女仆", "v": "女仆"},
            {"n": "兔女郎", "v": "兔女郎"},
            {"n": "护士", "v": "护士"},
            {"n": "美腿", "v": "美腿"},
            {"n": "美乳", "v": "美乳"},
            {"n": "少女", "v": "少女"},
            {"n": "熟女", "v": "熟女"},
            {"n": "中出", "v": "中出"},
            {"n": "肛交", "v": "肛交"},
            {"n": "剧情", "v": "剧情"},
            {"n": "制服", "v": "制服"},
            {"n": "角色扮演", "v": "角色扮演"},
            {"n": "校园", "v": "校园"},
            {"n": "单件作品", "v": "單體作品"}
        ]
        
        om_class = [
            {"n": "全部", "v": ""},
            {"n": "巨乳", "v": "巨乳"},
            {"n": "美乳", "v": "美乳"},
            {"n": "美臀", "v": "美臀"},
            {"n": "美腿", "v": "美腿"},
            {"n": "金发", "v": "金发"},
            {"n": "黑发", "v": "黑发"},
            {"n": "红发", "v": "红发"},
            {"n": "少女", "v": "少女"},
            {"n": "熟女", "v": "熟女"},
            {"n": "学生", "v": "学生"},
            {"n": "教师", "v": "教师"},
            {"n": "护士", "v": "护士"},
            {"n": "模特", "v": "模特"},
            {"n": "素人", "v": "素人"},
            {"n": "中出", "v": "中出"},
            {"n": "口交", "v": "口交"},
            {"n": "肛交", "v": "肛交"},
            {"n": "群交", "v": "群交"},
            {"n": "女同", "v": "女同"},
            {"n": "SM", "v": "SM"},
            {"n": "角色扮演", "v": "角色扮演"},
            {"n": "制服", "v": "制