import sys
import sqlite3
import json
import os
from base.spider import Spider

class Spider(Spider):
    def getName(self):
        return "Universal_DB_Spider"

    # ==========================================================================
    # 💎 【1. 配置与路径】 路径自适应 + 扫描深度控制
    # ==========================================================================
    SCAN_DIR_LIST = [
                "bh", "tvbox",  "bhh",         #👈电视📺专用文件夹，把db文件放在这里# 👈 u盘也用这个文件夹                                          
                "lz", "纯福利", "私藏视频",  "江湖",          # 👈 前面加#关闭   这里可以修改任意大佬包名 
                "VodPlus", "peekpili/php-scripts"                       #同上
          ]  
    MAX_DEPTH = 3  # 设置扫描深度为1-3级
    FOLDER_ICON = "https://gitcode.com/gcw_OAaqxWb5/tu/releases/download/%E5%9B%BE%E7%89%87/%E5%90%88%E9%9B%86.png"
                
    def init(self, extend=""):
        self.inited = True
        self.databases = {}
        self._db_cache = {}
        
        # 1. 路径自适应：内部存储 + 外部挂载点
        self.scan_roots = ["/storage/emulated/0"]
        try:
            if os.path.exists("/storage"):
                for s in os.listdir("/storage"):
                    if s not in ["self", "emulated", "knox", "sdcard0", "runtime"]:
                        full_s = os.path.join("/storage", s)
                        if os.path.isdir(full_s):
                            self.scan_roots.append(full_s)
        except: 
            pass
        
        # 2. 执行多级深度递归扫描
        for root in self.scan_roots:
            for sub in self.SCAN_DIR_LIST:
                target_dir = os.path.join(root, sub)
                if os.path.exists(target_dir):
                    self._scan_with_depth(target_dir, 1)

    def _scan_with_depth(self, current_dir, current_depth):
        """
        递归扫描函数：支持1-3级深度
        """
        if current_depth > self.MAX_DEPTH:
            return
            
        try:
            files = os.listdir(current_dir)
            for file in files:
                full_path = os.path.join(current_dir, file)
                if os.path.isdir(full_path):
                    # 如果是文件夹，递归进入下一级
                    self._scan_with_depth(full_path, current_depth + 1)
                elif file.endswith(".db"):
                    # 如果是数据库文件，记录
                    db_key = f"auto_{file}_{hash(full_path)}" # 增加hash防止同名冲突
                    if db_key not in self.databases:
                        self.databases[db_key] = {
                            "name": file, 
                            "path": full_path, 
                            "valid": 1
                        }
        except:
            pass
#
    def _get_connection(self, db_key):
        db_info = self.databases.get(db_key)
        if not db_info: return None
        db_path = db_info.get("path")
        if not db_path or not os.path.exists(db_path): return None
        try:
            conn = sqlite3.connect(db_path)
            # ==========================================
            # 🚀 二进制级性能调优
            # ==========================================
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode = OFF;") # 关闭日志，减少I/O
            cursor.execute("PRAGMA synchronous = OFF;")  # 异步模式
            cursor.execute("PRAGMA cache_size = 10000;") # 增加页面缓存（约10MB）
            cursor.execute("PRAGMA temp_store = MEMORY;")# 临时表存入内存
            cursor.execute("PRAGMA mmap_size = 268435456;") # 开启256MB的内存映射加速
            return conn
        except: return None
#
    def _get_auto_mapping(self, conn):
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = [row[0] for row in cursor.fetchall()]
            target_table = next((t for t in ["videos", "vod_unified_data", "cj", "vod", "data", "list", "video_detail"] if t in tables), tables[0] if tables else None)
            if not target_table: return None
            
            cursor.execute(f"PRAGMA table_info(`{target_table}`)")
            cols = [str(r[1]) for r in cursor.fetchall()]

            mapping = {}
            field_candidates = {
                "vod_id": ["id", "vod_id", "uuid", "guid", "vid"],
                "vod_name": ["name", "vod_name", "title", "subject", "display_name"],
                "vod_pic": ["image", "vod_pic", "pic", "pic_url", "thumbnail", "img", "cover"],
                "vod_play_url": ["play_url", "vod_play_url", "url", "link", "m3u8_url"],
                "vod_remarks": ["vod_remarks", "remarks", "note", "desc"],
                "category_field": ["type_name", "category_id", "class_name", "cate_name", "actress_id", "tag", "type"],
                "vod_actor": ["vod_actor", "actor", "star", "actress", "artist", "performer"],
                "vod_content": ["vod_content", "description", "summary", "intro", "detail", "content"],
                "vod_pubdate": ["vod_pubdate", "pubdate", "release_date", "date"],
                "vod_area": ["vod_area", "area", "region", "country"],
                "vod_year": ["vod_year", "year"],
                "vod_tags": ["vod_tags", "tags", "keywords", "label"],
                "vod_play_from": ["vod_play_from", "play_from", "source"],
                "actress_avatar": ["actress_avatar", "avatar", "logo", "LOOG"],
                "cate_name": ["cate_name", "type_name"]
            }

            for target_field, candidates in field_candidates.items():
                matches = [cand for cand in candidates if cand in cols]
                mapping[target_field] = matches[0] if matches else None

            return {"table_name": target_table, "field_mapping": mapping}
        except: return None

    def homeContent(self, filter):
        classes = []
        for db_key, db_info in self.databases.items():
            if db_info.get("valid") != 0:
                raw_name = db_info.get('name', db_key)
                clean_name = os.path.splitext(raw_name)[0]
                # 首页风格：一行二文件夹模式
                classes.append({
                    "type_id": db_key,
                    "type_name": clean_name,
                    "type_pic": self.FOLDER_ICON,
                    "pic": self.FOLDER_ICON
                })
        return {"class": classes}
# 🔴🔴==========================================================================
    def categoryContent(self, tid, pg, filter, extend):
        parts = tid.split('$')
        db_key = parts[0]
        curr_path = parts[1] if len(parts) > 1 else ""

        cache_key = f"tree_{db_key}"
        if cache_key not in self._db_cache:
            conn = self._get_connection(db_key)
            if not conn: return {"list": []}

            auto_info = self._get_auto_mapping(conn)
            if not auto_info:
                conn.close()
                return {"list": []}
            
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info(`{auto_info['table_name']}`)")
            all_cols = [str(r[1]) for r in cursor.fetchall()]
            
            mapping = auto_info["field_mapping"]
            filter_field = "type_name" if "type_name" in all_cols else mapping["category_field"]
            if not filter_field: filter_field = all_cols[0]

            cursor.execute(f"SELECT `{filter_field}`, COUNT(*) FROM `{auto_info['table_name']}` WHERE `{filter_field}` IS NOT NULL GROUP BY `{filter_field}`")
            raw_data = cursor.fetchall()
            type_counts = {str(row[0]): row[1] for row in raw_data}

            # 核心：使用当前文件自带的图片字段
            avatar_map = {}
            avatar_col = mapping.get("actress_avatar")
            if avatar_col and avatar_col in all_cols:
                try:
                    cursor.execute(f"SELECT DISTINCT `{filter_field}`, `{avatar_col}` FROM `{auto_info['table_name']}` WHERE `{avatar_col}` IS NOT NULL AND `{avatar_col}` != ''")
                    for row in cursor.fetchall():
                        avatar_map[str(row[0])] = row[1]
                except: pass

            self._db_cache[cache_key] = {
                "types": list(type_counts.keys()),
                "counts": type_counts,
                "field": filter_field,
                "table": auto_info['table_name'],
                "mapping": mapping,
                "avatar_map": avatar_map
            }
            conn.close()

        db_data = self._db_cache[cache_key]
        all_vals = db_data["types"]
        all_counts = db_data["counts"]
        avatar_map = db_data["avatar_map"]

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
            conn = self._get_connection(db_key)
            return self._fetch_video_list(conn, db_key, db_data["table"], db_data["mapping"], db_data["field"], curr_path if curr_path else None, pg, limit, offset)

        # 排序：有自带图片的优先显示
        sorted_dirs = sorted(list(sub_dirs_info.keys()), key=lambda x: (0 if avatar_map.get(x) else 1, -sub_dirs_info[x], x))
        paged_dirs = sorted_dirs[offset : offset + limit]

        vod_list = []
        for d in paged_dirs:
            display_name = d.split('/')[-1]
            num = sub_dirs_info[d]
            pic = avatar_map.get(d) or self.FOLDER_ICON

            vod_list.append({
                "vod_id": f"{db_key}${d}",
                "vod_name": f"{display_name} ({num})",
                "vod_pic": pic,
                "vod_tag": "folder",
                "style": {"type": "rect", "ratio": 1.7}      #原来是，"ratio": 1.2
            })

        return {"page": int(pg), "pagecount": int(pg) + 1, "limit": limit, "list": vod_list}

    def _fetch_video_list(self, conn, db_key, table_name, mapping, filter_field, category_val, pg, limit, offset):
        if not conn: return {"list": []}
        cursor = conn.cursor()
        vod_list = []
        f_id = mapping.get("vod_id") or "rowid"
        f_name = mapping.get("vod_name") or "rowid"
        f_pic = mapping.get("vod_pic") or "''"
        f_rem = mapping.get("vod_remarks") or "''"

        try:
            if category_val is not None:
                sql = f"SELECT `{f_id}`, `{f_name}`, `{f_pic}`, `{f_rem}` FROM `{table_name}` WHERE `{filter_field}` = ? LIMIT ? OFFSET ?"
                cursor.execute(sql, (category_val, limit, offset))
            else:
                sql = f"SELECT `{f_id}`, `{f_name}`, `{f_pic}`, `{f_rem}` FROM `{table_name}` LIMIT ? OFFSET ?"
                cursor.execute(sql, (limit, offset))

            for row in cursor.fetchall():
                pic = str(row[2]) if row[2] else "https://img.icons8.com/color/512/movie.png"
                vod_list.append({
                    "vod_id": f"{db_key}#ID#{row[0]}",
                    "vod_name": str(row[1]),
                    "vod_pic": pic,
                    "vod_remarks": str(row[3]) if len(row) > 3 else ""
                })
        except: pass
        finally: conn.close()
        return {"page": int(pg), "pagecount": int(pg) + 1, "limit": limit, "list": vod_list}
        # -独立且厚实的清洗工具 ---
    def clean_vod_url(self, raw_url):
        if not raw_url or not isinstance(raw_url, str):
            return ""
        # 1. 处理 $ 符号开头的标识
        clean_url = raw_url.split("$")[-1]
        # 2. 处理管道符 | 后的 UA 垃圾
        clean_url = clean_url.split("|")[0]
        # 3. 处理 & 后的 Referer 垃圾（准确定位 .m3u8 或 .mp4）
        for ext in [".m3u8", ".mp4", ".mkv", ".m4v"]:
            pos = clean_url.lower().find(ext)
            if pos != -1:
                clean_url = clean_url[:pos + len(ext)]
                break
        # 4. 如果没有找到后缀但有 &，强制切断
        if "&" in clean_url and ".m3u" not in clean_url.lower():
             clean_url = clean_url.split("&")[0]
        return clean_url.strip()
        #
        
#🔴🔴 ==========================================================================
    def detailContent(self, ids):
        mid_full = ids[0]
        
        # 🟢 新增逻辑：如果传入的是网络链接则直接构建返回
        if mid_full.startswith("http"):
            return {
                "list": [{
                    "vod_id": mid_full,
                    "vod_name": "网络视频预览",
                    "vod_pic": "",
                    "vod_remarks": "直链播放",
                    "vod_content": f"📍 外部链接: {mid_full}",
                    "vod_play_from": "直链",
                    "vod_play_url": mid_full
                }]
            }

        # --- 数据库解析流程 ---
        db_key, _, real_id = mid_full.partition("#ID#")
        conn = self._get_connection(db_key)
        if not conn: return {"list": []}

        auto_info = self._get_auto_mapping(conn)
        if not auto_info:
            conn.close()
            return {"list": []}
        
        conn.row_factory = sqlite3.Row 
        cursor = conn.cursor()
        mapping = auto_info["field_mapping"]
        id_col = mapping.get("vod_id") or "rowid"

        cursor.execute(f"SELECT * FROM `{auto_info['table_name']}` WHERE `{id_col}` = ?", (real_id,))
        row = cursor.fetchone()
        if not row: 
            conn.close()
            return {"list": []}

        def get_val(m_key):
            real_col = mapping.get(m_key)
            return str(row[real_col]) if (real_col and real_col in row.keys() and row[real_col] is not None) else ""
          
        # --- 🔴 关键缝合开始：清洗烂地址 ---
        raw_play_url = get_val("vod_play_url")
        
        # 1. 使用我们厚实的清洗工具进行“脱壳”
        clean_url = self.clean_vod_url(raw_play_url)
        
        # 2. 容错：如果清洗完啥也没了，用 ID 保底
        if not clean_url:
            clean_url = f"Play#{real_id}"
        # --- 🔴 关键缝合结束 ---

        vod = {
            "vod_id": mid_full,
            "vod_name": get_val("vod_name"),
            "vod_pic": get_val("vod_pic"),
            "vod_actor": get_val("vod_actor") or get_val("category_field"),
            "vod_remarks": get_val("vod_remarks"),
            "vod_year": get_val("vod_year"),
            "vod_content": get_val("vod_content") or get_val("vod_remarks"),
            "vod_play_from": "DB库", # 标记为清洗后的数据，强洗
            "vod_play_url": clean_url,  # 填入洗干净的地址
            "type_name": get_val("category_field")
        }
        conn.close()
        return {"list": [vod]}

    def playerContent(self, flag, id, vipFlags):
        return {"parse": 0, "url": id, "header": {"User-Agent": "Dalvik/2.1.0"}}

    def searchContent(self, key, quick, pg="1"):
        search_list = []
        for db_key, db_info in self.databases.items():
            conn = self._get_connection(db_key)
            if not conn: continue
            try:
                auto_info = self._get_auto_mapping(conn)
                mapping = auto_info["field_mapping"]
                f_name = mapping.get("vod_name")
                if not f_name: continue
                
                cursor = conn.cursor()
                f_id = mapping.get("vod_id") or "rowid"
                f_pic = mapping.get("vod_pic") or "''"
                sql = f"SELECT `{f_id}`, `{f_name}`, `{f_pic}` FROM `{auto_info['table_name']}` WHERE `{f_name}` LIKE ? LIMIT 10"
                cursor.execute(sql, (f"%{key}%",))
                for row in cursor.fetchall():
                    search_list.append({
                        "vod_id": f"{db_key}#ID#{row[0]}",
                        "vod_name": f"[{db_info['name']}] {row[1]}",
                        "vod_pic": str(row[2]) if row[2] else ""
                    })
                    
            except: pass
            finally: conn.close()
        return {"list": search_list} 