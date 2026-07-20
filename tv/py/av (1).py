# -*- coding: utf-8 -*-
# 123AV短视频 - Fongmi影视App适配爬虫
# 优化为短视频模式，支持滑动切换

import sys
import re
import json
import urllib.parse
sys.path.append('..')
from base.spider import Spider


class Spider(Spider):
    def getName(self):
        return "123AV"

    def init(self, extend=''):
        self.home_url = 'https://123av.fun'
        self.ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

    def getDependence(self):
        return []

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def homeContent(self, filter):
        return {
            'class': [
                {'type_id': 'publish-time/sort-desc', 'type_name': '最新发布'},
                {'type_id': 'view-count/sort-desc', 'type_name': '最多播放'},
                {'type_id': 'comment-count/sort-desc', 'type_name': '最多评论'},
                {'type_id': 'favorite-count/sort-desc', 'type_name': '最多收藏'},
                {'type_id': 'explore', 'type_name': '探索发现'},
                {'type_id': 'list', 'type_name': '排行榜'},
            ],
            'filters': {}
        }

    def homeVideoContent(self):
        return self.categoryContent('publish-time/sort-desc', 1, {}, {})

    def _fetch_html(self, url):
        try:
            rsp = self.fetch(url, headers={
                "User-Agent": self.ua,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9",
            }, timeout=15)
            if rsp and hasattr(rsp, 'text') and rsp.text:
                return rsp.text
        except Exception as e:
            print(f'fetch error: {e}')
        return ''

    def _extract_video_list(self, html):
        videos = []
        if not html:
            return videos

        # 匹配视频卡片
        card_pattern = re.compile(
            r'<a\s+([^>]*data-src="https://static\.123av\.fun/[^"]+\.m3u8"[^>]*)>(.*?)</a>',
            re.S
        )
        
        cards = card_pattern.findall(html)
        
        for attrs, content in cards:
            try:
                src_match = re.search(r'data-src="(https://static\.123av\.fun/[^"]+\.m3u8)"', attrs)
                poster_match = re.search(r'data-poster="([^"]*)"', attrs)
                id_match = re.search(r'data-id="(\d+)"', attrs)
                dur_match = re.search(r'data-duration="(\d+)"', attrs)
                
                title_match = re.search(r'<xwya-video[^>]*alt="([^"]*)"', content)
                
                if src_match and id_match:
                    m3u8_url = src_match.group(1)
                    vid = id_match.group(1)
                    poster = poster_match.group(1) if poster_match else ''
                    duration = dur_match.group(1) if dur_match else '0'
                    title = title_match.group(1).strip() if title_match else f'视频{vid}'
                    
                    dur = int(duration)
                    if dur >= 3600:
                        duration_str = f'{dur // 3600}:{(dur % 3600) // 60:02d}:{dur % 60:02d}'
                    else:
                        duration_str = f'{dur // 60:02d}:{dur % 60:02d}'
                    
                    videos.append({
                        'vod_id': vid,
                        'vod_name': title,
                        'vod_pic': poster,
                        'vod_remarks': duration_str,
                    })
            except Exception as e:
                continue

        return videos

    def categoryContent(self, tid, page, filter, ext):
        video_list = []
        
        if tid in ('explore', 'list', 'subscribe'):
            url = f'{self.home_url}/{tid}/page-{page}'
        else:
            url = f'{self.home_url}/{tid}/page-{page}'
        
        html = self._fetch_html(url)
        video_list = self._extract_video_list(html)

        return {
            'list': video_list,
            'page': int(page),
            'pagecount': 999,
            'limit': 20,
            'total': 999 * 20
        }

    def detailContent(self, did):
        """视频详情 - 关键修改：返回播放URL让playerContent处理"""
        video_list = []
        try:
            vid = did[0]
            detail_url = f'{self.home_url}/detail/{vid}'
            html = self._fetch_html(detail_url)

            if html:
                src_match = re.search(r'data-src="(https://static\.123av\.fun/[^"]+\.m3u8)"', html)
                poster_match = re.search(r'data-poster="([^"]*)"', html)
                title_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
                if not title_match:
                    title_match = re.search(r'property="og:title"\s+content="([^"]*)"', html)
                if not title_match:
                    title_match = re.search(r'<xwya-video[^>]*alt="([^"]*)"', html)
                
                desc_match = re.search(r'property="og:description"\s+content="([^"]*)"', html)
                dur_match = re.search(r'data-duration="(\d+)"', html)
                
                m3u8_url = src_match.group(1) if src_match else ''
                vod_pic = poster_match.group(1) if poster_match else ''
                vod_name = title_match.group(1).strip() if title_match else ''
                vod_content = desc_match.group(1) if desc_match else ''
                
                duration_str = ''
                if dur_match:
                    dur = int(dur_match.group(1))
                    if dur >= 3600:
                        duration_str = f'{dur // 3600}:{(dur % 3600) // 60:02d}:{dur % 60:02d}'
                    else:
                        duration_str = f'{dur // 60:02d}:{dur % 60:02d}'
            else:
                m3u8_url = ''
                vod_pic = ''
                vod_name = ''
                vod_content = ''
                duration_str = ''

            # 关键修改：如果直接有m3u8，放入播放URL
            # 使用特殊格式让Fongmi识别为短视频
            if m3u8_url:
                # 格式: 集数名称$url#集数名称$url
                vod_play_url = f'正片${m3u8_url}'
            else:
                vod_play_url = ''

            video_list.append({
                'vod_id': vid,
                'vod_name': vod_name,
                'vod_pic': vod_pic,
                'vod_remarks': duration_str,
                'vod_content': vod_content,
                'vod_play_from': '短视频',  # 改为短视频，可能触发滑动模式
                'vod_play_url': vod_play_url,
                'type_name': '短视频',
                'vod_year': '',
                'vod_area': '',
                'vod_director': '',
                'vod_actor': '',
            })

        except Exception as e:
            print(f'detailContent error: {e}')

        return {
            'list': video_list,
            'parse': 0,
            'jx': 0
        }

    def searchContent(self, key, quick, page='1'):
        video_list = []
        try:
            encoded_key = urllib.parse.quote(key)
            url = f'{self.home_url}/search/{encoded_key}/page-{page}'
            html = self._fetch_html(url)
            video_list = self._extract_video_list(html)
        except Exception as e:
            print(f'searchContent error: {e}')

        return {
            'list': video_list,
            'page': int(page),
            'pagecount': 99,
            'limit': 20,
            'total': 99 * 20
        }

    def playerContent(self, flag, pid, vipFlags):
        """播放器内容 - 关键修改"""
        # 如果pid已经是m3u8地址，直接返回
        if pid.startswith('http') and '.m3u8' in pid:
            return {
                'parse': 0,  # 直接播放
                'url': pid,
                'header': {
                    'User-Agent': self.ua,
                    'Referer': self.home_url + '/'
                }
            }

        # 如果是详情页URL，获取m3u8
        if '/detail/' in pid:
            html = self._fetch_html(pid)
            if html:
                src_match = re.search(r'data-src="(https://static\.123av\.fun/[^"]+\.m3u8)"', html)
                if src_match:
                    return {
                        'parse': 0,
                        'url': src_match.group(1),
                        'header': {
                            'User-Agent': self.ua,
                            'Referer': self.home_url + '/'
                        }
                    }

        # 默认返回，让外部解析
        return {
            'parse': 1,
            'url': pid,
            'header': {
                'User-Agent': self.ua,
                'Referer': self.home_url + '/'
            }
        }

    def localProxy(self, params):
        return {}

    def destroy(self):
        return '正在Destroy'


if __name__ == '__main__':
    pass