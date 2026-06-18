import sys
import re
import requests
from base.spider import Spider
from urllib3 import disable_warnings
disable_warnings()

class Spider(Spider):
    host = "https://m.xsnvshen.com"

    def getName(self):
        return "秀色女神"

    def init(self, extend=""):
        pass

    def homeContent(self, filter):
        classes = [
            {"type_id": "/album/new/", "type_name": "最新更新"},{"type_id": "/album/t1/", "type_name": "爱蜜社"},{"type_id": "/album/t133/", "type_name": "尤蜜荟"},{"type_id": "/album/t110/", "type_name": "蜜桃社"},{"type_id": "/album/t91/", "type_name": "尤物馆"},{"type_id": "/album/t102/", "type_name": "美媛馆"},{"type_id": "/album/t119/", "type_name": "波萝社"},{"type_id": "/album/t120/", "type_name": "推女郎"},{"type_id": "/album/t121/", "type_name": "兔几盟"},{"type_id": "/album/t127/", "type_name": "爱尤物"},{"type_id": "/album/t162/", "type_name": "尤果网"},{"type_id": "/album/t163/", "type_name": "青豆客"},{"type_id": "/album/t192/", "type_name": "推女神"},{"type_id": "/album/t122/", "type_name": "魅妍社"},{"type_id": "/album/t89/", "type_name": "头条女神"},{"type_id": "/album/t94/", "type_name": "克拉女神"},{"type_id": "/album/t105/", "type_name": "御女郎"},{"type_id": "/album/t113/", "type_name": "嗲囡囡"},{"type_id": "/album/t135/", "type_name": "优星馆"},{"type_id": "/album/t134/", "type_name": "星乐园"},{"type_id": "/album/t193/", "type_name": "语画界"},{"type_id": "/album/t147/", "type_name": "秀人网"},{"type_id": "/album/t164/", "type_name": "影私荟"},{"type_id": "/album/t170/", "type_name": "治愈系"},{"type_id": "/album/t144/", "type_name": "糖果画报"},{"type_id": "/album/t182/", "type_name": "顽味生活"},{"type_id": "/album/t109/", "type_name": "飞图网"},{"type_id": "/album/t125/", "type_name": "激萌文化"},{"type_id": "/album/t154/", "type_name": "模范学院"},{"type_id": "/album/t136/", "type_name": "花の颜"},{"type_id": "/album/t172/", "type_name": "YS-Web套图"},{"type_id": "/album/t111/", "type_name": "DGC套图"},{"type_id": "/album/t117/", "type_name": "Young Champion"},{"type_id": "/album/t132/", "type_name": "Bomb.tv"},{"type_id": "/album/t142/", "type_name": "Sabra.net"},{"type_id": "/album/t174/", "type_name": "Weekly Young Jump"},{"type_id": "/album/t177/", "type_name": "Weekly Big Comic Spirits"},{"type_id": "/album/t181/", "type_name": "@misty"},{"type_id": "/album/t188/", "type_name": "Weekly Playboy"},{"type_id": "/album/t145/", "type_name": "Young Magazine"}
        ]
        return {"class": classes}

    def categoryContent(self, tid, pg, filter, extend):
        curr_pg = int(pg)
        # 简洁的 URL 拼接：判断 tid 是否已包含参数
        url = f"{self.host}{tid}{('&' if '?' in tid else '?') if curr_pg > 1 else ''}{f'p={curr_pg}' if curr_pg > 1 else ''}"

        try:
            res = self.fetch(url, headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0)"}, timeout=10)
            html = res.text
        except:
            return {"list": []}

        # 匹配图集列表
        matches = re.findall(r'<a href="(/album/\d+)".*?(?:src|data-original)="([^"]+)".*?txtbts3">([^<]+)</div>', html, re.S)
        
        vod_list = [{
            "vod_id": h.strip('/'),
            "vod_name": n.strip(),
            "vod_pic": "https:" + p if p.startswith('//') else p,
            "vod_remarks": ""
        } for h, p, n in matches]

        # 核心翻页逻辑：尝试匹配总页数，匹配不到则根据当前页是否有数据自动+1（诱导翻页）
        page_match = re.search(r'(\d+)页|共\s*(\d+)\s*页', html)
        last_page = int(page_match.group(1) or page_match.group(2)) if page_match else (curr_pg + 1 if len(vod_list) >= 20 else curr_pg)

        return {
            "page": curr_pg,
            "pagecount": last_page,
            "limit": len(vod_list),
            "total": 999,
            "list": vod_list
        }

    def searchContent(self, key, quick, pg="1"):
        # 该站搜索可能较弱，可暂时返回空或简单实现
        return {"list": []}

    def detailContent(self, ids):
            aid = ids[0]
            url = f"{self.host}/{aid}"
            
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Mobile/15E148 Safari/604.1",
                    "Referer": "https://m.xsnvshen.com/"
                }
                res = requests.get(url, verify=False, timeout=15, headers=headers)
                html = res.text
            except:
                return {"list": []}
    
            # 标题
            name_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html) or re.search(r'<title>([^<|-]+)', html)
            name = name_match.group(1).strip() if name_match else "未知写真"
    
            # 封面
            pic_match = re.search(r'img src="(//img\.xsnvshen\.com/[^"]+)"', html)
            pic = "https:" + pic_match.group(1) if pic_match else ""
    
            # 简介
            desc = "暂无简介"
            desc_match = re.search(r'<div id="arcbox">(.*?)</div>', html, re.S)
            if desc_match:
                desc = re.sub(r'<[^>]+>', ' ', desc_match.group(1)).strip()
    
            total_images = 60   # 默认图片兜底数
    
            # 优先匹配带 <span> 的格式
            total_match = re.search(r'共\s*<span[^>]*>(\d+)</span>\s*张', html)
            if total_match:
                total_images = int(total_match.group(1))
            else:
                # 备用匹配（普通 "共 xx 张"）
                total_match2 = re.search(r'共\s*(\d+)\s*张', html)
                if total_match2:
                    total_images = int(total_match2.group(1))
    
            # === 提取 user_id ===
            user_match = re.search(r'/album/(\d+)/' + re.escape(aid.split('/')[-1]) + r'/', html)
            user_id = user_match.group(1) if user_match else "0"
    
            album_id = aid.split('/')[-1]
    
            # === 构造图片链接 ===
            img_list = []
            for i in range(total_images):
                img_url = f"https://img.xsnvshen.com/thumb_600x900/album/{user_id}/{album_id}/{i:03d}.jpg"
                img_list.append(img_url)

            pics_str = f"高清图集({len(img_list)}P)$pics://" + "&&".join(img_list)
    
            vod = {
                "vod_id": aid,
                "vod_name": name,
                "vod_pic": pic,
                "vod_remarks": f"共 {total_images} 张（构造）",
                "vod_content": desc[:280] + "..." if len(desc) > 280 else desc,
                "vod_play_from": "秀色女神",
                "vod_play_url": pics_str
            }
    
            return {"list": [vod]}

    def playerContent(self, flag, id, vipFlags):
        if id.startswith("pics://"):
            return {
                "parse": 0,
                "url": id,
                "header": {
                    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Mobile/15E148 Safari/604.1",
                    "Referer": "https://m.xsnvshen.com/"
                }
            }
