#地址发布www.7000.me
import requests
import re
import time
import os
import json
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

class MD44Crawler:
    def __init__(self):
        self.base_url = "https://www.md44.cc"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://www.md44.cc/',
            'Connection': 'keep-alive',
        })
        self.failed_urls = []
        
    def get_all_categories(self):
        """获取全部分类"""
        print("🎯 正在获取全部分类...")
        categories = []
        
        try:
            response = self.session.get(self.base_url, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 方法1: 从导航菜单获取分类
                nav_links = soup.find_all('a', href=re.compile(r'/(list|category|type)/'))
                for link in nav_links:
                    href = link.get('href', '')
                    name = link.get_text().strip()
                    
                    if (name and len(name) > 1 and 
                        not any(x in name for x in ['首页', 'Home', '主页', '登录', '注册', '搜索', '更多'])):
                        full_url = urljoin(self.base_url, href)
                        categories.append({
                            'name': name,
                            'url': full_url
                        })
                        print(f"📂 找到分类: {name}")
                
                # 方法2: 从分类区块获取
                category_sections = soup.find_all(['div', 'ul', 'nav'], class_=re.compile(r'nav|menu|cate|type', re.I))
                for section in category_sections:
                    links = section.find_all('a', href=True)
                    for link in links:
                        href = link.get('href')
                        name = link.get_text().strip()
                        if (href and name and len(name) > 1 and 
                            re.search(r'/(list|category|type)/', href) and
                            not any(x in name for x in ['首页', 'Home'])):
                            full_url = urljoin(self.base_url, href)
                            # 去重
                            if not any(cat['url'] == full_url for cat in categories):
                                categories.append({
                                    'name': name,
                                    'url': full_url
                                })
                                print(f"📂 找到分类: {name}")
                
                # 如果没找到分类，使用默认分类
                if not categories:
                    default_cats = [
                        {'name': '最新', 'url': f'{self.base_url}/vod/show/latest.html'},
                        {'name': '热门', 'url': f'{self.base_url}/vod/show/hot.html'},
                        {'name': '推荐', 'url': f'{self.base_url}/vod/show/recommend.html'},
                    ]
                    categories.extend(default_cats)
                    print("📂 使用默认分类")
                
                print(f"✅ 共找到 {len(categories)} 个分类")
                return categories
                
        except Exception as e:
            print(f"❌ 获取分类失败: {e}")
        
        return []

    def get_total_pages(self, category_url):
        """获取分类总页数"""
        try:
            response = self.session.get(category_url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 查找分页信息
                page_links = soup.find_all('a', href=re.compile(r'page=|list_\d+'))
                page_numbers = []
                
                for link in page_links:
                    href = link.get('href', '')
                    text = link.get_text().strip()
                    
                    # 从URL中提取页码
                    page_match = re.search(r'page=(\d+)', href)
                    if page_match:
                        page_numbers.append(int(page_match.group(1)))
                    
                    # 从文本中提取页码
                    if text.isdigit():
                        page_numbers.append(int(text))
                
                # 查找最后一页
                last_page_links = soup.find_all('a', string=re.compile(r'末页|最后|尾页|last', re.I))
                for link in last_page_links:
                    href = link.get('href', '')
                    page_match = re.search(r'page=(\d+)', href)
                    if page_match:
                        return int(page_match.group(1))
                
                if page_numbers:
                    return max(page_numbers)
                    
        except Exception as e:
            print(f"   ❌ 获取总页数失败: {e}")
        
        return 50  # 默认返回50页

    def get_videos_from_page(self, category_url, page=1):
        """从页面获取视频列表"""
        videos = []
        try:
            # 构造分页URL
            if '?' in category_url:
                page_url = f"{category_url}&page={page}"
            else:
                page_url = f"{category_url}?page={page}" if '?' not in category_url else f"{category_url}&page={page}"
            
            print(f"   📄 获取第 {page} 页")
            response = self.session.get(page_url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 查找视频列表容器
                video_containers = soup.find_all(['div', 'li'], class_=re.compile(r'video|item|box|card', re.I))
                
                for container in video_containers:
                    # 查找视频链接
                    video_link = container.find('a', href=re.compile(r'/vod/detail/|/video/|/play/'))
                    if video_link:
                        href = video_link.get('href')
                        title = video_link.get('title') or video_link.get_text().strip()
                        
                        if href and title:
                            full_url = urljoin(self.base_url, href)
                            
                            # 查找图片
                            img = container.find('img')
                            img_url = img.get('src') if img else ""
                            if img_url and not img_url.startswith('http'):
                                img_url = urljoin(self.base_url, img_url)
                            
                            video_data = {
                                'title': title,
                                'url': full_url,
                                'image': img_url,
                                'page_url': page_url
                            }
                            
                            # 去重
                            if not any(v['url'] == full_url for v in videos):
                                videos.append(video_data)
                
                # 如果BeautifulSoup没找到，使用正则表达式
                if not videos:
                    html = response.text
                    video_patterns = [
                        r'<a[^>]*href="(/vod/detail/[^"]+)"[^>]*title="([^"]+)"',
                        r'<a[^>]*href="(/video/[^"]+)"[^>]*>.*?<img[^>]*src="([^"]*)"[^>]*>.*?<h3[^>]*>([^<]+)</h3>',
                        r'<a[^>]*href="(/play/[^"]+)"[^>]*>([^<]+)</a>',
                    ]
                    
                    for pattern in video_patterns:
                        matches = re.findall(pattern, html, re.DOTALL)
                        for match in matches:
                            if len(match) >= 2:
                                href = match[0]
                                title = match[1] if len(match) == 2 else match[2]
                                
                                if href and title:
                                    full_url = urljoin(self.base_url, href)
                                    videos.append({
                                        'title': title.strip(),
                                        'url': full_url,
                                        'image': '',
                                        'page_url': page_url
                                    })
                
                print(f"   ✅ 找到 {len(videos)} 个视频")
                return videos
                
        except Exception as e:
            print(f"   ❌ 获取第 {page} 页失败: {e}")
            self.failed_urls.append(f"页面 {page_url}: {e}")
        
        return videos

    def get_all_pages_videos(self, category_url):
        """获取分类的所有页面视频"""
        all_videos = []
        
        # 先获取总页数
        total_pages = self.get_total_pages(category_url)
        print(f"   📖 总页数: {total_pages}")
        
        for page in range(1, total_pages + 1):
            videos = self.get_videos_from_page(category_url, page)
            
            if not videos:
                print(f"   ⏹️  第 {page} 页没有视频，停止翻页")
                break
            
            # 检查是否有重复视频
            new_videos = [v for v in videos if not any(av['url'] == v['url'] for av in all_videos)]
            
            if not new_videos and page > 1:
                print(f"   ⏹️  第 {page} 页都是重复视频，停止翻页")
                break
            
            all_videos.extend(new_videos)
            
            # 如果连续3页视频数量很少，可能到达末尾
            if len(videos) < 5 and page > 3:
                print(f"   ⏹️  连续页面视频较少，可能到达末尾")
                break
            
            page += 1
            time.sleep(0.3)  # 页间延迟
        
        print(f"   📊 分类共获取 {len(all_videos)} 个视频")
        return all_videos

    def extract_play_url(self, html, video_url):
        """从视频页面提取播放地址"""
        play_url = None
        
        # 方法1: 搜索m3u8文件
        m3u8_patterns = [
            r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']',
            r'src\s*:\s*["\'](https?://[^"\']+\.m3u8[^"\']*)["\']',
            r'file\s*:\s*["\'](https?://[^"\']+\.m3u8[^"\']*)["\']',
            r'url\s*:\s*["\'](https?://[^"\']+\.m3u8[^"\']*)["\']',
            r'video_url\s*:\s*["\'](https?://[^"\']+\.m3u8[^"\']*)["\']',
        ]
        
        for pattern in m3u8_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for match in matches:
                if '.m3u8' in match.lower():
                    play_url = match
                    break
            if play_url:
                break
        
        # 方法2: 搜索iframe
        if not play_url:
            iframe_match = re.search(r'<iframe[^>]*src="([^"]+)"', html)
            if iframe_match:
                iframe_src = iframe_match.group(1)
                if iframe_src.startswith('//'):
                    iframe_src = 'https:' + iframe_src
                elif iframe_src.startswith('/'):
                    iframe_src = urljoin(self.base_url, iframe_src)
                play_url = iframe_src
        
        # 方法3: 搜索视频播放器
        if not play_url:
            video_tags = re.findall(r'<video[^>]*src="([^"]+)"', html)
            for video_src in video_tags:
                if video_src and len(video_src) > 10:
                    play_url = video_src
                    break
        
        # 方法4: 搜索JavaScript变量
        if not play_url:
            js_patterns = [
                r'var\s+url\s*=\s*["\']([^"\']+)["\']',
                r'var\s+video_url\s*=\s*["\']([^"\']+)["\']',
                r'var\s+src\s*=\s*["\']([^"\']+)["\']',
            ]
            for pattern in js_patterns:
                matches = re.findall(pattern, html)
                for match in matches:
                    if any(ext in match for ext in ['.m3u8', '.mp4', '.flv']):
                        play_url = match
                        break
                if play_url:
                    break
        
        # 处理相对URL
        if play_url:
            if play_url.startswith('//'):
                play_url = 'https:' + play_url
            elif play_url.startswith('/'):
                play_url = urljoin(self.base_url, play_url)
        
        return play_url

    def get_video_play_url(self, video_url):
        """获取视频播放地址"""
        try:
            print(f"    🎬 解析视频页面")
            response = self.session.get(video_url, timeout=15)
            
            if response.status_code == 200:
                play_url = self.extract_play_url(response.text, video_url)
                
                if play_url:
                    print(f"    ✅ 找到播放地址")
                    return play_url
                else:
                    # 尝试从播放器页面进一步解析
                    play_url = self.deep_parse_video(response.text, video_url)
                    if play_url:
                        print(f"    ✅ 深度解析找到播放地址")
                        return play_url
                    else:
                        print(f"    ❌ 未找到播放地址")
                        return None
            else:
                print(f"    ❌ 请求失败: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"    ❌ 解析视频失败: {e}")
            self.failed_urls.append(f"视频 {video_url}: {e}")
            return None

    def deep_parse_video(self, html, video_url):
        """深度解析视频页面"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # 查找播放器iframe
            iframe = soup.find('iframe', src=True)
            if iframe:
                iframe_src = iframe['src']
                if iframe_src.startswith('//'):
                    iframe_src = 'https:' + iframe_src
                elif iframe_src.startswith('/'):
                    iframe_src = urljoin(self.base_url, iframe_src)
                
                # 获取iframe内容
                iframe_response = self.session.get(iframe_src, timeout=10)
                if iframe_response.status_code == 200:
                    return self.extract_play_url(iframe_response.text, iframe_src)
            
            # 查找视频播放器脚本
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    script_text = script.string
                    m3u8_matches = re.findall(r'https?://[^\s"\']+\.m3u8[^\s"\']*', script_text)
                    for match in m3u8_matches:
                        if len(match) > 20:
                            return match
            
            return None
            
        except Exception as e:
            print(f"    ❌ 深度解析失败: {e}")
            return None

    def crawl_complete_site(self):
        """爬取整个网站的所有内容"""
        print("🚀 开始爬取 MD44.cc 全站内容")
        print("=" * 60)
        
        start_time = time.time()
        
        # 获取所有分类
        categories = self.get_all_categories()
        if not categories:
            print("❌ 无法获取分类，退出")
            return
        
        all_data = {}
        total_videos_count = 0
        
        # 遍历每个分类
        for i, category in enumerate(categories, 1):
            print(f"\n🎯 [{i}/{len(categories)}] 处理分类: {category['name']}")
            
            # 获取该分类的所有视频
            category_videos = self.get_all_pages_videos(category['url'])
            
            if not category_videos:
                print(f"⚠️  分类 {category['name']} 没有获取到视频")
                continue
            
            # 获取每个视频的播放地址
            successful_videos = []
            for j, video in enumerate(category_videos, 1):
                print(f"  📹 [{j}/{len(category_videos)}] {video['title'][:30]}...")
                
                play_url = self.get_video_play_url(video['url'])
                
                if play_url:
                    video_data = {
                        'title': video['title'],
                        'play_url': play_url
                    }
                    successful_videos.append(video_data)
                    print(f"  ✅ 成功")
                else:
                    print(f"  ❌ 失败")
                
                # 延迟避免被封
                time.sleep(0.5)
            
            if successful_videos:
                all_data[category['name']] = successful_videos
                total_videos_count += len(successful_videos)
                print(f"🎉 分类 {category['name']} 完成: {len(successful_videos)} 个视频")
            else:
                print(f"⚠️  分类 {category['name']} 没有成功获取播放地址")
        
        # 保存结果
        if all_data:
            self.save_results(all_data)
            end_time = time.time()
            
            print(f"\n🎊 爬取完成!")
            print(f"📊 统计信息:")
            print(f"   • 分类数量: {len(all_data)}")
            print(f"   • 视频总数: {total_videos_count}")
            print(f"   • 耗时: {end_time - start_time:.2f} 秒")
            print(f"   • 失败请求: {len(self.failed_urls)}")
            
            if self.failed_urls:
                print(f"   • 失败详情已保存到 failed_urls.txt")
                with open('failed_urls.txt', 'w', encoding='utf-8') as f:
                    for failed in self.failed_urls:
                        f.write(failed + '\n')
        else:
            print("\n❌ 爬取失败，没有获取到任何视频")

    def save_results(self, data):
        """保存结果到文件"""
        filename = "md44_complete_videos.txt"
        print(f"\n💾 正在保存结果到 {filename}...")
        
        with open(filename, 'w', encoding='utf-8') as f:
            for category_name, videos in data.items():
                # 写入分类标题
                f.write(f"{category_name},#genre#\n")
                print(f"📂 写入分类: {category_name} ({len(videos)}个视频)")
                
                # 写入该分类下的所有视频
                for video in videos:
                    # 清理标题中的特殊字符
                    title = re.sub(r'[,#\n\r\t]', ' ', video['title']).strip()
                    play_url = video['play_url']
                    
                    f.write(f"{title},{play_url}\n")
                
                # 分类间添加空行
                f.write("\n")
        
        file_size = os.path.getsize(filename)
        print(f"✅ 文件保存成功: {filename} ({file_size} 字节)")

def main():
    print("=" * 60)
    print("🎬 MD44.cc 全站视频爬虫")
    print("📱 专为Termux优化版本")
    print("=" * 60)
    print("⚠️  注意: 请确保在合法范围内使用本工具")
    print("⏳ 爬取全站内容需要较长时间，请耐心等待...")
    print("=" * 60)
    
    crawler = MD44Crawler()
    
    try:
        crawler.crawl_complete_site()
    except KeyboardInterrupt:
        print("\n🛑 用户中断爬取")
    except Exception as e:
        print(f"\n💥 爬取过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()