import sys, re, requests
from concurrent.futures import ThreadPoolExecutor
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from base.spider import Spider

requests.packages.urllib3.disable_warnings()

class Spider(Spider):
    def getName(self): return "美人图"

    def init(self, extend=""):
        self.siteUrl = "https://meirentu.club"
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', 'Referer': self.siteUrl + '/'}
        self.sess = requests.Session()
        # 优化：超时时间降低，减少死等情况
        self.sess.mount('https://', HTTPAdapter(max_retries=Retry(total=2, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])))

    def fetch(self, url):
        try: return self.sess.get(url, headers=self.headers, timeout=5, verify=False)
        except: return None

    def homeContent(self, filter):
        cats = [
            {"type_name": "秀人网", "type_id": "xiuren"},
            {"type_name": "模范学院", "type_id": "mfstar"},
            {"type_name": "魅妍社", "type_id": "mistar"},
            {"type_name": "美媛馆", "type_id": "mygirl"},
            {"type_name": "爱蜜社", "type_id": "imiss"},
            {"type_name": "兔几盟", "type_id": "bololi"},
            {"type_name": "尤物馆", "type_id": "youwu"},
            {"type_name": "优星馆", "type_id": "uxing"},
            {"type_name": "蜜桃社", "type_id": "miitao"},
            {"type_name": "嗲囡囡", "type_id": "feilin"},
            {"type_name": "影私荟", "type_id": "wings"},
            {"type_name": "顽味生活", "type_id": "taste"},
            {"type_name": "星乐园", "type_id": "leyuan"},
            {"type_name": "花の颜", "type_id": "huayan"},
            {"type_name": "御女郎", "type_id": "dkgirl"},
            {"type_name": "薄荷叶", "type_id": "mintye"},
            {"type_name": "尤蜜荟", "type_id": "youmi"},
            {"type_name": "糖果画报", "type_id": "candy"},
            {"type_name": "模特联盟", "type_id": "mtmeng"},
            {"type_name": "猫萌榜", "type_id": "micat"},
            {"type_name": "花漾", "type_id": "huayang"},
            {"type_name": "星颜社", "type_id": "xingyan"},
            {"type_name": "画语界", "type_id": "xiaoyu"}
        ]
        return {'class': cats}

    def categoryContent(self, tid, pg, filter, extend):
        url = f"{self.siteUrl}/group/{tid}-{pg}.html" if str(pg) != '1' else f"{self.siteUrl}/group/{tid}.html"
        return self.postList(url, int(pg))

    def searchContent(self, key, quick, pg=1):
        url = f"{self.siteUrl}/search/{key}-{pg}.html"
        return self.postList(url, int(pg))

    def postList(self, url, pg):
        r = self.fetch(url)
        l = []
        if r and r.ok:
            html = r.text
            blocks = re.findall(r'<li[^>]*>(.*?)</li>', html, re.I | re.S)
            valid_blocks = [b for b in blocks if '/pic/' in b]
            if not valid_blocks:
                blocks = re.findall(r'<div[^>]*class=["\'][^"\']*(?:item|post|list|card|box|col-|update)[^"\']*["\'][^>]*>(.*?)</div>', html, re.I | re.S)
                valid_blocks = [b for b in blocks if '/pic/' in b]
            if not valid_blocks:
                valid_blocks = re.findall(r'(<a[^>]*href=["\'][^"\']*?/pic/\d+\.html["\'][^>]*>.*?</a>)', html, re.I | re.S)

            seen = set()
            for content in valid_blocks:
                href_match = re.search(r'href=["\']([^"\']*?/pic/\d+\.html)["\']', content, re.I)
                if not href_match: continue
                u = href_match.group(1)
                if u in seen: continue
                seen.add(u)

                title_match = re.search(r'class=["\'][^"\']*title[^"\']*["\'][^>]*>(.*?)<', content, re.I | re.S) or re.search(r'<p[^>]*>(.*?)</p>', content, re.I | re.S) or re.search(r'<h[1-6][^>]*>(.*?)</h[1-6]>', content, re.I | re.S) or re.search(r'title=["\']([^"\']+)["\']', content, re.I) or re.search(r'alt=["\']([^"\']+)["\']', content, re.I)
                t = re.sub(r'<[^>]+>', '', title_match.group(1)).strip() if title_match else ""
                
                if not t:
                    for at in re.findall(r'<a[^>]*>(.*?)</a>', content, re.I | re.S):
                        clean_t = re.sub(r'<[^>]+>', '', at).strip()
                        if len(clean_t) > 2:
                            t = clean_t
                            break
                if not t: t = "未知标题"
                t = t.replace('\n', '').replace('\r', '').replace('\t', '')

                img_urls = re.findall(r'(?:data-original|data-src|src)=["\']([^"\']+(?:jpg|png|jpeg|webp|gif))["\']', content, re.I)
                p = ""
                for iu in img_urls:
                    if not any(x in iu for x in ['avatar', 'icon', 'logo', 'loading', 'blank']):
                        p = iu
                        break
                if not p: p = f"{self.siteUrl}/static/img/logo.png"

                u = u if u.startswith("http") else f"{self.siteUrl}/{u.lstrip('/')}"
                p = p if p.startswith("http") else f"{self.siteUrl}/{p.lstrip('/')}"
                
                p = f"{p}@Referer={self.siteUrl}/"

                l.append({
                    'vod_id': f"{u}@@@{t}@@@{p}",
                    'vod_name': t,
                    'vod_pic': p,
                    'vod_remarks': '写真',
                    'style': {"type": "rect", "ratio": 1.33}
                })
        return {'list': l, 'page': pg, 'pagecount': pg + 1 if len(l) else pg, 'limit': 20, 'total': 9999}

    def detailContent(self, ids):
        vid = ids[0]
        name, pic = "未知", ""
        if "@@@" in vid:
            parts = vid.split("@@@")
            vid = parts[0]
            name = parts[1] if len(parts) > 1 else name
            pic = parts[2] if len(parts) > 2 else pic

        vod = {
            'vod_id': ids[0],
            'vod_name': name,
            'vod_pic': pic,
            'type_name': '美图',
            'vod_play_from': '美人图',
            'vod_play_url': f"点击浏览${vid}"
        }
        return {'list': [vod]}

    # 抽取单页 HTML 的方法封装
    def fetch_page_html(self, url):
        r = self.fetch(url)
        return r.text if r and r.ok else ""

    def playerContent(self, flag, id, vipFlags):
        html = self.fetch_page_html(id)
        imgs = []
        if html:
            self.extract_imgs(html, imgs)
            max_page = 1
            nums = re.findall(r'/pic/\d+-(\d+)\.html', html)
            if nums: max_page = max(map(int, nums))
            
            if max_page > 1:
                # 生成所有子分页的 URL
                urls_to_fetch = [id.replace('.html', f'-{i}.html') for i in range(2, min(max_page, 60) + 1)]
                
                # 开启多线程极速并发拉取 (最大 10 线程并发，map 保证返回顺序与请求顺序一致)
                with ThreadPoolExecutor(max_workers=10) as executor:
                    results = executor.map(self.fetch_page_html, urls_to_fetch)
                    for page_html in results:
                        if page_html:
                            self.extract_imgs(page_html, imgs)

        return {"parse": 0, "url": "pics://" + "&&".join(imgs) if imgs else "", "header": ""}

    def extract_imgs(self, html, imgs):
        content_m = re.search(r'class=["\'][^"\']*(?:content|article|gallery)[^"\']*["\'](.*?)<(?:div class="[^"\']*footer|/body|script)', html, re.S)
        target = content_m.group(1) if content_m else html
        for m in re.finditer(r'<img[^>]+(?:data-original|data-src|src)=["\']([^"\']+(?:jpg|jpeg|png|webp))["\']', target, re.I):
            url = m.group(1)
            if any(x in url for x in ['avatar', 'icon', 'logo', 'loading', 'smilies', 'qr', 'qrcode', 'none.gif']): continue
            if url.startswith('//'): url = 'https:' + url
            elif not url.startswith('http'): url = f"{self.siteUrl}/{url.lstrip('/')}"
            url = f"{url}@Referer={self.siteUrl}/"
            if url not in imgs: imgs.append(url)
