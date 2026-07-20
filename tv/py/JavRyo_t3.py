# JavRyo 视频源
# 支持搜索、分类浏览、播放解析

# coding=utf-8
# !/usr/bin/python

import sys
sys.path.append('..')

from base.spider import BaseSpider
import requests
from urllib.parse import quote
try:
    from curl_cffi import requests as cf_requests
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False
import json
import base64
import hashlib
import secrets
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from Crypto.Cipher import AES
from base.htmlParser import jsoup
import re
import os
from datetime import datetime

TIMEOUT = 10
try:
    LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'error.log')
except Exception:
    LOG_FILE = os.path.join(os.getcwd(), 'error.log')


class Spider(BaseSpider):
    def getName(self):
        return "JavRyo"

    filterable = False
    searchable = True
    host = 'https://javryo.com'
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
    }

    def init(self, extend=""):
        print("============{0}============".format(extend))
        print("[JavRyo] log file: {}".format(LOG_FILE))

    def _log(self, msg):
        line = "[{}] {}\n".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), msg)
        try:
            with open(LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(line)
        except Exception:
            pass
        print(msg)

    def getDependence(self):
        return []

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def homeContent(self, filter):
        result = {}
        class_names = '全部&最新&热门'.split('&')
        class_urls = 'movies&movies?orderby=date&movies?orderby=views'.split('&')
        classes = []
        for i in range(len(class_names)):
            classes.append({
                'type_name': class_names[i],
                'type_id': class_urls[i]
            })
        result['class'] = classes
        result['type'] = '视频'
        return result

    def homeVideoContent(self):
        return {'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        url = '{}/{}/page/{}/'.format(self.host, tid, pg)
        r = requests.get(url, headers=self.headers, timeout=TIMEOUT, verify=False)
        jsp = jsoup(url)
        pdfh = jsp.pdfh
        pd = jsp.pd
        data = jsp.pdfa(r.text, 'article.item')
        d = []
        for it in data:
            d.append({
                "vod_name": pdfh(it, '.data&&h3&&Text'),
                "vod_id": pd(it, '.poster&&a&&href'),
                "vod_remarks": pdfh(it, '.year&&Text'),
                "vod_pic": pd(it, '.poster&&img&&src'),
            })
        return {'list': d, 'page': pg, 'pagecount': 999, 'limit': 20, 'total': 999999}

    def detailContent(self, ids):
        url = ids[0]
        r = requests.get(url, headers=self.headers, timeout=TIMEOUT, verify=False)
        jsp = jsoup(url)
        pdfh = jsp.pdfh
        pd = jsp.pd
        html = r.text

        vod = {}
        vod['vod_name'] = pdfh(html, '.sheader&&h1&&Text')
        vod['vod_pic'] = pd(html, '.poster&&img&&src')
        vod['vod_content'] = pdfh(html, '.wp-content&&Text')
        vod['vod_year'] = pdfh(html, '.date&&Text')
        vod['vod_area'] = ''
        vod['vod_actor'] = pdfh(html, '.sgeneros&&Text')
        vod['vod_director'] = ''
        vod['vod_remarks'] = pdfh(html, '.year&&Text')
        vod['vod_play_from'] = 'JavRyo'

        player_options = jsp.pdfa(html, '#playeroptionsul&&li')
        lists = []
        for idx, option in enumerate(player_options):
            data_post = pdfh(option, 'li&&data-post')
            data_nume = pdfh(option, 'li&&data-nume')
            data_type = pdfh(option, 'li&&data-type')
            title = pdfh(option, 'span.title&&Text') or '播放{}'.format(idx + 1)
            lists.append('{}${}@@{}@@{}'.format(title, data_post, data_nume, data_type))

        vod['vod_play_url'] = '#'.join(lists)
        return {'list': [vod]}

    def searchContent(self, key, quick, pg=1):
        url = '{}/page/{}/?s={}'.format(self.host, pg, key)
        r = requests.get(url, headers=self.headers, timeout=TIMEOUT, verify=False)
        jsp = jsoup(url)
        pdfh = jsp.pdfh
        pd = jsp.pd
        data = jsp.pdfa(r.text, 'article.item')
        d = []
        for it in data:
            d.append({
                'vod_name': pdfh(it, '.data&&h3&&Text'),
                'vod_remarks': pdfh(it, '.year&&Text'),
                'vod_pic': pd(it, '.poster&&img&&src'),
                'vod_id': pd(it, '.poster&&a&&href'),
            })
        return {'list': d}

    def playerContent(self, flag, id, vipFlags=None):
        parts = id.split('@@')
        data_post = parts[0]
        data_nume = parts[1]
        data_type = parts[2]

        self._log('[player] === 开始播放解析 post={} nume={} type={}'.format(data_post, data_nume, data_type))

        ajax_url = '{}/wp-admin/admin-ajax.php'.format(self.host)
        ajax_data = {
            'action': 'doo_player_ajax',
            'post': data_post,
            'nume': data_nume,
            'type': data_type
        }
        r = requests.post(ajax_url, data=ajax_data, headers=self.headers, timeout=TIMEOUT, verify=False)
        ajax_json = r.json()
        iframe_url = ajax_json.get('embed_url', '')
        self._log('[player] iframe_url={}'.format(iframe_url))

        if not iframe_url:
            self._log('[player] iframe_url 为空')
            return {"parse": 0, "playUrl": '', "url": ''}

        if 'abysscdn.com' in iframe_url or 'short.icu' in iframe_url:
            return self._parse_abysscdn(iframe_url)

        return self._parse_embed4me(iframe_url)

    # ── Server 2: abysscdn ──────────────────────────────────────────────
    def _parse_abysscdn(self, embed_url):
        try:
            # 先尝试从 URL 提取 slug（支持 ?v=slug 和 short.icu/{slug} 两种格式）
            slug = None

            # 格式1: abysscdn.com/?v=slug
            m = re.search(r'[?&]v=([A-Za-z0-9_-]+)', embed_url)
            if m:
                slug = m.group(1)

            # 格式2: short.icu/{slug} 路径形式
            if not slug:
                m2 = re.search(r'short\.icu/([A-Za-z0-9_-]+)', embed_url)
                if m2:
                    slug = m2.group(1)

            # 格式3: 跟随跳转再提取
            if not slug and 'short.icu' in embed_url:
                r = requests.get(embed_url, headers=self.headers, timeout=TIMEOUT,
                                 verify=False, allow_redirects=True)
                final_url = r.url
                self._log('[abysscdn] short.icu 跳转后: {}'.format(final_url))
                m3 = re.search(r'[?&]v=([A-Za-z0-9_-]+)', final_url)
                if m3:
                    slug = m3.group(1)

            if not slug:
                self._log('[abysscdn] 无法提取 slug, embed_url={}'.format(embed_url))
                return {"parse": 0, "playUrl": '', "url": ''}

            # 用 curl_cffi 模拟浏览器 TLS 指纹绕过 CF
            info_headers = {
                'Accept': 'application/json, */*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://abysscdn.com/?v={}'.format(slug),
                'Origin': 'https://abysscdn.com',
                'x-client-screen': '1920x1080',
                'x-referer': self.host + '/',
            }
            if HAS_CURL_CFFI:
                r2 = cf_requests.get('https://abysscdn.com/info/{}'.format(slug),
                                     headers=info_headers, impersonate='chrome120', timeout=TIMEOUT)
            else:
                r2 = requests.get('https://abysscdn.com/info/{}'.format(slug),
                                  headers={**self.headers, **info_headers}, timeout=TIMEOUT, verify=False)
            self._log('[abysscdn] info HTTP {} body前100={}'.format(r2.status_code, r2.text[:100]))
            data = r2.json()
            self._log('[abysscdn] info HTTP {} user_id={} md5_id={}'.format(
                r2.status_code, data.get('user_id'), data.get('md5_id')))

            user_id = str(data['user_id'])
            md5_id = str(data['md5_id'])
            media_bytes = data['media'].encode('latin-1')

            key_str = '{}:{}:{}'.format(user_id, slug, md5_id)
            key = hashlib.md5(key_str.encode()).hexdigest().encode()
            iv_int = int.from_bytes(key[:16], 'big')
            cipher = AES.new(key, AES.MODE_CTR, initial_value=iv_int, nonce=b'')
            media_json = json.loads(cipher.decrypt(media_bytes).decode('utf-8'))
            self._log('[abysscdn] media 解密成功')

            frist = media_json.get('mp4', {}).get('fristDatas', [])
            if not frist:
                self._log('[abysscdn] fristDatas 为空')
                return {"parse": 0, "playUrl": '', "url": ''}

            fd_url = frist[0]['url']
            fd_size = frist[0]['size']
            self._log('[abysscdn] fd_url={} size(nominal)={}'.format(fd_url, fd_size))

            # 探测真实文件大小（size 字段是混淆值，不是真实大小）
            probe_headers = {
                'User-Agent': self.headers['User-Agent'],
                'Referer': 'https://abysscdn.com/',
                'Range': 'bytes=0-0',
            }
            if HAS_CURL_CFFI:
                probe_r = cf_requests.get(fd_url, headers=probe_headers, impersonate='chrome120', timeout=TIMEOUT)
            else:
                probe_r = requests.get(fd_url, headers=probe_headers, timeout=TIMEOUT, verify=False)
            cr = probe_r.headers.get('Content-Range', '')
            # Content-Range: bytes 0-0/14680064
            m_cr = re.search(r'/(\d+)', cr)
            if m_cr:
                real_size = int(m_cr.group(1))
                self._log('[abysscdn] 真实文件大小={}'.format(real_size))
            else:
                real_size = fd_size
                self._log('[abysscdn] 无法探测真实大小，使用 nominal size')

            data_b64 = base64.b64encode(json.dumps({
                'fd_url': fd_url,
                'fd_size': real_size,
            }, separators=(',', ':')).encode()).decode()

            base_proxy = self.getProxyUrl()
            if not base_proxy:
                base_proxy = 'http://127.0.0.1:9980/proxy?do=py'
            proxy_url = base_proxy + '&type=abysscdn&data=' + quote(data_b64, safe='')
            self._log('[abysscdn] proxy_url={}'.format(proxy_url[:80]))

            return {
                "parse": 0,
                "playUrl": '',
                "url": proxy_url,
                "header": json.dumps({'User-Agent': self.headers['User-Agent']}),
            }
        except Exception as e:
            self._log('[abysscdn] 解析失败: {}'.format(e))
            return {"parse": 0, "playUrl": '', "url": ''}

    # ── Server 1: embed4me ────────────────────────────────────────────
    def _parse_embed4me(self, iframe_url):
        try:
            m = re.search(r'embed4me\.com/(?:e/|#)([A-Za-z0-9_-]+)', iframe_url)
            if not m:
                self._log('[embed4me] 无法提取 video_id, url={}'.format(iframe_url))
                return {"parse": 0, "playUrl": '', "url": ''}
            video_id = m.group(1)
            self._log('[embed4me] video_id={}'.format(video_id))

            cdn_domains = [
                'https://svb.documentationhubsite.site',
                'https://sdqm.gameaddict.shop',
                'https://s6d.supplymarketplace.shop',
                'https://s6d.clarionbranding.cyou',
            ]

            path_patterns = ['is9', 'pp', '8q', 'il']

            timestamps = ['1779967351', '1781548403', '1782499627', '1782997159']

            for domain in cdn_domains:
                for path_part in path_patterns:
                    for ts in [''] + timestamps:
                        ts_suffix = '.' + ts if ts else ''
                        master_url = '{}/v4/{}/{}/cf-master{}.txt'.format(domain, path_part, video_id, ts_suffix)
                        master_headers = {
                            'User-Agent': self.headers['User-Agent'],
                            'Referer': 'https://javryo.embed4me.com/',
                        }
                        try:
                            master_r = requests.get(master_url, headers=master_headers, timeout=TIMEOUT, verify=False)
                            if master_r.status_code == 200:
                                master_content = master_r.text
                                if '#EXTM3U' in master_content:
                                    self._log('[embed4me] 获取播放列表成功, url={}'.format(master_url))

                                    stream_url = ''
                                    high_res_pattern = r'RESOLUTION=1920x1080.*?\n([^\n]+)'
                                    match_high = re.search(high_res_pattern, master_content, re.DOTALL)
                                    if match_high:
                                        stream_url = match_high.group(1).strip()
                                        self._log('[embed4me] 找到1080p流: {}'.format(stream_url))
                                    else:
                                        match_low = re.search(r'RESOLUTION=1280x720.*?\n([^\n]+)', master_content, re.DOTALL)
                                        if match_low:
                                            stream_url = match_low.group(1).strip()
                                            self._log('[embed4me] 找到720p流: {}'.format(stream_url))

                                    if stream_url:
                                        if not stream_url.startswith('http'):
                                            stream_url = '{}/v4/{}/{}/{}'.format(domain, path_part, video_id, stream_url)

                                        self._log('[embed4me] 解析成功, m3u8_url={}'.format(stream_url))
                                        return {
                                            "parse": 0,
                                            "playUrl": '',
                                            "url": stream_url,
                                            "header": json.dumps({'User-Agent': self.headers['User-Agent'], 'Referer': 'https://javryo.embed4me.com/'})
                                        }
                        except Exception as e:
                            pass

            self._log('[embed4me] 所有路径模式都无法获取播放列表')
            return {"parse": 0, "playUrl": '', "url": ''}

        except Exception as e:
            self._log('[embed4me] 解析失败: {}'.format(e))
            return {"parse": 0, "playUrl": '', "url": ''}

    def localProxy(self, params):
        """
        abysscdn .fd 文件流式解密代理
        params 由框架从 URL query 解析而来，结构如:
        {'do': 'py', 'type': 'abysscdn', 'data': '<base64json>'}
        """
        try:
            if params.get('type') != 'abysscdn':
                return [404, 'text/plain', 'not found']

            data_b64 = params.get('data', '')
            # URL decode 再补齐 base64 padding
            from urllib.parse import unquote
            data_b64 = unquote(data_b64)
            padding = 4 - len(data_b64) % 4
            if padding != 4:
                data_b64 += '=' * padding
            info = json.loads(base64.b64decode(data_b64).decode())
            fd_url = info['fd_url']
            fd_size = info['fd_size']

            # key = MD5(filename).hexdigest().encode('utf-8') → 32字节 AES-256-CTR
            # 只有前 65536 字节加密，后续明文
            ENCRYPT_SIZE = 65536
            fd_filename = fd_url.split('/')[-1]
            key_bytes = hashlib.md5(fd_filename.encode('utf-8')).hexdigest().encode('utf-8')

            range_header = params.get('range', '')
            CHUNK = 2 * 1024 * 1024
            byte_start = 0
            byte_end = fd_size - 1
            if range_header:
                m = re.match(r'bytes=(\d+)-(\d*)', range_header)
                if m:
                    byte_start = int(m.group(1))
                    byte_end = int(m.group(2)) if m.group(2) else min(byte_start + CHUNK - 1, fd_size - 1)
            else:
                byte_end = min(CHUNK - 1, fd_size - 1)

            self._log('[localProxy] range={}-{} total={}'.format(byte_start, byte_end, fd_size))

            dl_headers = {
                'User-Agent': self.headers['User-Agent'],
                'Referer': 'https://abysscdn.com/',
                'Range': 'bytes={}-{}'.format(byte_start, byte_end),
            }
            if HAS_CURL_CFFI:
                r = cf_requests.get(fd_url, headers=dl_headers, impersonate='chrome120', timeout=30)
            else:
                r = requests.get(fd_url, headers=dl_headers, timeout=30, verify=False)
            self._log('[localProxy] CDN HTTP={} size={}'.format(r.status_code, len(r.content)))
            raw = r.content

            if not raw:
                return [500, 'text/plain', 'empty response from CDN']

            # 只解密落在 [0, ENCRYPT_SIZE) 范围内的字节
            if byte_start < ENCRYPT_SIZE:
                enc_end = min(len(raw), ENCRYPT_SIZE - byte_start)
                enc_part = raw[:enc_end]
                # AES-CTR: counter 从 key[:16] 开始，按 byte_start 偏移
                block_offset = byte_start // 16
                byte_in_block = byte_start % 16
                initial_counter = int.from_bytes(key_bytes[:16], 'big') + block_offset
                cipher = AES.new(key_bytes, AES.MODE_CTR, initial_value=initial_counter, nonce=b'')
                if byte_in_block > 0:
                    cipher.decrypt(b'\x00' * byte_in_block)
                decrypted = cipher.decrypt(enc_part) + raw[enc_end:]
            else:
                decrypted = raw  # 超出加密范围，明文直接输出

            chunk_len = len(decrypted)
            actual_end = byte_start + chunk_len - 1
            self._log('[localProxy] 解密完成 {} bytes'.format(chunk_len))

            resp_headers = {
                'Content-Type': 'video/mp4',
                'Content-Length': str(chunk_len),
                'Accept-Ranges': 'bytes',
                'Content-Range': 'bytes {}-{}/{}'.format(byte_start, actual_end, fd_size),
            }
            return [206, 'video/mp4', decrypted, resp_headers]

        except Exception as e:
            self._log('[localProxy] 错误: {}'.format(e))
            return [500, 'text/plain', str(e)]
