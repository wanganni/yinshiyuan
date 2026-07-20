#coding=utf-8
import sys
import re
import json
import requests
sys.path.append('..')
from base.spider import Spider


class Spider(Spider):

    def __init__(self):
        super().__init__()
        self.site = 'https://www.dazhongs.com'
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.dazhongs.com/'
        })
        self.cateManual = {
            '电影': '1',
            '电视剧': '2',
            '综艺': '3',
            '动漫': '4',
            '短剧': '30',
        }

    def init(self, extend=''):
        pass

    def getName(self):
        return '大众影视'

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def _clean(self, text):
        if not text:
            return ''
        text = re.sub(r'<[^>]+>', '', text)
        text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('\u3000', ' ')
        text = ' '.join(text.split())
        return text.strip()

    def _get(self, url):
        try:
            r = self.session.get(url, timeout=15)
            r.encoding = 'utf-8'
            return r.text
        except Exception as e:
            print(f'_get error: {e}')
            return ''

    def _getVid(self, url):
        if not url:
            return ''
        m = re.search(r'/voddetail/(\d+)\.html', url)
        if m:
            return m.group(1)
        m = re.search(r'/vodplay/(\d+)-', url)
        if m:
            return m.group(1)
        return ''

    def _fixUrl(self, url):
        if not url:
            return ''
        url = url.replace('&amp;', '&')
        if url.startswith('//'):
            return 'https:' + url
        if url.startswith('/'):
            return self.site + url
        if not url.startswith('http'):
            return self.site + '/' + url
        return url

    def homeContent(self, filter):
        result = {'class': [], 'filters': {}, 'list': [], 'parse': 0, 'jx': 0}
        for k, v in self.cateManual.items():
            result['class'].append({'type_id': str(v), 'type_name': k})
        return result

    def homeVideoContent(self):
        videos = []
        try:
            html = self._get(self.site)
            if not html:
                return {'list': videos, 'parse': 0, 'jx': 0}
            seen = set()
            # 首页列表项: <li class="vodlist_item">...</li>
            for m in re.finditer(r'<li\s+class="vodlist_item[^"]*"[^>]*>(.*?)</li>', html, re.DOTALL):
                block = m.group(1)
                # 标题和链接
                tm = re.search(r'href="(/voddetail/\d+\.html)"[^>]*title="([^"]*)"', block)
                if not tm:
                    continue
                href = tm.group(1)
                title = tm.group(2)
                vid = self._getVid(href)
                if not vid or vid in seen:
                    continue
                seen.add(vid)
                # 封面
                pic = ''
                pm = re.search(r'data-original="([^"]+)"', block)
                if pm:
                    pic = self._fixUrl(pm.group(1))
                # 备注
                note = ''
                nm = re.search(r'class="pic_text[^"]*"[^>]*>([^<]*)<', block)
                if nm:
                    note = nm.group(1).strip()
                if title:
                    videos.append({
                        'vod_id': vid,
                        'vod_name': title,
                        'vod_pic': pic,
                        'vod_remarks': note
                    })
        except Exception as e:
            print(f'homeVideoContent error: {e}')
        return {'list': videos, 'parse': 0, 'jx': 0}

    def categoryContent(self, tid, pg, filter, extend):
        result = {'list': [], 'parse': 0, 'jx': 0}
        page = int(pg) if pg else 1
        try:
            if page == 1:
                url = f'{self.site}/vodtype/{tid}.html'
            else:
                url = f'{self.site}/vodtype/{tid}-{page}.html'

            html = self._get(url)
            if not html:
                return result
            seen = set()
            for m in re.finditer(r'<li\s+class="vodlist_item[^"]*"[^>]*>(.*?)</li>', html, re.DOTALL):
                block = m.group(1)
                tm = re.search(r'href="(/voddetail/\d+\.html)"[^>]*title="([^"]*)"', block)
                if not tm:
                    continue
                href = tm.group(1)
                title = tm.group(2)
                vid = self._getVid(href)
                if not vid or vid in seen:
                    continue
                seen.add(vid)
                pic = ''
                pm = re.search(r'data-original="([^"]+)"', block)
                if pm:
                    pic = self._fixUrl(pm.group(1))
                note = ''
                nm = re.search(r'class="pic_text[^"]*"[^>]*>([^<]*)<', block)
                if nm:
                    note = nm.group(1).strip()
                if title:
                    result['list'].append({
                        'vod_id': vid,
                        'vod_name': title,
                        'vod_pic': pic,
                        'vod_remarks': note
                    })
        except Exception as e:
            print(f'categoryContent error: {e}')

        result['page'] = page
        result['pagecount'] = page + 1 if len(result['list']) > 0 else page
        result['limit'] = len(result['list'])
        result['total'] = len(result['list'])
        return result

    def detailContent(self, ids):
        result = {'list': [], 'parse': 0, 'jx': 0}
        vid = ids[0] if ids else ''
        if not vid:
            return result
        try:
            html = self._get(f'{self.site}/voddetail/{vid}.html')
            if not html:
                return result

            # 标题
            title = ''
            tm = re.search(r'<h2\s+class="title[^"]*"[^>]*>([^<]+)<', html)
            if tm:
                title = self._clean(tm.group(1))
            if not title:
                tm = re.search(r'<title>([^<]+)', html)
                if tm:
                    title = self._clean(tm.group(1))

            # 封面
            pic = ''
            pm = re.search(r'class="vodlist_thumb[^"]*"[^>]*data-original="([^"]+)"', html)
            if pm:
                pic = self._fixUrl(pm.group(1))

            # 备注(状态)
            remarks = ''
            rm = re.search(r'class="data_style[^"]*"[^>]*>([^<]*)<', html)
            if rm:
                remarks = rm.group(1).strip()

            # 简介
            desc = ''
            dm = re.search(r'class="desc[^"]*"[^>]*>(.*?)</li>', html, re.DOTALL)
            if dm:
                desc = self._clean(dm.group(1))
                desc = re.sub(r'^简介：\s*', '', desc).strip()
            if not desc:
                dm2 = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', html)
                if dm2:
                    desc = dm2.group(1).strip()

            # 年份/地区/类型/主演/导演
            vod_year = ''
            vod_area = ''
            type_name = ''
            vod_actor = ''
            vod_director = ''

            data_items = re.findall(r'<li\s+class="data[^"]*"[^>]*>(.*?)</li>', html, re.DOTALL)
            if len(data_items) >= 1:
                first = data_items[0]
                ym = re.search(r'年份：</span><a[^>]*>([^<]+)', first)
                if ym:
                    vod_year = ym.group(1).strip()
                am = re.search(r'地区：</span><a[^>]*>([^<]+)', first)
                if am:
                    vod_area = am.group(1).strip()
                tm2 = re.search(r'类型：</span><a[^>]*>([^<]+)', first)
                if tm2:
                    type_name = tm2.group(1).strip()
            if len(data_items) >= 3:
                actor_block = data_items[2]
                actor_m = re.search(r'主演：(.*)', actor_block, re.DOTALL)
                if actor_m:
                    vod_actor = self._clean(actor_m.group(1))
            if len(data_items) >= 4:
                dir_block = data_items[3]
                dir_m = re.search(r'导演：(.*)', dir_block, re.DOTALL)
                if dir_m:
                    vod_director = self._clean(dir_m.group(1))

            # 线路和播放列表
            play_from = []
            play_url = []

            # 线路名称: #NumTab 下的 <a alt="线路名">
            tab_block = re.search(r'id="NumTab"[^>]*>(.*?)</div>', html, re.DOTALL)
            tabs = []
            if tab_block:
                tabs = re.findall(r'<a[^>]*alt="([^"]*)"[^>]*>', tab_block.group(1))

            # 播放列表: 每个 .play_list_box 内的 content_playlist
            panels = re.findall(r'class="play_list_box[^"]*"[^>]*>(.*?)</div>\s*</div>', html, re.DOTALL)

            for i, tab_name in enumerate(tabs):
                play_from.append(tab_name)
                episodes = []
                if i < len(panels):
                    for em in re.finditer(r'<a[^>]*href="(/vodplay/[^"]+)"[^>]*>([^<]+)<', panels[i]):
                        ep_href = em.group(1)
                        ep_name = em.group(2).strip()
                        if ep_name and ep_href:
                            episodes.append(f'{ep_name}${ep_href}')
                play_url.append('#'.join(episodes))

            # 兜底: 如果没找到线路tab但有播放列表 (单线路情况)
            if not tabs and panels:
                play_from.append('默认线路')
                episodes = []
                for em in re.finditer(r'<a[^>]*href="(/vodplay/[^"]+)"[^>]*>([^<]+)<', panels[0]):
                    ep_href = em.group(1)
                    ep_name = em.group(2).strip()
                    if ep_name and ep_href:
                        episodes.append(f'{ep_name}${ep_href}')
                play_url.append('#'.join(episodes))

            vod = {
                'vod_id': vid,
                'vod_name': title,
                'vod_pic': pic,
                'type_name': type_name,
                'vod_year': vod_year,
                'vod_area': vod_area,
                'vod_remarks': remarks,
                'vod_actor': vod_actor,
                'vod_director': vod_director,
                'vod_content': desc,
                'vod_play_from': '$$$'.join(play_from) if play_from else '',
                'vod_play_url': '$$$'.join(play_url) if play_url else ''
            }
            result['list'].append(vod)
        except Exception as e:
            print(f'detailContent error: {e}')
        return result

    def playerContent(self, flag, id, vipFlags):
        result = {}
        danmaku = 'http://127.0.0.1:9978/proxy?do=diydanmu'
        try:
            play_url = id
            if id and not id.startswith('http'):
                play_url = self.site + id

            html = self._get(play_url)

            # 优先从 player_aaaa JSON 提取 m3u8 直链
            m = re.search(r'player_aaaa\s*=\s*(\{.+?\})\s*<', html)
            if m:
                try:
                    data = json.loads(m.group(1))
                    m3u8 = data.get('url', '')
                    if m3u8 and '.m3u8' in m3u8:
                        result['parse'] = 0
                        result['url'] = m3u8
                        result['jx'] = 0
                        result['header'] = {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                            'Referer': self.site + '/'
                        }
                        result['danmaku'] = danmaku
                        return result
                except:
                    pass

            # 备用: 从页面找 m3u8 链接
            m = re.search(r'url["\s:]+(https?://[^"\s]*\.m3u8[^"\s]*)', html)
            if m:
                result['parse'] = 0
                result['url'] = m.group(1).replace('\\/', '/')
                result['jx'] = 0
                result['header'] = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Referer': self.site + '/'
                }
                result['danmaku'] = danmaku
                return result

            # 备用: iframe 嗅探
            m = re.search(r'<iframe[^>]+src="([^"]+)"', html)
            if m:
                result['parse'] = 1
                result['url'] = m.group(1)
                result['jx'] = 0
                result['header'] = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Referer': self.site + '/'
                }
                result['danmaku'] = danmaku
            else:
                # 最终兜底: 嗅探模式
                result['parse'] = 1
                result['url'] = play_url
                result['jx'] = 0
                result['header'] = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Referer': self.site + '/'
                }
                result['danmaku'] = danmaku
        except Exception as e:
            print(f'playerContent error: {e}')
            result['parse'] = 1
            result['url'] = id
            result['jx'] = 0
            result['header'] = {}
            result['danmaku'] = danmaku
        return result

    def searchContent(self, key, quick, pg='1'):
        result = {'list': [], 'parse': 0, 'jx': 0}
        page = int(pg) if pg else 1
        try:
            url = f'{self.site}/vodsearch/-------------.html'
            params = {'wd': key}
            if page > 1:
                params['page'] = page

            r = self.session.get(url, params=params, timeout=15)
            r.encoding = 'utf-8'
            html = r.text
            if not html:
                return result
            seen = set()
            # 搜索结果用 .searchlist_item
            for m in re.finditer(r'<li\s+class="searchlist_item[^"]*"[^>]*>(.*?)</li>', html, re.DOTALL):
                block = m.group(1)
                tm = re.search(r'href="(/voddetail/\d+\.html)"[^>]*title="([^"]*)"', block)
                if not tm:
                    continue
                href = tm.group(1)
                title = tm.group(2)
                vid = self._getVid(href)
                if not vid or vid in seen:
                    continue
                seen.add(vid)
                # 封面
                pic = ''
                pm = re.search(r'data-original="([^"]+)"', block)
                if pm:
                    pic = self._fixUrl(pm.group(1))
                # 备注
                note = ''
                nm = re.search(r'class="pic_text[^"]*"[^>]*>([^<]*)<', block)
                if nm:
                    note = nm.group(1).strip()
                if title:
                    result['list'].append({
                        'vod_id': vid,
                        'vod_name': title,
                        'vod_pic': pic,
                        'vod_remarks': note
                    })
        except Exception as e:
            print(f'searchContent error: {e}')
        return result

    def localProxy(self, params):
        return [200, "video/MP2T", {}, ""]


if __name__ == '__main__':
    spider = Spider()

    print('=' * 60)
    print('测试 homeContent ...')
    home = spider.homeContent(True)
    print(f"分类数量: {len(home['class'])}")
    for c in home['class']:
        print(f"  {c['type_id']}: {c['type_name']}")

    print()
    print('=' * 60)
    print('测试 homeVideoContent ...')
    hv = spider.homeVideoContent()
    print(f"首页列表数量: {len(hv['list'])}")
    for item in hv['list'][:5]:
        print(f"  {item['vod_name']} | {item['vod_id']} | {item['vod_remarks']}")

    print()
    print('=' * 60)
    print('测试 categoryContent (电影, 第1页) ...')
    cat = spider.categoryContent('1', '1', True, {})
    print(f"分类列表数量: {len(cat['list'])}")
    for item in cat['list'][:3]:
        print(f"  {item['vod_name']} | {item['vod_id']}")

    print()
    print('=' * 60)
    print('测试 searchContent (家业) ...')
    search = spider.searchContent('家业', False, '1')
    print(f"搜索结果数量: {len(search['list'])}")
    for item in search['list'][:3]:
        print(f"  {item['vod_name']} | {item['vod_id']}")

    print()
    print('=' * 60)
    test_id = '102577'
    print(f'测试 detailContent (vod_id={test_id}) ...')
    detail = spider.detailContent([test_id])
    if detail['list']:
        info = detail['list'][0]
        print(f"  标题: {info['vod_name']}")
        print(f"  年份: {info['vod_year']}")
        print(f"  地区: {info['vod_area']}")
        print(f"  类型: {info['type_name']}")
        print(f"  主演: {info['vod_actor']}")
        print(f"  导演: {info['vod_director']}")
        print(f"  备注: {info['vod_remarks']}")
        print(f"  封面: {info['vod_pic']}")
        print(f"  简介: {info['vod_content'][:80]}...")
        print(f"  线路: {info['vod_play_from']}")
        play_urls = info['vod_play_url'].split('$$$')
        for i, pu in enumerate(play_urls):
            eps = pu.split('#')
            print(f"  线路{i+1}: 共{len(eps)}集, 前3集名: {[e.split('$')[0] for e in eps[:3]]}")

    print()
    print('=' * 60)
    print('测试 playerContent ...')
    player = spider.playerContent('稳定线路①', f'/vodplay/102577-1-1.html', '')
    print(f"  parse: {player.get('parse')}")
    print(f"  url: {player.get('url', '')[:100]}...")
    print(f"  jx: {player.get('jx')}")

    print()
    print('全部测试完成!')
