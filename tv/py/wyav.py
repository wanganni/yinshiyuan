"""
@header({
  searchable: 1,
  filterable: 1,
  quickSearch: 1,
  title: '吾爱AV',
  lang: 'hipy'
})
"""

import gzip
import json
import re
import sys
import base64
from urllib.parse import unquote, urlparse
import requests

try:
    from pyquery import PyQuery as pq
    HAS_PYQUERY = True
except ImportError:
    try:
        from lxml import html as lxml_html
        HAS_LXML = True
    except ImportError:
        HAS_LXML = False
    HAS_PYQUERY = False
    pq = None

sys.path.append('..')
try:
    from base.spider import Spider
except ImportError:
    class Spider:
        def init(self, extend='{}'): pass
        def getName(self): pass
        def isVideoFormat(self, url): pass
        def manualVideoCheck(self): pass
        def destroy(self): pass
        def log(self, msg): print(f"[LOG] {msg}")

class Spider(Spider):

    def init(self, extend='{}'):
        try:
            config = json.loads(extend)
            self.proxies = config.get('proxy', {})
            self.plp = config.get('plp', '')
        except Exception as e:
            self.log(f"初始化配置失败: {e}")
            self.proxies = {}
            self.plp = ''

    def getName(self):
        return "吾爱AV"

    def isVideoFormat(self, url):
        video_extensions = ['.mp4', '.m3u8', '.avi', '.mov', '.wmv', '.flv', '.webm']
        return any(url.lower().endswith(ext) for ext in video_extensions)

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    host = 'https://m.wyav.tv'
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'referer': f'{host}/',
        'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
    }

    def homeContent(self, filter):
        try:
            response = requests.get(f"{self.host}", headers=self.headers, proxies=self.proxies, timeout=10)
            response.raise_for_status()
            data = self.getpq(response.text)
        except Exception as e:
            self.log(f"首页请求失败: {e}")
            return {'class': [], 'filters': {}, 'list': []}
            
        result = {}
        try:
            # 分类数据
            classes = [
                {'type_name': '首页', 'type_id': 'home'},
                {'type_name': '国产', 'type_id': 'guochan'},
                {'type_name': '日本', 'type_id': 'japan'},
                {'type_name': '欧美', 'type_id': 'europe'},
                {'type_name': '韩国', 'type_id': 'korea'},
                {'type_name': '动漫', 'type_id': 'anime'},
                {'type_name': '港台', 'type_id': 'gangtai'},
                {'type_name': '其他', 'type_id': 'other'}
            ]
            
            # 过滤器数据
            filters = {
                'home': [
                    {'key': 'sort', 'name': '排序', 'value': [
                        {'n': '最新', 'v': 'time'},
                        {'n': '热门', 'v': 'hits'},
                        {'n': '推荐', 'v': 'score'}
                    ]}
                ],
                'guochan': [
                    {'key': 'sort', 'name': '排序', 'value': [
                        {'n': '最新', 'v': 'time'},
                        {'n': '热门', 'v': 'hits'},
                        {'n': '推荐', 'v': 'score'}
                    ]}
                ],
                'japan': [
                    {'key': 'sort', 'name': '排序', 'value': [
                        {'n': '最新', 'v': 'time'},
                        {'n': '热门', 'v': 'hits'},
                        {'n': '推荐', 'v': 'score'}
                    ]}
                ],
                'europe': [
                    {'key': 'sort', 'name': '排序', 'value': [
                        {'n': '最新', 'v': 'time'},
                        {'n': '热门', 'v': 'hits'},
                        {'n': '推荐', 'v': 'score'}
                    ]}
                ],
                'korea': [
                    {'key': 'sort', 'name': '排序', 'value': [
                        {'n': '最新', 'v': 'time'},
                        {'n': '热门', 'v': 'hits'},
                        {'n': '推荐', 'v': 'score'}
                    ]}
                ],
                'anime': [
                    {'key': 'sort', 'name': '排序', 'value': [
                        {'n': '最新', 'v': 'time'},
                        {'n': '热门', 'v': 'hits'},
                        {'n': '推荐', 'v': 'score'}
                    ]}
                ],
                'gangtai': [
                    {'key': 'sort', 'name': '排序', 'value': [
                        {'n': '最新', 'v': 'time'},
                        {'n': '热门', 'v': 'hits'},
                        {'n': '推荐', 'v': 'score'}
                    ]}
                ],
                'other': [
                    {'key': 'sort', 'name': '排序', 'value': [
                        {'n': '最新', 'v': 'time'},
                        {'n': '热门', 'v': 'hits'},
                        {'n': '推荐', 'v': 'score'}
                    ]}
                ]
            }
            
            result['class'] = classes
            result['filters'] = filters
            result['list'] = self.parse_video_list(data)
        except Exception as e:
            self.log(f"首页数据处理失败: {e}")
            result = {'class': [], 'filters': {}, 'list': []}
            
        return result

    def homeVideoContent(self):
        return {}

    def categoryContent(self, tid, pg, filter, extend):
        videos = []
        try:
            # 构建分类URL
            sort = extend.get('sort', 'time')
            
            if tid == 'home':
                url = f"{self.host}/?page={pg}"
            else:
                url = f"{self.host}/vod/show/id/{tid}/page/{pg}?sort={sort}"
            
            response = requests.get(url, headers=self.headers, proxies=self.proxies, timeout=10)
            response.raise_for_status()
            data = self.getpq(response.text)
            
            videos = self.parse_video_list(data)
            pagecount = self.get_page_count(data)
            
        except Exception as e:
            self.log(f"分类内容获取失败: {e}")
            
        result = {
            'list': videos,
            'page': int(pg),
            'pagecount': pagecount,
            'limit': 20,
            'total': 999999
        }
        return result

    def detailContent(self, ids):
        try:
            vod_id = ids[0]
            if not vod_id.startswith('http'):
                vod_id = f"{self.host}/vod/detail/{vod_id}"
                
            response = requests.get(vod_id, headers=self.headers, proxies=self.proxies, timeout=10)
            response.raise_for_status()
            data = self.getpq(response.text)
        except Exception as e:
            self.log(f"详情页请求失败: {e}")
            return {'list': []}
            
        try:
            vod = {}
            
            # 提取基本信息
            vod['vod_name'] = self._get_text(data, '.video-info h1') or self._get_text(data, 'title')
            vod['vod_pic'] = self._get_attr(data, '.video-poster img', 'src')
            vod['vod_year'] = self.extract_info(data, '年份')
            vod['vod_area'] = self.extract_info(data, '地区')
            vod['vod_actor'] = self.extract_info(data, '演员')
            vod['vod_director'] = self.extract_info(data, '导演')
            vod['vod_content'] = self.extract_info(data, '简介')
            
            # 提取播放列表
            play_from = []
            play_url = []
            
            # 尝试多种播放列表选择器
            play_selectors = [
                '.play-list',
                '.video-playlist',
                '.episode-list',
                '.player-source'
            ]
            
            for selector in play_selectors:
                play_elements = self._find_elements(data, selector)
                if play_elements:
                    play_items = self._find_elements(play_elements, 'a')
                    if play_items:
                        play_list = []
                        for item in self._iterate_elements(play_items):
                            name = self._get_text(item, '') or f"第{len(play_list)+1}集"
                            url = self._get_attr(item, '', 'href')
                            if url and not url.startswith('http'):
                                url = f"{self.host}{url}"
                            if url:
                                play_list.append(f"{name}${url}")
                        
                        if play_list:
                            play_from.append("默认线路")
                            play_url.append('#'.join(play_list))
                        break
            
            # 如果没有找到播放列表，使用默认播放地址
            if not play_from:
                play_from.append("默认线路")
                play_url.append(f"正片${vod_id}")
            
            vod['vod_play_from'] = '$$$'.join(play_from)
            vod['vod_play_url'] = '$$$'.join(play_url)
            vod['vod_id'] = vod_id.split('/')[-1] if '/' in vod_id else vod_id
            
            return {'list': [vod]}
        except Exception as e:
            self.log(f"详情数据处理失败: {e}")
            return {'list': []}

    def searchContent(self, key, quick, pg="1"):
        try:
            url = f"{self.host}/vod/search/page/{pg}?wd={key}"
            response = requests.get(url, headers=self.headers, proxies=self.proxies, timeout=10)
            response.raise_for_status()
            data = self.getpq(response.text)
            
            videos = self.parse_video_list(data)
            return {
                'list': videos,
                'page': int(pg),
                'pagecount': self.get_page_count(data)
            }
        except Exception as e:
            self.log(f"搜索失败: {e}")
            return {'list': [], 'page': int(pg)}

    def playerContent(self, flag, id, vipFlags):
        try:
            # 如果是详情页URL，需要提取播放地址
            if 'vod/detail' in id:
                response = requests.get(id, headers=self.headers, timeout=10)
                response.raise_for_status()
                data = self.getpq(response.text)
                
                # 尝试提取直接播放地址
                play_url = self.extract_play_url(data)
                if play_url:
                    return {
                        'parse': 0,
                        'url': play_url,
                        'header': self.headers
                    }
            
            # 如果是直接播放地址
            if self.isVideoFormat(id):
                return {
                    'parse': 0,
                    'url': id,
                    'header': self.headers
                }
            
            # 默认返回原始URL
            return {
                'parse': 0,
                'url': id,
                'header': self.headers
            }
            
        except Exception as e:
            self.log(f"播放内容获取失败: {e}")
            return {
                'parse': 0,
                'url': '',
                'header': self.headers
            }

    def extract_play_url(self, data):
        """从详情页提取播放地址"""
        try:
            # 尝试多种视频地址选择器
            video_selectors = [
                'video source',
                '.player video',
                '#video-player source',
                'iframe'
            ]
            
            for selector in video_selectors:
                element = self._find_elements(data, selector)
                if element:
                    src = self._get_attr(element, '', 'src')
                    if src and self.isVideoFormat(src):
                        if not src.startswith('http'):
                            src = f"{self.host}{src}"
                        return src
            
            # 尝试从脚本中提取
            scripts = self._find_elements(data, 'script')
            for script in self._iterate_elements(scripts):
                script_text = self._get_text(script, '')
                if script_text:
                    # 查找常见的视频URL模式
                    video_patterns = [
                        r'http[^\s"\']*\.(mp4|m3u8|avi|mov|wmv|flv|webm)[^\s"\']*',
                        r'url\s*[=:]\s*["\']([^"\']*\.(mp4|m3u8|avi|mov|wmv|flv|webm)[^"\']*)["\']',
                        r'src\s*[=:]\s*["\']([^"\']*\.(mp4|m3u8|avi|mov|wmv|flv|webm)[^"\']*)["\']'
                    ]
                    
                    for pattern in video_patterns:
                        matches = re.findall(pattern, script_text, re.IGNORECASE)
                        for match in matches:
                            url = match[0] if isinstance(match, tuple) else match
                            if self.isVideoFormat(url):
                                if not url.startswith('http'):
                                    url = f"{self.host}{url}"
                                return url
            
            return None
        except Exception as e:
            self.log(f"提取播放地址失败: {e}")
            return None

    def extract_info(self, data, key):
        """从详情页提取指定信息"""
        try:
            # 查找包含关键信息的元素
            info_elements = self._find_elements(data, '.video-info, .info, .details')
            for element in self._iterate_elements(info_elements):
                text = self._get_text(element, '')
                if key in text:
                    # 提取冒号后的内容
                    pattern = f'{key}[：:]\s*([^\n<]+)'
                    match = re.search(pattern, text)
                    if match:
                        return match.group(1).strip()
            return ""
        except Exception as e:
            self.log(f"提取信息失败 {key}: {e}")
            return ""

    def parse_video_list(self, data):
        """解析视频列表"""
        videos = []
        try:
            # 尝试多种列表选择器
            list_selectors = [
                '.video-list .video-item',
                '.movie-list li',
                '.vod-items .item',
                '.list-item'
            ]
            
            for selector in list_selectors:
                items = self._find_elements(data, selector)
                if items:
                    for item in self._iterate_elements(items):
                        vod_id = self._get_attr(item, 'a', 'href')
                        if vod_id and not vod_id.startswith('http'):
                            vod_id = vod_id.split('/')[-1]
                        
                        vod_name = self._get_text(item, '.title, h3, .name')
                        vod_pic = self._get_attr(item, 'img', 'src')
                        vod_remarks = self._get_text(item, '.remarks, .score, .time')
                        
                        if vod_id and vod_name:
                            videos.append({
                                'vod_id': vod_id,
                                'vod_name': vod_name,
                                'vod_pic': vod_pic,
                                'vod_remarks': vod_remarks,
                                'style': {"type": "rect", "ratio": 1.33}
                            })
                    break
                    
        except Exception as e:
            self.log(f"解析视频列表失败: {e}")
            
        return videos

    def get_page_count(self, data):
        """获取总页数"""
        try:
            pagination = self._find_elements(data, '.pagination, .page-nav')
            if pagination:
                page_links = self._find_elements(pagination, 'a')
                page_numbers = []
                for link in self._iterate_elements(page_links):
                    text = self._get_text(link, '')
                    if text and text.isdigit():
                        page_numbers.append(int(text))
                
                if page_numbers:
                    return max(page_numbers)
            return 1
        except Exception as e:
            self.log(f"获取页数失败: {e}")
            return 1

    def localProxy(self, param):
        return {}

    def liveContent(self, url):
        return {}

    # 以下是HTML解析辅助方法
    def getpq(self, data):
        if HAS_PYQUERY:
            try:
                return pq(data)
            except Exception as e:
                self.log(f"PyQuery解析失败: {e}")
        
        if HAS_LXML:
            try:
                return lxml_html.fromstring(data)
            except Exception as e:
                self.log(f"lxml解析失败: {e}")
        
        self.log("使用备用解析方式")
        return SimpleHTMLParser(data)

    def _find_elements(self, data, selector):
        if data is None:
            return []
            
        if HAS_PYQUERY and hasattr(data, '__call__'):
            return data(selector)
        elif HAS_LXML and hasattr(data, 'xpath'):
            return data.xpath(selector)
        else:
            return getattr(data, 'find', lambda x: [])(selector)

    def _get_attr(self, element, selector, attr):
        if element is None:
            return None
            
        try:
            if HAS_PYQUERY and hasattr(element, 'attr'):
                target = element(selector) if selector else element
                return target.attr(attr) if target else None
            elif HAS_LXML and hasattr(element, 'xpath'):
                target = element.xpath(selector)[0] if selector else element
                return target.get(attr) if target is not None else None
            else:
                return getattr(element, 'get_attr', lambda x, y: None)(selector, attr)
        except:
            return None

    def _get_text(self, element, selector, index=None):
        if element is None:
            return ""
            
        try:
            if HAS_PYQUERY and hasattr(element, 'text'):
                target = element(selector) if selector else element
                if index is not None and hasattr(target, 'eq'):
                    target = target.eq(index)
                return target.text() if target else ""
            elif HAS_LXML and hasattr(element, 'xpath'):
                target = element.xpath(selector) if selector else [element]
                if index is not None and target:
                    target = [target[index]] if index < len(target) else []
                return ' '.join([elem.text_content().strip() for elem in target]) if target else ""
            else:
                return getattr(element, 'get_text', lambda x: "")(selector)
        except:
            return ""

    def _iterate_elements(self, data):
        if data is None:
            return []
            
        if hasattr(data, 'items'):
            return data.items()
        elif hasattr(data, '__iter__') and not isinstance(data, str):
            return data
        else:
            return [data]

class SimpleHTMLParser:
    def __init__(self, html_text):
        self.html = html_text
        self._elements = []
        
    def __call__(self, selector):
        return SimpleHTMLParser(self.html)
        
    def items(self):
        return [self]
        
    def attr(self, name):
        if name == 'href':
            match = re.search(r'href=[\'"]([^\'"]+)[\'"]', self.html)
            return match.group(1) if match else None
        elif name == 'src':
            match = re.search(r'src=[\'"]([^\'"]+)[\'"]', self.html)
            return match.group(1) if match else None
        return None
        
    def text(self):
        return re.sub(r'<[^>]+>', '', self.html).strip()