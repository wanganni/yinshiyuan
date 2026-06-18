# coding=utf-8
import re
from urllib.parse import urljoin
from base.spider import Spider

class Spider(Spider):
    def getName(self):
        return "PaPa视频"

    def init(self, extend=""):
        # 建议动态配置或确保此 host 正确
       # 地址发布http://5zmcsxkys1.744tv.com
        self.host = "http://202601.duduo.vip" 
        self.headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            "Referer": self.host
        }

    def homeContent(self, filter):
        # 根据图片 1000202100.jpg 准确提取分类 ID
        result = {}
        classes = [
            {'type_name': '国产', 'type_id': '20'},
            {'type_name': '无码', 'type_id': '21'},
            {'type_name': '字幕', 'type_id': '22'},
            {'type_name': '欧美', 'type_id': '23'},
            {'type_name': '三级', 'type_id': '24'},
            {'type_name': '动漫', 'type_id': '25'}
        ]
        result['class'] = classes
        return result

    def _parse_vod_list(self, root):
        """公共解析逻辑：根据图片 1000202101.jpg 的 stui-vodlist 结构"""
        videos = []
        # 定位 li 容器，类名为 stui-vodlist__item
        items = root.xpath("//li[contains(@class,'stui-vodlist__item')]")
        for item in items:
            try:
                # 1. 提取标题：从 h4 标签下的 a 标签获取
                name = item.xpath(".//h4[contains(@class,'title')]/a/text()")[0].strip()
                
                # 2. 提取链接并截取 ID：从 href="/6/index.php/vod/play/id/116255..." 中提取 116255
                href = item.xpath(".//h4[contains(@class,'title')]/a/@href")[0]
                vid = re.search(r'id/(\d+)', href).group(1)
                
                # 3. 提取图片：优先获取 data-original (懒加载地址)
                pic = item.xpath(".//a[contains(@class,'thumb')]/@data-original")
                if not pic:
                    pic = item.xpath(".//a[contains(@class,'thumb')]/@src")
                pic_url = urljoin(self.host, pic[0]) if pic else ""
                
                # 4. 提取副标题/备注（如：点击播放 或 时长）
                remark = item.xpath(".//span[contains(@class,'pic-text')]/text()")
                
                videos.append({
                    "vod_id": vid,
                    "vod_name": name,
                    "vod_pic": pic_url,
                    "vod_remarks": remark[0].strip() if remark else ""
                })
            except Exception:
                continue
        return videos

    def homeVideoContent(self):
        # 首页通常展示最新更新
        rsp = self.fetch(f"{self.host}/6/index.php", headers=self.headers)
        root = self.html(self.cleanText(rsp.text))
        return {'list': self._parse_vod_list(root)}

    def categoryContent(self, tid, pg, filter, extend):
        # 根据图片 1000202100.jpg 的链接格式拼接
        # 格式示例：/6/index.php/vod/type/id/20.html
        url = f"{self.host}/6/index.php/vod/type/id/{tid}/page/{pg}.html"
        rsp = self.fetch(url, headers=self.headers)
        root = self.html(self.cleanText(rsp.text))
        return {'list': self._parse_vod_list(root), 'page': pg}

    def detailContent(self, array):
        vid = array[0]
        # 直接构造播放页地址 (根据图片 1000202101.jpg 逻辑)
        # 苹果CMS通常播放地址是 /vod/play/id/{vid}/sid/1/nid/1.html
        play_url = f"{self.host}/6/index.php/vod/play/id/{vid}/sid/1/nid/1.html"
        
        # 详情页信息通常需要再次请求 vid 对应的 detail 页面，这里简单处理直接跳播放
        vod = {
            "vod_id": vid,
            "vod_name": "视频详情",
            "vod_play_from": "PaPa线路",
            "vod_play_url": f"点击播放${play_url}"
        }
        return {'list': [vod]}

    def searchContent(self, key, quick, pg):
        url = f"{self.host}/6/index.php/vod/search/page/{pg}/wd/{key}.html"
        rsp = self.fetch(url, headers=self.headers)
        root = self.html(self.cleanText(rsp.text))
        return {'list': self._parse_vod_list(root), 'page': pg}

    def playerContent(self, flag, id, vipFlags):
        # 此类网站通常需要 web 嗅探
        return {
            "parse": 1, 
            "url": id,
            "header": self.headers
        }
