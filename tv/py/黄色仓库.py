import re
import sys
import urllib.parse
import threading
import time
import requests
import base64
import gzip
import json
from io import BytesIO
from pyquery import PyQuery as pq
sys.path.append('..')
from base.spider import Spider
class Spider(Spider):
    def __init__(self):
        self.name = "黄色仓库"
        self.host = self.getDynamicHost()  # 初始化获取动态主机
        self.classes = self.preprocessClasses()  # 初始化分类
        # 动态更新请求头Referer（核心修复：不再写死）
        self.header["Referer"] = self.host.rstrip('/') + '/'
        
    def getName(self):
        return self.name
    
    def getDynamicHost(self):
        """动态获取主机地址（核心修复：通配兜底+格式强校验）"""
        try:
            # 解码base64获取初始永久入口
            initial_host = base64.b64decode('aHR0cDovL2hzY2submV0').decode('utf-8')
            # 强制保证初始入口格式合法
            if not initial_host.startswith(('http://', 'https://')):
                initial_host = f"http://{initial_host}"
            if initial_host.endswith('/'):
                initial_host = initial_host.rstrip('/')
            # 获取初始页面（添加超时，避免卡壳）
            response = requests.get(initial_host, headers=self.header, timeout=10)
            response.raise_for_status()  # 触发HTTP错误（4xx/5xx）
            html = response.text
            
            # 匹配strU参数
            strU_match = re.search(r'strU="(.*?)"', html)
            if not strU_match:
                return self.formatHost(initial_host)
                
            strU = strU_match.group(1)
            locationU = strU + initial_host + '/&p=/'
            
            # 获取重定向地址（禁止自动重定向，添加超时）
            redirect_response = requests.get(
                locationU, 
                headers=self.header, 
                allow_redirects=False,
                timeout=10
            )
            if 'location' in redirect_response.headers:
                new_host = redirect_response.headers['location']
                return self.formatHost(new_host)  # 格式化后返回
            else:
                # 尝试从JSON响应中获取
                try:
                    data = redirect_response.json()
                    json_host = data.get('location', initial_host)
                    return self.formatHost(json_host)
                except:
                    return self.formatHost(initial_host)
                    
        except Exception as e:
            print(f"获取动态主机失败: {e}")
            # 核心修复：通配兜底（0000ck.cc，利用任意数字跳转特性）
            return self.formatHost("https://huangsecangku.net")
    def formatHost(self, host):
        """主机地址格式化强校验（核心工具：杜绝无主机问题）"""
        if not host:
            host = "https://huangsecangku.net"
        # 补全协议头（无http/https则默认http）
        if not host.startswith(('http://', 'https://')):
            host = f"http://{host}"
        # 去除末尾斜杠（避免拼接时出现//）
        host = host.rstrip('/')
        # 过滤非法字符，保证主机名纯净
        host = re.sub(r'[^\w\.\-:/]', '', host)
        return host
    
    def preprocessClasses(self):
        """预处理分类数据（原逻辑不变）"""
        return [
            {"type_name": "日韩AV", "type_id": "1"},
            {"type_name": "国产系列", "type_id": "2"}, 
            {"type_name": "欧美", "type_id": "3"},
            {"type_name": "成人动漫", "type_id": "4"},
            {"type_name": "日本有码", "type_id": "7"},
            {"type_name": "一本道高清无码", "type_id": "8"},
            {"type_name": "有码中文字幕", "type_id": "9"},
            {"type_name": "日本无码", "type_id": "10"},
            {"type_name": "国产视频", "type_id": "15"},
            {"type_name": "欧美高清", "type_id": "21"},
            {"type_name": "动漫剧情", "type_id": "22"}
        ]
    
    def init(self, extend):
        pass
        
    def isVideoFormat(self, url):
        pass
        
    def manualVideoCheck(self):
        pass
        
    def homeContent(self, filter):
        """返回分类数据（原逻辑不变）"""
        result = {}
        result['class'] = self.classes
        return result
    def homeVideoContent(self):
        """推荐内容（原逻辑+异常增强）"""
        result = {}
        try:
            url = f"{self.host}/"
            rsp = self.fetch(url)
            root = pq(rsp.text)
            
            videos = []
            list_items = root('.stui-vodlist li')
            if not list_items:
                return result  # 无数据直接返回
            
            for item in list_items.items():
                vid = item.find('a').attr('href')
                if not vid or not vid.startswith('/vodplay/'):
                    continue
                    
                name = item.find('h4').text().strip()
                img = item.find('a').attr('data-original') or item.find('a').attr('src')
                remark = item.find('.pic-text').text().strip()
                
                if not name or not img:
                    continue
                
                videos.append({
                    "vod_id": vid,
                    "vod_name": name,
                    "vod_pic": self.getFullUrl(img),
                    "vod_remarks": remark
                })
            
            result['list'] = videos
        except Exception as e:
            print(f"获取推荐内容失败: {e}")
            result['list'] = []
            
        return result
    def categoryContent(self, tid, pg, filter, extend):
        """分类内容（原逻辑+异常增强）"""
        result = {}
        try:
            # 校验页码和分类ID，避免非法参数
            pg = int(pg) if str(pg).isdigit() else 1
            tid = str(tid) if str(tid).isdigit() else "1"
            url = f"{self.host}/vodtype/{tid}-{pg}.html"
            
            rsp = self.fetch(url)
            root = pq(rsp.text)
            
            videos = []
            list_items = root('.stui-vodlist li')
            if not list_items:
                result['list'] = []
                result['page'] = pg
                result['pagecount'] = 1
                return result
            
            for item in list_items.items():
                vid = item.find('a').attr('href')
                if not vid or not vid.startswith('/vodplay/'):
                    continue
                    
                name = item.find('h4').text().strip()
                img = item.find('a').attr('data-original') or item.find('a').attr('src')
                remark = item.find('.pic-text').text().strip()
                
                if not name or not img:
                    continue
                
                videos.append({
                    "vod_id": vid,
                    "vod_name": name,
                    "vod_pic": self.getFullUrl(img),
                    "vod_remarks": remark
                })
            
            result['list'] = videos
            result['page'] = pg
            result['pagecount'] = 9999
            result['limit'] = 6
            result['total'] = 999999
            
        except Exception as e:
            print(f"获取分类内容失败: {e}")
            result['list'] = []
            result['page'] = 1
            result['pagecount'] = 1
            result['limit'] = 6
            result['total'] = 0
            
        return result
    def extractM3U8Url(self, script_text):
        """提取m3u8链接（核心修改：保留提取+手动修格式+删除多余拼接）"""
        m3u8_urls = []
        if not script_text:
            return m3u8_urls
            
        print("开始提取m3u8链接...")
        
        # 方法1: 增强版 - 匹配多个播放配置变量（原player_aaaa+扩展）
        player_patterns = [
            r'var\s+player_\w+\s*=\s*({.*?});',  # 匹配player_任意字符（适配站点变量改名）
            r'player_\w+\s*=\s*({.*?});',
            r'var\s+videoPlayer\s*=\s*({.*?});',
            r'videoPlayer\s*=\s*({.*?});',
            r'var\s+playConfig\s*=\s*({.*?});'
        ]
        
        for pattern in player_patterns:
            player_match = re.search(pattern, script_text, re.DOTALL | re.IGNORECASE)
            if player_match:
                try:
                    player_data_str = player_match.group(1)
                    # 强力修复JSON格式+转义符（核心：恢复提取能力）
                    player_data_str = player_data_str.replace('\\/', '/').replace("'", '"').replace(',}', '}').replace(',]', ']')
                    player_data = json.loads(player_data_str)
                    
                    # 匹配多个url关键字段（适配不同站点）
                    url_keys = ['url', 'playUrl', 'videoUrl', 'm3u8Url', 'src']
                    m3u8_url = ""
                    for key in url_keys:
                        if key in player_data and '.m3u8' in str(player_data[key]):
                            m3u8_url = str(player_data[key]).strip()
                            break
                    
                    if m3u8_url:
                        print(f"从播放变量提取到m3u8: {m3u8_url[:50]}...")
                        # 手动轻量修格式：仅去转义+补协议，不拼接主机
                        m3u8_url = m3u8_url.replace('\\/', '/')
                        if m3u8_url.startswith('//'):
                            m3u8_url = f"https:{m3u8_url}"
                        m3u8_urls.append(m3u8_url)
                        return m3u8_urls
                        
                except Exception as e:
                    print(f"解析播放变量失败: {e}")
                    continue
        
        # 方法2: 增强版 - 直接匹配m3u8链接（适配更多格式）
        m3u8_patterns = [
            r'"(https?://[^\s"\']+\.m3u8[^\s"\']*)"',
            r"'(https?://[^\s'\"]+\.m3u8[^\s'\"]*)'",
            r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*',
            r'"url"\s*[:=]\s*"([^"]+\.m3u8[^"]*)"',
            r"url\s*[:=]\s*'([^']+\.m3u8[^']*)'"
        ]
        
        for pattern in m3u8_patterns:
            matches = re.findall(pattern, script_text, re.IGNORECASE)
            for match in matches:
                match = match.strip().replace('\\/', '/')  # 处理转义符，恢复提取
                if '.m3u8' in match and match not in m3u8_urls:
                    print(f"从正则匹配提取到m3u8: {match[:50]}...")
                    # 手动轻量修格式：仅补协议，不拼接主机
                    if match.startswith('//'):
                        match = f"https:{match}"
                    m3u8_urls.append(match)
                    return m3u8_urls
        
        print("未找到m3u8播放链接")
        return m3u8_urls
    def detailContent(self, array):
        """详情页面解析（原逻辑+稳定性增强+iframe地址手动修格式）"""
        result = {}
        if not array or len(array) == 0:
            return result
            
        try:
            vid = array[0]
            vid = self.getFullUrl(vid)  # 直接格式化，无需判断
            
            print(f"开始解析详情页面: {vid[:50]}...")
            rsp = self.fetch(vid, timeout=15)
            root = pq(rsp.text)
            
            # 提取标题（多节点适配）
            title = root('.stui-pannel__head .title').text().strip() or \
                    root('h1').text().strip() or \
                    root('title').text().split(' - ')[0].strip() or \
                    "未知标题"
            
            # 提取封面图（多节点适配）
            pic = root('.stui-vodlist__thumb').attr('data-original') or \
                  root('.stui-vodlist__thumb').attr('src') or \
                  root('meta[property="og:image"]').attr('content') or \
                  ""
            
            # 获取所有script内容（合并所有script，避免遗漏）
            script_text = "\n".join([script.text() for script in root('script').items()])
            
            # 提取m3u8播放链接
            m3u8_urls = self.extractM3U8Url(script_text)
            
            # 构建播放链接
            play_urls = []
            if m3u8_urls:
                for i, m3u8_url in enumerate(m3u8_urls):
                    play_urls.append(f"线路{i+1}${m3u8_url}")
            else:
                # 兜底：尝试从iframe提取（核心修改：手动修格式，删除getFullUrl）
                print("尝试从iframe中提取播放链接...")
                iframe_src = root('iframe').attr('src')
                if iframe_src:
                    # 手动修格式：去转义+补协议，不拼接主机
                    iframe_src = iframe_src.strip().replace('\\/', '/')
                    if iframe_src.startswith('//'):
                        iframe_src = f"https:{iframe_src}"
                    play_urls.append(f"iframe线路${iframe_src}")
                else:
                    play_urls.append(f"详情页线路${vid}")
            
            # 封装返回数据
            vod = {
                "vod_id": array[0],
                "vod_name": title,
                "vod_pic": self.getFullUrl(pic) if pic else "",
                "vod_content": title,
                "vod_play_from": "黄色仓库",
                "vod_play_url": "#".join(play_urls)
            }
            
            result['list'] = [vod]
            print(f"详情页解析完成，共{len(play_urls)}条播放线路")
            
        except Exception as e:
            print(f"解析详情页面失败: {e}")
            import traceback
            traceback.print_exc()
            # 异常兜底（保证返回格式合法）
            result['list'] = [{
                "vod_id": array[0] if array else "",
                "vod_name": "未知标题",
                "vod_pic": "",
                "vod_content": "",
                "vod_play_from": "默认线路",
                "vod_play_url": f"详情页线路${array[0] if array else ''}"
            }]
            
        return result
    def searchContent(self, key, quick):
        """搜索内容（原逻辑+编码增强）"""
        result = {}
        if not key:
            result['list'] = []
            return result
            
        try:
            # 强力编码关键词，适配所有站点
            key_enc = urllib.parse.quote(key, safe='')
            search_url = f"{self.host}/vodsearch/-------------.html?wd={key_enc}"
            rsp = self.fetch(search_url)
            root = pq(rsp.text)
            
            videos = []
            list_items = root('.stui-vodlist li')
            if not list_items:
                result['list'] = []
                return result
            
            for item in list_items.items():
                vid = item.find('a').attr('href')
                if not vid or not vid.startswith('/vodplay/'):
                    continue
                    
                name = item.find('h4').text().strip()
                img = item.find('a').attr('data-original') or item.find('a').attr('src')
                remark = item.find('.pic-text').text().strip()
                
                if not name or not img:
                    continue
                
                videos.append({
                    "vod_id": vid,
                    "vod_name": name,
                    "vod_pic": self.getFullUrl(img),
                    "vod_remarks": remark
                })
            
            result['list'] = videos
        except Exception as e:
            print(f"搜索失败: {e}")
            result['list'] = []
            
        return result
    def playerContent(self, flag, id, vipFlags):
        """播放页面解析（核心修改：删除getFullUrl+手动修格式+直接返回纯地址）"""
        result = {}
        try:
            print(f"playerContent被调用: flag={flag}, id={id[:50]}...")
            
            # 空值校验
            if not id:
                return result
            
            # 直接返回完整m3u8链接（优先级最高）
            if id.startswith(('http://', 'https://')) and '.m3u8' in id:
                result["parse"] = 0
                result["playUrl"] = ""
                result["url"] = id
                result["header"] = self.header
                print(f"直接返回m3u8链接")
                return result
            
            # 解析多线路格式（#分隔）- 核心修改：删除getFullUrl+手动修格式
            if '#' in id:
                play_sources = id.split('#')
                for source in play_sources:
                    if '$' in source:
                        _, url = source.split('$', 1)
                        url = url.strip().replace('\\/', '/')  # 处理转义符
                        if url and ('.m3u8' in url or url.startswith(('http://', 'https://'))):
                            result["parse"] = 0
                            result["playUrl"] = ""
                            result["url"] = url  # 直接返回，不拼接主机
                            result["header"] = self.header
                            print(f"从播放线路提取到有效链接")
                            return result
            
            # 兜底：重新解析详情页 - 核心修改：删除getFullUrl+手动修格式
            print(f"重新解析详情页获取播放链接")
            detail_result = self.detailContent([id])
            if detail_result and 'list' in detail_result and detail_result['list']:
                vod = detail_result['list'][0]
                play_url = vod.get('vod_play_url', '')
                if play_url and '#' in play_url:
                    play_sources = play_url.split('#')
                    for source in play_sources:
                        if '$' in source:
                            _, url = source.split('$', 1)
                            url = url.strip().replace('\\/', '/')  # 处理转义符
                            if url and '.m3u8' in url:
                                result["parse"] = 0
                                result["playUrl"] = ""
                                result["url"] = url  # 直接返回，不拼接主机
                                result["header"] = self.header
                                print(f"从详情页重新提取到m3u8")
                                return result
            
            print("无法提取有效播放链接")
            return {}
            
        except Exception as e:
            print(f"解析播放页面失败: {e}")
            import traceback
            traceback.print_exc()
            return {}
    def getFullUrl(self, url):
        """获取完整URL（核心增强：基于formatHost，仅用于分类/封面/页面路径）"""
        if not url:
            return ""
        if url.startswith(('http://', 'https://')):
            return url
        if url.startswith('//'):
            return f"https:{url}"
        # 基于格式化后的host拼接，避免//问题
        return f"{self.host}{url if url.startswith('/') else '/' + url}"
    # 基础配置
    config = {
        "player": {},
        "filter": {}
    }
    # 初始请求头（Referer会在__init__中动态更新）
    header = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        "Referer": "",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Connection": "keep-alive"
    }
    def localProxy(self, param):
        action = {}
        return action
