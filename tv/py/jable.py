import sys, re, requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from base.spider import Spider

requests.packages.urllib3.disable_warnings()

class Spider(Spider):
    def getName(self): return "Jable"

    def init(self, extend=""):
        self.siteUrl = "https://jable.tv"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://jable.tv/",
        }
        self.sess = requests.Session()
        self.sess.mount('https://', HTTPAdapter(max_retries=Retry(total=3, status_forcelist=[500, 502, 503, 504])))

    def fetch(self, url):
        try: return self.sess.get(url, headers=self.headers, timeout=15, verify=False)
        except: return None

    def homeContent(self, filter):
        r = self.fetch(self.siteUrl)
        cats = []
        if r and r.ok:
            # 动态抓取首页的所有 tag 作为分类
            for m in re.finditer(r'<a[^>]+class=["\']tag["\'][^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', r.text, re.I):
                url_path = m.group(1)
                name = re.sub(r'<[^>]+>', '', m.group(2)).strip()
                tid = url_path.strip('/')
                if tid and name and tid not in [c['type_id'] for c in cats]:
                    cats.append({"type_id": tid, "type_name": name})
        
        # 兜底静态分类
        if not cats:
            cats = [
                {"type_id": "latest-updates", "type_name": "最近更新"},
                {"type_id": "hot", "type_name": "热门影片"},
                {"type_id": "categories/bdsm", "type_name": "主奴调教"},
                {"type_id": "categories/sex-only", "type_name": "直接开啪"},
                {"type_id": "categories/chinese-subtitle", "type_name": "中文字幕"},
                {"type_id": "categories/insult", "type_name": "凌辱快感"},
                {"type_id": "categories/uniform", "type_name": "制服诱惑"},
                {"type_id": "categories/roleplay", "type_name": "角色剧情"},
                {"type_id": "categories/private-cam", "type_name": "盗摄偷拍"},
                {"type_id": "categories/uncensored", "type_name": "无码破解"},
                {"type_id": "categories/pov", "type_name": "男友视角"},
                {"type_id": "categories/groupsex", "type_name": "多P群交"},
                {"type_id": "categories/pantyhose", "type_name": "丝袜美腿"},
                {"type_id": "categories/lesbian", "type_name": "女同欢愉"}
            ]
        return {'class': cats}

    def categoryContent(self, tid, pg, filter, extend):
        url = f"{self.siteUrl}/{tid}/{pg}/" if str(pg) != '1' else f"{self.siteUrl}/{tid}/"
        return self.postList(url, int(pg))

    def searchContent(self, key, quick, pg=1):
        url = f"{self.siteUrl}/search/{key}/{pg}/" if str(pg) != '1' else f"{self.siteUrl}/search/{key}/"
        return self.postList(url, int(pg))

    def postList(self, url, pg):
        r = self.fetch(url)
        l = []
        if r and r.ok:
            blocks = r.text.split('<div class="video-img-box')[1:]
            for block in blocks:
                href_match = re.search(r'href=["\']([^"\']+/videos/[^"\']+)["\']', block)
                if not href_match: continue
                u = href_match.group(1)

                title_match = re.search(r'<h6 class="title"[^>]*>\s*<a[^>]*>(.*?)</a>', block, re.S)
                t = re.sub(r'<[^>]+>', '', title_match.group(1)).strip() if title_match else "未知"

                pic_match = re.search(r'data-src=["\']([^"\']+)["\']', block) or re.search(r'src=["\']([^"\']+)["\']', block)
                p = pic_match.group(1) if pic_match else ""

                u = u if u.startswith("http") else f"{self.siteUrl}/{u.lstrip('/')}"
                
                l.append({
                    # 传参大法：直接携带标题和图片给详情页
                    'vod_id': f"{u}@@@{t}@@@{p}",
                    'vod_name': t,
                    'vod_pic': p,
                    'vod_remarks': '1080P',
                    'style': {"type": "rect", "ratio": 1.33}
                })
        return {'list': l, 'page': pg, 'pagecount': pg + 1 if len(l) else pg, 'limit': 24, 'total': 9999}

    def detailContent(self, ids):
        vid = ids[0]
        name, pic = "未知", ""
        
        # 还原传参
        if "@@@" in vid:
            parts = vid.split("@@@")
            vid = parts[0]
            name = parts[1] if len(parts) > 1 else name
            pic = parts[2] if len(parts) > 2 else pic

        # 获取详情页，通过正则直接抓取 m3u8 直链
        r = self.fetch(vid)
        m3u8_url = ""
        if r and r.ok:
            m_m3u8 = re.search(r"https?://[^\s'\" ]+\.m3u8", r.text)
            if m_m3u8: m3u8_url = m_m3u8.group(0)

        vod = {
            'vod_id': ids[0],
            'vod_name': name,
            'vod_pic': pic,
            'type_name': '视频',
            'vod_play_from': 'Jable',
            # 如果成功获取直链，则传直链，否则传详情页URL让 playerContent 兜底
            'vod_play_url': f"播放${m3u8_url}" if m3u8_url else f"播放${vid}"
        }
        return {'list': [vod]}

    def playerContent(self, flag, id, vipFlags):
        # 由于 detailContent 已经解析出了真实的 m3u8，这里直接返回交给底层播放器即可
        return {
            "parse": 0, 
            "url": id, 
            "header": {
                "Referer": "https://jable.tv/",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        }
