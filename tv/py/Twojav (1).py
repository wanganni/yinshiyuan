import sys
import os
class Spider():
    def getName(self):
        return "Twojav"

    def init(self, extend=""):
        pass

    def homeContent(self, filter):
        # 预留给稍后的测试：抓取首页分类和推荐
        result = {}
        cateManual = {
            "有码": "censored",
            "无码": "uncensored",
            "素人": "amateur",
            "VR": "vr"
        }
        classes = []
        for k in cateManual:
            classes.append({
                'type_name': k,
                'type_id': cateManual[k]
            })
        result['class'] = classes
        return result

    def getDependence(self):
        return []

    def init(self, extend=""):
        pass

    def homeVideoContent(self):
        import re
        import requests
        url = "https://twojav.com/cn"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        try:
            res = requests.get(url, headers=headers, timeout=10)
            res.encoding = 'utf-8'
            html = res.text
            vod_list = []
            pattern = r'video-card">.*?href="/cn/v/(?P<id>[^"]+)".*?background-image: url\(\'(?P<pic>[^\']+)\'\).*?class="title">(?P<name>.*?)</a>'
            matches = re.finditer(pattern, html, re.S)
            for m in matches:
                vod_list.append({
                    "vod_id": m.group('id'),
                    "vod_name": m.group('name').strip(),
                    "vod_pic": m.group('pic'),
                    "vod_remarks": "高清"
                })
            return {"list": vod_list}
        except Exception as e:
            return {"list": [], "msg": str(e)}
        import re
        import requests
        url = "https://twojav.com/cn"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        try:
            res = requests.get(url, headers=headers, timeout=10)
            res.encoding = 'utf-8'
            html = res.text
            vod_list = []
            # 修正后的正则：匹配链接ID、封面图URL和标题
            # 结构：<a href="/cn/v/(?P<id>.*?)".*?background-image: url\('(?P<pic>.*?)'\).*?class="title">(?P<name>.*?)</a>
            pattern = r'video-card">.*?href="/cn/v/(?P<id>[^"]+)".*?background-image: url\(\'(?P<pic>[^\']+)\'\).*?class="title">(?P<name>.*?)</a>'
            matches = re.finditer(pattern, html, re.S)
            for m in matches:
                vod_list.append({
                    "vod_id": m.group('id'),
                    "vod_name": m.group('name').strip(),
                    "vod_pic": m.group('pic'),
                    "vod_remarks": "高清"
                })
            return {"list": vod_list}
        except Exception as e:
            return {"list": [], "msg": str(e)}
        import re
        import requests
        url = "https://twojav.com/cn"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        try:
            res = requests.get(url, headers=headers, timeout=10)
            html = res.text
            vod_list = []
            # 匹配视频项：包含 ID、标题、封面
            pattern = r'href="/cn/movie/(?P<id>[^"]+)" title="(?P<name>[^"]+)".*?data-src="(?P<pic>[^"]+)"'
            matches = re.finditer(pattern, html, re.S)
            for m in matches:
                vod_list.append({
                    "vod_id": m.group('id'),
                    "vod_name": m.group('name'),
                    "vod_pic": m.group('pic'),
                    "vod_remarks": "高清"
                })
            return {"list": vod_list}
        except Exception as e:
            return {"list": [], "msg": str(e)}
        import re
        # 这里模拟调用之前 http_request 的逻辑，实际开发中通常在类内定义 fetch 方法
        url = "https://twojav.com/cn"
        # 假设环境已提供简单的请求能力，或通过 py_exec 注入
        # 为了演示稳定性，我们先用正则处理之前获取到的 HTML 片段
        html = """之前获取到的HTML片段...""" 
        
        vod_list = []
        # 匹配视频项的正则示例
        pattern = r'<a href="/cn/movie/(?P<id>.*?)".*?title="(?P<name>.*?)".*?data-src="(?P<pic>.*?)"'
        matches = re.finditer(pattern, html)
        for m in matches:
            vod_list.append({
                "vod_id": m.group('id'),
                "vod_name": m.group('name'),
                "vod_pic": m.group('pic'),
                "vod_remarks": "高清"
            })
        return {"list": vod_list}

    def categoryContent(self, tid, pg, filter, extend):
        import re
        import requests
        # 兼容不同分类的 URL 构造
        url = f"https://twojav.com/cn/{tid}?page={pg}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://twojav.com/cn'
        }
        try:
            res = requests.get(url, headers=headers, timeout=10)
            res.encoding = 'utf-8'
            html = res.text
            
            vod_list = []
            # 使用更宽容的正则，去掉对 video-grid 容器的依赖，直接抓取 video-card
            pattern = r'video-card">.*?href="/cn/v/(?P<id>[^"]+)".*?background-image: url\(\'(?P<pic>[^\']+)\'\).*?class="title">(?P<name>.*?)</a>'
            matches = re.finditer(pattern, html, re.S)
            
            for m in matches:
                vod_list.append({
                    "vod_id": m.group('id'),
                    "vod_name": m.group('name').strip(),
                    "vod_pic": m.group('pic'),
                    "vod_remarks": f"第{pg}页"
                })
            
            return {
                "page": pg,
                "pagecount": 999,
                "limit": len(vod_list),
                "total": 9999,
                "list": vod_list
            }
        except Exception as e:
            return {"list": [], "msg": f"分类抓取失败: {str(e)}"}
        import re
        import requests
        # tid: censored, uncensored, amateur, vr 等
        url = f"https://twojav.com/cn/{tid}/{pg}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        try:
            res = requests.get(url, headers=headers, timeout=10)
            res.encoding = 'utf-8'
            html = res.text
            vod_list = []
            # 复用 homeVideoContent 的正则逻辑
            pattern = r'video-card">.*?href="/cn/v/(?P<id>[^"]+)".*?background-image: url\(\'(?P<pic>[^\']+)\'\).*?class="title">(?P<name>.*?)</a>'
            matches = re.finditer(pattern, html, re.S)
            for m in matches:
                vod_list.append({
                    "vod_id": m.group('id'),
                    "vod_name": m.group('name').strip(),
                    "vod_pic": m.group('pic'),
                    "vod_remarks": "高清"
                })
            return {
                "page": pg,
                "pagecount": 99,  # 暂时硬编码或解析最大页数
                "limit": len(vod_list),
                "total": 999,
                "list": vod_list
            }
        except Exception as e:
            return {"list": [], "msg": str(e)}
        pass

    def detailContent(self, array):
        import re
        import requests
        tid = array[0]
        url = f"https://twojav.com/cn/v/{tid}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        try:
            res = requests.get(url, headers=headers, timeout=10)
            res.encoding = 'utf-8'
            html = res.text
            
            title = re.search(r'<h1>(.*?)</h1>', html)
            pic = re.search(r'background-image: url\(\'(.*?)\'\)', html)
            # 提取 JS 中的 m3u8 地址
            m3u8_match = re.search(r"let currentAddress\s*=\s*'(.*?)';", html)
            play_url = m3u8_match.group(1) if m3u8_match else ""
            
            vod = {
                "vod_id": tid,
                "vod_name": title.group(1).strip() if title else tid,
                "vod_pic": pic.group(1) if pic else "",
                "vod_play_from": "Twojav",
                "vod_play_url": f"HLS播放${play_url}" 
            }
            return {"list": [vod]}
        except Exception as e:
            return {"list": [], "msg": str(e)}
        import re
        import requests
        tid = array[0]
        url = f"https://twojav.com/cn/v/{tid}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        try:
            res = requests.get(url, headers=headers, timeout=10)
            res.encoding = 'utf-8'
            html = res.text
            
            # 解析基本信息（标题、图片等）
            title = re.search(r'<h1>(.*?)</h1>', html)
            pic = re.search(r'background-image: url\(\'(.*?)\'\)', html)
            
            # 详情页通常包含播放地址，TVBox 格式：线路名$播放ID
            # 我们先假设播放 ID 就是当前的 tid，或者是页面里的某个 play_url
            vod = {
                "vod_id": tid,
                "vod_name": title.group(1) if title else tid,
                "vod_pic": pic.group(1) if pic else "",
                "vod_play_from": "Twojav",
                "vod_play_url": f"立即播放${tid}" 
            }
            return {"list": [vod]}
        except Exception as e:
            return {"list": [], "msg": str(e)}
        pass

    def searchContent(self, keyword, quick, pg):
        import re
        import requests
        from urllib.parse import quote
        url = f"https://twojav.com/cn/search?q={quote(keyword)}&page={pg}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://twojav.com/cn',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive'
        }
        try:
            # 使用 Session 保持并尝试绕过简单的频率限制
            session = requests.Session()
            res = session.get(url, headers=headers, timeout=15)
            res.encoding = 'utf-8'
            html = res.text
            
            vod_list = []
            # 兼容首页和搜索页的通用正则
            pattern = r'video-card">.*?href="/cn/v/(?P<id>[^"]+)".*?background-image: url\(\'(?P<pic>[^\']+)\'\).*?class="title">(?P<name>.*?)</a>'
            matches = re.finditer(pattern, html, re.S)
            for m in matches:
                vod_list.append({
                    "vod_id": m.group('id'),
                    "vod_name": m.group('name').strip(),
                    "vod_pic": m.group('pic'),
                    "vod_remarks": "搜索结果"
                })
            return {"list": vod_list}
        except Exception as e:
            # 即使失败也返回空列表而非崩溃
            return {"list": [], "msg": f"抓取失败: {str(e)}"}
        import re
        import requests
        from urllib.parse import quote
        url = f"https://twojav.com/cn/search?q={quote(keyword)}&page={pg}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        try:
            res = requests.get(url, headers=headers, timeout=10)
            res.encoding = 'utf-8'
            html = res.text
            vod_list = []
            pattern = r'video-card">.*?href="/cn/v/(?P<id>[^"]+)".*?background-image: url\(\'(?P<pic>[^\']+)\'\).*?class="title">(?P<name>.*?)</a>'
            matches = re.finditer(pattern, html, re.S)
            for m in matches:
                vod_list.append({
                    "vod_id": m.group('id'),
                    "vod_name": m.group('name').strip(),
                    "vod_pic": m.group('pic'),
                    "vod_remarks": "搜索结果"
                })
            return {"list": vod_list}
        except Exception as e:
            return {"list": [], "msg": str(e)}
        pass

    def playerContent(self, flag, id, vipFlags):
        # 这里的 id 已经是解析出来的 m3u8 URL 了
        return {
            "parse": 0,
            "url": id,
            "header": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        }
        pass