# -*- coding: utf-8 -*-
import re
import sys
from pyquery import PyQuery as pq
from base64 import b64decode, b64encode
from requests import Session

sys.path.append('..')
from base.spider import Spider


class Spider(Spider):
    def init(self, extend=""):
        self.headers['referer'] = f'{self.host}/'
        self.session = Session()
        self.session.headers.update(self.headers)

    def getName(self):
        return "JAV目录大全"

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    host = "https://javmenu.com"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'sec-ch-ua': '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-full-version': '"133.0.6943.98"',
        'sec-ch-ua-arch': '"x86"',
        'sec-ch-ua-platform': '"Windows"',
        'sec-ch-ua-platform-version': '"19.0.0"',
        'sec-ch-ua-model': '""',
        'sec-ch-ua-full-version-list': '"Not(A:Brand";v="99.0.0.0", "Google Chrome";v="133.0.6943.98", "Chromium";v="133.0.6943.98"',
        'dnt': '1',
        'upgrade-insecure-requests': '1',
        'sec-fetch-site': 'none',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-user': '?1',
        'sec-fetch-dest': 'document',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'priority': 'u=0, i'
    }

    # -------------------- 业务接口 --------------------
    def homeContent(self, filter):
        cateManual = {
            "FC2在线": "/zh/fc2/online",
            "成人动画": "/zh/hanime/online",
            "国产在线": "/zh/chinese/online",
            "有码在线": "/zh/censored/online",
            "无码在线": "/zh/uncensored/online",
            "欧美在线": "/zh/western/online"
        }
        classes = [{'type_name': k, 'type_id': v} for k, v in cateManual.items()]
        return {'class': classes}

    def homeVideoContent(self):
        data = self.getpq("/zh")
        return {'list': self.getlist(data(".video-list-item"))}

    def categoryContent(self, tid, pg, filter, extend):
        url = f"{self.host}{tid}" if pg == '1' else f"{self.host}{tid}?page={pg}"
        data = self.getpq(url)
        return {
            'list': self.getlist(data(".video-list-item")),
            'page': pg,
            'pagecount': 9999,
            'limit': 90,
            'total': 999999
        }

    def detailContent(self, ids):
        vod_id = ids[0]
        if not vod_id.startswith('http'):
            url = f"{self.host}{vod_id}"
        else:
            url = vod_id
            vod_id = vod_id.replace(self.host, '')
        data = self.getpq(url)
        vod = {
            'vod_id': vod_id,
            'vod_name': data('h1').text() or data('title').text().split(' - ')[0],
            'vod_pic': self.getCover(data),
            'vod_content': data('.card-text').text() or '',
            'vod_director': '',
            'vod_actor': self.getActors(data),
            'vod_area': '日本',
            'vod_year': self.getYear(data('.text-muted').text()),
            'vod_remarks': self.getRemarks(data),
            'vod_play_from': 'JAV在线',
            'vod_play_url': self.getPlaylist(data, url)
        }
        return {'list': [vod]}

    def searchContent(self, key, quick, pg="1"):
        url = f"{self.host}/zh/search?wd={key}&page={pg}"
        data = self.getpq(url)
        return {'list': self.getlist(data(".video-list-item"))}

    def playerContent(self, flag, id, vipFlags):
        return {'parse': 0, 'url': self.d64(id), 'header': self.headers}

    # -------------------- 私有工具 --------------------
    def getlist(self, data):
        vlist = []
        for item in data.items():
            link = item('a').attr('href')
            if not link or '/zh/' not in link:
                continue
            link = link.replace(self.host, '') if link.startswith(self.host) else link
            name = item('.card-title').text() or item('img').attr('alt') or ''
            if not name:
                continue
            vlist.append({
                'vod_id': link,
                'vod_name': name.split(' - ')[0].strip(),
                'vod_pic': self.getListPicture(item),
                'vod_remarks': (item('.text-muted').text() or '').strip(),
                'style': {'ratio': 1.5, 'type': 'rect'}
            })
        return vlist

    # ******** 修复版本：支持LazyLoad和正确过滤 ********
    def getListPicture(self, item):
        """
        获取列表中的图片
        支持LazyLoad延迟加载机制
        过滤水印、占位符和无预览图
        """
        # 获取所有img标签
        imgs = item('img')
        
        for img in imgs.items():
            # 优先级：先从data-src获取（LazyLoad属性），再从src获取
            pic = img.attr('data-src') or img.attr('src')
            
            # 过滤条件：排除水印、占位符、加载图片
            if pic and not any(keyword in pic for keyword in ['button_logo', 'no_preview', 'loading.gif', 'loading.png']):
                return pic
        
        return ''

    def getCover(self, data):
        """
        获取详情页的图片
        支持LazyLoad延迟加载机制
        过滤水印、占位符和无预览图
        """
        # 获取所有img标签
        imgs = data('img')
        
        for img in imgs.items():
            # 优先级：先从data-src获取（LazyLoad属性），再从src获取
            pic = img.attr('data-src') or img.attr('src')
            
            # 过滤条件：排除水印、占位符、加载图片
            if pic and not any(keyword in pic for keyword in ['button_logo', 'no_preview', 'loading.gif', 'loading.png', 'website_building']):
                return pic
        
        return ''

    # **********************************
    def getActors(self, data):
        """获取演员信息"""
        actors = []
        h1_text = data('h1').text()
        if h1_text:
            actors.extend(h1_text.strip().split()[1:])
        actor_links = data('a[href*="/actor/"]')
        for actor_link in actor_links.items():
            actor_text = actor_link.text()
            if actor_text and actor_text not in actors:
                actors.append(actor_text)
        return ','.join(actors) if actors else '未知'

    def getYear(self, date_str):
        """从日期字符串中提取年份"""
        m = re.search(r'(\d{4})-\d{2}-\d{2}', date_str or '')
        return m.group(1) if m else ''

    def getRemarks(self, data):
        """获取备注信息（标签）"""
        tags = [tag.text() for tag in data('.badge').items() if tag.text()]
        return ' '.join(set(tags)) if tags else ''

    def getPlaylist(self, data, url):
        """
        获取播放列表
        从source、video标签和脚本中提取m3u8链接
        """
        play_urls, seen = [], set()
        
        # 从source标签获取
        for src in data('source').items():
            u = src.attr('src')
            if u and u not in seen:
                play_urls.append(f"源{len(play_urls)+1}${self.e64(u)}")
                seen.add(u)
        
        # 从video标签获取
        for u in data('video').items():
            u = u.attr('src')
            if u and u not in seen:
                play_urls.append(f"线路{len(play_urls)+1}${self.e64(u)}")
                seen.add(u)
        
        # 从脚本中提取m3u8链接
        for m in re.findall(r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*', data('script').text()):
            if m not in seen:
                play_urls.append(f"线路{len(play_urls)+1}${self.e64(m)}")
                seen.add(m)
        
        # 如果没有找到播放链接，使用页面URL
        if not play_urls:
            play_urls.append(f"在线播放${self.e64(url)}")
        
        return '#'.join(play_urls)

    def getpq(self, path=''):
        """获取页面内容并返回PyQuery对象"""
        url = path if path.startswith('http') else f'{self.host}{path}'
        try:
            rsp = self.session.get(url, timeout=20)
            rsp.encoding = 'utf-8'
            return pq(rsp.text)
        except Exception as e:
            print(f"getpq error: {e}")
            return pq('')

    def e64(self, text):
        """Base64编码"""
        try:
            return b64encode(text.encode('utf-8')).decode('utf-8')
        except Exception:
            return ''

    def d64(self, encoded_text):
        """Base64解码"""
        try:
            return b64decode(encoded_text.encode('utf-8')).decode('utf-8')
        except Exception:
            return ''