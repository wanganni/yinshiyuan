# -*- coding: utf-8 -*-
import copy
import gzip
import json
import re
import time
import uuid
import requests
from base64 import b64decode
from Crypto.Hash import SHA1, HMAC
from pyquery import PyQuery as pq
import os

class MissAVSpider:
    def __init__(self, site="https://missav.com", cfproxy="", plp=""):
        self.host = site
        self.cfproxy = cfproxy
        self.plp = plp
        self.proxy = {}
        self.xhost = 'https://client-rapi-missav.recombee.com'
        self.countr = '/dm15/cn'
        
        self.headers = {
            'referer': f'{self.host}',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'
        }
        
        # 压缩的分类数据
        self.ccccc = 'H4sIAAAAAAAAA4uuViqpLEiNz0vMTVWyUlB6Nqfhxf6Jz2ZveTZtg5IORC4zBSSTkmtqaKKfnKefl1quVKuDrm/ahid75zzZ0fV0RxOGPgsLkL6i1JzUxOJULHqnL3i+oPHZ1san7bvQ9ZoZGYL0luYlp+YV5xelpugCDcnGNOPp0s1P9sx4sqPhxfIOVDOAuhOTS4pSi4tTizH1Pd+4++m8bgwd6al5RdiUP+2f+GJhz9OpbRg6chOzU4uAOmIBkkRrDlIBAAA='
        self.fts = 'H4sIAAAAAAAAA23P30rDMBQG8FeRXM8X8FVGGZk90rA0HU3SMcZgXjn8V6p2BS2KoOiFAwUn2iK+TBP7GBpYXbG9/c6Pc77TnaABjNHOFtojVIDPUQcx7IJJvl9ydX30GwSYSpN0J4iZgTqJiywrPlN1vm/GJiPMJgGxJaZo2qnc3WXDuZIKMqSwUcX7Ui8O1DJRH3Gldh3CgMM2l31BhNGW8euq3PNFrac+PVNZ2NYzjMrbY53c6/Sm2uwDBczB7mGxqaDTWfkV6atXvXiu4FD2KeHOf3nxViahjv8YxwHYtWfyQ3NvFZYP85oSno3HvYDAiNevPqnosWFHAAPahnU6b2DXY8Jp0bO8QdfEmlo/SBd5PPUBAAA='
        self.actfts = 'H4sIAAAAAAAAA5WVS2sUQRRG/0rT6xTcqq5Xiwjm/X6sQxZjbBLRBBeOIEGIIEgWrtwI4lJEQsjGhU6Iv2bGcf6FVUUydW/d1SxT55sDfbpmsn9WP+/e1A+q+rh7dnT8qp6rT3snXTz4N7icXH4OB697L/rxZP+sPo1g+Ot8PPg+vvoyOb+IOJ7Vb+fuqGxkJSrZmMOTexiORDjAGxs3GvDGinCANjp5NPbo4NHYo5NHYI8OHoM9JnkM9pjgMdhjksdijwkeiz02eSz22OCx2GOTx2GPDR6HPS55HPa44HHY45LHY48LHo89Pnk89vjg8djjk6fFHh88bfAcxNXduz/sv0Qvfnz74+/X65lf/OMqfzD9ndF8geYzWijQQkaLBVrMaKlASxktF2g5o5UCrWS0WqDVjNYKtJbReoHWM9oo0EZGmwXazGirQFsZbRdoO6OdAu1ktFug3Yz2CrRH70TvqEN3YvT75+TP+5nvxMNKwf0pCIWur4JwM5spVCAaRJtI9ZQ2IPBPg47UTKkGgb/wJlI7pQYE/ho/QsiCaFv61E+7J338Izj6MJi8+xSefnhzO/PTK1CmGt58G118zM+pDBloPtBk0PBBQwaKDxQZSD6QZAB8QN6UbNlAtmTg+cCTgeMDRwaWDywZ8JKSlJS8pCQlJS8pSUnJS0pSUvKSkpSUvKQkJYGXBFISeEkgJYGXBFISeEkgJYGXBFISeEkgJYGXBFISeEkgJYGXBFISeElI/7QO/gOZ7bAksggAAA=='

    def ungzip(self, data):
        """解压gzip数据"""
        result = gzip.decompress(b64decode(data)).decode('utf-8')
        return json.loads(result)

    def getsign(self, text):
        """生成签名"""
        message_bytes = text.encode('utf-8')
        key_bytes = b'Ikkg568nlM51RHvldlPvc2GzZPE9R4XGzaH9Qj4zK9npbbbTly1gj9K4mgRn0QlV'
        h = HMAC.new(key_bytes, digestmod=SHA1)
        h.update(message_bytes)
        signature = h.hexdigest()
        return signature

    def get_categories(self):
        """获取所有分类"""
        print("正在获取分类列表...")
        try:
            categories = self.ungzip(self.ccccc)
            print(f"成功获取 {len(categories)} 个分类")
            return categories
        except Exception as e:
            print(f"获取分类失败: {e}")
            return []

    def get_videos_by_category_page(self, tid, page):
        """获取指定分类和页面的视频列表"""
        print(f"  正在获取分类 {tid} 第 {page} 页...")
        
        params = {'page': page}
        url = f"{self.host}/{tid}"
        
        try:
            if self.cfproxy:
                url = f"{self.cfproxy}{url}"
            
            response = requests.get(url, params=params, headers=self.headers, proxies=self.proxy)
            response.raise_for_status()
            
            data = pq(response.content)
            videos = []
            
            # 根据分类类型使用不同的解析方法
            if tid in ['cn/genres', 'cn/makers']:
                videos = self.parse_gmsca(data)
            elif tid == 'cn/actresses':
                videos = self.parse_actca(data)
            else:
                videos = self.parse_video_list(data('.grid-cols-2.md\\:grid-cols-3 .thumbnail.group'))
            
            print(f"    获取到 {len(videos)} 个视频")
            return videos
            
        except Exception as e:
            print(f"获取分类 {tid} 第 {page} 页失败: {e}")
            return []

    def parse_video_list(self, data):
        """解析视频列表"""
        videos = []
        names, ids = [], []
        
        for i in data.items():
            k = i('.overflow-hidden.shadow-lg a')
            id = k.eq(0).attr('href')
            name = i('.text-secondary').text()
            
            if id and id not in ids and name not in names:
                ids.append(id)
                names.append(name)
                videos.append({
                    'vod_id': id.split('/', 3)[-1],
                    'vod_name': name,
                    'vod_pic': k.eq(0)('img').attr('data-src'),
                    'vod_year': '' if len(list(k.items())) < 3 else k.eq(1).text(),
                    'vod_remarks': k.eq(-1).text()
                })
        
        return videos

    def parse_gmsca(self, data):
        """解析类型和制造商页面"""
        acts = []
        for i in data('.grid.grid-cols-2.md\\:grid-cols-3 div').items():
            id = i('.text-nord13').attr('href')
            if id:
                acts.append({
                    'vod_id': id.split('/', 3)[-1],
                    'vod_name': i('.text-nord13').text(),
                    'vod_pic': '',
                    'vod_remarks': i('.text-nord10').text()
                })
        return acts

    def parse_actca(self, data):
        """解析女优页面"""
        acts = []
        for i in data('.max-w-full ul li').items():
            id = i('a').attr('href')
            if id:
                acts.append({
                    'vod_id': id.split('/', 3)[-1],
                    'vod_name': i('img').attr('alt'),
                    'vod_pic': i('img').attr('src'),
                    'vod_year': i('.text-nord10').eq(-1).text(),
                    'vod_remarks': i('.text-nord10').eq(0).text()
                })
        return acts

    def get_video_play_url(self, video_id):
        """获取视频播放链接"""
        print(f"    正在获取视频播放链接: {video_id}")
        
        try:
            url = f"{self.cfproxy}{self.host}/{video_id}" if self.cfproxy else f"{self.host}/{video_id}"
            response = requests.get(url, headers=self.headers, proxies=self.proxy)
            response.raise_for_status()
            
            v = pq(response.content)
            sctx = v('body script').text()
            
            # 尝试从JavaScript中提取播放链接
            play_url = self.extract_play_url_from_js(sctx)
            if play_url:
                return play_url
            
            # 如果无法提取，返回嗅探链接
            return f"嗅探${url}"
            
        except Exception as e:
            print(f"获取视频 {video_id} 播放链接失败: {e}")
            return None

    def extract_play_url_from_js(self, jstxt):
        """从JavaScript代码中提取播放链接"""
        try:
            # 这里简化处理，实际可能需要更复杂的JS解析
            # 查找可能的m3u8链接
            m3u8_pattern = r'https?://[^\s"\']+\.m3u8[^\s"\']*'
            matches = re.findall(m3u8_pattern, jstxt)
            if matches:
                return f"多画质${matches[0]}"
            
            # 查找其他视频链接
            video_pattern = r'https?://[^\s"\']+\.(mp4|m3u8|avi|mkv|flv)[^\s"\']*'
            matches = re.findall(video_pattern, jstxt)
            if matches:
                return f"直接播放${matches[0]}"
                
        except Exception as e:
            print(f"解析JavaScript失败: {e}")
        
        return None

    def crawl_all_videos(self, max_pages_per_category=10):
        """爬取所有分类的所有视频"""
        print("开始爬取MissAV视频...")
        
        # 获取所有分类
        categories = self.get_categories()
        if not categories:
            print("无法获取分类，程序退出")
            return {}
            
        all_results = {}
        
        # 遍历每个分类
        for category in categories:
            category_name = category['type_name']
            category_id = category['type_id']
            
            print(f"\n正在爬取分类: {category_name} ({category_id})")
            all_results[category_name] = []
            
            # 遍历页数
            for page in range(1, max_pages_per_category + 1):
                videos = self.get_videos_by_category_page(category_id, page)
                
                if not videos:
                    print(f"  第 {page} 页没有数据，停止获取该分类")
                    break
                
                # 获取每个视频的播放链接
                for i, video in enumerate(videos):
                    print(f"    正在处理第 {i+1}/{len(videos)} 个视频: {video['vod_name'][:30]}...")
                    play_url = self.get_video_play_url(video['vod_id'])
                    
                    if play_url:
                        all_results[category_name].append({
                            'title': video['vod_name'],
                            'play_url': play_url,
                            'video_id': video['vod_id'],
                            'remarks': video.get('vod_remarks', ''),
                            'year': video.get('vod_year', '')
                        })
                    else:
                        print(f"      获取播放链接失败: {video['vod_name']}")
                
                # 添加延迟避免请求过快
                time.sleep(1)
                
            print(f"分类 {category_name} 爬取完成，共 {len(all_results[category_name])} 个视频")
                
        return all_results

    def save_to_txt(self, data, filename="missav_videos.txt"):
        """保存数据到txt文件，格式为：分类名,#genre#"""
        print(f"\n正在保存数据到 {filename}...")
        
        total_videos = 0
        with open(filename, 'w', encoding='utf-8') as f:
            for category_name, videos in data.items():
                if videos:  # 只保存有视频的分类
                    total_videos += len(videos)
                    # 写入分类行
                    f.write(f"{category_name},#genre#\n")
                    
                    # 写入该分类下的所有视频
                    for video in videos:
                        # 清理标题中的特殊字符
                        title = video['title'].replace(',', '，').replace('\n', ' ')
                        # 格式：视频标题,播放链接
                        f.write(f"{title},{video['play_url']}\n")
                    
                    f.write("\n")  # 分类之间空一行
        
        print(f"数据保存完成！共保存 {len(data)} 个分类，{total_videos} 个视频")

def main():
    # 配置参数
    config = {
        'site': 'https://missav.com',
        'cfproxy': '',  # 如果需要代理可以在这里设置
        'plp': ''       # 播放代理
    }
    
    try:
        # 创建爬虫实例
        spider = MissAVSpider(
            site=config['site'],
            cfproxy=config['cfproxy'],
            plp=config['plp']
        )
        
        # 开始爬取（每个分类最多爬取5页，避免请求过多）
        all_videos = spider.crawl_all_videos(max_pages_per_category=5)
        
        # 保存结果
        if all_videos:
            spider.save_to_txt(all_videos)
            print("\n爬取完成！")
        else:
            print("没有获取到任何视频数据")
            
    except Exception as e:
        print(f"程序运行出错: {e}")

if __name__ == "__main__":
    main()