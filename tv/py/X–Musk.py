# -*- coding: utf-8 -*-
import os
import re
import sys
import time
import base64
import random
import colorsys
import threading
from urllib.parse import quote, unquote

import requests
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

try:
    import ujson as json
except Exception:
    import json

try:
    import html as html_lib
except Exception:
    html_lib = None

sys.path.append("..")
from base.spider import Spider


PROXY_PORT = 20172
PROXIES = {
    "http": "http://127.0.0.1:%s" % PROXY_PORT,
    "https": "http://127.0.0.1:%s" % PROXY_PORT,
}


POST_HTML = """<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<meta name="referrer" content="no-referrer">
<style>
body{margin:0;background:#111;color:#eee;font-family:sans-serif;line-height:1.6;padding:16px;overscroll-behavior:none}
.card{background:#1b1b1b;border-radius:16px;padding:16px;margin-bottom:12px}
.name{font-size:18px;font-weight:700}.meta{opacity:.65;font-size:13px;margin-top:3px}
.text{font-size:16px;white-space:pre-wrap;margin-top:12px}
.tools{display:flex;gap:10px;position:sticky;top:0;z-index:20;background:rgba(17,17,17,.94);padding:10px 0;margin-bottom:8px}
.btn{border:0;border-radius:999px;background:#d8eadf;color:#1a2a20;padding:8px 14px;font-size:14px}
.media img{width:100%;height:auto;border-radius:12px;margin-top:12px;background:#222;display:block}
.commentBox{background:#181818;border-radius:16px;padding:12px;margin-top:16px}
.commentTitle{font-weight:700;margin-bottom:8px}
.comment{display:flex;gap:10px;padding:10px 0;border-bottom:1px solid rgba(255,255,255,.08)}
.comment:last-child{border-bottom:0}
.commentAvatar{width:34px;height:34px;border-radius:50%;object-fit:cover;background:#333;flex:0 0 auto}
.commentBody{flex:1;min-width:0}
.commentName{font-size:13px;color:#9ecbff;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-bottom:2px}
.commentText{font-size:14px;word-break:break-word}
.floatLayer{position:fixed;left:10px;right:10px;bottom:18px;z-index:30;pointer-events:none;display:none}
.floatComment{display:block;width:max-content;max-width:88%;background:rgba(0,0,0,.62);color:#fff;border-radius:999px;padding:6px 12px;margin-top:6px;font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;animation:fm 7s linear both}
@keyframes fm{0%{opacity:0;transform:translateY(20px)}12%{opacity:1}85%{opacity:1}100%{opacity:0;transform:translateY(-55px)}}
.overlay{position:fixed;inset:0;background:#000;display:none;justify-content:center;align-items:center;z-index:999;touch-action:pan-y}
.overlay.active{display:flex}.overlay img{max-width:100%;max-height:100%;object-fit:contain}
.counter{position:fixed;left:50%;bottom:18px;transform:translateX(-50%);background:rgba(0,0,0,.55);padding:6px 12px;border-radius:999px;font-size:13px;color:#fff}
</style></head><body>
<div class="card"><div class="name">###NAME###</div><div class="meta">###META###</div><div class="text">###TEXT###</div></div>
<div class="tools"><button class="btn" onclick="toCmt()">查看评论</button><button class="btn" onclick="floatCmt()">浮层评论</button></div>
<div class="media">###MEDIA###</div>
<div id="commentBox" class="commentBox"><div class="commentTitle">评论 ###COMMENT_COUNT###</div>###COMMENTS###</div>
<div id="floatLayer" class="floatLayer">###FLOAT_COMMENTS###</div>
<div id="overlay" class="overlay" onclick="closeZoom()"><img id="zoomedImg" src="" onclick="event.stopPropagation()"><div id="counter" class="counter"></div></div>
<script>
const overlay=document.getElementById('overlay'),zoomedImg=document.getElementById('zoomedImg'),counter=document.getElementById('counter');
let imgs=[],idx=0,sx=0,sy=0,mx=0,my=0;
function zoom(img){imgs=Array.from(document.querySelectorAll('.media img'));idx=imgs.indexOf(img);showImg();overlay.classList.add('active')}
function closeZoom(){overlay.classList.remove('active')}
function showImg(){if(idx>=0&&idx<imgs.length){zoomedImg.src=imgs[idx].src;counter.innerText=(idx+1)+' / '+imgs.length}}
function chg(d){let n=idx+d;if(n>=0&&n<imgs.length){idx=n;showImg()}}
function retryImage(img){let r=parseInt(img.getAttribute('data-retry')||'0');if(r>=4)return;img.setAttribute('data-retry',r+1);setTimeout(()=>{let u=img.src.replace(/([?&])retry=\\d+/,'');img.src=u+(u.includes('?')?'&':'?')+'retry='+Date.now()},900*(r+1))}
function toCmt(){document.getElementById('commentBox').scrollIntoView({behavior:'smooth',block:'start'})}
function floatCmt(){let f=document.getElementById('floatLayer');f.style.display=f.style.display==='block'?'none':'block'}
overlay.addEventListener('touchstart',e=>{let t=e.touches[0];sx=t.clientX;sy=t.clientY;mx=0;my=0},{passive:true});
overlay.addEventListener('touchmove',e=>{let t=e.touches[0];mx=t.clientX-sx;my=t.clientY-sy},{passive:true});
overlay.addEventListener('touchend',()=>{if(Math.abs(mx)>60&&Math.abs(mx)>Math.abs(my)*1.3){mx<0?chg(1):chg(-1)}});
</script></body></html>"""


class Spider(Spider):
    COOKIE_FILE = "/storage/emulated/0/TV/.X_cookie"
    OPS_FILE = "/storage/emulated/0/TV/.X_ops_cache"

    X_LOGO = "https://abs.twimg.com/responsive-web/client-web/icon-ios.77d25eba.png"
    DEFAULT_AVATAR = "https://abs.twimg.com/sticky/default_profile_images/default_profile_400x400.png"

    STYLE_TWEET = {"type": "rect"}
    STYLE_USER = {"type": "list", "ratio": 1.1}

    OPS = (
        "HomeTimeline",
        "Following",
        "UserTweets",
        "UserMedia",
        "SearchTimeline",
        "TweetDetail",
        "UserByScreenName",
    )

    KEEP_CK = ("auth_token", "ct0", "twid", "lang")

    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    def getName(self):
        return "X"

    def init(self, extend=""):
        self.proxies = PROXIES
        self.cfg = self._load_ext(extend)
        self.ua = self.cfg.get("ua") or self.headers["User-Agent"]

        self.page_size = int(self.cfg.get("page_size", 20))
        self.home_count = int(self.cfg.get("home_count", 120))
        self.media_count = int(self.cfg.get("media_count", 120))
        self.following_count = int(self.cfg.get("following_count", 120))
        self.search_count = int(self.cfg.get("search_count", 20))

        self.cookie_file = self.cfg.get("cookie_file") or self.COOKIE_FILE
        self.ops_file = self.cfg.get("ops_file") or self.OPS_FILE

        self.session = Session()
        self.session.headers.update(self.headers)
        self.session.headers["User-Agent"] = self.ua
        self.session.proxies.update(self.proxies)
        self._mount()

        self.cookie = self._norm_ck(self.cfg.get("cookie") or self._read(self.cookie_file))
        if self.cookie:
            self._set_cookie(self.cookie, save=bool(self.cfg.get("cookie")))

        self.bearer = self.cfg.get("bearer", "")
        self.ops = {}
        self._load_ops()
        self.ops.update(self.cfg.get("ops", {}) or {})

        self.uid = self.cfg.get("user_id") or self._uid_from_ck()
        self._reset()

    def _mount(self):
        try:
            retry = Retry(total=1, backoff_factor=0.25, status_forcelist=[429, 500, 502, 503, 504], allowed_methods=["GET"])
        except Exception:
            retry = Retry(total=1, backoff_factor=0.25, status_forcelist=[429, 500, 502, 503, 504], method_whitelist=["GET"])
        ad = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=40)
        self.session.mount("http://", ad)
        self.session.mount("https://", ad)

    def _reset(self):
        self.tweet_cache = {}
        self.user_cache = {}
        self.comment_cache = {}
        self.page_cache = {}
        self.cursor_cache = {}
        self.media_pool = {}
        self.video_pool = []
        self.video_seen = set()
        self.video_cursor = ""
        self.video_done = False
        self.video_round = 0
        self.video_empty = 0

    def _load_ext(self, extend):
        try:
            if isinstance(extend, dict):
                return extend
            s = str(extend or "").strip()
            if s.startswith("{"):
                return json.loads(s)
            if s.startswith("http"):
                return json.loads(requests.get(s, headers=self.headers, proxies=PROXIES, timeout=10).text.strip())
            if "auth_token=" in s and "ct0=" in s:
                return {"cookie": s}
        except Exception:
            pass
        return {}

    def _read(self, path):
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return f.read().strip()
        except Exception:
            pass
        return ""

    def _write(self, path, text):
        try:
            d = os.path.dirname(path)
            if d and not os.path.exists(d):
                os.makedirs(d)
            with open(path, "w", encoding="utf-8") as f:
                f.write(text or "")
        except Exception:
            pass

    def _ck_dict(self, ck):
        d = {}
        for p in (ck or "").replace("\r", "").replace("\n", "").split(";"):
            p = p.strip()
            if p and "=" in p:
                k, v = p.split("=", 1)
                if k.strip() and v.strip():
                    d[k.strip()] = v.strip()
        return d

    def _norm_ck(self, ck):
        ck = (ck or "").strip()
        if ck.lower().startswith("cookie:"):
            ck = ck[7:].strip()
        d = self._ck_dict(ck)
        if d and "lang" not in d:
            d["lang"] = "zh-cn"
        return "; ".join("%s=%s" % (k, d[k]) for k in self.KEEP_CK if d.get(k))

    def _set_cookie(self, ck, save=True):
        ck = self._norm_ck(ck)
        if "auth_token=" not in ck or "ct0=" not in ck:
            return False
        self.cookie = ck
        try:
            self.session.cookies.clear()
        except Exception:
            pass
        for k, v in self._ck_dict(ck).items():
            try:
                self.session.cookies.set(k, v, domain=".x.com", path="/")
                self.session.cookies.set(k, v, domain=".twitter.com", path="/")
            except Exception:
                pass
        if save:
            self._write(self.cookie_file, ck)
        return True

    def _uid_from_ck(self):
        m = re.search(r"u=(\d+)", unquote(self._ck_dict(self.cookie).get("twid", "")))
        return m.group(1) if m else ""

    def _ok(self):
        d = self._ck_dict(self.cookie)
        return bool(d.get("auth_token") and d.get("ct0"))

    def _x_headers(self):
        h = {
            "User-Agent": self.ua,
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://x.com/home",
            "Origin": "https://x.com",
            "Cookie": self.cookie,
            "x-twitter-active-user": "yes",
            "x-twitter-client-language": "zh-cn",
        }
        ct0 = self._ck_dict(self.cookie).get("ct0")
        if ct0:
            h["x-csrf-token"] = ct0
        if self.bearer:
            h["authorization"] = "Bearer " + self.bearer
            h["x-twitter-auth-type"] = "OAuth2Session"
        return h

    def _load_ops(self):
        try:
            if os.path.exists(self.ops_file):
                d = json.loads(self._read(self.ops_file))
                self.bearer = self.bearer or d.get("bearer", "")
                self.ops.update(d.get("ops", {}) or {})
        except Exception:
            pass

    def _save_ops(self):
        self._write(self.ops_file, json.dumps({"bearer": self.bearer, "ops": self.ops, "ts": int(time.time())}, ensure_ascii=False))

    def _bootstrap(self):
        if self.bearer and all(self.ops.get(x) for x in ("HomeTimeline", "Following", "UserMedia", "UserByScreenName", "TweetDetail")):
            return
        try:
            html = self.session.get("https://x.com/home", headers=self._x_headers(), timeout=12).text or ""
            self.bearer = self.bearer or self._bearer(html)
            for u in self._scripts(html)[:30]:
                try:
                    js = self.session.get(u, headers={"User-Agent": self.ua, "Referer": "https://x.com/home"}, timeout=10).text
                    self.bearer = self.bearer or self._bearer(js)
                    self._find_ops(js)
                    if all(self.ops.get(x) for x in ("HomeTimeline", "Following", "UserMedia", "UserByScreenName", "TweetDetail")):
                        break
                except Exception:
                    pass
            self._save_ops()
        except Exception:
            pass

    def _bearer(self, text):
        for p in (r"Bearer\s+([A-Za-z0-9%_\-\.]+)", r"(AAAAAAAAA[A-Za-z0-9%_\-\.]{50,})"):
            m = re.search(p, text or "")
            if m:
                return unquote(m.group(1))
        return ""

    def _scripts(self, html):
        out = []
        for m in re.finditer(r'<script[^>]+src=["\']([^"\']+\.js)["\']', html or ""):
            u = m.group(1)
            u = "https:" + u if u.startswith("//") else ("https://x.com" + u if u.startswith("/") else u)
            if u.startswith("http") and u not in out:
                out.append(u)
        for m in re.finditer(r"(https://abs\.twimg\.com/responsive-web/client-web/[^\"']+\.js)", html or ""):
            if m.group(1) not in out:
                out.append(m.group(1))
        return out

    def _find_ops(self, js):
        if not js:
            return
        for op in self.OPS:
            if self.ops.get(op):
                continue
            for p in (
                r'queryId:"([A-Za-z0-9_\-]+)",operationName:"' + re.escape(op) + r'"',
                r'operationName:"' + re.escape(op) + r'",queryId:"([A-Za-z0-9_\-]+)"',
                r'"queryId":"([A-Za-z0-9_\-]+)","operationName":"' + re.escape(op) + r'"',
                r'"operationName":"' + re.escape(op) + r'","queryId":"([A-Za-z0-9_\-]+)"',
                r'operationName:\s*"' + re.escape(op) + r'".{0,700}?queryId:\s*"([A-Za-z0-9_\-]+)"',
                r'queryId:\s*"([A-Za-z0-9_\-]+)".{0,700}?operationName:\s*"' + re.escape(op) + r'"',
            ):
                m = re.search(p, js)
                if m:
                    self.ops[op] = m.group(1)
                    break

    def _features(self, media=False, search=False):
        f = {
            "rweb_video_screen_enabled": False,
            "profile_label_improvements_pcf_label_in_post_enabled": True,
            "creator_subscriptions_tweet_preview_api_enabled": True,
            "responsive_web_graphql_timeline_navigation_enabled": True,
            "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
            "communities_web_enable_tweet_community_results_fetch": True,
            "c9s_tweet_anatomy_moderator_badge_enabled": True,
            "articles_preview_enabled": True,
            "responsive_web_edit_tweet_api_enabled": True,
            "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
            "view_counts_everywhere_api_enabled": True,
            "longform_notetweets_consumption_enabled": True,
            "responsive_web_twitter_article_tweet_consumption_enabled": True,
            "freedom_of_speech_not_reach_fetch_enabled": True,
            "standardized_nudges_misinfo": True,
            "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
            "longform_notetweets_rich_text_read_enabled": True,
            "longform_notetweets_inline_media_enabled": not media,
            "responsive_web_enhance_cards_enabled": False,
        }
        if media or search:
            f.update({
                "rweb_cashtags_enabled": True,
                "responsive_web_profile_redirect_enabled": False,
                "premium_content_api_read_enabled": False,
                "content_disclosure_indicator_enabled": True,
                "content_disclosure_ai_generated_indicator_enabled": True,
                "post_ctas_fetch_enabled": False,
            })
        if search:
            f.update({
                "rweb_tipjar_consumption_enabled": False,
                "verified_phone_label_enabled": False,
                "responsive_web_grok_analyze_button_fetch_trends_enabled": False,
                "responsive_web_grok_analyze_post_followups_enabled": True,
                "rweb_cashtags_composer_attachment_enabled": True,
                "responsive_web_jetfuel_frame": True,
                "responsive_web_grok_share_attachment_enabled": True,
                "responsive_web_grok_annotations_enabled": True,
                "rweb_conversational_replies_downvote_enabled": False,
                "responsive_web_grok_show_grok_translated_post": True,
                "responsive_web_grok_analysis_button_from_backend": True,
                "responsive_web_grok_image_annotation_enabled": True,
                "responsive_web_grok_imagine_annotation_enabled": True,
                "responsive_web_grok_community_note_auto_translation_is_enabled": True,
            })
        return f

    def _graphql(self, op, variables, media=False, search=False, ft=None, retry=True):
        if not self._ok():
            return {}
        if not self.bearer or not self.ops.get(op):
            self._bootstrap()
        qid = self.ops.get(op)
        if not qid:
            return {"_error": "缺少 operationId: " + op}
        params = {
            "variables": json.dumps(variables, ensure_ascii=False, separators=(",", ":")),
            "features": json.dumps(self._features(media, search or op == "SearchTimeline"), ensure_ascii=False, separators=(",", ":")),
        }
        if ft is None:
            ft = {
                "withArticleRichContentState": True,
                "withArticlePlainText": False,
                "withGrokAnalyze": False,
                "withDisallowedReplyControls": False,
            }
        if search or op == "SearchTimeline":
            ft = None
        if ft:
            params["fieldToggles"] = json.dumps(ft, ensure_ascii=False, separators=(",", ":"))
        try:
            h = self._x_headers()
            h["content-type"] = "application/json"
            r = self.session.get("https://x.com/i/api/graphql/%s/%s" % (qid, op), params=params, headers=h, timeout=18)
            text = r.text or ""
            if r.status_code in (401, 403, 429) or r.status_code >= 500 or not text.strip():
                return {"_error": "HTTP %s" % r.status_code}
            if "json" not in (r.headers.get("content-type") or "").lower() and not text.lstrip().startswith("{"):
                return {"_error": "非 JSON"}
            return r.json()
        except Exception as e:
            if retry:
                time.sleep(random.uniform(0.4, 1.0))
                return self._graphql(op, variables, media, search, ft, False)
            return {"_error": str(e)}

    def _img(self, url):
        url = self._raw_img(url)
        if not url:
            return ""
        if not url.startswith("http"):
            return url
        if "type=ximg" in url or "127.0.0.1" in url or "localhost" in url:
            return url
        if "twimg.com" in url or "x.com" in url or "twitter.com" in url:
            return "%s&type=ximg&url=%s" % (self.getProxyUrl(), quote(url, safe=""))
        return url

    def _raw_img(self, url):
        if not url:
            return ""
        url = str(url).replace("\\/", "/").replace("&amp;", "&")
        if url.startswith("//"):
            url = "https:" + url
        return url

    def _proxy_img(self, url):
        try:
            url = unquote(url or "")
            if not url.startswith("http"):
                return [404, "text/plain", ""]
            h = {
                "User-Agent": self.ua,
                "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                "Referer": "https://x.com/",
                "Origin": "https://x.com",
            }
            if self.cookie:
                h["Cookie"] = self.cookie
            r = self.session.get(url, headers=h, timeout=18, allow_redirects=True, proxies=self.proxies)
            if r.status_code != 200 or not r.content:
                return [404, "text/plain", ""]
            return [200, r.headers.get("content-type") or "image/jpeg", r.content]
        except Exception:
            return [500, "text/plain", ""]

    def homeContent(self, filter):
        return {
            "class": [
                {"type_id": "videos", "type_name": "推荐"},
                {"type_id": "following", "type_name": "关注用户"},
                {"type_id": "me", "type_name": "我的主页"},
                {"type_id": "x_config", "type_name": "X配置"},
            ],
            "filters": {},
        }

    def homeVideoContent(self):
        pass

    def categoryContent(self, tid, pg, filter, extend):
        if tid == "x_config":
            return self._config()
        if not self._ok():
            return {"list": [], "page": 1, "pagecount": 1}
        if tid == "videos":
            return self._home_videos(pg)
        if tid == "following":
            return self._following(pg, self.uid)
        if tid.startswith("following::"):
            return self._following(pg, tid.split("::", 1)[1])
        if tid == "me":
            return self._user_media(self.uid, pg)
        if tid.startswith("user::"):
            return self._user_media(tid.split("::")[1], pg)
        return {"list": [], "page": 1, "pagecount": 1}

    def _config(self):
        ok = self._ok()
        return {
            "list": [
                {
                    "vod_id": "xconf::input",
                    "vod_name": "手动输入 X Cookie",
                    "vod_pic": self._img(self.X_LOGO),
                    "vod_remarks": "已登录" if ok else "未登录",
                    "vod_content": self.cookie_file,
                    "style": self.STYLE_USER,
                },
                {
                    "vod_id": "xconf::status",
                    "vod_name": "检查 Cookie 状态",
                    "vod_pic": self._img(self.X_LOGO),
                    "vod_remarks": "已登录" if ok else "未登录",
                    "vod_content": self.cookie or "未配置",
                    "style": self.STYLE_USER,
                },
                {
                    "vod_id": "xconf::clear",
                    "vod_name": "清除本地 Cookie",
                    "vod_pic": self._img(self.X_LOGO),
                    "vod_remarks": "清除",
                    "vod_content": self.cookie_file,
                    "style": self.STYLE_USER,
                },
            ],
            "page": 1,
            "pagecount": 1,
        }

    def searchContent(self, key, quick, pg="1"):
        key = (key or "").strip()
        if not key or not self._ok():
            return {"list": [], "page": 1, "pagecount": 1}
        screen = self._screen(key)
        if screen:
            item = self._user_by_screen(screen)
            if item:
                return {"list": [item], "page": 1, "pagecount": 1, "limit": 1, "total": 1}

        def fetch(cursor):
            v = {
                "rawQuery": key,
                "count": self.search_count,
                "querySource": "typed_query",
                "product": "People",
                "withGrokTranslatedBio": True,
                "withQuickPromoteEligibilityTweetFields": False,
            }
            if cursor:
                v["cursor"] = cursor
            return self._parse_users(self._graphql("SearchTimeline", v, search=True))

        return self._paged("search:" + key, pg, fetch)

    def _screen(self, key):
        m = re.search(r"(?:x\.com|twitter\.com)/([A-Za-z0-9_]{1,15})(?:[/?#]|$)", key, re.I)
        if m and m.group(1).lower() not in ("home", "search", "i", "explore", "notifications", "messages"):
            return m.group(1)
        m = re.search(r"@([A-Za-z0-9_]{1,15})", key)
        if m:
            return m.group(1)
        return key if re.match(r"^[A-Za-z0-9_]{1,15}$", key) else ""

    def _user_by_screen(self, screen):
        data = self._graphql("UserByScreenName", {"screen_name": screen.strip().lstrip("@"), "withSafetyModeUserFields": True})
        try:
            user = (((data.get("data") or {}).get("user") or {}).get("result") or {})
        except Exception:
            user = {}
        return self._user_vod(user) if isinstance(user, dict) and user.get("__typename") != "UserUnavailable" else None

    def _home_videos(self, pg):
        p = self._page(pg)
        need = p * self.page_size
        while len(self.video_pool) < need and not self.video_done and self.video_round < max(30, p * 20):
            self.video_round += 1
            old = self.video_cursor
            v = {
                "count": self.home_count,
                "includePromotedContent": False,
                "latestControlAvailable": True,
                "withCommunity": True,
                "requestContext": "loadMore" if old else "launch",
            }
            if old:
                v["cursor"] = old
            items, bottom = self._parse_timeline(self._graphql("HomeTimeline", v))
            if not items and bottom and bottom != old:
                self.video_cursor = bottom
                continue
            if not items:
                self.video_empty += 1
                if self.video_empty < 2:
                    time.sleep(0.5)
                    continue
                self.video_done = True
                break
            self.video_empty = 0
            for it in items:
                tid = self._tid(it.get("vod_id", ""))
                c = self.tweet_cache.get(tid, {})
                if tid and tid not in self.video_seen and (c.get("_video_groups") or c.get("_videos")):
                    self.video_seen.add(tid)
                    self.video_pool.append(it)
            self.video_cursor = bottom if bottom and bottom != old else self.video_cursor
            if not bottom or bottom == old:
                self.video_done = True
        return self._pool(self.video_pool, p, not self.video_done)

    def _following(self, pg, uid):
        if not uid:
            return {"list": [], "page": 1, "pagecount": 1}

        def fetch(cursor):
            v = {"userId": str(uid), "count": self.following_count, "includePromotedContent": False}
            if cursor:
                v["cursor"] = cursor
            return self._parse_users(self._graphql("Following", v))

        return self._paged("following:" + str(uid), pg, fetch)

    def _user_media_page(self, uid, cursor=""):
        jobs = [
            (
                "UserMedia",
                {
                    "userId": str(uid),
                    "count": self.media_count,
                    "includePromotedContent": False,
                    "withClientEventToken": False,
                    "withBirdwatchNotes": False,
                    "withVoice": True,
                },
                True,
                {"withArticlePlainText": False},
            ),
            (
                "UserTweets",
                {
                    "userId": str(uid),
                    "count": self.media_count,
                    "includePromotedContent": False,
                    "withQuickPromoteEligibilityTweetFields": True,
                    "withVoice": True,
                    "withV2Timeline": True,
                },
                False,
                None,
            ),
        ]
        for op, v, media, ft in jobs:
            if cursor:
                v["cursor"] = cursor
            items, bottom = self._parse_timeline(self._graphql(op, v, media=media, ft=ft))
            if items or bottom:
                return items, bottom
        return [], ""

    def _user_media(self, uid, pg):
        if not uid:
            return {"list": [], "page": 1, "pagecount": 1}
        p = self._page(pg)
        st = self.media_pool.setdefault(str(uid), {"pool": [], "seen": set(), "cursor": "", "done": False, "round": 0, "empty": 0})
        need = p * self.page_size
        while len(st["pool"]) < need and not st["done"] and st["round"] < max(120, p * 80):
            st["round"] += 1
            old = st["cursor"]
            items, bottom = self._user_media_page(uid, old)
            if not items and bottom and bottom != old:
                st["cursor"] = bottom
                continue
            if not items:
                st["empty"] += 1
                if st["empty"] < 2:
                    time.sleep(0.5)
                    continue
                st["done"] = True
                break
            st["empty"] = 0
            for it in items:
                for card in self._media_cards(it):
                    key = card.get("vod_id") or card.get("vod_pic")
                    if key and key not in st["seen"]:
                        st["seen"].add(key)
                        st["pool"].append(card)
            if bottom and bottom != old:
                st["cursor"] = bottom
            else:
                st["done"] = True
        return self._pool(st["pool"], p, not st["done"])

    def _pool(self, pool, p, more):
        s = (p - 1) * self.page_size
        e = p * self.page_size
        return {
            "list": pool[s:e],
            "page": p,
            "pagecount": p + 1 if more or len(pool) > e else p,
            "limit": self.page_size,
            "total": 999999 if more or len(pool) > e else len(pool),
        }

    def _paged(self, key, pg, fetch):
        p = self._page(pg)
        ck = "%s:p:%s" % (key, p)
        if ck in self.page_cache:
            items, bottom = self.page_cache[ck]
            return self._page_ret(items, p, bottom)
        cursor = self.cursor_cache.get("%s:c:%s" % (key, p - 1), "") if p > 1 else ""
        if p > 1 and not cursor:
            for i in range(1, p):
                prev = self.cursor_cache.get("%s:c:%s" % (key, i - 1), "") if i > 1 else ""
                items, bottom = fetch(prev)
                self.page_cache["%s:p:%s" % (key, i)] = (items, bottom)
                if not bottom:
                    break
                self.cursor_cache["%s:c:%s" % (key, i)] = bottom
            cursor = self.cursor_cache.get("%s:c:%s" % (key, p - 1), "")
        items, bottom = fetch(cursor)
        self.page_cache[ck] = (items, bottom)
        if bottom:
            self.cursor_cache["%s:c:%s" % (key, p)] = bottom
        return self._page_ret(items, p, bottom)

    def _page_ret(self, items, p, bottom):
        return {"list": items, "page": p, "pagecount": p + 1 if bottom else p, "limit": self.page_size, "total": 999999 if bottom else len(items)}

    def _parse_timeline(self, data):
        if not isinstance(data, dict) or data.get("errors") or data.get("_error"):
            return [], ""
        out, seen = [], set()
        for n in self._nodes(data):
            if not isinstance(n, dict) or not isinstance(n.get("tweet_results"), dict):
                continue
            tw = self._unwrap(n.get("tweet_results", {}).get("result"))
            if not isinstance(tw, dict):
                continue
            legacy = tw.get("legacy") or {}
            tid = str(tw.get("rest_id") or legacy.get("id_str") or "")
            if tid and tid not in seen:
                item = self._tweet_vod(tw)
                if item:
                    seen.add(tid)
                    out.append(item)
        return out, self._bottom(data)

    def _parse_users(self, data):
        if not isinstance(data, dict) or data.get("errors") or data.get("_error"):
            return [], ""
        entries, out = [], []
        self._entries(data, entries)
        for e in entries:
            if self._is_cursor(e):
                continue
            c = e.get("content") or {}
            u = self._user_vod_from(c)
            if u:
                out.append(u)
            for it in c.get("items", []) or []:
                u = self._user_vod_from(it)
                if u:
                    out.append(u)
        seen, uniq = set(), []
        for it in out:
            vid = it.get("vod_id")
            if vid and vid not in seen:
                seen.add(vid)
                uniq.append(it)
        return uniq, self._bottom(data)

    def _tweet_vod(self, tw):
        legacy = tw.get("legacy") or {}
        tid = str(tw.get("rest_id") or legacy.get("id_str") or "")
        if not tid:
            return None
        user = (((tw.get("core") or {}).get("user_results") or {}).get("result") or {}) or self._best_user(tw) or {}
        uleg = user.get("legacy") or {}
        uid = str(user.get("rest_id") or uleg.get("id_str") or "")
        screen = uleg.get("screen_name") or user.get("screen_name") or self._deep(user, ("screen_name",)) or ""
        uname = uleg.get("name") or user.get("name") or self._deep(user, ("name",)) or "X用户"
        text = self._clean(legacy.get("full_text") or legacy.get("text") or "")
        cover, photos, videos, groups = self._media(tw)
        cover = self._img(cover or self._avatar(user) or self.DEFAULT_AVATAR)
        views = ((tw.get("views") or {}).get("count") or "")
        tp = "视频" if groups or videos else ("图片" if photos else "文字")
        remark = [tp]
        if views:
            remark.append("浏览 " + str(views))
        remark.append("评%s 转%s 赞%s" % (legacy.get("reply_count", 0), legacy.get("retweet_count", 0), legacy.get("favorite_count", 0)))
        title = ("@%s  %s" % (screen, text[:45]) if screen else text[:60]).strip() or uname
        item = {
            "vod_id": "tweet:" + tid,
            "vod_name": title,
            "vod_pic": cover,
            "vod_remarks": " / ".join(remark),
            "vod_content": "%s\n\n@%s\n%s" % (text, screen, legacy.get("created_at", "")),
            "vod_director": self._cr_following(uid, "%s 正在关注的人" % uname) if uid else "",
            "style": self.STYLE_TWEET,
            "_tweet_id": tid,
            "_user_id": uid,
            "_screen_name": screen,
            "_user_name": uname,
            "_photos": photos,
            "_videos": videos,
            "_video_groups": groups,
        }
        self.tweet_cache[tid] = item
        return {"vod_id": item["vod_id"], "vod_name": title, "vod_pic": cover, "vod_remarks": item["vod_remarks"], "style": self.STYLE_TWEET}

    def _media(self, tw):
        legacy = tw.get("legacy") or {}
        photos, videos, groups, cover = [], [], [], ""
        medias = []
        medias.extend(((legacy.get("extended_entities") or {}).get("media") or []))
        medias.extend(((legacy.get("entities") or {}).get("media") or []))
        for m in medias:
            c = self._add_media(m, photos, videos, groups)
            if c and not cover:
                cover = c
        bv = self._bind(((tw.get("card") or {}).get("legacy") or {}).get("binding_values"))
        for k in ("player_image", "thumbnail_image_original", "thumbnail_image", "photo_image_full_size"):
            u = bv.get(k)
            if isinstance(u, str) and u.startswith("http"):
                cover = cover or u
                if not groups and u not in photos:
                    photos.append(u)
        for k in ("player_stream_url", "player_url"):
            u = bv.get(k)
            if isinstance(u, str) and u.startswith("http"):
                groups.append({"cover": cover, "duration": 180, "variants": [{"name": self._qname(u, 0, ""), "url": u, "bitrate": 0, "type": "url"}]})
                videos.append(u)
        unified = bv.get("unified_card")
        if isinstance(unified, str) and unified.strip().startswith("{"):
            try:
                for _, m in (json.loads(unified).get("media_entities") or {}).items():
                    c = self._add_media(m, photos, videos, groups)
                    if c and not cover:
                        cover = c
            except Exception:
                pass
        clean, seen = [], set()
        for g in groups:
            vs = g.get("variants") or []
            if not vs:
                continue
            k = self._vkey(vs[0].get("url", ""))
            if k and k not in seen:
                seen.add(k)
                clean.append(g)
        return cover, self._uniq(photos), self._uniq(videos), clean

    def _add_media(self, m, photos, videos, groups):
        if not isinstance(m, dict):
            return ""
        cover = self._raw_img(m.get("media_url_https") or m.get("media_url") or m.get("url") or "")
        mt = m.get("type") or m.get("media_type") or ""
        if mt == "photo":
            if cover and cover not in photos:
                photos.append(cover)
            return cover
        if mt not in ("video", "animated_gif"):
            return cover
        info = m.get("video_info") or {}
        duration = int(info.get("duration_millis", 0) or 0) // 1000 or 180
        variants = []
        for v in info.get("variants") or []:
            url = v.get("url") or ""
            ct = v.get("content_type") or ""
            br = int(v.get("bitrate", 0) or 0)
            if not url:
                continue
            tp = "mp4" if "mp4" in ct or ".mp4" in url else ("hls" if "mpegurl" in ct.lower() or ".m3u8" in url else "url")
            variants.append({"name": self._qname(url, br, ct), "url": url, "bitrate": br, "type": tp})
        variants = self._variants(variants)
        if variants:
            groups.append({"cover": cover, "duration": duration, "variants": variants})
            videos.append(self._best_variant({"variants": variants}).get("url", ""))
        return cover

    def _variants(self, arr):
        mp4 = sorted([x for x in arr if x.get("type") == "mp4"], key=lambda x: x.get("bitrate", 0), reverse=True)
        hls = [x for x in arr if x.get("type") == "hls"]
        other = [x for x in arr if x.get("type") not in ("mp4", "hls")]
        out, seen = [], set()
        for x in hls + mp4 + other:
            k = self._variant_key(x.get("url", ""))
            if k and k not in seen:
                seen.add(k)
                out.append(x)
        return out

    def _best_variant(self, g):
        vs = g.get("variants") or []
        if not vs:
            return {}
        for x in vs:
            if x.get("type") == "hls":
                return x
        return sorted(vs, key=lambda x: x.get("bitrate", 0), reverse=True)[0]

    def _media_cards(self, item):
        tid = self._tid(item.get("vod_id", ""))
        c = self.tweet_cache.get(tid, {})
        if not tid or not c:
            return []
        base = {"vod_name": c.get("vod_name") or item.get("vod_name") or "X媒体", "vod_content": c.get("vod_content", ""), "vod_director": c.get("vod_director", ""), "style": self.STYLE_TWEET}
        groups = c.get("_video_groups") or []
        if groups:
            out = []
            for i, g in enumerate(groups):
                if g.get("variants"):
                    d = dict(base)
                    d.update({"vod_id": "tweet:%s::video::%s" % (tid, i), "vod_pic": self._img(g.get("cover") or c.get("vod_pic", "")), "vod_remarks": "视频 / %s" % c.get("vod_remarks", "")})
                    out.append(d)
            return out
        photos = self._uniq(c.get("_photos") or [])
        if photos:
            d = dict(base)
            d.update({"vod_id": "tweet:%s::photo::0" % tid, "vod_pic": self._img(photos[0]), "vod_remarks": "图片 %s张 / %s" % (len(photos), c.get("vod_remarks", ""))})
            return [d]
        return []

    def detailContent(self, ids):
        vid = ids[0] if ids else ""
        if not vid:
            return {"list": []}
        if vid.startswith("xconf::"):
            names = {"xconf::input": "手动输入 X Cookie", "xconf::status": "检查 Cookie 状态", "xconf::clear": "清除本地 Cookie"}
            return {"list": [{"vod_id": vid, "vod_name": names.get(vid, "X配置"), "vod_pic": self._img(self.X_LOGO), "vod_remarks": "配置", "vod_content": self.cookie or self.cookie_file, "vod_play_from": "配置", "vod_play_url": "执行$" + vid}]}
        if vid.startswith("user::"):
            arr = vid.split("::")
            uid = arr[1] if len(arr) > 1 else ""
            screen = arr[2] if len(arr) > 2 else ""
            u = self.user_cache.get(uid, {})
            name = u.get("name") or screen or "X用户"
            return {"list": [{"vod_id": "user::%s::%s" % (uid, screen), "vod_name": "%s  @%s" % (name, screen), "vod_pic": self._img(u.get("avatar", self.DEFAULT_AVATAR)), "vod_remarks": "推主用户", "vod_content": u.get("description", ""), "vod_tag": "folder", "style": self.STYLE_USER, "vod_director": self._cr_raw("user::%s::%s" % (uid, screen), "%s 的媒体帖" % name) + "　" + self._cr_raw("following::%s" % uid, "%s 正在关注的人" % name)}]}
        tid = self._tid(vid)
        item = self.tweet_cache.get(tid) or self._tweet_detail(tid)
        if not item:
            return {"list": []}
        groups = item.get("_video_groups") or []
        selected = None
        if "::video::" in vid:
            try:
                selected = int(vid.rsplit("::", 1)[1])
            except Exception:
                pass

        post_ep = "查看帖子$xpost::" + self._b64(json.dumps(item, ensure_ascii=False))
        play_from, play_url = [], []

        if groups:
            use = [groups[selected]] if selected is not None and 0 <= selected < len(groups) else groups
            eps = []
            for i, g in enumerate(use):
                v = self._best_variant(g)
                if v.get("url"):
                    title = "视频%s-%s" % (i + 1, v.get("name", "播放")) if len(use) > 1 else v.get("name", "播放")
                    eps.append("%s$%s_dm_%s" % (title, tid, v["url"]))
            if eps:
                eps.append(post_ep)
                play_from.append("X视频")
                play_url.append("#".join(eps))
        elif item.get("_videos"):
            eps = ["视频%s$%s_dm_%s" % (i + 1, tid, u) for i, u in enumerate(item.get("_videos") or []) if u]
            if eps:
                eps.append(post_ep)
                play_from.append("X视频")
                play_url.append("#".join(eps))

        if not play_from:
            play_from.append("查看帖子")
            play_url.append(post_ep)

        return {"list": [{"vod_id": "tweet:" + tid, "vod_name": item.get("vod_name", ""), "vod_pic": self._img(item.get("vod_pic", "")), "vod_remarks": item.get("vod_remarks", ""), "vod_content": item.get("vod_content", ""), "vod_director": item.get("vod_director", ""), "style": self.STYLE_TWEET, "vod_play_from": "$$$".join(play_from), "vod_play_url": "$$$".join(play_url)}]}

    def _tweet_detail(self, tid):
        v = {"focalTweetId": str(tid), "with_rux_injections": False, "includePromotedContent": False, "withCommunity": True, "withQuickPromoteEligibilityTweetFields": True, "withBirdwatchNotes": True, "withVoice": True, "withV2Timeline": True}
        items, _ = self._parse_timeline(self._graphql("TweetDetail", v))
        for it in items:
            if it.get("vod_id") == "tweet:" + str(tid):
                return self.tweet_cache.get(str(tid))
        return self.tweet_cache.get(str(tid))

    def playerContent(self, flag, id, vipFlags):
        header = {"User-Agent": self.ua, "Referer": "https://x.com/"}
        if id.startswith("xconf::"):
            if id == "xconf::input":
                self._input_ck()
            elif id == "xconf::status":
                self._toast("状态：%s\n路径：%s\nuser_id：%s\nCookie：%s" % ("已登录" if self._ok() else "未登录", self.cookie_file, self.uid or "未识别", self.cookie or "空"))
            elif id == "xconf::clear":
                self._clear_ck()
            return {"parse": 0, "playUrl": "", "url": "about:blank", "header": header}
        if id.startswith("xpost::"):
            try:
                self._show_post(json.loads(self._unb64(id.split("::", 1)[1])))
            except Exception:
                pass
            return {"parse": 0, "playUrl": "", "url": "about:blank", "header": header}
        if "_dm_" in id:
            tid, url = id.split("_dm_", 1)
            try:
                threading.Thread(target=self._refresh_dm, args=(tid, self._duration(tid)), daemon=True).start()
            except Exception:
                pass
            return {"parse": 0, "playUrl": "", "url": url, "header": header}
        if "x.com" in id or "twitter.com" in id:
            header.update(self._x_headers())
        return {"parse": 0, "playUrl": "", "url": id, "header": header}

    def localProxy(self, param):
        try:
            if isinstance(param, str):
                try:
                    param = json.loads(param)
                except Exception:
                    param = {}
            tp = self._pget(param, "type")
            if tp == "ximg":
                return self._proxy_img(self._pget(param, "url"))
            if tp == "xdm":
                return self._dm_xml(self._comments(self._pget(param, "tid")), int(self._pget(param, "times") or 180))
        except Exception:
            pass
        return [404, "text/plain", ""]

    def _duration(self, tid):
        for g in self.tweet_cache.get(str(tid), {}).get("_video_groups") or []:
            try:
                d = int(g.get("duration", 0) or 0)
                if d > 0:
                    return d
            except Exception:
                pass
        return 180

    def _refresh_dm(self, tid, duration):
        try:
            time.sleep(0.8)
            dm = "%s&type=xdm&tid=%s&times=%s" % (self.getProxyUrl(), quote(str(tid)), int(duration or 180))
            requests.get("http://127.0.0.1:9978/action?do=refresh&type=danmaku&path=%s" % quote(dm), timeout=3, headers={"User-Agent": "Mozilla/5.0"})
        except Exception:
            pass

    def _pget(self, p, k):
        if not isinstance(p, dict):
            return ""
        v = p.get(k, "")
        return v[0] if isinstance(v, list) and v else v

    def _comments(self, tid, limit=120):
        return [x.get("text", "") for x in self._comment_items(tid, limit) if x.get("text")]

    def _comment_items(self, tid, limit=120):
        tid = str(tid or "")
        if not tid:
            return []
        ck = "comments:" + tid
        if ck in self.comment_cache:
            return self.comment_cache[ck][:limit]
        items, seen, cursor = [], set(), ""
        for _ in range(3):
            data = self._tweet_detail_raw(tid, cursor)
            for n in self._nodes(data):
                if not isinstance(n, dict) or not isinstance(n.get("tweet_results"), dict):
                    continue
                tw = self._unwrap(n.get("tweet_results", {}).get("result"))
                if not isinstance(tw, dict):
                    continue
                legacy = tw.get("legacy") or {}
                cid = str(tw.get("rest_id") or legacy.get("id_str") or "")
                if not cid or cid == tid or cid in seen:
                    continue
                conv = str(legacy.get("conversation_id_str") or "")
                reply = str(legacy.get("in_reply_to_status_id_str") or "")
                if (conv or reply) and conv != tid and reply != tid:
                    continue
                text = self._clean(legacy.get("full_text") or legacy.get("text") or "")
                if not text or len(text) > 120:
                    continue
                user = (((tw.get("core") or {}).get("user_results") or {}).get("result") or {}) or self._best_user(tw) or {}
                uleg = user.get("legacy") or {}
                items.append({"id": cid, "name": uleg.get("name") or user.get("name") or self._deep(user, ("name",)) or "X用户", "screen": uleg.get("screen_name") or user.get("screen_name") or self._deep(user, ("screen_name",)) or "", "avatar": self._avatar(user) or self.DEFAULT_AVATAR, "text": text})
                seen.add(cid)
                if len(items) >= limit:
                    self.comment_cache[ck] = items
                    return items
            bottom = self._bottom(data)
            if not bottom or bottom == cursor:
                break
            cursor = bottom
        self.comment_cache[ck] = items
        return items[:limit]

    def _tweet_detail_raw(self, tid, cursor=""):
        v = {"focalTweetId": str(tid), "with_rux_injections": False, "includePromotedContent": False, "withCommunity": True, "withQuickPromoteEligibilityTweetFields": True, "withBirdwatchNotes": True, "withVoice": True, "withV2Timeline": True}
        if cursor:
            v["cursor"] = cursor
        return self._graphql("TweetDetail", v)

    def _dm_xml(self, comments, duration):
        try:
            duration = max(30, int(duration or 180))
            total = len(comments)
            now = int(time.time())
            xml = [
                '<?xml version="1.0" encoding="UTF-8"?>',
                "<i><chatserver>chat.x.com</chatserver><chatid>88888888</chatid><mission>0</mission><maxlimit>99999</maxlimit><state>0</state><real_name>0</real_name><source>x</source>",
                '<d p="0,5,25,16711680,%s,0,0,0">共有%s条评论弹幕来袭！！！</d>' % (now, total),
            ]
            if total <= 0:
                xml.append('<d p="2,1,25,16777215,%s,0,0,1">暂无评论弹幕</d>' % now)
            else:
                for i, text in enumerate(comments):
                    t = round(max(0, min(duration, (i / float(total)) * duration + random.uniform(-2.5, 2.5))), 1)
                    safe = self._dm_escape(text)
                    if safe:
                        xml.append('<d p="%s,1,25,%s,%s,0,%s,%s">%s</d>' % (t, self._dm_color(), now, abs(hash(safe)) % 1000000, i + 2, safe))
            xml.append("</i>")
            return [200, "text/xml", "\n".join(xml)]
        except Exception:
            return [500, "text/plain", ""]

    def _dm_escape(self, text):
        return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", re.sub(r"https://t\.co/\S+", "", text or "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").strip()

    def _dm_color(self):
        if random.random() < 0.1:
            r, g, b = colorsys.hsv_to_rgb(random.random(), random.uniform(0.65, 1.0), random.uniform(0.80, 1.0))
            return str((int(r * 255) << 16) + (int(g * 255) << 8) + int(b * 255))
        return "16777215"

    def _show_post(self, item):
        imgs = ['<img src="%s" onclick="zoom(this)" onerror="retryImage(this)" data-retry="0">' % self._esc(self._img(u)) for u in item.get("_photos", []) or []]
        tid = str(item.get("_tweet_id") or "")
        try:
            comments = self._comment_items(tid, 80) if tid else []
        except Exception:
            comments = []

        ch, fh = [], []
        if comments:
            for i, c in enumerate(comments):
                text = self._esc(c.get("text", ""))
                name = self._esc(c.get("name") or "评论")
                screen = self._esc(c.get("screen") or "")
                avatar = self._esc(self._img(c.get("avatar") or self.DEFAULT_AVATAR))
                show = "%s @%s" % (name, screen) if screen else name
                ch.append('<div class="comment"><img class="commentAvatar" src="%s"><div class="commentBody"><div class="commentName">%s</div><div class="commentText">%s</div></div></div>' % (avatar, show, text))
                if i < 14:
                    short = self._esc((("@%s：%s" % (screen, c.get("text", ""))) if screen else c.get("text", ""))[:80])
                    fh.append('<div class="floatComment" style="animation-delay:%.2fs">%s</div>' % (i * 0.55, short))
        else:
            ch.append('<div class="comment"><div class="commentBody"><div class="commentText">暂无可见评论。</div></div></div>')

        html = POST_HTML.replace("###NAME###", self._esc(item.get("_user_name") or item.get("vod_name") or ""))
        html = html.replace("###META###", self._esc("@%s" % item.get("_screen_name", "")))
        html = html.replace("###TEXT###", self._esc(item.get("vod_content", "")))
        html = html.replace("###MEDIA###", "".join(imgs))
        html = html.replace("###COMMENT_COUNT###", str(len(comments)))
        html = html.replace("###COMMENTS###", "".join(ch))
        html = html.replace("###FLOAT_COMMENTS###", "".join(fh))
        self._popup(html)

    def _input_ck(self):
        try:
            from java import jclass, dynamic_proxy
            from java.lang import Runnable

            act = self._activity()
            if not act:
                return

            Builder = jclass("android.app.AlertDialog$Builder")
            EditText = jclass("android.widget.EditText")
            TextView = jclass("android.widget.TextView")
            LinearLayout = jclass("android.widget.LinearLayout")
            LP = jclass("android.widget.LinearLayout$LayoutParams")
            InputType = jclass("android.text.InputType")
            DialogClick = jclass("android.content.DialogInterface$OnClickListener")
            Toast = jclass("android.widget.Toast")

            class Run(dynamic_proxy(Runnable)):
                def __init__(self, fn):
                    super().__init__()
                    self.fn = fn

                def run(self):
                    self.fn()

            class Click(dynamic_proxy(DialogClick)):
                def __init__(self, fn):
                    super().__init__()
                    self.fn = fn

                def onClick(self, dialog, which):
                    self.fn()

            def ui():
                root = LinearLayout(act)
                root.setOrientation(LinearLayout.VERTICAL)
                root.setPadding(36, 8, 36, 0)

                tip = TextView(act)
                tip.setText("粘贴完整 X Cookie。\n保存后只保留 auth_token、ct0、twid、lang。\n路径：" + self.cookie_file)
                root.addView(tip, LP(-1, -2))

                edit = EditText(act)
                edit.setSingleLine(False)
                edit.setMinLines(5)
                edit.setMaxLines(10)
                edit.setHorizontallyScrolling(False)
                edit.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_MULTI_LINE | InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS)
                edit.setText(self.cookie or "")
                root.addView(edit, LP(-1, -2))

                def save():
                    ck = str(edit.getText().toString()).strip()
                    if self._set_cookie(ck, True):
                        self.uid = self._uid_from_ck()
                        self._reset()
                        Toast.makeText(act, "X Cookie 已保存", 0).show()
                    else:
                        Toast.makeText(act, "Cookie 无效：至少需要 auth_token 和 ct0", 1).show()

                Builder(act).setTitle("手动输入 X Cookie").setView(root).setNegativeButton("取消", None).setPositiveButton("保存", Click(save)).show()

            act.getWindow().getDecorView().post(Run(ui))
        except Exception as e:
            self._toast("输入框失败：" + str(e))

    def _clear_ck(self):
        try:
            if os.path.exists(self.cookie_file):
                os.remove(self.cookie_file)
        except Exception:
            pass
        self.cookie = ""
        self.uid = ""
        try:
            self.session.cookies.clear()
        except Exception:
            pass
        self._reset()
        self._toast("已清除 X Cookie")

    def _activity(self):
        try:
            from java import jclass

            JClass = jclass("java.lang.Class")
            AT = JClass.forName("android.app.ActivityThread")
            cur = AT.getMethod("currentActivityThread").invoke(None)
            f = AT.getDeclaredField("mActivities")
            f.setAccessible(True)
            for r in f.get(cur).values().toArray():
                rc = r.getClass()
                pf = rc.getDeclaredField("paused")
                pf.setAccessible(True)
                if not pf.getBoolean(r):
                    af = rc.getDeclaredField("activity")
                    af.setAccessible(True)
                    return af.get(r)
        except Exception:
            pass
        return None

    def _toast(self, msg):
        try:
            from java import jclass, dynamic_proxy
            from java.lang import Runnable

            act = self._activity()
            if not act:
                return
            Toast = jclass("android.widget.Toast")

            class Run(dynamic_proxy(Runnable)):
                def __init__(self, fn):
                    super().__init__()
                    self.fn = fn

                def run(self):
                    self.fn()

            act.getWindow().getDecorView().post(Run(lambda: Toast.makeText(act, str(msg), 1).show()))
        except Exception:
            pass

    def _popup(self, html):
        try:
            from java import jclass, dynamic_proxy
            from java.lang import Runnable

            act = self._activity()
            if not act:
                return

            class Run(dynamic_proxy(Runnable)):
                def __init__(self, fn):
                    super().__init__()
                    self.fn = fn

                def run(self):
                    self.fn()

            def ui():
                Dialog = jclass("android.app.Dialog")
                WebView = jclass("android.webkit.WebView")
                ColorDrawable = jclass("android.graphics.drawable.ColorDrawable")
                Color = jclass("android.graphics.Color")
                d = Dialog(act)
                d.requestWindowFeature(1)
                w = WebView(act)
                ws = w.getSettings()
                ws.setJavaScriptEnabled(True)
                ws.setDomStorageEnabled(True)
                w.setBackgroundColor(Color.BLACK)
                w.loadDataWithBaseURL("https://x.com/", html, "text/html", "utf-8", None)
                d.setContentView(w)
                d.show()
                win = d.getWindow()
                if win:
                    win.getDecorView().setPadding(0, 0, 0, 0)
                    win.setBackgroundDrawable(ColorDrawable(Color.TRANSPARENT))
                    win.setLayout(-1, -1)

            act.getWindow().getDecorView().post(Run(ui))
        except Exception:
            pass

    def _user_vod_from(self, c):
        if not isinstance(c, dict):
            return None
        ic = c.get("itemContent") or c
        ur = ic.get("user_results") or {}
        result = ur.get("result") if isinstance(ur, dict) else None
        if not isinstance(result, dict):
            result = self._best_user(c)
        return self._user_vod(result, c) if isinstance(result, dict) else None

    def _user_vod(self, user, source=None):
        if not isinstance(user, dict):
            return None
        leg = user.get("legacy") or {}
        core = user.get("core") or {}
        uid = str(user.get("rest_id") or leg.get("id_str") or "")
        if not uid:
            m = re.search(r"(\d{6,})", str(user.get("id") or ""))
            uid = m.group(1) if m else ""
        if not uid:
            return None
        screen = leg.get("screen_name") or core.get("screen_name") or user.get("screen_name") or self._deep(user, ("screen_name",)) or ""
        name = leg.get("name") or core.get("name") or user.get("name") or self._deep(user, ("name",)) or "X用户"
        desc = leg.get("description") or ((user.get("profile_bio") or {}).get("description")) or user.get("description") or self._deep(user, ("description",)) or ""
        avatar = self._img(self._avatar(user) or self._avatar(source) or self.DEFAULT_AVATAR)
        self.user_cache[uid] = {"id": uid, "screen_name": screen, "name": name, "description": desc, "avatar": avatar}
        return {
            "vod_id": "user::%s::%s" % (uid, screen),
            "vod_name": "%s  @%s" % (name, screen),
            "vod_pic": avatar,
            "vod_remarks": "媒体 %s / 帖子 %s / 关注 %s / 粉丝 %s" % (leg.get("media_count", 0), leg.get("statuses_count", 0), leg.get("friends_count", 0), leg.get("followers_count", 0)),
            "vod_content": desc,
            "vod_tag": "folder",
            "style": self.STYLE_USER,
            "vod_director": self._cr_following(uid, "%s 正在关注的人" % name),
        }

    def _avatar(self, obj):
        if not obj:
            return ""
        direct = self._deep(obj, ("profile_image_url_https", "profile_image_url", "profile_image_url_400x400", "avatar_url", "image_url"))
        if direct and ("profile_images" in direct or "twimg.com" in direct):
            return self._fix_avatar(direct)
        for s in self._strings(obj):
            m = re.search(r'https://pbs\.twimg\.com/profile_images/[^"\'>\s\\]+', s.replace("\\/", "/"))
            if m:
                return self._fix_avatar(m.group(0))
        return ""

    def _fix_avatar(self, u):
        u = self._raw_img(u)
        return u.replace("_normal.", "_400x400.") if "_normal." in u else u

    def _best_user(self, obj):
        best, score = None, -1
        for n in self._nodes(obj):
            if not isinstance(n, dict):
                continue
            r = n.get("user_results", {}).get("result") if isinstance(n.get("user_results"), dict) else n
            if not isinstance(r, dict):
                continue
            leg, core = r.get("legacy") or {}, r.get("core") or {}
            if not str(r.get("rest_id") or leg.get("id_str") or ""):
                continue
            sc = (5 if leg.get("screen_name") or core.get("screen_name") or r.get("screen_name") else 0) + (5 if leg.get("name") or core.get("name") or r.get("name") else 0) + (20 if self._avatar(r) else 0)
            if sc > score:
                best, score = r, sc
        return best

    def _unwrap(self, r):
        if not isinstance(r, dict):
            return None
        if r.get("__typename") == "TweetWithVisibilityResults":
            return self._unwrap(r.get("tweet"))
        if r.get("__typename") == "TweetTombstone":
            return None
        if isinstance(r.get("tweet"), dict):
            return self._unwrap(r.get("tweet"))
        rt = (r.get("legacy") or {}).get("retweeted_status_result", {})
        if isinstance(rt, dict) and isinstance(rt.get("result"), dict):
            return self._unwrap(rt.get("result")) or r
        return r

    def _entries(self, obj, out):
        if isinstance(obj, dict):
            if "entryId" in obj and "content" in obj:
                out.append(obj)
            for v in obj.values():
                self._entries(v, out)
        elif isinstance(obj, list):
            for v in obj:
                self._entries(v, out)

    def _is_cursor(self, e):
        if not isinstance(e, dict):
            return False
        eid = str(e.get("entryId", "")).lower()
        c = e.get("content") or {}
        cur = ((c.get("operation") or {}).get("cursor") or {}) if isinstance(c.get("operation"), dict) else {}
        return "cursor" in eid or bool(c.get("cursorType")) or bool(cur.get("cursorType"))

    def _bottom(self, obj):
        cs = []
        for n in self._nodes(obj):
            if not isinstance(n, dict):
                continue
            if n.get("cursorType") == "Bottom" and isinstance(n.get("value"), str):
                cs.append(n.get("value"))
            eid = str(n.get("entryId", "")).lower()
            c = n.get("content") or {}
            if "cursor-bottom" in eid or "cursorbottom" in eid:
                v = c.get("value") or n.get("value")
                if not v and isinstance(c.get("operation"), dict):
                    v = ((c.get("operation") or {}).get("cursor") or {}).get("value")
                if isinstance(v, str):
                    cs.append(v)
            if isinstance(c, dict):
                if c.get("cursorType") == "Bottom" and isinstance(c.get("value"), str):
                    cs.append(c.get("value"))
                cur = ((c.get("operation") or {}).get("cursor") or {}) if isinstance(c.get("operation"), dict) else {}
                if cur.get("cursorType") == "Bottom" and isinstance(cur.get("value"), str):
                    cs.append(cur.get("value"))
        out = []
        for c in cs:
            if c and c not in ("0", "-1") and c not in out:
                out.append(c)
        return out[-1] if out else ""

    def _bind(self, bv):
        out = {}
        items = bv.items() if isinstance(bv, dict) else ([(x.get("key"), x.get("value")) for x in bv if isinstance(x, dict)] if isinstance(bv, list) else [])
        for k, v in items:
            if k:
                out[k] = (v.get("string_value") or v.get("scribe_key") or ((v.get("image_value") or {}).get("url")) or v.get("url") or "") if isinstance(v, dict) else v
        return out

    def _nodes(self, obj):
        if isinstance(obj, dict):
            yield obj
            for v in obj.values():
                for x in self._nodes(v):
                    yield x
        elif isinstance(obj, list):
            for v in obj:
                for x in self._nodes(v):
                    yield x

    def _strings(self, obj):
        if isinstance(obj, str):
            yield obj
        elif isinstance(obj, dict):
            for v in obj.values():
                for s in self._strings(v):
                    yield s
        elif isinstance(obj, list):
            for v in obj:
                for s in self._strings(v):
                    yield s

    def _deep(self, obj, keys):
        for n in self._nodes(obj):
            if isinstance(n, dict):
                for k in keys:
                    v = n.get(k)
                    if isinstance(v, str) and v.strip():
                        return v.strip()
                    if isinstance(v, int):
                        return str(v)
        return ""

    def _qname(self, url, br=0, ct=""):
        m = re.search(r"/vid/[^/]+/(\d+)x(\d+)/", url or "")
        if m:
            return "%sP" % min(int(m.group(1)), int(m.group(2)))
        if ".m3u8" in (url or "") or "mpegurl" in str(ct).lower():
            return "X"
        return "%skbps" % int(br / 1000) if br else "视频"

    def _vkey(self, url):
        return re.sub(r"/vid/[^/]+/", "/vid/QUALITY/", (url or "").split("?tag=")[0])

    def _variant_key(self, url):
        return (url or "").split("?tag=")[0]

    def _tid(self, vod_id):
        return (vod_id or "").replace("tweet:", "").split("::", 1)[0]

    def _page(self, pg):
        try:
            return max(1, int(pg or 1))
        except Exception:
            return 1

    def _uniq(self, arr):
        out = []
        for x in arr:
            if x and x not in out:
                out.append(x)
        return out

    def _clean(self, text):
        return re.sub(r"\s+", " ", re.sub(r"https://t\.co/\S+", "", (text or "").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">"))).strip()

    def _cr_raw(self, cid, name):
        return "[a=cr:%s/]%s[/a]" % (json.dumps({"id": cid, "name": name}, ensure_ascii=False), name)

    def _cr_following(self, uid, name):
        return self._cr_raw("following::%s" % uid, name)

    def _b64(self, s):
        return base64.urlsafe_b64encode((s if isinstance(s, bytes) else str(s).encode("utf-8"))).decode("utf-8").rstrip("=")

    def _unb64(self, s):
        return base64.urlsafe_b64decode((s + "=" * (-len(s) % 4)).encode("utf-8")).decode("utf-8", "ignore")

    def _esc(self, s):
        s = "" if s is None else str(s)
        return html_lib.escape(s) if html_lib else s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def isVideoFormat(self, url):
        return bool(re.search(r"\.(m3u8|mp4|flv|mov|mkv)(\?|$)", url or "", re.I))

    def manualVideoCheck(self):
        return False

    def liveContent(self, url):
        return {"list": []}

    def destroy(self):
        try:
            self.session.close()
        except Exception:
            pass