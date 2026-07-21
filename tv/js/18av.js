var rule = {
    title:'18av',
    host:'https://18av.mm-cg.com',
    url:'/zh/fyclass/all/fypage.html',
    searchUrl: '/zh/fc_search/all/**/fypage.html',
    headers:{
'User-Agent': 'Mozilla/5.0 (Linux; Android 11; M2007J3SC Build/RKQ1.200826.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/77.0.3865.120 MQQBrowser/6.2 TBS/045713 Mobile Safari/537.36',
            'Referer': 'https://18av.mm-cg.com',
    },
    timeout:5000,
    class_name:'中文字幕&无码&动漫&自拍',//静态分类名称拼接
    class_url:'chinese_list&uncensored_list&animation_list&dt_list',//静态分类标识拼接
   //class_parse:'ul.animenu__nav&&li;a&&Text;a&&href',
    limit:5,
    play_parse:true,
    lazy:'',
    一级:'.posts&&.post;h3&&Text;img&&src;.meta&&Text;a&&href',
    //数组;标题;图片;副标题;链接
    二级:'*',
    搜索: '.posts&&.post;h3&&Text;img&&src;.meta&&Text;a&&href',
	
}

