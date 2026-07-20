# coding=utf-8
# !/usr/bin/python
# 蜜桃视频 T3 爬虫 (本地女优库 + 蜜桃信息融合)
import sys
sys.path.append('..')

from base.spider import BaseSpider
import requests
import json
import base64
import hashlib
import time
import re
import os
import string
import random
import threading
import sqlite3
from urllib.parse import quote, unquote
from Crypto.Cipher import AES
import concurrent.futures

TIMEOUT = 10

# 站点配置
SITES_REMOTE_URL = ""
SITES = [
    {'name': 'nht966', 'host': 'https://www.nht966hht.vip:9527'},
    {'name': 'httre666', 'host': 'https://www.newhttestre666.cc'},
]
BACKUP_SITES = [
    {'name': 'backup1', 'host': 'https://www.mitao555.com'},
    {'name': 'backup2', 'host': 'https://www.mitao666.cc'},
]

SIGN_KEY  = 'opum3_Loily$SV^6H'
BUNDLE_ID = 'com.ht9.web20.video'
BRAND_ID  = 'hongtao'
VERSION   = '1.0.0'
PROJECT_ID = '1'
PROXY_TYPE = 'mitao_img'

# 本地数据库扫描目录
LOCAL_DB_DIRS = [
    "/storage/emulated/0/私藏视频/",
    "/storage/emulated/0/lz/女优库/"
]

def log(msg):
    print(f"[蜜桃] {time.strftime('%H:%M:%S')} {msg}")

class Spider(BaseSpider):
    def getName(self):
        return "蜜桃视频"

    def isVideoFormat(self, url):
        return url and ('.mp4' in url or '.m3u8' in url or '.ts' in url)

    def manualVideoCheck(self):
        return False

    filterable = True
    searchable = True
    host = SITES[0]['host']
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "lang": "cn",
        "deviceType": "H5-android",
    }

    _speed_cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.mitao_cache.json')
    _speed_cache_ttl = 1800
    _lock = threading.Lock()
    _speed_test_done = False
    _api_fail_count = 0
    _max_api_fail = 3

    _user_id = ''
    _session_id = ''
    _device_id = ''
    _session_inited = False
    _categories = []
    _video_type_list = []

    _session_cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.mitao_session.json')
    _session_cache_ttl = 1800

    # 本地数据库管理
    databases = {}
    _db_lock = threading.Lock()

    # 蜜桃女优信息缓存
    _mitao_actress_map = {}   # name -> {"img": url, "name": display_name}
    _mitao_actress_fetched = False

    def _scan_local_databases(self):
        seen = set()
        for d in LOCAL_DB_DIRS:
            if not os.path.exists(d):
                continue
            for root, _, files in os.walk(d):
                for file in files:
                    if file.endswith(".db"):
                        full = os.path.abspath(os.path.join(root, file))
                        if full in seen:
                            continue
                        seen.add(full)
                        key = f"local_{file}"
                        if key in self.databases:
                            key = f"local_{os.path.basename(root)}_{file}"
                        self.databases[key] = {"name": file, "path": full}
        log(f"扫描到 {len(self.databases)} 个本地数据库")

    def _get_db_connection(self, db_key):
        info = self.databases.get(db_key)
        if not info or not os.path.exists(info['path']):
            return None
        try:
            conn = sqlite3.connect(info['path'])
            conn.row_factory = sqlite3.Row
            return conn
        except:
            return None

    def _is_exclusive_db(self, conn):
        try:
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='video_actress'")
            return cur.fetchone() is not None
        except:
            return False

    # ---------- 本地女优列表获取 ----------
    def _get_local_actresses(self):
        """从所有本地专属库中获取去重的女优列表（name, count, avatar）"""
        actresses = {}
        for db_key in self.databases:
            conn = self._get_db_connection(db_key)
            if not conn:
                continue
            try:
                if not self._is_exclusive_db(conn):
                    conn.close()
                    continue
                cur = conn.cursor()
                cur.execute("""
                    SELECT a.name, COUNT(va.vod_id) as cnt
                    FROM actresses a
                    LEFT JOIN video_actress va ON a.cate_id = va.cate_id
                    GROUP BY a.cate_id
                    HAVING cnt > 0
                """)
                for row in cur.fetchall():
                    name = row[0]
                    cnt = row[1]
                    if name not in actresses:
                        actresses[name] = {"count": 0, "avatar": ""}
                    actresses[name]["count"] += cnt
                # 尝试获取头像（如果表里有avatar字段）
                try:
                    cur.execute("SELECT name, avatar FROM actresses WHERE avatar IS NOT NULL AND avatar != ''")
                    for row in cur.fetchall():
                        if row[0] in actresses:
                            actresses[row[0]]["avatar"] = row[1]
                except:
                    pass
                conn.close()
            except Exception as e:
                log(f"读取数据库 {db_key} 女优信息出错: {e}")
                try:
                    conn.close()
                except:
                    pass
        return actresses

    # ---------- 蜜桃女优信息同步 ----------
    def _fetch_mitao_actress_map(self):
        """从蜜桃API获取所有女优信息，构建名字->{img,name}映射，最多获取200条"""
        if self._mitao_actress_fetched:
            return
        self._select_best_site()
        self._ensure_session()
        page = 0
        max_pages = 10
        while page < max_pages:
            resp = self._api_request('/ht/content/getActors', {
                'pageNo': str(page),
                'pageSize': '20',
                'sort': '1'
            })
            if not resp or resp.get('code') != 10000:
                break
            data = resp.get('data', {})
            items = data.get('actorList') or data.get('list') or data.get('data') or []
            if not isinstance(items, list) or len(items) == 0:
                break
            for item in items:
                name = str(self._try_get(item, 'actorName','name','title','artName','actor_name','actor'))
                img = str(self._try_get(item, 'actorPic','actorImg','img','avatar','cover','imageUrl','headImg','head','photo','image','pic','actor_img'))
                if name and name not in self._mitao_actress_map:
                    self._mitao_actress_map[name] = {
                        "img": img if img else "",
                        "display_name": name
                    }
            page += 1
            if len(items) < 20:
                break
        self._mitao_actress_fetched = True
        log(f"蜜桃女优信息同步完成，共 {len(self._mitao_actress_map)} 条")

    # ---------- 本地视频匹配（多级模糊）----------
    def _find_local_play_url(self, actress_name, video_title):
        clean_title = re.sub(r'[【】\[\]\(\)（）\s\-_\.]', '', video_title).strip()
        for db_key in self.databases:
            conn = self._get_db_connection(db_key)
            if not conn:
                continue
            try:
                if not self._is_exclusive_db(conn):
                    conn.close()
                    continue
                cur = conn.cursor()
                # 级别1：精确女优名 + 标题模糊
                if actress_name:
                    cur.execute("""
                        SELECT v.m3u8_url, v.vod_play_url
                        FROM videos v
                        JOIN video_actress va ON v.vod_id = va.vod_id
                        JOIN actresses a ON va.cate_id = a.cate_id
                        WHERE a.name = ? AND v.title LIKE ?
                        LIMIT 1
                    """, (actress_name, f"%{video_title}%"))
                    row = cur.fetchone()
                    if row and (row["m3u8_url"] or row["vod_play_url"]):
                        url = row["m3u8_url"] or row["vod_play_url"]
                        conn.close()
                        return url
                # 级别2：模糊女优名 + 标题模糊
                if actress_name:
                    cur.execute("""
                        SELECT v.m3u8_url, v.vod_play_url
                        FROM videos v
                        JOIN video_actress va ON v.vod_id = va.vod_id
                        JOIN actresses a ON va.cate_id = a.cate_id
                        WHERE a.name LIKE ? AND v.title LIKE ?
                        LIMIT 1
                    """, (f"%{actress_name}%", f"%{video_title}%"))
                    row = cur.fetchone()
                    if row and (row["m3u8_url"] or row["vod_play_url"]):
                        url = row["m3u8_url"] or row["vod_play_url"]
                        conn.close()
                        return url
                # 级别3：仅标题模糊
                cur.execute("""
                    SELECT m3u8_url, vod_play_url
                    FROM videos
                    WHERE title LIKE ?
                    LIMIT 1
                """, (f"%{video_title}%",))
                row = cur.fetchone()
                if row and (row["m3u8_url"] or row["vod_play_url"]):
                    url = row["m3u8_url"] or row["vod_play_url"]
                    conn.close()
                    return url
                # 级别4：清洗后标题关键词
                if clean_title and clean_title != video_title:
                    cur.execute("""
                        SELECT m3u8_url, vod_play_url
                        FROM videos
                        WHERE title LIKE ?
                        LIMIT 1
                    """, (f"%{clean_title}%",))
                    row = cur.fetchone()
                    if row and (row["m3u8_url"] or row["vod_play_url"]):
                        url = row["m3u8_url"] or row["vod_play_url"]
                        conn.close()
                        return url
                conn.close()
            except Exception as e:
                log(f"匹配查询出错 {db_key}: {e}")
                try:
                    conn.close()
                except:
                    pass
        return None

    # ---------- 动态站点 ----------
    def _fetch_remote_sites(self):
        if not SITES_REMOTE_URL:
            return
        try:
            r = requests.get(SITES_REMOTE_URL, timeout=5)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list) and len(data) > 0 and 'host' in data[0]:
                    global SITES
                    SITES = data
                    log(f"远程站点更新成功，共 {len(SITES)} 个")
        except Exception as e:
            log(f"获取远程站点失败: {e}")

    def _get_cached_site(self):
        try:
            if os.path.exists(self._speed_cache_file):
                with open(self._speed_cache_file, 'r') as f:
                    data = json.load(f)
                if time.time() - data.get('ts', 0) < self._speed_cache_ttl:
                    return data.get('host', ''), True
        except:
            pass
        return '', False

    def _save_cached_site(self, host):
        try:
            with open(self._speed_cache_file, 'w') as f:
                json.dump({'host': host, 'ts': time.time()}, f)
        except:
            pass

    def _select_best_site(self, force=False):
        if self._speed_test_done and not force:
            return
        self._fetch_remote_sites()
        if not force:
            cached_host, valid = self._get_cached_site()
            if valid:
                self.host = cached_host
                self._speed_test_done = True
                return
        results = {}
        all_sites = SITES + BACKUP_SITES
        def test_site(site):
            try:
                start = time.time()
                r = requests.get(site['host'], headers=self.headers, timeout=TIMEOUT, verify=False)
                if 200 <= r.status_code < 500:
                    results[site['name']] = time.time() - start
                else:
                    results[site['name']] = 999
            except:
                results[site['name']] = 999
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(all_sites)) as executor:
            futures = [executor.submit(test_site, s) for s in all_sites]
            concurrent.futures.wait(futures, timeout=TIMEOUT + 2)
        valid_sites = [s for s in all_sites if results.get(s['name'], 999) < TIMEOUT]
        if valid_sites:
            best = min(valid_sites, key=lambda x: results[x['name']])
            self.host = best['host']
        else:
            self.host = all_sites[0]['host']
            log("所有站点测速失败，使用第一个站点")
        self._speed_test_done = True
        self._save_cached_site(self.host)
        log(f"当前工作站点: {self.host}")

    # 会话缓存
    def _save_session_cache(self):
        try:
            data = {
                'ts': time.time(),
                'user_id': self._user_id,
                'session_id': self._session_id,
                'device_id': self._device_id,
                'categories': self._categories,
                'video_type_list': self._video_type_list,
            }
            with open(self._session_cache_file, 'w') as f:
                json.dump(data, f, ensure_ascii=False)
        except:
            pass

    def _load_session_cache(self):
        try:
            if not os.path.exists(self._session_cache_file):
                return False
            with open(self._session_cache_file, 'r') as f:
                data = json.load(f)
            if time.time() - data.get('ts', 0) >= self._session_cache_ttl:
                return False
            self._user_id = data.get('user_id', '')
            self._session_id = data.get('session_id', '')
            self._device_id = data.get('device_id', '')
            self._categories = data.get('categories', [])
            self._video_type_list = data.get('video_type_list', [])
            if not self._user_id or not self._session_id:
                return False
            return True
        except:
            return False

    # AES 相关
    @staticmethod
    def _zero_pad(data, block_size=16):
        pad_len = block_size - (len(data) % block_size)
        return data if pad_len == block_size else data + b'\x00' * pad_len

    @staticmethod
    def _zero_unpad(data):
        return data.rstrip(b'\x00')

    def _gen_key(self, timestamp):
        return str(timestamp)[-6:] + SIGN_KEY[:4] + BUNDLE_ID[:6]

    def _gen_iv(self):
        return BUNDLE_ID[-6:] + SIGN_KEY[-4:] + self._device_id[:6]

    def _aes_encrypt(self, plaintext, key_str, iv_str):
        key, iv = key_str.encode(), iv_str.encode()
        cipher = AES.new(key, AES.MODE_CBC, iv)
        padded = self._zero_pad(plaintext.encode())
        return base64.b64encode(cipher.encrypt(padded)).decode()

    def _aes_decrypt(self, ciphertext_b64, key_str, iv_str):
        try:
            key, iv = key_str.encode(), iv_str.encode()
            cipher = AES.new(key, AES.MODE_CBC, iv)
            cleaned = re.sub(r'\s', '', ciphertext_b64)
            encrypted = base64.b64decode(cleaned)
            decrypted = cipher.decrypt(encrypted)
            try:
                return self._zero_unpad(decrypted).decode('utf-8', errors='replace')
            except:
                pad_len = decrypted[-1]
                if 1 <= pad_len <= 16:
                    return decrypted[:-pad_len].decode('utf-8', errors='replace')
                return decrypted.decode('utf-8', errors='replace')
        except Exception as e:
            log(f"AES解密失败: {e}")
            return ''

    def _generate_sign(self, params, api_path):
        sorted_keys = sorted(params.keys())
        concat = ''.join(str(params[k]) for k in sorted_keys)
        return hashlib.md5((concat + SIGN_KEY + api_path).encode()).hexdigest().upper()

    @staticmethod
    def _generate_device_id():
        return 'H5-' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=32))

    def _common_params(self):
        hostname = self.host.replace('https://', '').replace('http://', '')
        return {'timezone': 'Asia/Karachi', 'version': VERSION, 'channelId': 67,
                'channelId2': hostname, 'brandId': BRAND_ID}

    def _api_request(self, endpoint, params=None, skip_encrypt=False, _t=None, retry=2):
        if params is None:
            params = {}
        timestamp = str(_t) if _t else str(int(time.time() * 1000))
        key_str = self._gen_key(timestamp)
        iv_str = self._gen_iv()
        full_params = self._common_params()
        full_params['t'] = timestamp
        full_params.update(params)
        full_params['sign'] = self._generate_sign(full_params, endpoint)
        api_url = self.host + endpoint
        headers = dict(self.headers)
        headers['t'] = timestamp
        if self._user_id:
            headers['userId'] = self._user_id
        if self._session_id:
            headers['sessionId'] = self._session_id
        headers['deviceId'] = self._device_id or ''
        headers['bundleId'] = BUNDLE_ID
        if skip_encrypt:
            body = json.dumps(full_params, ensure_ascii=False, separators=(',', ':'))
            headers['Content-Type'] = 'application/json'
            headers['encrypt'] = 'false'
        else:
            plain = json.dumps(full_params, ensure_ascii=False, separators=(',', ':'))
            body = self._aes_encrypt(plain, key_str, iv_str)
            headers['Content-Type'] = 'text/plain'
            headers['encrypt'] = 'true'
        for attempt in range(retry):
            try:
                r = self.session.post(api_url, data=body, headers=headers, timeout=TIMEOUT, verify=False)
                resp = r.json()
                if resp.get('code') == 10000 and isinstance(resp.get('data'), str) and resp['data']:
                    decrypted = self._aes_decrypt(resp['data'], key_str, iv_str)
                    if decrypted:
                        resp['data'] = json.loads(decrypted)
                self._api_fail_count = 0
                return resp
            except Exception as e:
                log(f"API请求失败 {endpoint}: {e}")
                if attempt == retry - 1:
                    self._api_fail_count += 1
                    if self._api_fail_count >= self._max_api_fail:
                        log("连续失败次数过多，尝试切换站点...")
                        self._select_best_site(force=True)
                        self._api_fail_count = 0
                    return None
                time.sleep(0.5)
        return None

    def _ensure_session(self):
        if self._session_inited:
            return
        if self._load_session_cache():
            self._session_inited = True
            if not self._video_type_list:
                self._refresh_video_type_list()
            if self._categories:
                return
        if not self._device_id:
            self._device_id = self._generate_device_id()
        appcfg = self._api_request('/ht/users/appConfig')
        if appcfg and appcfg.get('code') == 10000:
            ac_data = appcfg.get('data', {})
            if isinstance(ac_data, dict) and ac_data.get('appConfig'):
                ac_cfg = ac_data['appConfig']
                if isinstance(ac_cfg, dict) and ac_cfg.get('videoTypeList'):
                    self._video_type_list = ac_cfg['videoTypeList']
        shared_t = int(time.time() * 1000)
        resp1 = self._api_request('/ht/users/initH5_1', _t=shared_t)
        if resp1 and resp1.get('code') == 10000:
            data = resp1.get('data', {})
            if data.get('deviceId'):
                self._device_id = data['deviceId']
            if data.get('typeTitleList'):
                self._categories = data['typeTitleList']
        self._api_request('/ht/users/initH5_2', _t=shared_t)
        resp = self._api_request('/ht/users/deviceLogin', {
            'bundleId': BUNDLE_ID, 'brandId': BRAND_ID, 'projectId': PROJECT_ID
        })
        if resp and resp.get('code') == 10000:
            data = resp.get('data', {})
            self._user_id = data.get('userId', '')
            self._session_id = data.get('sessionId', '')
        if not self._categories:
            self._categories = [
                {'contentId': 'home', 'title': '最新'},
                {'contentId': 'hot', 'title': '热门'},
            ]
        self._session_inited = True
        self._save_session_cache()

    def _refresh_video_type_list(self):
        appcfg = self._api_request('/ht/users/appConfig')
        if appcfg and appcfg.get('code') == 10000:
            ac_data = appcfg.get('data', {})
            if isinstance(ac_data, dict) and ac_data.get('appConfig'):
                ac_cfg = ac_data['appConfig']
                if isinstance(ac_cfg, dict) and ac_cfg.get('videoTypeList'):
                    self._video_type_list = ac_cfg['videoTypeList']

    def get_proxy_image_url(self, img_url):
        if not img_url:
            return ''
        base = self.getProxyUrl() or 'http://127.0.0.1:9980/proxy?do=py'
        return base + '&type=' + PROXY_TYPE + '&url=' + quote(img_url, safe='')

    def _fmt_duration(self, seconds):
        try:
            s = int(seconds or 0)
        except:
            return ''
        if s <= 0:
            return ''
        m, s = divmod(s, 60)
        return f"{m}:{s:02d}"

    def init(self, extend=""):
        cached_host, valid = self._get_cached_site()
        if valid:
            self.host = cached_host
            self._speed_test_done = True
        self._scan_local_databases()

    _CATEGORY_BLACKLIST = {'成人游戏', '漫画', '小说', '蜜穴女友', '一键脱衣', '春药商城', '同城交友', '吃瓜', '成人漫画'}

    def homeContent(self, filter):
        self._select_best_site()
        self._ensure_session()
        if not self._categories:
            self._session_inited = False
            self._ensure_session()
        classes = []
        filters = {}
        for cat in self._categories:
            cid = str(cat.get('contentId', ''))
            title = cat.get('title', '')
            if not cid or not title or title in self._CATEGORY_BLACKLIST:
                continue
            classes.append({'type_id': cid, 'type_name': title})
            cat_filters = []
            sub_cats = [v for v in self._video_type_list if str(v.get('typePid', '')) == cid]
            if sub_cats:
                sub_values = [{'n': '全部', 'v': ''}]
                for sc in sub_cats:
                    sc_id = str(sc.get('typeId', ''))
                    sc_name = sc.get('typeName', '')
                    if sc_id and sc_name:
                        sub_values.append({'n': sc_name, 'v': sc_id})
                if len(sub_values) > 1:
                    cat_filters.append({'key': 'label', 'name': '分类', 'value': sub_values})
            first_level = [v for v in self._video_type_list if str(v.get('typePid', '')) == '0' and str(v.get('typeId', '')) == cid]
            if first_level:
                tags_str = first_level[0].get('tags', '')
                if tags_str:
                    tag_list = [t.strip() for t in tags_str.split(',') if t.strip()]
                    if tag_list:
                        tag_values = [{'n': '全部', 'v': ''}]
                        for t in tag_list:
                            tag_values.append({'n': t, 'v': t})
                        cat_filters.append({'key': 'tag', 'name': '标签', 'value': tag_values})
            cat_filters.append({'key': 'sort', 'name': '排序', 'value': [
                {'n': '最近更新', 'v': '0'},
                {'n': '最多播放', 'v': '1'},
                {'n': '最多收藏', 'v': '2'},
            ]})
            if cat_filters:
                filters[cid] = cat_filters
        classes.append({'type_id': 'actor', 'type_name': '女优'})
        filters['actor'] = []   # 女优分类无在线筛选器，本地数据展示
        classes.append({'type_id': 'topic', 'type_name': '专题'})
        home_videos = self.categoryContent('home', 1, '', {})
        return {
            'class': classes,
            'filters': filters,
            'type': '影视',
            'list': home_videos.get('list', []),
            'page': home_videos.get('page', 1),
            'pagecount': home_videos.get('pagecount', 1),
            'limit': home_videos.get('limit', 0),
            'total': home_videos.get('total', 0),
        }

    def homeVideoContent(self, tid, pg, filter, extend):
        return self.categoryContent(tid or 'home', pg, filter, extend)

    # ---------- 分类内容（女优本地化）----------
    def categoryContent(self, tid, pg, filter, extend):
        tid = str(tid)
        pg = int(pg)
        self._select_best_site()
        self._ensure_session()
        vod_list = []

        # 女优展开作品（本地数据库）
        if tid.startswith('actor_') and '@' in tid:
            real_tid = tid.replace('@', '')
            actress_name = real_tid[len('actor_'):]
            # 直接从本地数据库获取该女优的视频
            return self._local_actress_videos(actress_name, pg)

        # 专题展开
        if tid.startswith('topic_') and '@' in tid:
            topic_id = tid[len('topic_'):].replace('@', '')
            resp = self._api_request('/ht/content/queryOriTopicVideos', {
                'topicId': topic_id, 'pageNo': str(pg-1), 'pageSize': '20'
            })
            if resp and resp.get('code') == 10000:
                data = resp.get('data', {})
                vod_list = self._extract_videos_from_data(data)
            total_page = max(1, len(vod_list) // 20 + (1 if len(vod_list) % 20 else 0))
            return {'list': vod_list, 'page': pg, 'pagecount': total_page, 'limit': len(vod_list), 'total': len(vod_list)}

        # 女优列表（本地数据库）
        if tid == 'actor':
            return self._local_actress_list(pg)

        # 专题列表（蜜桃API）
        if tid == 'topic':
            resp = self._api_request('/ht/content/getOriTopicList', {'pageNo': str(pg-1), 'pageSize': '20'})
            if resp and resp.get('code') == 10000:
                data = resp.get('data', {})
                vod_list = self._parse_topic_list(data)
                return {'list': vod_list, 'page': pg, 'pagecount': 50, 'limit': len(vod_list), 'total': len(vod_list)*50}
            return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 0, 'total': 0}

        # 首页/最新/热门
        if tid in ('home', 'new', 'hot'):
            sort_map = {'home':'1','new':'1','hot':'2'}
            resp = self._api_request('/ht/content/queryTypeVideosH5', {'pageNo': str(pg-1), 'pageSize': '20', 'sort': sort_map.get(tid,'1'), 'type': '1'})
            if resp and resp.get('code') == 10000:
                data = resp.get('data', {})
                items = data.get('typeVideoList') or data.get('list') or data.get('data') or data.get('videoList') or []
                if isinstance(items, list):
                    for v in items:
                        parsed = self._parse_video(v)
                        if parsed:
                            vod_list.append(parsed)
                total_page = int(data.get('totalPage') or 1)
                return {'list': vod_list, 'page': pg, 'pagecount': total_page, 'limit': len(vod_list), 'total': total_page*20}
            return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 0, 'total': 0}

        # 数值分类
        api_params = {'pageNo': str(pg-1), 'pageSize': '20', 'typeId': tid, 'type': '1'}
        if isinstance(extend, dict):
            for key in ('label','tag','sort'):
                if extend.get(key):
                    api_params[key] = extend[key]
        resp = self._api_request('/ht/content/queryTypeVideosH5', api_params)
        if resp and resp.get('code') == 10000:
            data = resp.get('data', {})
            items = data.get('typeVideoList') or data.get('list') or data.get('data') or data.get('videoList') or []
            if isinstance(items, list):
                for v in items:
                    parsed = self._parse_video(v)
                    if parsed:
                        vod_list.append(parsed)
            total_page = int(data.get('totalPage') or 1)
            return {'list': vod_list, 'page': pg, 'pagecount': total_page, 'limit': len(vod_list), 'total': total_page*20}
        return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 0, 'total': 0}

    # ---------- 本地女优列表 ----------
    def _local_actress_list(self, pg):
        # 获取本地女优数据
        local_actresses = self._get_local_actresses()
        if not local_actresses:
            return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 0, 'total': 0}
        # 同步蜜桃女优信息
        self._fetch_mitao_actress_map()
        # 构建列表
        actress_items = []
        for name, info in local_actresses.items():
            cnt = info['count']
            avatar = info.get('avatar', '')
            # 蜜桃信息覆盖
            mitao = self._mitao_actress_map.get(name)
            if mitao:
                display_name = mitao['display_name']
                pic = mitao['img'] if mitao['img'] else avatar
            else:
                display_name = name
                pic = avatar
            if not pic:
                pic = 'https://cloud.7so.top/f/p8PPHA/%E5%90%88%E9%9B%86.png'  # 默认封面
            actress_items.append({
                'vod_id': f"actor_{name}@",
                'vod_name': f"{display_name} ({cnt})",
                'vod_pic': self.get_proxy_image_url(pic) if pic else '',
                'vod_tag': 'folder',
                'vod_remarks': f"{cnt}部"
            })
        # 分页
        limit = 20
        page = int(pg)
        start = (page - 1) * limit
        paged = actress_items[start:start+limit]
        total_page = max(1, len(actress_items) // limit + (1 if len(actress_items) % limit else 0))
        return {
            'list': paged,
            'page': page,
            'pagecount': total_page,
            'limit': limit,
            'total': len(actress_items)
        }

    # ---------- 本地女优作品列表 ----------
    def _local_actress_videos(self, actress_name, pg):
        videos = []
        for db_key in self.databases:
            conn = self._get_db_connection(db_key)
            if not conn:
                continue
            try:
                if not self._is_exclusive_db(conn):
                    conn.close()
                    continue
                cur = conn.cursor()
                cur.execute("""
                    SELECT v.vod_id, v.title, v.pic_url, v.vod_remarks
                    FROM videos v
                    JOIN video_actress va ON v.vod_id = va.vod_id
                    JOIN actresses a ON va.cate_id = a.cate_id
                    WHERE a.name = ?
                """, (actress_name,))
                for row in cur.fetchall():
                    pic = row[2] if row[2] else 'https://img.icons8.com/color/512/movie.png'
                    videos.append({
                        'vod_id': f"local_{db_key}#ID#{row[0]}",
                        'vod_name': row[1] or row[0],
                        'vod_pic': pic,
                        'vod_remarks': row[3] or '',
                        'vod_play_from': '本地播放',
                        'vod_play_url': json.dumps({'actor': actress_name, 'title': row[1] or row[0]}, ensure_ascii=False)
                    })
                conn.close()
            except Exception as e:
                log(f"获取本地女优作品出错: {e}")
                try:
                    conn.close()
                except:
                    pass
        # 去重并分页
        limit = 20
        page = int(pg)
        start = (page - 1) * limit
        paged = videos[start:start+limit]
        total_page = max(1, len(videos) // limit + (1 if len(videos) % limit else 0))
        return {
            'list': paged,
            'page': page,
            'pagecount': total_page,
            'limit': limit,
            'total': len(videos)
        }

    # 辅助方法
    def _extract_videos_from_data(self, data):
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = (data.get('videoList') or data.get('list') or data.get('data') or
                     data.get('videos') or data.get('typeVideoList') or
                     data.get('topicVideoIdList') or data.get('searchList') or
                     data.get('contentList') or data.get('records') or
                     data.get('pageData') or data.get('resultList') or [])
        else:
            return []
        if not isinstance(items, list):
            return []
        result = []
        for v in items:
            if isinstance(v, dict):
                if v.get('contentType') is None:
                    v['contentType'] = 1
                parsed = self._parse_video(v)
                if parsed:
                    result.append(parsed)
        return result

    @staticmethod
    def _try_get(item, *keys):
        for k in keys:
            v = item.get(k)
            if v is not None and v != '':
                return v
        return ''

    def _parse_topic_list(self, data):
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get('topicList') or data.get('oriTopicList') or data.get('list') or data.get('data') or data.get('topics') or []
        else:
            return []
        if not isinstance(items, list):
            return []
        results, seen = [], set()
        for item in items:
            if not isinstance(item, dict):
                continue
            tid = str(self._try_get(item, 'topicId','id','contentId','oriTopicId','topic_id'))
            name = str(self._try_get(item, 'topicName','name','title','oriTopicName','topic_name','topic'))
            img = str(self._try_get(item, 'topicPic','topicImg','img','cover','imageUrl','pic','thumb','image','topic_img','oriTopicImg'))
            cnt = str(self._try_get(item, 'videoCount','count','contentCount','totalCount','total','video_count'))
            if not tid or tid in seen:
                continue
            seen.add(tid)
            results.append({
                'vod_id': 'topic_' + tid + '@',
                'vod_name': name or ('专题'+tid),
                'vod_pic': self.get_proxy_image_url(img or self.host+'/favicon.ico'),
                'vod_tag': 'folder',
                'vod_remarks': f'{cnt}部' if cnt else ''
            })
        return results

    def _parse_video(self, item):
        if item.get('contentType') is not None and item.get('contentType') != 1:
            return None
        vid = str(self._try_get(item, 'contentId','id','videoId'))
        title = self._try_get(item, 'title','name','videoTitle')
        pic = self._try_get(item, 'img','cover','coverUrl','pic','imageUrl')
        remarks = self._try_get(item, 'duration','playCount','remark')
        if remarks and str(remarks).isdigit():
            remarks = self._fmt_duration(remarks)
        return {
            'vod_id': vid,
            'vod_name': title,
            'vod_pic': self.get_proxy_image_url(pic) if pic else '',
            'vod_remarks': str(remarks) if remarks else ''
        }

    def detailContent(self, ids):
        did = ids[0] if isinstance(ids, list) else ids
        # 本地视频详情
        if did.startswith('local_'):
            parts = did.split('#ID#')
            if len(parts) != 2:
                return {'list': []}
            db_key, vid = parts[0].replace('local_', ''), parts[1]
            return self._local_detail(db_key, vid)
        # 蜜桃在线详情
        self._select_best_site()
        self._ensure_session()
        resp = self._api_request('/ht/content/detail', {'contentId': str(did)})
        if not resp or resp.get('code') != 10000:
            return {'list': []}
        detail = resp.get('data', {})
        if not detail:
            return {'list': []}
        title = self._try_get(detail, 'title','name','videoTitle') or '未知标题'
        pic = self._try_get(detail, 'cover','coverUrl','img','imageUrl')
        desc = self._try_get(detail, 'description','desc','intro')
        duration = detail.get('duration', 0)
        actor = self._try_get(detail, 'actor','actors')
        play_url = self._try_get(detail, 'videoUrl','playUrl','url','m3u8Url','sl')
        vod_play_url = '播放$' + (play_url or str(did))
        return {'list': [{
            'vod_id': str(did),
            'vod_name': title,
            'vod_pic': self.get_proxy_image_url(pic) if pic else '',
            'vod_actor': str(actor) if actor else '',
            'vod_director': '',
            'vod_content': desc,
            'vod_year': '',
            'vod_area': '',
            'vod_remarks': self._fmt_duration(duration),
            'vod_play_from': '蜜桃视频',
            'vod_play_url': vod_play_url,
            'type': 'video',
        }]}

    def _local_detail(self, db_key, vid):
        conn = self._get_db_connection(db_key)
        if not conn:
            return {'list': []}
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM videos WHERE vod_id = ?", (vid,))
            row = cur.fetchone()
            if not row:
                conn.close()
                return {'list': []}
            # 获取演员和标签
            actors = ""
            try:
                cur.execute("SELECT a.name FROM actresses a JOIN video_actress va ON a.cate_id = va.cate_id WHERE va.vod_id = ?", (vid,))
                actors = ",".join([r[0] for r in cur.fetchall()])
            except:
                pass
            tags = ""
            try:
                cur.execute("SELECT t.tag_name FROM tags t JOIN video_tag vt ON t.tag_name = vt.tag_name WHERE vt.vod_id = ?", (vid,))
                tags = ",".join([r[0] for r in cur.fetchall()])
            except:
                pass
            raw_play = row["m3u8_url"] or row["vod_play_url"] or ""
            conn.close()
            return {'list': [{
                'vod_id': f"local_{db_key}#ID#{vid}",
                'vod_name': row["title"] or vid,
                'vod_pic': row["pic_url"] or "",
                'vod_actor': actors,
                'vod_director': '',
                'vod_content': row["vod_content"] or "",
                'vod_remarks': row["vod_remarks"] or "",
                'vod_pubdate': row["vod_pubdate"] or "",
                'vod_area': row["vod_area"] or "",
                'vod_year': row["vod_year"] or "",
                'vod_tags': tags,
                'vod_play_from': '本地播放',
                'vod_play_url': json.dumps({'actor': actors, 'title': row["title"] or vid}, ensure_ascii=False),
                'type': 'video'
            }]}
        except Exception as e:
            log(f"本地详情获取失败: {e}")
            try:
                conn.close()
            except:
                pass
            return {'list': []}

    def searchContent(self, key, quick, pg=1):
        self._select_best_site()
        self._ensure_session()
        pg = int(pg)
        resp = self._api_request('/ht/content/search', {'keywords': key, 'pageNo': pg-1, 'pageSize': 20})
        if not resp or resp.get('code') != 10000:
            return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 0, 'total': 0}
        data = resp.get('data', {})
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get('searchList') or data.get('list') or data.get('data') or data.get('videoList') or data.get('records') or data.get('resultList') or data.get('content') or []
        else:
            items = []
        if not isinstance(items, list):
            return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 0, 'total': 0}
        vod_list = []
        for v in items:
            if isinstance(v, dict) and v.get('contentType') is None:
                v['contentType'] = 1
            p = self._parse_video(v)
            if p:
                vod_list.append(p)
        total_page = int(data.get('totalPage') or 1) if isinstance(data, dict) else max(1, len(vod_list)//20)
        return {'list': vod_list, 'page': pg, 'pagecount': total_page, 'limit': len(vod_list), 'total': total_page*20}

    def playerContent(self, flag, id, vipFlags=None):
        # 本地播放
        if flag == '本地播放':
            try:
                info = json.loads(id)
                actress = info.get('actor', '')
                title = info.get('title', '')
                local_url = self._find_local_play_url(actress, title)
                if local_url:
                    headers = {"User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; MIbox PRO Build/PI)"}
                    if local_url.lower().endswith('.m3u8'):
                        from urllib.parse import urlparse
                        parsed = urlparse(local_url)
                        headers["Referer"] = f"{parsed.scheme}://{parsed.netloc}/"
                    return {'parse': 0, 'url': local_url, 'jx': 0, 'header': headers}
                else:
                    log(f"本地未匹配到视频: {actress} - {title}")
                    return {'parse': 0, 'url': '', 'jx': 0}
            except Exception as e:
                log(f"本地播放处理失败: {e}")
                return {'parse': 0, 'url': '', 'jx': 0}

        # 在线播放
        url = id.split('$')[-1]
        if url.startswith('http'):
            return {'parse':0, 'url':url, 'jx':0, 'header':{'User-Agent':self.headers['User-Agent'], 'Referer':self.host+'/'}}
        self._select_best_site()
        self._ensure_session()
        resp = self._api_request('/ht/content/detail', {'contentId': url})
        if not resp or resp.get('code') != 10000:
            return {'parse':0, 'url':'', 'jx':0}
        detail = resp.get('data', {})
        play_url = self._try_get(detail, 'videoUrl','playUrl','url','m3u8Url','sl')
        return {'parse':0, 'url':play_url or '', 'jx':0, 'header':{'User-Agent':self.headers['User-Agent'], 'Referer':self.host+'/'}}

    def localProxy(self, params):
        try:
            if params.get('type') != PROXY_TYPE:
                return [404, 'text/plain', 'not found']
            img_url = params.get('url', '')
            if not img_url:
                return [400, 'text/plain', 'missing url']
            img_url = unquote(img_url)
            r = requests.get(img_url, headers={'User-Agent':self.headers['User-Agent'], 'Referer':self.host+'/'}, timeout=TIMEOUT, verify=False)
            if r.status_code != 200:
                return [404, 'text/plain', 'image not found']
            data = r.content
            if data[:2] != b'\xff\xd8' and data[:4] != b'\x89PNG' and not (data[:4]==b'RIFF' and data[8:12]==b'WEBP'):
                decoded = bytes(b ^ 0x88 for b in data)
                if decoded[:2] == b'\xff\xd8' or decoded[:4] == b'\x89PNG' or (decoded[:4]==b'RIFF' and decoded[8:12]==b'WEBP'):
                    data = decoded
            if data[:2] == b'\xff\xd8':
                return [200, 'image/jpeg', data, {'Content-Length': str(len(data))}]
            elif data[:4] == b'\x89PNG':
                return [200, 'image/png', data, {'Content-Length': str(len(data))}]
            elif data[:4] == b'RIFF' and data[8:12] == b'WEBP':
                return [200, 'image/webp', data, {'Content-Length': str(len(data))}]
            else:
                mime = r.headers.get('Content-Type', 'image/jpeg')
                if mime.startswith('image/'):
                    return [200, mime, data, {'Content-Length': str(len(data))}]
                return [404, 'text/plain', 'invalid image format']
        except Exception as e:
            log(f"图片代理错误: {e}")
            return [500, 'text/plain', 'proxy error']