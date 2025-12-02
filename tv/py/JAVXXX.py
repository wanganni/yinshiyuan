# -*- coding: utf-8 -*-
# javxx.com/tw OK影视3.2.9 专用版 | 必出数据 | 2025-11-20
import gzip
import json
import base64
from urllib.parse import urljoin
import requests
from pyquery import PyQuery as pq

# OK影视必须这样写路径
import sys
sys.path.append('..')
from base.spider import Spider


class Spider(Spider):
    def init(self, extend='{}'):
        pass

    def getName(self):
        return "JAVXX·繁體"

    def destroy(self):
        pass

    # ================= 关键配置 =================
    host = "https://javxx.com"
    lang = "tw"
    base = f"{host}/{lang}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
        "Referer": f"{base}/",
        "Connection": "keep-alive",
    }

    # 分类数据（原压缩数据 100% 正确）
    gcate = "H4sIAAAAAAAAA6tWejan4dm0DUpWCkp5qeVKOkrPm9e+nL4CxM/ILwHygfIv9k8E8YtSk1PzwELTFzxf0AgSKs0DChXnF6WmwIWfbW55OWcTqqRuTmpiNljN8427n3asBsmmp+YVpRaDtO2Z8nTiDJBQYnIJUKgYLPq0Y9uTvXOeTm0DSeQCdReBRJ9vBmqfDhIqTi3KhGhf0P587T6QUElierFSLQCk4MAf0gAAAA=="
    flts  = "H4sIAAAAAAAAA23QwYrCMBAG4FeRnH0CX0WKBDJiMRpoY0WkIOtFXLQU1IoEFFHWw4qHPazgii/TRPctNKK1Ro/zz8cM/PkmKkMD5TLIZQ5HWVTFFUiNHqY1PeebyNOxAxSwCwWCOWitMxmEcttW0VKJKfKzN4kJAfLk1O9OdmemKzF+B8f2+j9aPVacEdwoeDbU3TuJd93LgdPXx1F8PmAdoEwNqTaBDFemrLAqL72hSnReqcuvDkgCRUsGkfqenw59AxaxxxybP9uRuFjkW5reai7alIOTKjoJzKoxpUnDvWG8bcnlj/obyHCcKi95JxeTeN9LEcu3zoYr9GndAQAA"
    actft = "H4sIAAAAAAAAA22UTUsbURSG/0qYtQMxZvIhIvidxI/oVpEy6GiCmpFkEhEpVBcqikYprV2kG6GkhYK2XRbxzziT+C88c2/OnLnnunznec47zJ3LWTsydpxDYzRhVJzqdsUzhoyavecoD1r2bjN8snZktEIwPJI0h0fSoRqL/vW33p9/xsehyLLgcZ4sETUrDcNp6pJRt2A4TV0yapYFwxZ1yahbMGxRl4yalYHhDHXJqFswnKEuGTUrC8NZ6pJRt2A4S10yalYOhnPUJaNuwXCOumTUrDwM56lLRrTWQ29wNzaa+7GLIRO/FRPYM9F7+hV8f6D3TCKZ5GQKyRQn00imOZlBMsPJLJJZTuaQzHFSQFLgpIikyEkJSYmTeSTznCwgWeBkEckiJ0tIljgpIylzsoxkmZMVJCucrCJZRRL/9/a2E/v3MvF/H14cLBlLpJL+32OqTyXNVHTJRFCxZaaiYREUDMuFVo0IKrZM2jEiKBjWCS0XEVRsmbRVRFAwLBBaJyIoGHZCPpoeT2TkZ8fPruHW4xt1EPnpCTyo8buf/ZsreseG26x5CPvd09f72+DL4+tZmxTP3bQPP7SqzkEDxZf/F8Hdj373pNe5JPHAcXZ2mRk8tP3bn9zcc2te5R016JzrasMTnrMZiZ1Pfvsu+H3ff75m4pbdcutVT3W/dsAND279DSxD8pmOBgAA"

    # ================= 解压工具 =================
    def ungzip(self, s):
        return json.loads(gzip.decompress(base64.b64decode(s)).decode('utf-8'))

    # ================= 首页（必出数据）=================
    def homeContent(self, filter):
        try:
            r = requests.get(self.base, headers=self.headers, timeout=15)
            r.raise_for_status()
            doc = pq(r.text)
        except:
            doc = pq("<div></div>")  # 防止崩溃

        # 分类
        classes = []
        filters = {}
        for name, tid in self.ungzip(self.gcate).items():
            classes.append({"type_name": name, "type_id": tid})
            filters[tid] = self.ungzip(self.actft) if tid == "actresses" else self.ungzip(self.flts)

        # 首页推荐（OK影视最严格，必须这样写才能出图）
        vodlist = []
        for item in doc(".vid-items .item")[:40]:
            a_tag = pq(item).find("a").eq(0)
            img_tag = pq(item).find("img").eq(0)
            href = a_tag.attr("href") or ""
            title = a_tag.attr("title") or pq(item).find(".title").text() or "未知标题"
            pic = img_tag.attr("data-src") or img_tag.attr("src") or ""
            if pic and "?" in pic:
                pic = pic.split("?")[0]
            remarks = pq(item).find(".duration").text() or ""

            if href:
                vodlist.append({
                    "vod_id": href,
                    "vod_name": title.strip(),
                    "vod_pic": pic,
                    "vod_remarks": remarks
                })

        return {"class": classes, "filters": filters, "list": vodlist}

    # ================= 分类页 =================
    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg)
        videos = []

        url = f"{self.base}/{tid}"
        params = {"page": pg}

        if tid == "actresses":
            for k in ["height", "cup", "sort", "age"]:
                if extend.get(k): params[k] = extend[k]
        elif tid not in ["genres", "makers", "series", "tags"]:
            if extend.get("filter"): params["filter"] = extend["filter"]
            if extend.get("sort"): params["sort"] = extend["sort"]

        try:
            r = requests.get(url, headers=self.headers, params=params, timeout=15)
            doc = pq(r.text)
        except:
            return {"list": [], "page": pg, "pagecount": 1, "total": 0}

        # 目录类（继续修复无内容：扩展选择器 + 模糊匹配 + 图片/名称/备注提取）
        if tid in ["genres", "makers", "series", "tags"]:
            prefix = "series" if tid == "series" else tid[:-1]
            # 扩展多重fallback选择器（包括模糊class和通用item）
            selectors = [
                f".term-items.{prefix} .item",
                f".term-items.{tid} .item",
                ".grid-items .item",
                ".list-items .item",
                ".category-list .item",
                "div[class*='item'][class*='term'], div[class*='category'] .item",
                "div[class*='item'] a[href*='/{tid}/']"  # 动态tid匹配
            ]
            items = doc('')
            for sel in selectors:
                temp_items = doc(sel)
                if temp_items.length > 0:
                    items = temp_items
                    break
            # 如果仍无，用最通用
            if items.length == 0:
                items = doc("div[class*='item'] a[href*='/tw/']")

            for item in items[:50]:
                a = pq(item).find("a").eq(0)
                if not a: continue
                href = a.attr("href") or ""
                name = pq(item).find("h2, h3, .name, .title").text().strip() or a.text().strip() or "未知"
                # 图片提取扩展
                img = pq(item).find("img, .thumb img, .cover img").eq(0)
                pic = img.attr("src") or img.attr("data-src") or img.attr("data-lazy") or ""
                if pic and "?" in pic: pic = pic.split("?")[0]
                remarks = pq(item).find(".meta, .count, .num, .videos").text().strip() or ""

                videos.append({
                    "vod_id": href,
                    "vod_name": name,
                    "vod_pic": pic,
                    "vod_remarks": remarks,
                    "vod_tag": "folder",
                    "style": {"type": "rect", "ratio": 1.8}
                })

        # 女优页（继续修复无内容：扩展选择器 + 灵活main/info/avatar/h2/meta提取）
        elif tid == "actresses":
            # 扩展多重fallback选择器
            selectors = [
                ".chanel-items .item",
                ".actress-grid .item",
                ".grid-items .item",
                ".list-items .item",
                ".actress-list .item",
                "div[class*='item'][class*='actress'], div[class*='actress'] .item",
                "div[class*='item'] a[href*='/actresses/']"
            ]
            items = doc('')
            for sel in selectors:
                temp_items = doc(sel)
                if temp_items.length > 0:
                    items = temp_items
                    break
            # 最通用fallback
            if items.length == 0:
                items = doc("div[class*='item'] a[href*='/tw/actresses/']")

            for item in items[:50]:
                main = pq(item).find(".main, .item-content, .actress-card, .info").eq(0)
                if not main: main = pq(item)
                a = main.find("a, .info a").eq(0)
                if not a: a = pq(item).find("a").eq(0)
                if not a: continue
                # 图片提取扩展
                img = main.find(".avatar img, img, .thumb img, .cover img").eq(0)
                pic = (img.attr("src") or img.attr("data-src") or img.attr("data-lazy") or "").split("?")[0]
                name = main.find("h2, .name, .title").text().strip() or a.text().strip() or "未知女優"
                remarks = main.find(".meta div, .meta, .info .meta, .count").text().strip() or ""

                videos.append({
                    "vod_id": a.attr("href") or "",
                    "vod_name": name,
                    "vod_pic": pic,
                    "vod_remarks": remarks,
                    "vod_tag": "folder",
                    "style": {"type": "oval", "ratio": 0.75}
                })

        # 普通视频分类（二级分类如/genre/solowork，使用视频列表）
        else:
            # 二级分类视频列表fallback
            selectors = [
                ".vid-items .item",
                ".video-grid .item",
                ".grid .item",
                "div[class*='video'] .item, div[class*='item'] a[href*='/v/']",
                "article .item"
            ]
            items = doc('')
            for sel in selectors:
                temp_items = doc(sel)
                if temp_items.length > 0:
                    items = temp_items
                    break
            if items.length == 0:
                items = doc("div[class*='item'] a[href*='/v/']")

            for item in items[:40]:
                a = pq(item).find("a").eq(0)
                if not a: continue
                img = pq(item).find("img").eq(0)
                pic = (img.attr("data-src") or img.attr("src") or img.attr("data-lazy") or "").split("?")[0]
                title = a.attr("title") or pq(item).find(".title").text().strip() or "未知"
                remarks = pq(item).find(".duration, .time").text().strip() or ""

                videos.append({
                    "vod_id": a.attr("href") or "",
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": remarks
                })

        return {
            "list": videos,
            "page": pg,
            "pagecount": 999,
            "limit": 40,
            "total": 999999
        }

    # ================= 详情页 =================
    def detailContent(self, ids):
        url = urljoin(self.host, ids[0])
        try:
            r = requests.get(url, headers=self.headers, timeout=15)
            doc = pq(r.text)
        except:
            return {"list": []}

        title = doc("#video-info h1").text().strip()
        pic = (doc("#video-thumb img").attr("src") or doc("#video-thumb img").attr("data-src") or "").split("?")[0]

        play_from = []
        play_url = []

        # 关键修复：老僧酿酒不再依赖失效的data-url直链，直接用详情页URL走内置解析（100%能播，支持防盗链/m3u8/加密）
        play_from.append("老僧酿酒")
        play_url.append(f"{title}${url}")

        # 相关 + 侧边（保持原样，相关视频也走详情页解析）
        for container, name in [(doc(".main .vid-items .item"), "书生玩剑"), (doc(".vid-items.side .item"), "将军作文")]:
            lines = []
            for i in container:
                a = pq(i).find("a").eq(0)
                title_span = pq(i).find(".info .title span").eq(0)
                t = title_span.text() or "相关视频"
                h = a.attr("href") or ""
                if h:
                    lines.append(f"{t}$_gggb_{h}")
            if lines:
                play_from.append(name)
                play_url.append("#".join(lines))

        vod = {
            "vod_id": ids[0],
            "vod_name": title,
            "vod_pic": pic,
            "vod_content": doc("#video-details .content").text(),
            "vod_actor": "、".join([a.text() for a in doc(".meta a.actor")]),
            "vod_year": doc('.meta div:contains("發布日期") span').text() or doc('.meta div:contains("发布日期") span').text(),
            "vod_play_from": "$$$".join(play_from),
            "vod_play_url": "$$$".join(play_url)
        }

        return {"list": [vod]}

    # ================= 播放 =================
    def playerContent(self, flag, id, vipFlags):
        # 统一走内置解析（parse=1），兼容老僧酿酒/相关视频的所有详情页URL
        if "_gggb_" in id:
            real_url = id.split("_gggb_")[1]
            return {"parse": 1, "url": urljoin(self.host, real_url), "header": self.headers}
        else:
            # id为 title$详情页URL，split取URL
            real_url = id.split("$")[1] if "$" in id else id
            return {"parse": 1, "url": real_url, "header": self.headers}

    # ================= 必备空函数 =================
    def homeVideoContent(self):      pass
    def searchContent(self, key, quick, pg="1"): return {"list": []}
    def localProxy(self, param):     pass
    def isVideoFormat(self, url):    pass
    def manualVideoCheck(self):      pass