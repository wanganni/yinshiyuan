import json
import re
import sys
import requests
from urllib.parse import urljoin

sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    
    def init(self, extend=""):
        self.host = "https://eey.myacetwve.buzz"
        self.home_url = "https://eey.myacetwve.buzz/chu/"
        self.header = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 15; RMX3770 Build/AP3A.240617.008) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/130.0.6723.58 Mobile Safari/537.36'
        }
        self.class_names = '国产视频&国产主播&91大神&热门事件&传媒自拍&日本有码&日本无码&日韩主播&动漫肉番&女同性恋&中文字幕&强奸乱伦&熟女人妻&制服诱惑&AV解说&女星换脸&欧美精品&日韩无码&强奸乱伦&欧美精品&人妻系列&中文字幕&动漫精品&日韩精品&伦理影片&制服诱惑&自拍偷拍&3P合辑&AV明星&巨乳系列&颜射系列&口交视频&自慰系列&国产精品&SM重味&教师学生&大秀视频&国产精品&华语AV&黑料吃瓜&欧美&禁漫&学生&乱伦&探花&日本有码&日本无码&主播网红&日本素人&精品推荐&国产色情&主播直播&亚洲无码&中文字幕&巨乳美乳&人妻熟女&欧美精品&强奸乱伦&萝莉少女&亚洲有码&伦理三级&成人动漫&自拍偷拍&制服丝袜&口交颜射&日本精品&Cosplay&素人自拍&台湾辣妹&国产情色&自拍偷拍&日本无码&日本有码&人妻熟女&中文字幕&欧美精品&卡通动漫&韩国主播&伦理三级&传媒原创&口爆颜射&岛国素人&岛国女优&萝莉少女&重口调教&美颜巨乳&岛国群交&制服诱惑&同性女优&日韩无码&国产精品&日韩精品&欧美精品&动漫精品&自拍偷拍&伦理影片&中文字幕&人妻系列&制服诱惑&强奸乱伦&AV明星&SM重味&巨乳系列&颜射系列&口交视频&自慰系列&教师学生&大秀视频&明星换脸&国产自拍&日本无码&日本有码&中文字幕&欧美精品&成人动漫&日本素人&高清名优&三级伦理&网红主播&映画传媒&人妻熟女&口爆颜射&萝莉少女&SM调教&美乳巨乳&短视频&制服诱惑&女同性爱&AI换脸&麻豆传媒&精东影业&蜜桃传媒&果冻传媒&星空无限传媒&SA国际传媒&性视界传媒&国产-自拍&国产-偷拍&国产-探花&国产-主播&天美传媒&欧美-高清无码&日本-中文字幕&日本-无码流出&日本-高清有码&皇家华人&欧美-中文字幕&刘玥&玩偶姐姐&国产自拍&主播诱惑&探花约炮&偷拍偷窥&网曝吃瓜&抖阴短片&传媒剧情&日韩主播&日韩无码&中文字幕&AV解说&换脸明星&强奸乱伦&女优明星&欧美激情&重口激情&三级伦理&剧情动漫&SM调教&女同性恋&国产视频&中文字幕&国产传媒&日本有码&日本无码&欧美无码&强奸乱伦&制服诱惑&国产主播&激情动漫&明星换脸&抖阴视频&女优明星&网曝黑料&伦理三级&AV解说&SM调教&萝莉少女&极品媚黑&女同性恋&亚洲无码&亚洲有码&欧美情色&中文字幕&动漫卡通&美女主播&人妻熟女&强奸乱伦&三级伦理&国产自拍&国产传媒&女优合集&国产乱伦&网曝门事件&绿帽淫妻&国产乱伦&AV解说&国产探花&亚洲情色&国产主播&国产自拍&无码专区&欧美性爱&熟女人妻&强奸乱伦&巨乳美乳&中文字幕&制服诱惑&女同性恋&卡通动画&视频伦理&少女萝莉&重口色情&人兽性交&福利姬&制服丝袜&群交淫乱&无码专区&偷拍自拍&卡通动漫&中文字幕&欧美性爱&巨乳美乳&国产裸聊&国产自拍&国产盗摄&伦理三级&女同性恋&少女萝莉&人妖系列&虚拟VR&国产区&AV区&欧美区&动漫区&网红主播&国产传媒&探花系列&人妻熟女&日本无码&美乳巨乳&强制侵犯&制服诱惑&绝色佳人&风俗泡泡浴&家庭乱伦&AV解说&三级电影&少女萝莉&SM调教&绝顶潮吹&麻豆视频&91制片厂&天美传媒&蜜桃传媒&皇家华人&星空传媒&精东影业&大象传媒&91茄子&性视界传媒&兔子先生&杏吧原创&玩偶姐姐&香蕉传媒&SA国际传媒&EDmosaic&PsychoPorn&糖心Vlog&葫芦影业&果冻传媒'
        self.class_urls = '2&3&4&5&6&7&8&9&10&11&12&13&14&15&16&17&444&19&20&21&22&23&24&25&26&27&28&29&30&31&32&33&34&35&36&37&38&49&50&51&52&53&54&55&56&57&58&59&60&62&63&64&65&66&67&68&69&70&71&72&73&74&75&76&77&78&79&80&81&105&106&107&108&109&110&111&112&113&114&115&116&117&118&119&120&121&122&123&124&133&134&135&136&137&138&139&140&141&142&143&144&145&146&147&148&149&150&151&152&155&156&157&158&159&160&161&162&163&164&165&166&167&168&169&170&171&172&173&174&187&188&189&190&191&192&193&194&195&196&197&198&199&201&202&203&204&205&207&208&274&275&276&277&278&279&280&281&282&283&284&285&286&287&288&289&290&291&292&293&297&298&299&300&301&302&303&304&305&306&307&308&309&310&311&312&313&314&315&316&322&323&324&325&326&327&328&329&330&331&339&340&341&342&343&344&345&346&348&349&350&351&352&353&354&355&356&357&358&359&360&361&362&363&364&366&367&368&369&370&371&372&373&374&375&376&377&378&379&380&381&383&384&385&386&387&388&389&390&391&392&393&394&395&396&397&398&399&400&401&402&424&425&426&427&428&429&430&431&432&433&434&435&436&437&438&439&440&441&442&443&'

    def getName(self):
        return "小chu女"

    def isVideoFormat(self, url):
        return re.search(r'\.(m3u8|mp4|flv|avi|mkv|wmv|mpg|mpeg|mov|ts|3gp|rm|rmvb|asf|m4a|mp3|wma)', url) is not None

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    def homeContent(self, filter):
        result = {}
        classes = []
        
        names = self.class_names.split('&')
        urls = self.class_urls.split('&')
        
        for n, u in zip(names, urls):
            classes.append({
                'type_name': n,
                'type_id': u
            })
            
        result['class'] = classes
        result['filters'] = {}
        return result

    def homeVideoContent(self):
        try:
            r = self.fetch(self.home_url, headers=self.header)
            root = self.soup(r.text, 'html.parser')
            vods = self._parse_list_items(root)
            return {'list': vods}
        except Exception as e:
            return {'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        url = f"{self.host}/vodtype/{tid}-{pg}/"
        
        try:
            r = self.fetch(url, headers=self.header)
            root = self.soup(r.text, 'html.parser')
            vods = self._parse_list_items(root)
            
            return {
                'list': vods,
                'page': int(pg),
                'pagecount': 9999,
                'limit': 30,
                'total': 999999
            }
        except Exception as e:
            return {'list': []}

    def detailContent(self, ids):
        url = ids[0]
        try:
            r = self.fetch(url, headers=self.header)
            html = r.text
            root = self.soup(html, 'html.parser')
            
            vod = {}
            vod['vod_id'] = url
            vod['vod_name'] = root.select_one('h1').get_text(strip=True) if root.select_one('h1') else ''
            
            type_node = root.select_one('.f-24')
            vod['type_name'] = type_node.get_text(strip=True) if type_node else ''
            
            pic_node = root.select_one('.detail-image-wrapper img')
            vod['vod_pic'] = self._get_abs_url(pic_node.get('data-src'), url) if pic_node else ''
            
            vod['vod_content'] = '瑟瑟才是源动力:' + vod['vod_name'].replace('剧情介绍：', '')
            
            tabs = [t.get_text(strip=True) for t in root.select('span.tx-flex-sh')]
            vod['vod_play_from'] = '$$$'.join(tabs)
            
            play_lists = []
            
            containers = root.select('span.tx-flex-sh')
            
            for container in containers:
                links = container.select('a')
                if not links:
                    continue
                    
                episode_list = []
                for a in links:
                    name = a.get_text(strip=True)
                    href = a.get('href')
                    episode_list.append(f"{name}${self._get_abs_url(href, url)}")
                
                if episode_list:
                    play_lists.append('#'.join(episode_list))

            vod['vod_play_url'] = '$$$'.join(play_lists)
            return {'list': [vod]}
            
        except Exception as e:
            return {'list': []}

    def searchContent(self, key, quick, pg="1"):
        search_url = f"{self.host}/vodsearch/{key}----------{pg}---/"
        
        try:
            r = self.fetch(search_url, headers=self.header)
            root = self.soup(r.text, 'html.parser')
            vods = self._parse_list_items(root)
            return {
                'list': vods,
                'page': int(pg)
            }
        except Exception as e:
            return {'list': []}

    def playerContent(self, flag, id, vipFlags):
        url = id
        
        if re.search(r'\.(m3u8|mp4)', url):
            return {
                'parse': 0,
                'url': url,
                'header': {
                    'User-Agent': self.header['User-Agent'],
                    'Referer': self.home_url
                }
            }
        else:
            try:
                r = self.fetch(url, headers=self.header)
                html = r.text
                
                if 'player_data=' in html:
                    json_str = html.split('player_data=')[1].split('<')[0]
                    data = json.loads(json_str)
                    play_url = data.get('url')
                    
                    return {
                        'parse': 0,
                        'url': play_url,
                        'header': {
                            'User-Agent': self.header['User-Agent'],
                            'Referer': self.home_url
                        }
                    }
                
                return {'parse': 1, 'url': url, 'header': self.header}
                
            except Exception as e:
                return {'parse': 1, 'url': url, 'header': self.header}

    def _parse_list_items(self, root):
        vods = []
        items = root.select('.item-box')
        
        for item in items:
            link_el = item.select_one('a[href*="/voddetail/"]')
            if not link_el:
                continue
                
            title = link_el.get('title', '') or link_el.get_text(strip=True)
            
            img_el = item.select_one('img')
            pic = img_el.get('data-src') if img_el else ''
            if pic and not pic.startswith('http'):
                pic = self.host + pic
                
            smalls = item.select('small')
            desc = smalls[1].get_text(strip=True) if len(smalls) > 1 else ''
            
            vid = link_el.get('href')
            vid = self._get_abs_url(vid, self.host)
            
            vods.append({
                'vod_name': title,
                'vod_pic': pic,
                'vod_remarks': desc,
                'vod_id': vid
            })
        return vods
    
    def _get_abs_url(self, url, base):
        if not url: return base
        if url.startswith('http'): return url
        return urljoin(base, url)

    def soup(self, html, parser):
        from bs4 import BeautifulSoup
        return BeautifulSoup(html, parser)

    def localProxy(self, param):
        pass
