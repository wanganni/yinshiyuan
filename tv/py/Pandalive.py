# -*- coding: utf-8 -*-
import requests
import urllib.parse
import json

class Spider:
    def init(self, extend=""):
        self.host = "https://5721004.xyz"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.pandalive.co.kr/',
            'Origin': 'https://www.pandalive.co.kr'
        }
        print("PandaLive 專業版 (僅 PandaTV) 初始化成功")

    def getName(self):
        return "PandaLive"

    def getDependence(self):
        return []

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    def localProxy(self, param):
        return None

    def homeContent(self, filter):
        """首頁 - 僅保留 PandaTV 分類與對應篩選器"""
        try:
            # 只保留 PandaTV
            classes = [
                {'type_id': 'pandalive', 'type_name': '🐼 PandaTV'}
            ]
            
            filters = {
                "pandalive": [
                    {
                        "key": "type",
                        "name": "類型",
                        "value": [
                            {"n": "全部", "v": "all"},
                            {"n": "🔞 19+", "v": "adult"},
                            {"n": "🔐 密碼房", "v": "pw"},
                            {"n": "💎 粉絲房", "v": "fan"}
                        ]
                    },
                    {
                        "key": "sort",
                        "name": "排序",
                        "value": [
                            {"n": "觀眾量 ↓", "v": "user-desc"},
                            {"n": "實時熱度 ↓", "v": "totalScoreCnt-desc"},
                            {"n": "關注量 ↓", "v": "bookmarkCnt-desc"}
                        ]
                    }
                ]
            }
            
            # 獲取首頁推薦數據 (從 JSON 獲取以保證有圖片)
            all_data = self._fetch_json_data()
            return {
                'class': classes,
                'list': all_data[:30],
                'filters': filters
            }
        except Exception as e:
            print(f"homeContent錯誤: {e}")
            return {'class': [], 'list': []}

    def homeVideoContent(self):
        try:
            return {'list': self._fetch_json_data()[:20]}
        except:
            return {'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        """分類頁 - 基於 JSON 的篩選排序邏輯"""
        try:
            all_list = self._fetch_json_data()
            filtered = all_list
            
            # 1. 執行篩選
            f_type = extend.get('type', 'all')
            if f_type == 'adult':
                filtered = [v for v in filtered if v.get('_isAdult')]
            elif f_type == 'pw':
                filtered = [v for v in filtered if v.get('_isPw')]
            elif f_type == 'fan':
                filtered = [v for v in filtered if v.get('_type') == 'fan']
            
            # 2. 執行排序
            sort_type = extend.get('sort', 'user-desc')
            if sort_type == 'user-desc':
                filtered.sort(key=lambda x: x.get('_user_count', 0), reverse=True)
            elif sort_type == 'totalScoreCnt-desc':
                filtered.sort(key=lambda x: x.get('_score', 0), reverse=True)
            elif sort_type == 'bookmarkCnt-desc':
                filtered.sort(key=lambda x: x.get('_bookmark', 0), reverse=True)
            
            # 3. 分頁
            pg = int(pg)
            limit = 30
            start = (pg - 1) * limit
            end = start + limit
            page_list = filtered[start:end] if start < len(filtered) else []
            
            return {
                'list': page_list,
                'page': pg,
                'pagecount': (len(filtered) + limit - 1) // limit if filtered else 1,
                'limit': limit,
                'total': len(filtered)
            }
        except Exception as e:
            print(f"categoryContent錯誤: {e}")
            return {'list': [], 'page': int(pg)}

    def _fetch_json_data(self):
        """抓取 list.json 數據，確保 vod_pic 獲取正確"""
        try:
            url = f"{self.host}/player/list.json"
            res = requests.get(url, headers=self.headers, timeout=10)
            if res.status_code != 200:
                return []
            
            data = res.json()
            raw_list = data.get('list', [])
            
            processed = []
            for item in raw_list:
                user_id = item.get('userId', '')
                nick = item.get('userNick', '未知主播')
                title = item.get('title', '無標題')
                
                is_adult = item.get('isAdult', False)
                is_pw = item.get('isPw', False)
                v_type = item.get('type', '')
                
                processed.append({
                    'vod_id': f"live_{user_id}",
                    'vod_name': f"📺 {nick}",
                    'vod_pic': item.get('thumbUrl', 'https://tupian.li/images/2024/03/30/660769b1ba623.png'),
                    'vod_remarks': f"👤 {item.get('user', 0)} {'🔞' if is_adult else ''}",
                    'vod_content': title,
                    'vod_actor': user_id,
                    '_isAdult': is_adult,
                    '_isPw': is_pw,
                    '_type': v_type,
                    '_user_count': item.get('user', 0),
                    '_score': item.get('totalScoreCnt', 0),
                    '_bookmark': item.get('bookmarkCnt', 0)
                })
            return processed
        except Exception as e:
            print(f"JSON抓取失敗: {e}")
            return []

    def detailContent(self, ids):
        """詳情頁 - 保持對接 list.m3u 獲取真實流地址的邏輯"""
        try:
            first_id = ids[0] if isinstance(ids, list) else ids
            user_id = first_id.replace("live_", "")
            
            stream_url = ""
            m3u_res = requests.get(f"{self.host}/player/list.m3u", headers=self.headers, timeout=10)
            if m3u_res.status_code == 200:
                lines = m3u_res.text.split('\n')
                for i, line in enumerate(lines):
                    # 匹配格式: #EXTINF:0,主播ID,主播名稱
                    if f",{user_id}," in line and i + 1 < len(lines):
                        stream_url = lines[i+1].strip()
                        break
            
            if not stream_url:
                # 如果 M3U 匹配不到，嘗試模糊匹配主播 ID
                for i, line in enumerate(lines):
                    if user_id in line and i + 1 < len(lines):
                        stream_url = lines[i+1].strip()
                        break

            proxies = [
                "https://hubu.515355.xyz/proxy/?",
                "https://flank.515355.xyz/proxy/",
                "https://uae2.515355.xyz/proxy/",
                "https://pol.515355.xyz/proxy/",
                "https://f00.515355.xyz/proxy/",
                "https://ce2.515355.xyz/proxy/?",
            ]
            
            # 1. 首先创建列表，并将“直连”作为第一个元素添加进去
            play_links = [f"直連${stream_url}"]

# 2. 然后通过 extend() 方法或循环，将生成的代理链接追加到列表中
            play_links.extend([f"代理{i}${p}{stream_url}" for i, p in enumerate(proxies, 1)])

            
            vod = {
                'vod_id': first_id,
                'vod_name': f"PandaTV - {user_id}",
                'vod_pic': 'https://tupian.li/images/2024/03/30/660769b1ba623.png',
                'vod_content': f'主播: {user_id}',
                'vod_play_from': 'PandaLive',
                'vod_play_url': '#'.join(play_links)
            }
            return {'list': [vod]}
        except Exception as e:
            print(f"detailContent錯誤: {e}")
            return {'list': []}

    def searchContent(self, key, quick, pg="1"):
        """搜索 - 帶 pg="1" 修復"""
        try:
            all_v = self._fetch_json_data()
            key_l = key.lower()
            res = [v for v in all_v if key_l in v['vod_name'].lower() or key_l in v['vod_actor'].lower()]
            return {'list': res[:50], 'page': int(pg)}
        except:
            return {'list': [], 'page': int(pg)}

    def playerContent(self, flag, id, vipFlags):
        return {
            'parse': 0,
            'url': id,
            'header': self.headers
        }