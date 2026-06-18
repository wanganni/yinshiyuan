import re
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# ==================== 常量配置 ====================
DEFAULT_BASE_URL = "https://missav.ai"
REQUEST_TIMEOUT = 15
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://missav.ai/",
    "Connection": "keep-alive"
}

# ==================== 辅助函数 ====================
def fetch_html(url):
    """请求并返回HTML文本"""
    resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT)
    resp.encoding = 'utf-8'
    if resp.status_code != 200:
        raise Exception(f"HTTP {resp.status_code}")
    return resp.text

def parse_video_list(html):
    """
    解析视频列表页，返回TVBox格式的列表
    """
    if not html or "Just a moment" in html:
        print("警告：可能被 Cloudflare 拦截")
        return []

    soup = BeautifulSoup(html, 'html.parser')
    results = []

    # 根据JS中的选择器：div.group 下的视频卡片
    groups = soup.select("div.group")
    for group in groups:
        link_tag = group.select_one("a.text-secondary")
        if not link_tag:
            continue
        href = link_tag.get("href")
        if not href:
            continue

        title = link_tag.get_text(strip=True)
        img_tag = group.select_one("img")
        img_src = img_tag.get("data-src") or img_tag.get("src", "") if img_tag else ""
        duration = group.select_one(".absolute.bottom-1.right-1")
        duration_text = duration.get_text(strip=True) if duration else ""

        # 提取番号用于生成封面（可选）
        video_id = href.split('/')[-1].replace("-uncensored-leak", "").replace("-chinese-subtitle", "").upper()
        # 备用封面，原JS使用了 fourhoi.com，这里保留从img获取
        cover_url = img_src

        results.append({
            "vod_id": href.strip("/"),
            "vod_name": title,
            "vod_pic": cover_url,
            "vod_remarks": duration_text,
            "vod_content": f"番号: {video_id}"
        })
    return results

def load_list(category="dm588/cn/release", sort="released_at", page=1):
    """浏览视频列表"""
    url = f"{DEFAULT_BASE_URL}/{category}?sort={sort}"
    if page > 1:
        url += f"&page={page}"
    html = fetch_html(url)
    return parse_video_list(html)

def search_videos(keyword, page=1):
    """搜索视频"""
    if not keyword.strip():
        return []
    url = f"{DEFAULT_BASE_URL}/cn/search/{requests.utils.quote(keyword)}"
    if page > 1:
        url += f"?page={page}"
    html = fetch_html(url)
    return parse_video_list(html)

def get_vod_detail(vod_id_or_url):
    """
    获取视频详情（含播放地址）
    vod_id_or_url: 可以是完整URL或相对路径，如 "/cn/xxx"
    """
    if vod_id_or_url.startswith("http"):
        url = vod_id_or_url
    else:
        url = urljoin(DEFAULT_BASE_URL, vod_id_or_url)
    html = fetch_html(url)
    soup = BeautifulSoup(html, 'html.parser')

    # 提取标题
    title_tag = soup.select_one('meta[property="og:title"]')
    title = title_tag.get("content") if title_tag else ""
    if not title:
        title_tag = soup.select_one('h1')
        title = title_tag.get_text(strip=True) if title_tag else "未知标题"

    video_url = ""

    # 1. 尝试从所有 script 中提取 surrit.com 的 m3u8
    for script in soup.find_all("script"):
        script_content = script.string or ""
        if not script_content:
            continue

        # 直连 surrit.com 的 m3u8
        m3u8_matches = re.findall(r'https://surrit\.com/[a-f0-9\-]+/[^"\'\s]*\.m3u8', script_content)
        if m3u8_matches:
            video_url = m3u8_matches[0]
            break

        # 如果包含 eval 混淆，尝试提取 UUID 构造链接
        if "eval(function" in script_content:
            uuid_matches = re.findall(r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', script_content)
            if uuid_matches:
                video_url = f"https://surrit.com/{uuid_matches[0]}/playlist.m3u8"
                break

    # 2. 如果还没找到，尝试简单匹配 source = '...'
    if not video_url:
        simple_match = re.search(r"source\s*=\s*['\"]([^'\"]+)['\"]", html)
        if simple_match:
            video_url = simple_match.group(1)

    if not video_url:
        raise Exception("未找到播放地址")

    # 处理可能的 HTML 实体
    video_url = video_url.replace("&amp;", "&")

    return {
        "vod_id": vod_id_or_url,
        "vod_name": title,
        "vod_play_from": "MissAV源",
        "vod_play_url": f"播放器${video_url}",
        "vod_content": "",
        # 可选字段
        "vod_pic": "",
        "vod_actor": "",
        "vod_year": ""
    }

# ==================== 可选：Flask API 服务（TVBox 适配） ====================
def create_app():
    from flask import Flask, request, jsonify
    app = Flask(__name__)

    # 分类映射（可根据需要扩展）
    CATEGORY_MAP = {
        "1": {"category": "dm588/cn/release", "sort": "released_at", "name": "最新发布"},
        "2": {"category": "dm169/cn/weekly-hot", "sort": "views", "name": "本周热门"},
        "3": {"category": "dm257/cn/monthly-hot", "sort": "views", "name": "月度热门"},
        "4": {"category": "dm621/cn/uncensored-leak", "sort": "released_at", "name": "无码流出"},
        "5": {"category": "dm29/cn/tokyohot", "sort": "released_at", "name": "东京热"},
        "6": {"category": "dm265/cn/chinese-subtitle", "sort": "released_at", "name": "中文字幕"},
    }

    @app.route("/vodtype/<type_id>/<int:page>")
    def vod_type(type_id, page):
        """TVBox 分类接口"""
        if type_id not in CATEGORY_MAP:
            return jsonify({"list": [], "total": 0})
        cfg = CATEGORY_MAP[type_id]
        try:
            vod_list = load_list(category=cfg["category"], sort=cfg["sort"], page=page)
            return jsonify({"list": vod_list, "total": len(vod_list)})
        except Exception as e:
            print(f"分类加载失败: {e}")
            return jsonify({"list": [], "total": 0})

    @app.route("/voddetail/<vod_id>")
    def vod_detail(vod_id):
        """TVBox 详情接口（vod_id 为视频的路径，如 cn/xxx）"""
        try:
            detail = get_vod_detail(vod_id)
            # TVBox 详情要求返回一个包含 list 的字典（单个视频的列表）
            return jsonify({"list": [detail]})
        except Exception as e:
            print(f"详情加载失败: {e}")
            return jsonify({"list": []})

    @app.route("/search")
    def search():
        """搜索接口（可选，TVBox 可通过配置调用）"""
        keyword = request.args.get("wd", "")
        page = int(request.args.get("page", 1))
        try:
            vod_list = search_videos(keyword, page)
            return jsonify({"list": vod_list, "total": len(vod_list)})
        except Exception as e:
            print(f"搜索失败: {e}")
            return jsonify({"list": [], "total": 0})

    return app

if __name__ == "__main__":
    # 测试：直接输出列表
    print("=== 测试：浏览最新发布第1页 ===")
    lst = load_list(page=1)
    print(json.dumps(lst, ensure_ascii=False, indent=2))

    # 测试搜索
    print("\n=== 测试：搜索关键词 'ABP' ===")
    search_res = search_videos("ABP", page=1)
    print(json.dumps(search_res, ensure_ascii=False, indent=2))

    # 测试详情（需要提供真实 vod_id，例如从上面结果中取一个）
    if lst:
        sample_id = lst[0]["vod_id"]  # 例如 "cn/xxx"
        print(f"\n=== 测试详情：{sample_id} ===")
        try:
            detail = get_vod_detail(sample_id)
            print(json.dumps(detail, ensure_ascii=False, indent=2))
        except Exception as e:
            print(f"详情提取失败: {e}")

    # 如需启动 Flask 服务，取消注释以下两行
    # app = create_app()
    # app.run(host="0.0.0.0", port=5000)