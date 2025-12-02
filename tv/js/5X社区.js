var rule = {
    title: '[密] 5X社区',
    地址发布页:'https://hwj1ens1kgh5qus.rtuiio990.88cyooi.top/',
    host: 'https://hwj1ens1kgh5qus.rtuiio990.88cyooi.top/',
    url: 'https://hwj1ens1kgh5qus.rtuiio990.88cyooi.top/videos/fyclass?page=fypage',
    homeUrl: 'https://hwj1ens1kgh5qus.rtuiio990.88cyooi.top/',
    
   searchUrl: 'https://hwj1ens1kgh5qus.rtuiio990.88cyooi.top/search/videos/**?page=fypage',
    detailUrl: '',

    searchable: 2,
    quickSearch: 1,
    filterable: 1,
    limit: 30,
    编码: 'utf-8',
    timeout: 5000,
    headers: {
      'User-Agent': 'Mozilla/5.0 (Linux; Android 15; RMX3770 Build/AP3A.240617.008) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/130.0.6723.58 Mobile Safari/537.36'
      
    
    },
    class_name: '5X社区会员原创作品&Paco&SM性虐&三级片&东京热&丝袜诱惑&中文字幕&公众场所及户外&加勒比&口爆颜射&器具自慰&国产AV&天然素人&女同&小格式综合&性party&成人动漫&成人直播&探花大神&无码破解&日本无码&日本有码&本道&李宗瑞全集&欧美&潮吹&肛交&韩国女主播系列&韩国综合&高清',
    class_url:  '5XSQ members original works&Pacopacomama&sm&Tertiary film&Tokyo Hot&Pantyhose temptation&Chinese subtitle&Public places and outdoors&Caribbeancom&Cumshot&Masturbation&homemade-selfie&10musume&Lesbian&Small format synthesis&Sex party&Adult Anime&chinese-anchor&tanhua-god&reducing-mosaic&Japan Uncensored&Japan Coded&pondo&The Complete Works of Li Zongrui&Europe and America&Squirting&Anal sex&Korean female anchor series&Korea General&HD',
    
//    图片来源: '@Referer=https://xg.acubsam.top/label/sort/@User-Agent=Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.91 Mobile Safari/537.36',
    
    //是否启用辅助嗅探: 1,0
    sniffer: 0,
    // 辅助嗅探规则
    isVideo: 'http((?!http).){26,}\\.(m3u8|mp4|flv|avi|mkv|wmv|mpg|mpeg|mov|ts|3gp|rm|rmvb|asf|m4a|mp3|wma)',
    play_parse: true,
    lazy: $js.toString(() => {
        input = {
            parse: 1,
            url: input,
            js: 'document.querySelector("#playleft iframe").contentWindow.document.querySelector("#start").click();'
        };
    }),
    
    
    
/*搜索: $js.toString(() => {
let nsurl = input, kwd = KEY;
let ktype;
if (/@/.test(KEY)) {
    [ktype, kwd] = KEY.split('@');
    if (/国产/.test(ktype)) { 
        nsurl = input.replace('1','14')
    } else if (/日本无码/.test(ktype)) { 
        nsurl = input.replace('1','27')
    } else if (/剧情大片/.test(ktype)) { 
        nsurl = input.replace('1','92')
    } else { 
        nsurl = input
    }
};
nsurl = `${nsurl}?wd=${kwd}&page=${MY_PAGE}`;
let klists = pdfa(fetch(nsurl), '.vod');
VODS = [];
klists.forEach((it) => {
    VODS.push({
        vod_name: pdfh(it, '.vod-txt&&a&&Text'),
        vod_pic: pdfh(it, '.lazy&&data-original'),
        vod_remarks: pdfh(it, 'a&&Text'),
        vod_id: pdfh(it, '.vod-txt&&a&&href')
    })
})
}),*/
    
    
    
    
    lazy: $js.toString(() => {
    
    let kurl = fetch(input).split('meta property="og:video:url" content="')[1].split('"')[0];

if (/\.(m3u8|mp4)/.test(kurl)) {
    input = { jx: 0, parse: 0, url: kurl, header: {'User-Agent': MOBILE_UA, 'Referer': getHome(kurl)} }
} else {
    input = { jx: 0, parse: 1, url: input }
}
}),
/*  let kcode = JSON.parse(fetch(input).split('aaaa=')[1].split('<')[0]);
let kurl = kcode.url;
if (/\.(m3u8|mp4)/.test(kurl)) {
    input = { jx: 0, parse: 0, url: kurl, header: {'User-Agent': MOBILE_UA, 'Referer': getHome(kurl)} }
} else {
    input = { jx: 0, parse: 1, url: input }
}
}),*/

    double: false,
    
    tab_rename: {
        '道长在线': '社区专线'
    },
    hikerListCol: "movie_2",
    hikerClassListCol: "movie_2",
    推荐: '*',
    
/*    一级: $js.toString(() => {
    let klist=pdfa(request(input),'.item:has(.img)');
     let k=[];
    klist.forEach(it=>{
     k.push({
    title: pdfh(it,'a&&title'),
     pic_url: !pdfh(it,'.lazyload&&data-src').startsWith('http') ? HOST + pdfh(it,'.lazyload&&data-src') : pdfh(it,'.lazyload&&data-src'),

    desc: '请您欣赏！',
     url: pdfh(it,'a&&href'),
    content: ''    
     })
    });
    setResult(k)
    }),*/
    
    

  一级: '.thumb;a&&title;source&&srcset;.duration&&a&&title;a&&href',
    二级: '*',
   搜索: '*',
}