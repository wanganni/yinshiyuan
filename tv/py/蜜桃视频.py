# coding=utf-8
# !/usr/bin/python
# 蜜桃视频 T3 爬虫（完全合并涩库引擎 + 指定扫描目录）
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
from urllib.parse import quote, unquote, urlparse
from Crypto.Cipher import AES
import concurrent.futures

# ========== 蜜桃配置 ==========
TIMEOUT = 10
SITES_REMOTE_URL = ""
SITES = [
    {'name': 'nht966', 'host': 'https://www.nhtv523phht.vip:9527'},
    {'name': 'httre666', 'host': 'https://www.newhttestre666.cc'},
]
BACKUP_SITES = [
    {'name': 'backup1', 'host': 'https://www.nhtv523phht.vip:9527'},
    {'name': 'backup2', 'host': 'https://www.mitao666.cc'},
]
SIGN_KEY  = 'opum3_Loily$SV^6H'
BUNDLE_ID = 'com.ht9.web20.video'
BRAND_ID  = 'hongtao'
VERSION   = '1.0.0'
PROJECT_ID = '1'
PROXY_TYPE = 'mitao_img'

def log(msg):
    print(f"[蜜桃] {time.strftime('%H:%M:%S')} {msg}")

# ========== 涩库引擎（完整合并，仅修改扫描目录） ==========
class SikuEngine:
    DB_DIRS = [
        "/storage/emulated/0/纯福利/db/",
        "/storage/emulated/0/女优库/",
        "/storage/emulated/0/私藏视频/",
        "/storage/emulated/0/lz/db/"
    ]
    DEFAULT_COVER = "https://cloud.7so.top/f/p8PPHA/%E5%90%88%E9%9B%86.png"
    MOVIE_ICON = "https://img.icons8.com/color/512/movie.png"

    def __init__(self):
        self._db_cache = {}
        self.databases = {}
        self.sub_icons = {}

    def init(self, extend=""):
        self._auto_scan_databases()
        icon_config_path = "/storage/emulated/0/私藏视频/二级分类.json"
        if os.path.exists(icon_config_path):
            try:
                with open(icon_config_path, 'r', encoding='utf-8') as f:
                    self.sub_icons = json.load(f)
            except:
                pass

    def _auto_scan_databases(self):
        seen_paths = set()
        for d in self.DB_DIRS:
            if not os.path.exists(d):
                continue
            for root, _, files in os.walk(d):
                for file in files:
                    if file.endswith(".db"):
                        full_path = os.path.join(root, file)
                        abs_path = os.path.abspath(full_path)
                        if abs_path in seen_paths:
                            continue
                        seen_paths.add(abs_path)
                        db_key = f"auto_{file}"
                        if db_key in self.databases:
                            db_key = f"auto_{os.path.basename(root)}_{file}"
                        self.databases[db_key] = {"name": file, "path": abs_path}

    def _get_connection(self, db_key):
        info = self.databases.get(db_key)
        if not info or not os.path.exists(info["path"]):
            return None
        conn = sqlite3.connect(info["path"])
        conn.row_factory = sqlite3.Row
        return conn

    def _is_exclusive_db(self, conn):
        try:
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='video_actress'")
            return cur.fetchone() is not None
        except:
            return False

    # ==================== 首页（数据库列表） ====================
    def homeContent(self, filter):
        classes = []
        for db_key, db_info in self.databases.items():
            name = os.path.splitext(db_info['name'])[0]
            conn = self._get_connection(db_key)
            count_str = ""
            if conn:
                try:
                    if self._is_exclusive_db(conn):
                        cur = conn.cursor()
                        cur.execute("SELECT COUNT(*) FROM videos")
                        total = cur.fetchone()[0]
                        count_str = f" ({total})"
                except:
                    pass
                finally:
                    conn.close()
            classes.append({
                "type_id": f"siku:{db_key}",  # 涩库内部路径前缀
                "type_name": f"{name}{count_str}",
                "type_pic": self.DEFAULT_COVER,
                "pic": self.DEFAULT_COVER,
                "icon": self.DEFAULT_COVER,
                "vod_pic": self.DEFAULT_COVER
            })
        return {"class": classes}

    # ==================== 分类内容 ====================
    def categoryContent(self, tid, pg, filter=None, extend=None):
        """tid 格式: siku:db_key$sub..."""
        if tid.startswith("siku:"):
            tid = tid[5:]
        parts = tid.split('$')
        db_key = parts[0]
        conn = self._get_connection(db_key)
        if not conn:
            return {"list": []}
        if self._is_exclusive_db(conn):
            result = self._exclusive_category(conn, db_key, parts, pg)
        else:
            result = self._legacy_category(conn, db_key, parts, pg)
        conn.close()
        # 所有返回的 vod_id 添加前缀 siku: 以便蜜桃路由
        for vod in result.get('list', []):
            if 'vod_id' in vod:
                vod['vod_id'] = f"siku:{vod['vod_id']}"
        return result

    def _exclusive_category(self, conn, db_key, parts, pg):
        class_id = parts[1] if len(parts) > 1 else ""
        sub_name = parts[2] if len(parts) > 2 else ""

        if not class_id:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM video_actress")
            actress_cnt = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM videos")
            video_total = cur.fetchone()[0]

            vod_list = [
                {"vod_id": f"{db_key}$actor_ranking", "vod_name": f"演员榜 ({actress_cnt})", "vod_pic": self.DEFAULT_COVER, "vod_tag": "folder"},
                {"vod_id": f"{db_key}$video_ranking", "vod_name": f"影片榜 ({video_total})", "vod_pic": self.DEFAULT_COVER, "vod_tag": "folder"},
            ]
            return {"page": 1, "pagecount": 2, "limit": 20, "list": vod_list}

        if class_id == "actor_ranking":
            if not sub_name:
                return self._list_actresses(conn, db_key, pg)
            else:
                return self._list_videos_by_actress(conn, db_key, sub_name, pg)

        elif class_id == "video_ranking":
            if not sub_name:
                return self._list_video_ranking(conn, db_key, pg)
            else:
                return self._list_videos_by_category(conn, db_key, sub_name, pg)

        elif class_id == "actress":
            if not sub_name:
                return self._list_actresses(conn, db_key, pg)
            else:
                return self._list_videos_by_actress(conn, db_key, sub_name, pg)

        elif class_id == "video_cate":
            if not sub_name:
                return self._list_hot_videos(conn, db_key, pg)
            else:
                return self._list_videos_by_category(conn, db_key, sub_name, pg)

        elif class_id == "tag":
            if not sub_name:
                return self._list_categories(conn, db_key, pg, "video_cate")
            else:
                return self._list_videos_by_category(conn, db_key, sub_name, pg)

        return {"list": []}

    def _list_actresses(self, conn, db_key, pg):
        cur = conn.cursor()
        cur.execute("""
            SELECT a.name, a.avatar, COUNT(va.vod_id) as cnt
            FROM actresses a
            LEFT JOIN video_actress va ON a.cate_id = va.cate_id
            GROUP BY a.cate_id HAVING cnt > 0
            ORDER BY cnt DESC
        """)
        rows = cur.fetchall()
        return self._paginate_dirs(rows, pg, db_key, "actor_ranking")

    def _list_hot_videos(self, conn, db_key, pg):
        cur = conn.cursor()
        cur.execute("""
            SELECT v.title, v.pic_url, COUNT(vr.vod_id) as cnt
            FROM videos v
            JOIN video_ranking vr ON v.vod_id = vr.vod_id
            GROUP BY v.vod_id
            ORDER BY cnt DESC
            LIMIT 100
        """)
        rows = cur.fetchall()
        if not rows:
            cur.execute("SELECT title, pic_url, 1 as cnt FROM videos ORDER BY created_at DESC LIMIT 100")
            rows = cur.fetchall()
        limit = 20
        page = int(pg)
        start = (page - 1) * limit
        paged = rows[start:start+limit]
        vod_list = []
        for r in paged:
            name = r[0]
            pic = r[1] if r[1] else self.MOVIE_ICON
            vod_list.append({
                "vod_id": f"{db_key}$video_cate${name}",
                "vod_name": name,
                "vod_pic": pic,
                "vod_tag": "video"
            })
        return {"page": page, "pagecount": page+1, "limit": limit, "list": vod_list}

    def _list_video_ranking(self, conn, db_key, pg):
        cur = conn.cursor()
        cur.execute("""
            SELECT v.vod_id, v.title, v.pic_url, COUNT(vr.vod_id) as cnt
            FROM videos v
            JOIN video_ranking vr ON v.vod_id = vr.vod_id
            GROUP BY v.vod_id
            ORDER BY cnt DESC
            LIMIT 100
        """)
        rows = cur.fetchall()
        if not rows:
            cur.execute("SELECT vod_id, title, pic_url, 1 as cnt FROM videos ORDER BY created_at DESC LIMIT 100")
            rows = cur.fetchall()
        limit = 20
        page = int(pg)
        start = (page - 1) * limit
        paged = rows[start:start+limit]
        vod_list = []
        for r in paged:
            vid = r[0]
            name = r[1]
            pic = r[2] if r[2] else self.MOVIE_ICON
            vod_list.append({
                "vod_id": f"{db_key}#ID#{vid}",
                "vod_name": name,
                "vod_pic": pic,
                "vod_tag": "video"
            })
        return {"page": page, "pagecount": page+1, "limit": limit, "list": vod_list}

    def _list_categories(self, conn, db_key, pg, cat_type="video_cate"):
        cur = conn.cursor()
        cur.execute("SELECT main_category, COUNT(*) as cnt FROM video_category GROUP BY main_category ORDER BY cnt DESC")
        rows = cur.fetchall()
        limit = 20
        page = int(pg)
        start = (page - 1) * limit
        paged = rows[start:start+limit]
        vod_list = []
        for r in paged:
            cat = r[0]
            cnt = r[1]
            vod_list.append({
                "vod_id": f"{db_key}${cat_type}${cat}",
                "vod_name": f"{cat} ({cnt})",
                "vod_pic": self.DEFAULT_COVER,
                "vod_tag": "folder"
            })
        return {"page": page, "pagecount": page+1, "limit": limit, "list": vod_list}

    def _list_videos_by_category(self, conn, db_key, category_val, pg):
        limit = 20
        page = int(pg)
        offset = (page - 1) * limit
        cur = conn.cursor()
        cur.execute("""
            SELECT v.vod_id, v.title, v.pic_url, v.vod_remarks
            FROM videos v
            JOIN video_category vc ON v.vod_id = vc.vod_id
            WHERE vc.main_category = ?
            LIMIT ? OFFSET ?
        """, (category_val, limit, offset))
        rows = cur.fetchall()
        vod_list = []
        for r in rows:
            pic = r[2] if r[2] else self.MOVIE_ICON
            vod_list.append({
                "vod_id": f"{db_key}#ID#{r[0]}",
                "vod_name": r[1] or r[0],
                "vod_pic": pic,
                "vod_remarks": r[3] or ""
            })
        return {"page": page, "pagecount": page+1, "limit": limit, "list": vod_list}

    def _list_videos_by_actress(self, conn, db_key, actress_name, pg):
        limit = 20
        page = int(pg)
        offset = (page - 1) * limit
        cur = conn.cursor()
        cur.execute("""
            SELECT v.vod_id, v.title, v.pic_url, v.vod_remarks
            FROM videos v
            JOIN video_actress va ON v.vod_id = va.vod_id
            JOIN actresses a ON va.cate_id = a.cate_id
            WHERE a.name = ?
            LIMIT ? OFFSET ?
        """, (actress_name, limit, offset))
        rows = cur.fetchall()
        vod_list = []
        for r in rows:
            pic = r[2] if r[2] else self.MOVIE_ICON
            vod_list.append({
                "vod_id": f"{db_key}#ID#{r[0]}",
                "vod_name": r[1] or r[0],
                "vod_pic": pic,
                "vod_remarks": r[3] or ""
            })
        return {"page": page, "pagecount": page+1, "limit": limit, "list": vod_list}

    def _paginate_dirs(self, rows, pg, db_key, cat_type):
        limit = 20
        page = int(pg)
        start = (page - 1) * limit
        paged = rows[start:start + limit]
        vod_list = []
        for r in paged:
            name = r[0]
            avatar = r[1] or ""
            cnt = r[2]
            pic = avatar if avatar else self.DEFAULT_COVER
            vod_list.append({
                "vod_id": f"{db_key}${cat_type}${name}",
                "vod_name": f"{name} ({cnt})",
                "vod_pic": pic,
                "vod_tag": "folder"
            })
        return {"page": page, "pagecount": page + 1, "limit": limit, "list": vod_list}

    # ==================== 旧版数据库兼容 ====================
    def _legacy_category(self, conn, db_key, parts, pg):
        curr_path = parts[1] if len(parts) > 1 else ""
        cache_key = f"tree_{db_key}"
        if cache_key not in self._db_cache:
            auto_info = self._get_auto_mapping(conn)
            if not auto_info:
                return {"list": []}
            cursor = conn.cursor()
            table_name = auto_info['table_name']
            mapping = auto_info['field_mapping']

            cursor.execute(f"PRAGMA table_info(`{table_name}`)")
            all_cols = [str(r[1]) for r in cursor.fetchall()]

            filter_field = mapping.get("category_field")
            if not filter_field:
                for cand in ["type_name", "category", "cate_name", "type", "tag", "class_name", "actress_id"]:
                    if cand in all_cols:
                        filter_field = cand
                        break
            if not filter_field:
                self._db_cache[cache_key] = {
                    "types": [], "counts": {}, "field": None,
                    "table": table_name, "mapping": mapping, "avatar_map": {}
                }
                return self._legacy_fetch_video_list(conn, db_key, table_name, mapping, None, None, pg, 20, (int(pg)-1)*20)

            cursor.execute(f"SELECT `{filter_field}`, COUNT(*) FROM `{table_name}` WHERE `{filter_field}` IS NOT NULL GROUP BY `{filter_field}`")
            raw_data = cursor.fetchall()
            type_counts = {str(row[0]): row[1] for row in raw_data}
            avatar_map = {}
            if "actress_avatar" in all_cols:
                try:
                    cursor.execute(
                        f"SELECT `{filter_field}`, `actress_avatar` FROM `{table_name}` "
                        "WHERE `actress_avatar` IS NOT NULL AND `actress_avatar` != ''"
                    )
                    for row in cursor.fetchall():
                        cat_val = str(row[0])
                        avatar_url = row[1]
                        if cat_val not in avatar_map:
                            avatar_map[cat_val] = avatar_url
                except: pass
            self._db_cache[cache_key] = {
                "types": list(type_counts.keys()), "counts": type_counts,
                "field": filter_field, "table": table_name,
                "mapping": mapping, "avatar_map": avatar_map
            }

        db_data = self._db_cache[cache_key]
        all_vals = db_data["types"]
        all_counts = db_data["counts"]
        avatar_map = db_data.get("avatar_map", {})
        filter_field = db_data.get("field")
        if not filter_field:
            return self._legacy_fetch_video_list(conn, db_key, db_data["table"], db_data["mapping"], None, None, pg, 20, (int(pg)-1)*20)

        sub_dirs_info = {}
        for val in all_vals:
            count = all_counts.get(val, 0)
            if curr_path == "":
                d = val.split('/')[0]
                sub_dirs_info[d] = sub_dirs_info.get(d, 0) + count
            elif val.startswith(curr_path + "/"):
                suffix = val[len(curr_path):].lstrip('/')
                if suffix:
                    d = f"{curr_path}/{suffix.split('/')[0]}"
                    sub_dirs_info[d] = sub_dirs_info.get(d, 0) + count

        limit = 20
        offset = (int(pg) - 1) * limit
        if not sub_dirs_info:
            return self._legacy_fetch_video_list(conn, db_key, db_data["table"], db_data["mapping"],
                                                 filter_field, curr_path if curr_path else None, pg, limit, offset)
        if len(sub_dirs_info) == 1:
            single_dir = list(sub_dirs_info.keys())[0]
            has_deeper = any(v.startswith(single_dir + "/") for v in all_vals)
            if not has_deeper:
                return self._legacy_fetch_video_list(conn, db_key, db_data["table"], db_data["mapping"],
                                                     filter_field, single_dir, pg, limit, offset)

        sorted_dirs = sorted(sub_dirs_info.keys(), key=lambda d: (-sub_dirs_info[d], d))
        paged_dirs = sorted_dirs[offset : offset + limit]
        vod_list = []
        for d in paged_dirs:
            display_name = d.split('/')[-1]
            num = sub_dirs_info[d]
            pic = avatar_map.get(d) or self.sub_icons.get(d) or self.sub_icons.get(display_name) or self.DEFAULT_COVER
            vod_list.append({
                "vod_id": f"{db_key}${d}",
                "vod_name": f"{display_name} ({num})",
                "vod_pic": pic,
                "vod_tag": "folder",
                "style": {"type": "rect", "ratio": 1.8}
            })
        return {"page": int(pg), "pagecount": int(pg) + 1, "limit": limit, "list": vod_list}

    def _get_auto_mapping(self, conn):
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = [row[0] for row in cursor.fetchall()]
            if not tables:
                return None
            target_table = next((t for t in ["videos", "vod_unified_data", "cj", "vod", "data", "list", "video_detail"] if t in tables), tables[-1])
            cursor.execute(f"PRAGMA table_info(`{target_table}`)")
            cols = [str(r[1]) for r in cursor.fetchall()]
            mapping = {}
            field_candidates = {
                "vod_id": ["id", "vod_id", "uuid", "guid", "vid"],
                "vod_name": ["name", "vod_name", "title", "subject", "display_name"],
                "vod_pic": ["image", "vod_pic", "pic", "pic_url", "thumbnail", "img", "cover"],
                "vod_play_url": ["play_url", "vod_play_url", "url", "link", "m3u8_url"],
                "vod_remarks": ["vod_remarks", "remarks", "note", "desc"],
                "category_field": ["type_name", "category_id", "class_name", "cate_name", "actress_id", "tag", "type", "category"],
                "vod_actor": ["vod_actor", "actor", "star", "actress", "artist", "performer"],
                "vod_content": ["vod_content", "description", "summary", "intro", "detail", "content"],
                "vod_pubdate": ["vod_pubdate", "pubdate", "release_date", "date"],
                "vod_area": ["vod_area", "area", "region", "country"],
                "vod_year": ["vod_year", "year"],
                "vod_tags": ["vod_tags", "tags", "keywords", "label"],
                "vod_play_from": ["vod_play_from", "play_from", "source"]
            }
            for target_field, candidates in field_candidates.items():
                matches = [cand for cand in candidates if cand in cols]
                mapping[target_field] = matches[0] if matches else None
            return {"table_name": target_table, "field_mapping": mapping}
        except:
            return None

    def _legacy_fetch_video_list(self, conn, db_key, table_name, mapping, filter_field, category_val, pg, limit, offset):
        cursor = conn.cursor()
        vod_list = []
        f_id = mapping.get("vod_id") or "rowid"
        f_name = mapping.get("vod_name") or "rowid"
        f_pic = mapping.get("vod_pic") or "''"
        f_rem = mapping.get("vod_remarks") or "''"
        try:
            if category_val is not None and filter_field is not None:
                sql = f"SELECT `{f_id}`, `{f_name}`, `{f_pic}`, `{f_rem}` FROM `{table_name}` WHERE `{filter_field}` = ? LIMIT ? OFFSET ?"
                cursor.execute(sql, (category_val, limit, offset))
            else:
                sql = f"SELECT `{f_id}`, `{f_name}`, `{f_pic}`, `{f_rem}` FROM `{table_name}` LIMIT ? OFFSET ?"
                cursor.execute(sql, (limit, offset))
            for row in cursor.fetchall():
                pic = str(row[2]) if row[2] else ""
                if not pic:
                    pic = self.MOVIE_ICON
                vod_list.append({
                    "vod_id": f"{db_key}#ID#{row[0]}",
                    "vod_name": str(row[1]),
                    "vod_pic": pic,
                    "vod_remarks": str(row[3]) if len(row) > 3 else ""
                })
        except:
            pass
        return {"page": int(pg), "pagecount": int(pg) + 1, "limit": limit, "list": vod_list}

    # ==================== 详情 ====================
    def detailContent(self, ids):
        mid = ids[0]
        if mid.startswith("siku:"):
            mid = mid[5:]
        if '#ID#' in mid:
            parts = mid.split('#ID#')
            db_key, real_id = parts[0], parts[1]
        elif '#NAME#' in mid:
            parts = mid.split('#NAME#')
            db_key, vod_name = parts[0], parts[1]
            real_id = vod_name
        else:
            return {"list": []}
        conn = self._get_connection(db_key)
        if not conn:
            return {"list": []}
        if self._is_exclusive_db(conn):
            return self._exclusive_detail(conn, db_key, real_id)
        return self._legacy_detail(conn, db_key, real_id)

    def _legacy_detail(self, conn, db_key, real_id):
        auto_info = self._get_auto_mapping(conn)
        if not auto_info:
            conn.close()
            return {"list": []}
        table_name = auto_info["table_name"]
        mapping = auto_info["field_mapping"]
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        id_col = mapping.get("vod_id") or "rowid"
        cursor.execute(f"SELECT * FROM `{table_name}` WHERE `{id_col}` = ?", (real_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return {"list": []}
        def get_val(m_key):
            real_col = mapping.get(m_key)
            return str(row[real_col]) if (real_col and real_col in row.keys() and row[real_col] is not None) else ""
        raw_play_url = get_val("vod_play_url")
        play_url = raw_play_url.split('$$$')[-1] if '$$$' in raw_play_url else raw_play_url
        play_url = self._fix_v_encoded_url(play_url)
        vod = {
            "vod_id": f"siku:{db_key}#ID#{real_id}",
            "vod_name": get_val("vod_name"),
            "vod_pic": get_val("vod_pic"),
            "vod_actor": get_val("vod_actor") or get_val("category_field"),
            "vod_director": "",
            "vod_remarks": get_val("vod_remarks"),
            "vod_pubdate": get_val("vod_pubdate"),
            "vod_area": get_val("vod_area"),
            "vod_year": get_val("vod_year"),
            "vod_tags": get_val("vod_tags"),
            "vod_content": get_val("vod_content") or get_val("vod_remarks"),
            "vod_play_from": get_val("vod_play_from") or "自动识别",
            "vod_play_url": play_url,
            "type_name": get_val("category_field") or get_val("type_name")
        }
        conn.close()
        return {"list": [vod]}

    def _exclusive_detail(self, conn, db_key, vid_or_name):
        cur = conn.cursor()
        cur.execute("SELECT * FROM videos WHERE vod_id = ? OR title = ?", (vid_or_name, vid_or_name))
        row = cur.fetchone()
        if not row:
            conn.close()
            return {"list": []}
        vod_id = row["vod_id"]
        actors, tags = "", ""
        try:
            cur.execute("SELECT a.name FROM actresses a JOIN video_actress va ON a.cate_id = va.cate_id WHERE va.vod_id = ?", (vod_id,))
            actors = ",".join([r[0] for r in cur.fetchall()])
            cur.execute("SELECT t.tag_name FROM tags t JOIN video_tag vt ON t.tag_name = vt.tag_name WHERE vt.vod_id = ?", (vod_id,))
            tags = ",".join([r[0] for r in cur.fetchall()])
        except:
            pass
        raw_play = row["m3u8_url"] or row["vod_play_url"] or ""
        play_url = self._fix_v_encoded_url(raw_play)
        conn.close()
        return {"list": [{
            "vod_id": f"siku:{db_key}#ID#{vod_id}",
            "vod_name": row["title"] or vid_or_name,
            "vod_pic": row["pic_url"] or "",
            "vod_actor": actors,
            "vod_director": "whos.tv",
            "vod_remarks": row["vod_remarks"] or "",
            "vod_pubdate": row["vod_pubdate"] or "",
            "vod_area": row["vod_area"] or "",
            "vod_year": row["vod_year"] or "",
            "vod_tags": tags,
            "vod_content": row["vod_content"] or "",
            "vod_play_from": row["vod_play_from"] or "whos.tv",
            "vod_play_url": play_url,
            "type_name": row["type_name"] or "成人影片"
        }]}

    def _fix_v_encoded_url(self, raw_url):
        if not raw_url:
            return raw_url
        for prefix in ["高清$ ", "高清$", "高清 ", "高清"]:
            if raw_url.startswith(prefix):
                raw_url = raw_url[len(prefix):]
                break
        url = raw_url.replace('://V', '://')
        url = url.replace('V', '/')
        return url

    # ==================== 播放 ====================
    def playerContent(self, flag, id, vipFlags=None):
        playurl = id.split("|")[0]
        playurl = self._fix_v_encoded_url(playurl)
        headers = {"User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; MIbox PRO Build/PI)"}
        if playurl.strip().lower().endswith('.m3u8'):
            try:
                parsed = urlparse(playurl)
                headers["Referer"] = f"{parsed.scheme}://{parsed.netloc}/"
            except:
                pass
        return {"parse": 0, "url": playurl, "header": headers}

    # ==================== 搜索（暂不启用） ====================
    def searchContent(self, key, quick, pg="1"):
        return {"list": [], "page": pg}


# ========== 蜜桃主爬虫（不变） ==========
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

    def __init__(self):
        super().__init__()
        self.siku = SikuEngine()
        self.siku.init()

    # ========== 蜜桃网络功能 ==========
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
        except: pass
        return '', False

    def _save_cached_site(self, host):
        try:
            with open(self._speed_cache_file, 'w') as f:
                json.dump({'host': host, 'ts': time.time()}, f)
        except: pass

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
        except: pass

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
        except: return False

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
        except: return ''
        if s <= 0:
            return ''
        m, s = divmod(s, 60)
        return f"{m}:{s:02d}"

    def init(self, extend=""):
        cached_host, valid = self._get_cached_site()
        if valid:
            self.host = cached_host
            self._speed_test_done = True

    _CATEGORY_BLACKLIST = {'成人游戏', '漫画', '小说', '蜜穴女友', '一键脱衣', '春药商城', '同城交友', '吃瓜', '成人漫画'}

    def homeContent(self, filter):
        self._select_best_site()
        self._ensure_session()
        if not self._categories:
            self._session_inited = False
            self._ensure_session()
        classes, filters = [], {}
        for cat in self._categories:
            cid, title = str(cat.get('contentId', '')), cat.get('title', '')
            if not cid or not title or title in self._CATEGORY_BLACKLIST:
                continue
            classes.append({'type_id': cid, 'type_name': title})
            cat_filters = []
            sub_cats = [v for v in self._video_type_list if str(v.get('typePid', '')) == cid]
            if sub_cats:
                sub_values = [{'n': '全部', 'v': ''}]
                for sc in sub_cats:
                    sc_id, sc_name = str(sc.get('typeId', '')), sc.get('typeName', '')
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
                {'n': '最近更新', 'v': '0'}, {'n': '最多播放', 'v': '1'}, {'n': '最多收藏', 'v': '2'}
            ]})
            if cat_filters:
                filters[cid] = cat_filters
        # 添加涩库分类
        classes.append({'type_id': 'siku', 'type_name': '涩库'})
        filters['siku'] = []
        classes.append({'type_id': 'topic', 'type_name': '专题'})
        home_videos = self.categoryContent('home', 1, '', {})
        return {
            'class': classes, 'filters': filters, 'type': '影视',
            'list': home_videos.get('list', []), 'page': home_videos.get('page', 1),
            'pagecount': home_videos.get('pagecount', 1), 'limit': home_videos.get('limit', 0),
            'total': home_videos.get('total', 0)
        }

    def homeVideoContent(self, tid, pg, filter, extend):
        return self.categoryContent(tid or 'home', pg, filter, extend)

    # ========== 分类路由 ==========
    def categoryContent(self, tid, pg, filter, extend):
        tid, pg = str(tid), int(pg)
        # 涩库首页
        if tid == 'siku':
            siku_home = self.siku.homeContent({})
            vod_list = []
            for cls in siku_home.get('class', []):
                vod_list.append({
                    'vod_id': cls['type_id'],      # 已包含 siku: 前缀
                    'vod_name': cls['type_name'],
                    'vod_pic': cls.get('vod_pic', ''),
                    'vod_tag': 'folder'
                })
            return {'list': vod_list, 'page': 1, 'pagecount': 1, 'limit': len(vod_list), 'total': len(vod_list)}
        # 涩库子分类 (tid 以 siku: 开头)
        if tid.startswith('siku:'):
            return self.siku.categoryContent(tid, pg)

        # 蜜桃在线分类
        if tid.startswith('topic_') and '@' in tid:
            topic_id = tid[len('topic_'):].replace('@', '')
            resp = self._api_request('/ht/content/queryOriTopicVideos', {'topicId': topic_id, 'pageNo': str(pg-1), 'pageSize': '20'})
            if resp and resp.get('code') == 10000:
                vod_list = self._extract_videos_from_data(resp.get('data', {}))
            else:
                vod_list = []
            total_page = max(1, len(vod_list) // 20 + (1 if len(vod_list) % 20 else 0))
            return {'list': vod_list, 'page': pg, 'pagecount': total_page, 'limit': len(vod_list), 'total': len(vod_list)}
        if tid == 'topic':
            resp = self._api_request('/ht/content/getOriTopicList', {'pageNo': str(pg-1), 'pageSize': '20'})
            if resp and resp.get('code') == 10000:
                vod_list = self._parse_topic_list(resp.get('data', {}))
                return {'list': vod_list, 'page': pg, 'pagecount': 50, 'limit': len(vod_list), 'total': len(vod_list)*50}
            return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 0, 'total': 0}
        if tid in ('home', 'new', 'hot'):
            sort_map = {'home':'1','new':'1','hot':'2'}
            resp = self._api_request('/ht/content/queryTypeVideosH5', {'pageNo': str(pg-1), 'pageSize': '20', 'sort': sort_map.get(tid,'1'), 'type': '1'})
            if resp and resp.get('code') == 10000:
                data = resp.get('data', {})
                items = data.get('typeVideoList') or data.get('list') or data.get('data') or data.get('videoList') or []
                vod_list = [self._parse_video(v) for v in items if isinstance(v, dict) and self._parse_video(v)]
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
            vod_list = [self._parse_video(v) for v in items if isinstance(v, dict) and self._parse_video(v)]
            total_page = int(data.get('totalPage') or 1)
            return {'list': vod_list, 'page': pg, 'pagecount': total_page, 'limit': len(vod_list), 'total': total_page*20}
        return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 0, 'total': 0}

    def _extract_videos_from_data(self, data):
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = (data.get('videoList') or data.get('list') or data.get('data') or data.get('videos') or
                     data.get('typeVideoList') or data.get('topicVideoIdList') or data.get('searchList') or
                     data.get('contentList') or data.get('records') or data.get('pageData') or data.get('resultList') or [])
        else:
            return []
        return [self._parse_video(v) for v in items if isinstance(v, dict) and self._parse_video(v)]

    @staticmethod
    def _try_get(item, *keys):
        for k in keys:
            v = item.get(k)
            if v is not None and v != '':
                return v
        return ''

    def _parse_topic_list(self, data):
        items = data if isinstance(data, list) else data.get('topicList') or data.get('oriTopicList') or data.get('list') or data.get('data') or data.get('topics') or []
        if not isinstance(items, list):
            return []
        results, seen = [], set()
        for item in items:
            if not isinstance(item, dict): continue
            tid = str(self._try_get(item, 'topicId','id','contentId','oriTopicId','topic_id'))
            name = str(self._try_get(item, 'topicName','name','title','oriTopicName','topic_name','topic'))
            img = str(self._try_get(item, 'topicPic','topicImg','img','cover','imageUrl','pic','thumb','image','topic_img','oriTopicImg'))
            cnt = str(self._try_get(item, 'videoCount','count','contentCount','totalCount','total','video_count'))
            if not tid or tid in seen: continue
            seen.add(tid)
            results.append({
                'vod_id': 'topic_' + tid + '@', 'vod_name': name or ('专题'+tid),
                'vod_pic': self.get_proxy_image_url(img or self.host+'/favicon.ico'), 'vod_tag': 'folder',
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
        return {'vod_id': vid, 'vod_name': title, 'vod_pic': self.get_proxy_image_url(pic) if pic else '', 'vod_remarks': str(remarks) if remarks else ''}

    # ========== 详情路由 ==========
    def detailContent(self, ids):
        did = ids[0] if isinstance(ids, list) else ids
        if did.startswith('siku:'):
            return self.siku.detailContent([did])
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
            'vod_id': str(did), 'vod_name': title,
            'vod_pic': self.get_proxy_image_url(pic) if pic else '',
            'vod_actor': str(actor) if actor else '', 'vod_director': '',
            'vod_content': desc, 'vod_year': '', 'vod_area': '',
            'vod_remarks': self._fmt_duration(duration),
            'vod_play_from': '蜜桃视频', 'vod_play_url': vod_play_url, 'type': 'video'
        }]}

    def searchContent(self, key, quick, pg=1):
        self._select_best_site()
        self._ensure_session()
        pg = int(pg)
        resp = self._api_request('/ht/content/search', {'keywords': key, 'pageNo': pg-1, 'pageSize': 20})
        if not resp or resp.get('code') != 10000:
            return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 0, 'total': 0}
        data = resp.get('data', {})
        items = data if isinstance(data, list) else data.get('searchList') or data.get('list') or data.get('data') or data.get('videoList') or data.get('records') or data.get('resultList') or data.get('content') or []
        if not isinstance(items, list):
            return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 0, 'total': 0}
        vod_list = [self._parse_video(v) for v in items if isinstance(v, dict) and self._parse_video(v)]
        total_page = int(data.get('totalPage') or 1) if isinstance(data, dict) else max(1, len(vod_list)//20)
        return {'list': vod_list, 'page': pg, 'pagecount': total_page, 'limit': len(vod_list), 'total': total_page*20}

    # ========== 播放路由 ==========
    def playerContent(self, flag, id, vipFlags=None):
        if id.startswith('siku:'):
            return self.siku.playerContent(flag, id[5:], vipFlags)
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

    # ========== 图片代理 ==========
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