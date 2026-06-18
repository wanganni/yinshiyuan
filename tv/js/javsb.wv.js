const baseUrl = 'https://jav.sb';

// ========== 必需接口 ==========

function homeContent() {
    return {
        class: [
            { type_id: "Censored", type_name: "日本有码" },
            { type_id: "Uncensored", type_name: "日本无码" },
            { type_id: "CHN_SUB", type_name: "中文字幕" },
            { type_id: "FC2-PPV", type_name: "FC2-PPV" },
            { type_id: "Mosaic_Removed", type_name: "无码破解" },
            { type_id: "MGS", type_name: "MGS动画" }
        ],
        filters: {}
    };
}

async function homeVideoContent() {
    let resp = await Java.req(baseUrl + "/");
    return { list: parseList(resp.body) };
}

async function categoryContent(tid, pg) {
    // 修复分类地址：javtype/{tid}/page/{pg}.html
    let url = pg == 1 ? `${baseUrl}/javtype/${tid}.html` : `${baseUrl}/javtype/${tid}/page/${pg}.html`;
    let resp = await Java.req(url);
    return {
        list: parseList(resp.body),
        page: parseInt(pg),
        pagecount: 99
    };
}

async function detailContent(ids) {
    let url = ids[0].startsWith('http') ? ids[0] : `${baseUrl}${ids[0]}`;
    let resp = await Java.req(url);
    return { list: [parseDetail(resp.body, ids[0])] };
}

async function searchContent(key, quick, pg) {
    let url = `${baseUrl}/search/${encodeURIComponent(key)}/page/${pg}.html`;
    let resp = await Java.req(url);
    return { list: parseList(resp.body), page: parseInt(pg) };
}

/**
 * 重点：利用注入脚本解决点击问题
 */
async function playerContent(flag, id) {
    // 注入脚本逻辑：
    // 1. 寻找页面中 src 包含 videojs.html 的 iframe
    // 2. 在 iframe 内部寻找 #promo-start 按钮并点击
    // 3. 点击后，页面会自动请求 m3u8，壳程序通过 keyword 捕获链接
    const clickScript = `
        (function() {
            let count = 0;
            let t = setInterval(() => {
                count++;
                // 1. 尝试在当前页或 iframe 寻找按钮
                let btn = document.querySelector('#promo-start');
                if (!btn) {
                    let iframe = document.querySelector('iframe[src*="videojs.html"]');
                    if (iframe && iframe.contentDocument) {
                        btn = iframe.contentDocument.querySelector('#promo-start');
                    }
                }
                
                // 2. 如果找到则点击并清除定时器
                if (btn) {
                    btn.click();
                    console.log('JAVSB: 已自动点击播放按钮');
                    clearInterval(t);
                }
                
                // 3. 超时保护 (15秒)
                if (count > 150) clearInterval(t);
            }, 100);
        })();
    `;

    return {
        type: 'sniff',
        url: id, // 传入详情页或播放页 URL
        keyword: '.m3u8|.mp4',
        script: clickScript,
        timeout: 20
    };
}

// ========== 通用解析函数 ==========

function parseList(html) {
    if (!html) return [];
    let vods = [];
    let seen = new Set();
    // 针对 thumbnail group 结构
    let itemRegex = /<div class="thumbnail group">([\s\S]*?)<div class="my-2 text-sm/gi;
    let match;
    while ((match = itemRegex.exec(html)) !== null) {
        let content = match[1];
        let linkMatch = content.match(/href="([^"]+)"/);
        if (!linkMatch) continue;
        let id = linkMatch[1];
        if (seen.has(id)) continue;
        seen.add(id);

        let imgMatch = content.match(/data-src="([^"]+)"/) || content.match(/src="([^"]+)"/);
        let titleMatch = content.match(/alt="([^"]+)"/);
        let remarkMatch = content.match(/text-nord5[^>]*>([^<]+)</);

        vods.push({
            vod_id: id,
            vod_name: titleMatch ? titleMatch[1].trim() : "未知",
            vod_pic: imgMatch ? (imgMatch[1].startsWith('http') ? imgMatch[1] : baseUrl + imgMatch[1]) : "",
            vod_remarks: remarkMatch ? remarkMatch[1].trim() : ""
        });
    }
    return vods;
}

function parseDetail(html, id) {
    let titleMatch = html.match(/<h1[^>]*>([\s\S]*?)<\/h1>/);
    let title = titleMatch ? titleMatch[1].replace(/<[^>]*>/g, '').trim() : '详情';
    let imgMatch = html.match(/class="lozad[^>]*data-src="([^"]+)"/) || html.match(/<img[^>]*src="([^"]+)"/);
    let pic = imgMatch ? (imgMatch[1].startsWith('http') ? imgMatch[1] : baseUrl + imgMatch[1]) : "";

    return {
        vod_name: title,
        vod_pic: pic,
        vod_content: title,
        vod_play_from: 'JavSB',
        vod_play_url: `立即播放$${baseUrl}${id}`
    };
}
