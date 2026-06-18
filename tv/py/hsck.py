# coding=utf-8
#!/usr/bin/python
import sys
import re
import urllib.parse
import json
import requests
from pyquery import PyQuery as pq

sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def getName(self):
        return "黄色仓库(完美去广告)"

    def init(self, extend):
        print("=============黄色仓库初始化===========")
        self.host = "https://huangsecangku.net"
        print(f"当前固定域名: {self.host}")

    def homeContent(self, filter):
        result = {}
        cateManual = [
            {"type_name": "国产视频", "type_id": "2"},
            {"type_name": "日韩AV", "type_id": "1"},
            {"type_name": "欧美视频", "type_id": "3"},
            {"type_name": "强奸乱伦", "type_id": "4"},
            {"type_name": "日本有码", "type_id": "7"},
            {"type_name": "无码专区", "type_id": "8"},
            {"type_name": "中文字幕", "type_id": "9"}
        ]
        result['class'] = cateManual
        return result

    def homeVideoContent(self):
        try:
            url = f'{self.host}/vodtype/2-1.html'
            print(f"首页加载: {url}")
            videos = self.getVideos(url)
            return {'list': videos}
        except Exception as e:
            print(f"首页解析失败: {e}")
            return {'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        url = f'{self.host}/vodtype/{tid}-{pg}.html'
        videos = self.getVideos(url)
        
        result['list'] = videos
        result['page'] = int(pg)
        result['pagecount'] = 9999
        result['limit'] = 20
        result['total'] = 999999
        return result

    def detailContent(self, array):
        tid = array[0]
        if tid.startswith('http'):
            url = tid
        else:
            url = f'{self.host}{tid}'
            
        print(f"解析详情: {url}")
        rsp = self.fetch(url) 
        html = rsp.text
        
        video = self.getDetail(html)
        play_url = self.getPlayUrl(html)
        
        playFrom = ['黄色仓库']
        playList = [f"点击播放${play_url}"] if play_url else []

        result = {
            'list': [
                {
                    'vod_id': tid,
                    'vod_name': video['title'],
                    'vod_pic': video['pic'],
                    'type_name': "HSCK",
                    'vod_remarks': video['remarks'],
                    'vod_content': video['content'],
                    'vod_play_from': '$$$'.join(playFrom),
                    'vod_play_url': '$$$'.join(playList)
                }
            ]
        }
        return result

    def searchContent(self, key, quick, page='1'):
        result = {}
        url = f'{self.host}/vodsearch/-------------.html?wd={urllib.parse.quote(key)}'
        videos = self.getVideos(url)
        result['list'] = videos
        return result

    def playerContent(self, flag, id, vipFlags):
        result = {}
        result["parse"] = 0
        result["playUrl"] = ''
        result["url"] = id
        result["header"] = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }
        return result

    # ================= 辅助函数 =================

    def fetch(self, url):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }
        try:
            r = requests.get(url, headers=headers, verify=False, timeout=10)
            r.encoding = 'utf-8'
            return r
        except Exception as e:
            print(f"Fetch Error: {e}")
            return None

    def getVideos(self, url):
        """列表解析（完美去广告版）"""
        videos = []
        # 【修改点】新增"抖音"、"快手"、"白狐"等关键词
        banned_keywords = [
            "澳门", "葡京", "充值", "彩金", "博彩", "娱乐城", 
            "APP", "下载", "直播", "荷官", "群", "QQ", "微信", 
            "代理", "招募", "招聘", "站长", "推荐", "空降", 
            "选妃", "上门", "同城", "约炮", "更有", "专属",
            "安全跳转", "网址", "地址", "回家", "官方", "邀请",
            "抖音", "快手", "白狐", "点我"
        ]

        try:
            rsp = self.fetch(url)
            if not rsp: return []
            
            html = rsp.text
            root = pq(html)
            
            items = root('.stui-vodlist li, .myui-vodlist li, .module-item, .vodlist li')
            
            # 暴力提取备用逻辑
            if len(items) == 0:
                print("常规解析为空，尝试暴力提取...")
                links = root('a')
                seen = set()
                for link in links.items():
                    href = link.attr('href')
                    if href and ('/vodplay/' in href or '/play/' in href) and href not in seen:
                        seen.add(href)
                        title = link.attr('title') or link.text() or ""
                        
                        if any(k in title for k in banned_keywords):
                            continue

                        img_tag = link.find('img')
                        if not img_tag: img_tag = link.parent().find('img')
                        img = img_tag.attr('data-original') or img_tag.attr('src') or ""
                        
                        if title:
                            videos.append({
                                "vod_id": href,
                                "vod_name": title,
                                "vod_pic": self.getFullUrl(img),
                                "vod_remarks": "直接解析"
                            })
                return videos

            # 常规解析逻辑
            for item in items.items():
                link = item.find('a').attr('href')
                if not link: continue
                
                title = item.find('a').attr('title') or item.find('h4').text()
                if not title: continue 

                # 【修改点】过滤包含黑名单关键词的标题
                if any(k in title for k in banned_keywords):
                    print(f"过滤广告: {title}")
                    continue

                img = item.find('a').attr('data-original') or item.find('a').attr('src') or item.find('img').attr('src')
                remarks = item.find('.pic-text').text() or item.find('.pic-tag').text()
                
                videos.append({
                    "vod_id": link,
                    "vod_name": title,
                    "vod_pic": self.getFullUrl(img),
                    "vod_remarks": remarks
                })
        except Exception as e:
            print(f"列表解析出错: {e}")
            
        return videos

    def getDetail(self, html):
        root = pq(html)
        detail = { 'title': '', 'pic': '', 'content': '', 'remarks': '' }
        try:
            detail['title'] = root('h1').text() or root('title').text()
            img = root('.stui-vodlist__thumb').attr('data-original') or root('img.lazy').attr('src')
            if img: detail['pic'] = self.getFullUrl(img)
            detail['content'] = root('.stui-pannel_bd').text() or detail['title']
        except: pass
        return detail

    def getPlayUrl(self, html):
        play_url = ''
        try:
            match = re.search(r'player_aaaa\s*=\s*({.*?})', html)
            if match:
                data = json.loads(match.group(1))
                return self.getFullUrl(data.get('url', ''))
            
            urls = re.findall(r'["\']([^"\']+\.m3u8[^"\']*)["\']', html)
            if urls: return self.getFullUrl(urls[0])
            
            raw_urls = re.findall(r'http[s]?://[^\s"\'<>]+\.m3u8', html)
            if raw_urls: return raw_urls[0]
        except: pass
        return play_url

    def getFullUrl(self, url):
        if not url: return ""
        if url.startswith("http"): return url
        if url.startswith("//"): return "https:" + url
        return self.host + url

    def isVideoFormat(self, url): pass
    def manualVideoCheck(self): pass
    def localProxy(self, param): return []
