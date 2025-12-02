import requests
import re
import time
import json
import base64
from urllib.parse import urljoin, unquote
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MobileTVBoxSpider:
    def __init__(self, base_url=None):
        self.base_url = base_url or "https://she.llydy27.xyz/rk.php"
        self.session = requests.Session()
        # 手机端User-Agent
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.162 Mobile Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        # TVBox解析jar引用
        self.jar_sniffers = [
            "https://raw.githubusercontent.com/qist/tvbox/master/jar/decoder.jar",
            "https://raw.githubusercontent.com/liu673cn/box/main/m.json",
            "https://fongmi.cachefly.net/0.0.8/jar/decoder.jar"
        ]
        
    def get_page_content(self, url, max_retries=3):
        """获取页面内容"""
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=15)
                response.raise_for_status()
                response.encoding = 'utf-8'
                return response.text
            except Exception as e:
                logger.warning(f"尝试 {attempt + 1} 失败: {url}, 错误: {str(e)}")
                time.sleep(3)
        return None
    
    def extract_categories(self, html_content):
        """提取所有分类链接和名称"""
        categories = []
        
        # 多种匹配模式适应不同页面结构
        patterns = [
            r'<li class=".*?"><a href="(/rk\.php/vod/type/id/\d+\.html)"[^>]*>([^<]+)</a></li>',
            r'<a href="(/vod/type/id/\d+\.html)"[^>]*>([^<]+)</a>',
            r'href="(/rk\.php/vod/type/id/\d+\.html)"[^>]*>([^<]+)</a>'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html_content)
            for url, name in matches:
                if name.strip() and '网站首页' not in name and '首页' not in name:
                    full_url = urljoin(self.base_url, url)
                    categories.append({
                        'name': name.strip(),
                        'url': full_url,
                        'id': re.search(r'/id/(\d+)', url).group(1) if re.search(r'/id/(\d+)', url) else ''
                    })
            if categories:
                break
        
        return categories
    
    def get_total_pages(self, html_content, max_pages=50):
        """获取总页数，限制最大页数"""
        patterns = [
            r'<a class="[^"]*" href="[^"]*/page/(\d+)\.html">(\d+)</a>',
            r'href="[^"]*/page/(\d+)\.html"[^>]*>尾页</a>',
            r'<span[^>]*>(\d+)</span>\s*页',
            r'共\s*(\d+)\s*页'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html_content)
            if matches:
                if pattern == patterns[0]:  # 第一种模式特殊处理
                    page_numbers = [int(num) for _, num in matches]
                    total_pages = max(page_numbers) if page_numbers else 1
                else:
                    total_pages = max([int(match) for match in matches if match.isdigit()])
                
                return min(total_pages, max_pages)
        
        return 1
    
    def extract_video_links(self, html_content):
        """从页面提取视频详情页链接和标题"""
        video_data = []
        
        # 多种视频列表匹配模式
        patterns = [
            r'<div class="item\s*">\s*<a href="(/rk\.php/vod/detail/id/\d+\.html)"[^>]*>.*?<strong class="title">([^<]+)</strong>',
            r'<a href="(/vod/detail/id/\d+\.html)"[^>]*>.*?<span[^>]*>([^<]+)</span>',
            r'<li[^>]*>\s*<a href="(/vod/detail/id/\d+\.html)"[^>]*>.*?<h3[^>]*>([^<]+)</h3>'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html_content, re.DOTALL)
            for relative_url, title in matches:
                full_url = urljoin(self.base_url, relative_url)
                video_data.append({
                    'url': full_url,
                    'title': self.clean_title(title.strip())
                })
            if video_data:
                break
        
        return video_data
    
    def clean_title(self, title):
        """清理标题，移除特殊字符"""
        # 移除HTML标签
        title = re.sub(r'<[^>]+>', '', title)
        # 移除特殊字符但保留中文、英文、数字和常见标点
        title = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s\-_（）()【】\[\]\.]', '', title)
        return title.strip()
    
    def sniff_video_url(self, detail_url, title):
        """嗅探视频播放地址，支持多种解析方式"""
        html_content = self.get_page_content(detail_url)
        if not html_content:
            return None
        
        # 方法1: 直接匹配m3u8链接
        m3u8_matches = re.findall(r'https?://[^\s"\'<>]*?\.m3u8(?:\?[^\s"\'<>]*)?', html_content, re.IGNORECASE)
        
        # 方法2: 匹配base64编码的m3u8链接
        base64_patterns = [
            r'var\s+[^=]*=\s*["\']([A-Za-z0-9+/=]+40==)["\']',
            r'url\s*:\s*["\']([A-Za-z0-9+/=]{20,})["\']',
            r'video_url\s*=\s*["\']([A-Za-z0-9+/=]{20,})["\']'
        ]
        
        base64_matches = []
        for pattern in base64_patterns:
            matches = re.findall(pattern, html_content)
            for match in matches:
                try:
                    decoded = base64.b64decode(match).decode('utf-8')
                    if '.m3u8' in decoded:
                        base64_matches.append(decoded)
                except:
                    continue
        
        # 方法3: 匹配JSON格式的视频信息
        json_patterns = [
            r'var\s+player_\w+\s*=\s*(\{.*?\});',
            r'window\.videoInfo\s*=\s*(\{.*?\});',
            r'var\s+video_data\s*=\s*(\{.*?\});'
        ]
        
        json_matches = []
        for pattern in json_patterns:
            matches = re.findall(pattern, html_content, re.DOTALL)
            for match in matches:
                try:
                    data = json.loads(match)
                    # 尝试从JSON中提取url、video_url、m3u8等字段
                    for key in ['url', 'video_url', 'm3u8', 'video', 'src']:
                        if key in data and isinstance(data[key], str) and '.m3u8' in data[key]:
                            json_matches.append(data[key])
                except:
                    continue
        
        # 方法4: 匹配iframe中的视频地址
        iframe_matches = re.findall(r'<iframe[^>]*src="([^"]*)"[^>]*>', html_content, re.IGNORECASE)
        for iframe_url in iframe_matches:
            full_iframe_url = urljoin(detail_url, iframe_url)
            iframe_content = self.get_page_content(full_iframe_url)
            if iframe_content:
                iframe_m3u8 = re.findall(r'https?://[^\s"\'<>]*?\.m3u8', iframe_content, re.IGNORECASE)
                m3u8_matches.extend(iframe_m3u8)
        
        # 合并所有匹配结果
        all_matches = m3u8_matches + base64_matches + json_matches
        
        # 去重和过滤
        unique_links = []
        seen_links = set()
        for link in all_matches:
            clean_link = unquote(link.split('"')[0].split("'")[0].split('\\')[0])
            if (clean_link and clean_link not in seen_links and 
                ('.m3u8' in clean_link.lower() or '.mp4' in clean_link.lower())):
                # 确保是完整的URL
                if clean_link.startswith('http'):
                    unique_links.append(clean_link)
                    seen_links.add(clean_link)
        
        # 返回第一个有效的链接
        return unique_links[0] if unique_links else None
    
    def generate_tvbox_format(self, title, video_url, category_name):
        """生成TVBox兼容的格式"""
        # TVBox标准格式
        return {
            "name": title,
            "url": video_url,
            "type": 0,  # 0表示直接播放
            "playerType": 1,  # 1表示系统播放器
            "headers": {
                "User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.162 Mobile Safari/537.36",
                "Referer": self.base_url
            }
        }
    
    def crawl_category_page(self, category_name, page_url, page_num, total_pages, output_file):
        """爬取单个分类页面的视频，并实时保存"""
        logger.info(f"爬取 {category_name} 第 {page_num}/{total_pages} 页")
        
        page_content = self.get_page_content(page_url)
        if not page_content:
            logger.warning(f"无法获取 {category_name} 第 {page_num} 页内容")
            return 0
        
        # 获取本页所有视频详情页链接和标题
        video_data = self.extract_video_links(page_content)
        logger.info(f"{category_name} 第 {page_num} 页: 找到 {len(video_data)} 个视频")
        
        # 如果是第一页，写入分类标题
        if page_num == 1:
            with open(output_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{category_name},#genre#\n")
        
        # 异步嗅探视频链接
        success_count = 0
        
        with ThreadPoolExecutor(max_workers=3) as executor:  # 减少线程数避免被封
            future_to_video = {
                executor.submit(self.sniff_video_url, video['url'], video['title']): video 
                for video in video_data
            }
            
            for future in as_completed(future_to_video):
                video = future_to_video[future]
                try:
                    video_url = future.result(timeout=30)  # 设置超时
                    if video_url:
                        # 实时写入文件
                        with open(output_file, 'a', encoding='utf-8') as f:
                            f.write(f"{video['title']},{video_url}\n")
                        success_count += 1
                        logger.info(f"成功提取: {video['title'][:20]}...")
                except Exception as e:
                    logger.error(f"提取视频链接失败: {str(e)}")
        
        logger.info(f"{category_name} 第 {page_num} 页: 成功提取 {success_count}/{len(video_data)} 个视频链接")
        return success_count
    
    def crawl_category(self, category, max_pages=50, output_file="mobile_tvbox_videos.txt"):
        """爬取单个分类的所有页面的视频链接，并实时保存"""
        category_name = category['name']
        base_url = category['url']
        
        logger.info(f"开始爬取分类: {category_name}")
        
        total_success = 0
        
        # 获取第一页内容来确定总页数
        first_page_content = self.get_page_content(base_url)
        if not first_page_content:
            logger.error(f"无法获取分类首页: {category_name}")
            return total_success
        
        total_pages = self.get_total_pages(first_page_content, max_pages)
        logger.info(f"分类 {category_name} 共有 {total_pages} 页")
        
        # 爬取所有页面
        for page in range(1, total_pages + 1):
            if page == 1:
                page_url = base_url
            else:
                # 多种分页URL格式支持
                if '/page/' in base_url:
                    page_url = re.sub(r'/page/\d+', f'/page/{page}', base_url)
                else:
                    page_url = base_url.replace('.html', f'/page/{page}.html')
            
            page_success = self.crawl_category_page(category_name, page_url, page, total_pages, output_file)
            total_success += page_success
            
            # 页面间延迟，避免请求过快
            if page < total_pages:
                time.sleep(2)
        
        logger.info(f"分类 {category_name} 完成: 总共找到 {total_success} 个视频链接")
        return total_success
    
    def crawl_all_categories(self, max_workers=2, max_pages=50, output_file="mobile_tvbox_videos.txt"):
        """爬取所有分类的所有页面"""
        # 初始化输出文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# TVBox手机版视频源\n")
            f.write("# 生成时间: " + time.strftime("%Y-%m-%d %H:%M:%S") + "\n")
            f.write("# 格式: 分类名,#genre#\n")
            f.write("#       视频标题,视频链接\n\n")
        
        # 获取首页内容
        homepage_content = self.get_page_content(self.base_url)
        if not homepage_content:
            logger.error("无法获取首页内容")
            return {}
        
        # 提取所有分类
        categories = self.extract_categories(homepage_content)
        logger.info(f"找到 {len(categories)} 个分类")
        
        # 使用线程池并行爬取（减少线程数避免被封）
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_category = {
                executor.submit(self.crawl_category, category, max_pages, output_file): category 
                for category in categories
            }
            
            # 处理完成的任务
            category_results = {}
            for future in as_completed(future_to_category):
                category = future_to_category[future]
                try:
                    success_count = future.result()
                    category_results[category['name']] = success_count
                    logger.info(f"分类 {category['name']} 爬取完成，共 {success_count} 个链接")
                except Exception as e:
                    logger.error(f"爬取分类 {category['name']} 时出错: {str(e)}")
                    category_results[category['name']] = 0
        
        return category_results

def main():
    """主函数"""
    BASE_URL = "https://she.llydy27.xyz/rk.php"
    OUTPUT_FILE = "mobile_tvbox_videos.txt"
    
    spider = MobileTVBoxSpider(BASE_URL)
    
    print("=" * 60)
    print("手机TVBox视频嗅探解析器")
    print("=" * 60)
    print("特点:")
    print("  ✓ 手机端优化")
    print("  ✓ 多解析方式支持")
    print("  ✓ TVBox格式兼容")
    print("  ✓ 实时保存数据")
    print("  ✓ 智能去重过滤")
    print("=" * 60)
    
    try:
        # 爬取所有分类的所有页面（最多50页）
        results = spider.crawl_all_categories(
            max_workers=2, 
            max_pages=50, 
            output_file=OUTPUT_FILE
        )
        
        # 统计总数
        total_links = sum(results.values())
        print(f"\n🎉 爬取完成！总共找到 {total_links} 个视频链接")
        
        # 显示各分类统计
        print("\n📊 各分类统计:")
        for category_name, count in results.items():
            print(f"  📁 {category_name}: {count} 个视频链接")
        
        print(f"\n💾 文件已保存: {OUTPUT_FILE}")
        print("\n📺 TVBox使用说明:")
        print("  1. 将文件导入TVBox应用")
        print("  2. 选择相应的分类即可播放")
        print("  3. 支持m3u8、mp4等格式")
        print("\n⚠️  注意: 请遵守相关法律法规，合理使用")
        
    except KeyboardInterrupt:
        print("\n⏹️  用户中断爬取")
        print(f"💾 已爬取的数据已保存到: {OUTPUT_FILE}")
    except Exception as e:
        logger.error(f"爬取过程中发生错误: {str(e)}")
        print(f"💾 部分数据已保存到: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()