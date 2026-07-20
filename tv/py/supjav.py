import urllib.parse
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from curl_cffi import requests
from bs4 import BeautifulSoup

app = FastAPI()

BASE_URL = "https://supjav.com"

# 伪装完整的 Chrome 请求头
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://supjav.com/",
}

def fetch_html(url: str) -> str:
    """使用 curl_cffi 完美模拟 Chrome 指纹，绕过 Cloudflare 获取真实 HTML"""
    try:
        # impersonate="chrome" 会完全模拟真实浏览器的 TLS 和 HTTP/2 指纹
        response = requests.get(url, headers=HEADERS, impersonate="chrome", timeout=15)
        if response.status_code == 200:
            return response.text
    except Exception as e:
        print(f"请求失败: {e}")
    return ""

@app.get("/")
async def tvbox_api(request: Request):
    # 获取 TvBox 传入的参数
    params = request.query_params
    ac = params.get("ac", "list")
    pg = max(1, int(params.get("pg", 1)))
    wd = params.get("wd", "").strip() # TvBox 的搜索关键字参数名通常为 wd
    ids = params.get("ids", "").strip()

    # 1. 列表 / 搜索 模式 (TvBox: ac=list 或 ac=videolist)
    if ac in ["list", "videolist"]:
        if wd:
            # 搜索 URL
            url = f"{BASE_URL}/?s={urllib.parse.quote(wd)}" + (f"&paged={pg}" if pg > 1 else "")
        else:
            # 分页主页 URL
            url = f"{BASE_URL}/page/{pg}" if pg > 1 else f"{BASE_URL}/"

        html = fetch_html(url)
        video_list = []

        if html:
            soup = BeautifulSoup(html, "html.parser")
            # 采用全盲扫描带有 title 且包含 .html 的 a 标签，100% 容错
            a_tags = soup.find_all("a", href=True)
            
            seen_ids = set()
            for a in a_tags:
                href = a["href"]
                title = a.get("title", "").strip()
                
                # 筛选合规的视频链接
                if ".html" in href and title and "supjav.com" in href:
                    if any(x in href for x in ["popular", "category", "maker", "cast", "tag"]):
                        continue
                        
                    # 提取视频唯一ID
                    vod_id = href.split("/")[-1].replace(".html", "")
                    if vod_id in seen_ids:
                        continue
                    seen_ids.add(vod_id)

                    # 寻找图片标签
                    img_tag = a.find("img")
                    pic = ""
                    if img_tag:
                        pic = img_tag.get("src") or img_tag.get("data-original") or img_tag.get("data-src") or ""

                    video_list.append({
                        "vod_id": vod_id,       # TvBox 必需：视频唯一标识
                        "vod_name": title,      # TvBox 必需：视频名称
                        "vod_pic": pic.strip(), # TvBox 必需：图片
                        "vod_remarks": "高清"   # TvBox 可选：备注标签
                    })

        # 返回 TvBox 标准的列表响应格式
        return JSONResponse({
            "page": pg,
            "pagecount": pg + 1,  # 动态流式分页提示
            "limit": len(video_list),
            "total": len(video_list) * 10,
            "list": video_list
        })

    # 2. 详情 / 播放 模式 (TvBox: ac=detail)
    elif ac == "detail" and (ids or params.get("id")):
        vod_id = ids or params.get("id")
        # 补全视频真实的播放详情页 URL
        target_url = f"{BASE_URL}/{vod_id}.html"
        
        html = fetch_html(target_url)
        vod_play_url = f"点击播放${target_url}" # 默认将网页交给支持嗅探的TvBox

        if html:
            soup = BeautifulSoup(html, "html.parser")
            # 这里可以进阶解析页面里的真实播放源（如果需要），通常 TvBox 开启内置嗅探即可直接播放 supjav 的视频流。
            pass

        # 返回 TvBox 标准的详情响应格式
        return JSONResponse({
            "list": [
                {
                    "vod_id": vod_id,
                    "vod_name": f"视频 ID: {vod_id}",
                    "vod_play_from": "SupJav内嵌", # 播放源名称
                    "vod_play_url": vod_play_url   # 播放地址（名称$地址，多集用#分割）
                }
            ]
        })

    # 如果没有匹配的 ac 参数，返回空白 TvBox 模板
    return JSONResponse({"list": []})

if __name__ == "__main__":
    import uvicorn
    # 本地启动在 8000 端口
    uvicorn.run(app, host="0.0.0.0", port=8000)