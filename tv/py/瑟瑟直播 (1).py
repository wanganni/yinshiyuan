# -*- coding: utf-8 -*-
import json
import sys
import traceback
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    primary_host = 'http://api.hclyz.com:81/mf/'
    backup_host = 'http://api.maiyoux.com:81/mf/'
    host = primary_host
    platforms = []

    def init(self, extend=""):
        if extend:
            h = extend.strip()
            if not h.endswith('/'):
                h += '/'
            self.host = h
        else:
            self.host = self.primary_host

        content = None
        for base in [self.host, self.backup_host]:
            try:
                txt = self.fetch(base + 'json.txt').text
                data = None
                try:
                    data = json.loads(txt)
                except Exception:
                    data = None

                if data is not None:
                    self.host = base
                    self.platforms = self._parse_catalog_json(data)
                    if self.platforms:
                        return
                else:
                    plats = self._parse_catalog_text(txt)
                    if plats:
                        self.host = base
                        self.platforms = plats
                        return
            except Exception:
                continue

    def _parse_catalog_json(self, data):
        items = []
        if isinstance(data, dict):
            if 'pingtai' in data and isinstance(data['pingtai'], list):
                items = data['pingtai']
            else:
                if all(isinstance(v, dict) for v in data.values()):
                    items = list(data.values())
        elif isinstance(data, list):
            items = data

        platforms = []
        for it in items:
            name = it.get('mc') or it.get('title') or it.get('name') or ''
            img = it.get('tp1') or it.get('xinimg') or it.get('img') or ''
            file = it.get('dz') or it.get('address') or it.get('file') or ''
            count = it.get('sl') or it.get('Number') or it.get('count') or 0
            try:
                count = int(count)
            except Exception:
                pass
            if name and file:
                if not file.endswith('.txt'):
                    file += '.txt'
                if not file.startswith('json'):
                    file = 'json' + file
                platforms.append({
                    'name': name,
                    'img': img,
                    'file': file,
                    'count': count
                })
        return platforms

    def _parse_catalog_text(self, txt):
        plats = []
        block = txt.strip()
        if not block:
            return plats
        if block.startswith('{') and block.endswith('}'):
            block = block[1:-1]
        chunks = [c for c in block.split('|') if c.strip()]
        curr = {'mc': '', 'tp1': '', 'dz': '', 'sl': 0}
        def flush():
            if curr.get('mc') and curr.get('dz'):
                try:
                    sl = int(curr.get('sl') or 0)
                except Exception:
                    sl = curr.get('sl') or 0
                fname = curr.get('dz')
                if not fname.endswith('.txt'):
                    fname += '.txt'
                if not fname.startswith('json'):
                    fname = 'json' + fname
                plats.append({
                    'name': curr.get('mc'),
                    'img': curr.get('tp1'),
                    'file': fname,
                    'count': sl
                })
        for c in chunks:
            s = c.strip()
            if s.startswith('@mc'):
                if curr.get('mc') or curr.get('dz'):
                    flush()
                    curr = {'mc': '', 'tp1': '', 'dz': '', 'sl': 0}
                curr['mc'] = s.replace('@mc', '', 1)
            elif s.startswith('@tp1'):
                curr['tp1'] = s.replace('@tp1', '', 1)
            elif s.startswith('@dz'):
                curr['dz'] = s.replace('@dz', '', 1)
            elif s.startswith('@sl'):
                curr['sl'] = s.replace('@sl', '', 1)
        if curr.get('mc') or curr.get('dz'):
            flush()
        return plats

    def _load_platform_rooms(self, file_path, pg=1):
        url_candidates = [
            self.host + file_path,
        ]
        alt_path = file_path.replace('json', '', 1)
        if alt_path != file_path:
            url_candidates.insert(0, self.host + alt_path)

        data = None
        raw = None
        for u in url_candidates:
            try:
                raw = self.fetch(u).text
                data = json.loads(raw)
                break
            except Exception:
                data = None
                continue

        rooms = []
        if isinstance(data, dict):
            if 'zhubo' in data and isinstance(data['zhubo'], list):
                rooms = data['zhubo']
            elif 'list' in data and isinstance(data['list'], list):
                rooms = data['list']
            elif 'data' in data and isinstance(data['data'], list):
                rooms = data['data']
            elif 'rooms' in data and isinstance(data['rooms'], list):
                rooms = data['rooms']
        elif isinstance(data, list):
            rooms = data

        videos = []
        for idx, r in enumerate(rooms or [], 1):
            title = r.get('title') or r.get('name') or r.get('nickname') or f'主播{idx}'
            address = r.get('address') or r.get('url') or r.get('stream') or ''
            img = r.get('img') or r.get('pic') or r.get('avatar') or ''
            remarks = r.get('Number') or r.get('online') or r.get('viewers') or ''
            if title and address:
                videos.append({
                    'vod_id': address,
                    'vod_name': title,
                    'vod_pic': img,
                    'vod_remarks': str(remarks)
                })
        total = len(videos)
        if pg > 1:
            start = (pg - 1) * 20
            videos = videos[start:start + 20]
        return videos, total

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        pass

    def getName(self):
        return 'Leospring直播'

    def homeContent(self, filter):
        classes = []
        for p in self.platforms:
            classes.append({
                'type_id': p['file'],
                'type_name': p['name'],
            })
        return {'class': classes}

    def homeVideoContent(self):
        return {'list': []}

    def _find_platform(self, tid):
        for p in self.platforms:
            if p['file'] == tid or p['name'] == tid:
                return p
        return None

    def categoryContent(self, tid, pg, filter, extend):
        p = self._find_platform(tid)
        if not p:
            return {'list': [], 'page': pg, 'pagecount': 0, 'limit': 0, 'total': 0}
        
        videos, total = self._load_platform_rooms(p['file'], int(pg))
        pagecount = (total + 19) // 20
        result = {
            'list': videos,
            'page': pg,
            'pagecount': pagecount,
            'limit': min(len(videos), 20),
            'total': total
        }
        return result

    def searchContent(self, key, quick, pg="1"):
        key = (key or '').strip().lower()
        out = []
        if not key:
            return {'list': out}
        for p in self.platforms:
            videos, _ = self._load_platform_rooms(p['file'])
            for v in videos:
                if key in v['vod_name'].lower():
                    out.append(v)
            if len(out) >= 50:
                break
        return {'list': out[:50]}

    def detailContent(self, ids):
        try:
            address = ids[0]
            if not address:
                return {'list': []}
            
            vod = {
                'vod_id': address,
                'vod_name': '直播源',
                'vod_play_from': '瑟瑟站大佬张佬',
                'vod_play_url': address,
                'vod_content': '多看少打卡',
            }
            return {'list': [vod]}
        except Exception as e:
            traceback.print_exc()
            return {'list': []}

    def playerContent(self, flag, id, vipFlags):
        return {
            'parse': 0,
            'url': id
        }

    def localProxy(self, param):
        pass
