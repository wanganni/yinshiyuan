# -*- coding: utf-8 -*-
import sys
import requests
import re
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):

    def init(self, extend=""):
        self.host = "https://hwj1ens1kgh5qus.rtuiio990.88cyooi.top"
        self.header = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 15; RMX3770 Build/AP3A.240617.008) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/130.0.6723.58 Mobile Safari/537.36'
        }

    def getName(self):
        return "5X社区"

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    def homeContent(self, filter):
        result = {}
        classes = []
        
        cate_names = '5X社区会员原创作品&Paco&SM性虐&三级片&东京热&丝袜诱惑&中文字幕&公众场所及户外&加勒比&口爆颜射&器具自慰&国产AV&天然素人&女同&小格式综合&性party&成人动漫&成人直播&探花大神&无码破解&日本无码&日本有码&本道&李宗瑞全集&欧美&潮吹&肛交&韩国女主播系列&韩国综合&高清'
        cate_ids = '5XSQ members original works&Pacopacomama&sm&Tertiary film&Tokyo Hot&Pantyhose temptation&Chinese subtitle&Public places and outdoors&Caribbeancom&Cumshot&Masturbation&homemade-selfie&10musume&Lesbian&Small format synthesis&Sex party&Adult Anime&chinese-anchor&tanhua-god&reducing-mosaic&Japan Uncensored&Japan Coded&pondo&The Complete Works of Li Zongrui&Europe and America&Squirting&Anal sex&Korean female anchor series&Korea General&HD'
        
        names = cate_names.split('&')
        ids = cate_ids.split('&')
        
        for i in range(len(names)):
            classes.append({
                'type_name': names[i],
                'type_id': ids[i]
            })
            
        result['class'] = classes
        result['filters'] = {}
        return result

    def homeVideoContent(self):
        return {'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        url = f"{self.host}/videos/{tid}?page={pg}"
        res = requests.get(url, headers=self.header)
        res.encoding = 'utf-8'
        
        vods = []
        pattern = re.compile(r'<div class="thumb">.*?<a href="(.*?)".*?title="(.*?)".*?srcset="(.*?)".*?<span class="duration">.*?title="(.*?)"', re.S)
        items = pattern.findall(res.text)
        
        for href, title, img, duration in items:
            if not img.startswith('http'):
                img = self.host + img if img.startswith('/') else self.host + '/' + img
            
            vods.append({
                'vod_id': href,
                'vod_name': title,
                'vod_pic': img,
                'vod_remarks': duration
            })
            
        result['list'] = vods
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 30
        result['total'] = 999999
        return result

    def detailContent(self, ids):
        vid = ids[0]
        url = vid if 'http' in vid else f"{self.host}{vid}"
        
        vod = {
            'vod_id': vid,
            'vod_name': '5X视频',
            'vod_pic': '',
            'type_name': '',
            'vod_year': '',
            'vod_area': '',
            'vod_remarks': '',
            'vod_actor': '',
            'vod_director': '',
            'vod_content': ''
        }
        
        vod['vod_play_from'] = '5X社区'
        vod['vod_play_url'] = f"在线播放${url}"
        return {'list': [vod]}

    def searchContent(self, key, quick, pg="1"):
        result = {}
        url = f"{self.host}/search/videos/{key}?page={pg}"
        res = requests.get(url, headers=self.header)
        res.encoding = 'utf-8'
        
        vods = []
        pattern = re.compile(r'<div class="thumb">.*?<a href="(.*?)".*?title="(.*?)".*?srcset="(.*?)".*?<span class="duration">.*?title="(.*?)"', re.S)
        items = pattern.findall(res.text)
        
        for href, title, img, duration in items:
            if not img.startswith('http'):
                img = self.host + img if img.startswith('/') else self.host + '/' + img
                
            vods.append({
                'vod_id': href,
                'vod_name': title,
                'vod_pic': img,
                'vod_remarks': duration
            })
            
        result['list'] = vods
        result['page'] = pg
        return result

    def playerContent(self, flag, id, vipFlags):
        url = id
        try:
            res = requests.get(url, headers=self.header)
            video_url = re.search(r'meta property="og:video:url" content="(.*?)"', res.text).group(1)
            return {'parse': 0, 'url': video_url, 'header': self.header}
        except:
            return {'parse': 1, 'url': url, 'header': self.header}

    def localProxy(self, param):
        pass
