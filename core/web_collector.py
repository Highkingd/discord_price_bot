import aiohttp
import asyncio
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
import re
from typing import Dict, List, Optional
import logging
from urllib.parse import urljoin

class WebDataCollector:
    def __init__(self):
        self.data_file = "data/web_data.json"
        self.data = self.load_data()
        self.sources = {
            'war_thunder': {
                'wiki': 'https://wiki.warthunder.com',
                'news': 'https://warthunder.com/en/news/',
                'devblog': 'https://warthunder.com/en/devblog/',
                'changelog': 'https://warthunder.com/en/game/changelog/'
            },
            'game_market': {
                'gaijin_market': 'https://trade.gaijin.net/',
                'marketplace': 'https://store.gaijin.net/catalog.php'
            }
        }
        
        # Headers để tránh bị block
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Các pattern để trích xuất thông tin
        self.patterns = {
            'price': r'(\d+[.,]?\d*)\s*(GJN|USD|EUR|₽|VND|₫)',
            'vehicle_name': r'([A-Z][A-Za-z0-9-_]+(?:\s+[A-Za-z0-9-_]+)*)',
            'br_rating': r'BR\s*(\d+\.\d+|\d+)',
            'repair_cost': r'Repair cost:?\s*(\d+[.,]?\d*)',
            'modification': r'Modification cost:?\s*(\d+[.,]?\d*)'
        }
        
        # Khởi tạo logger
        self.setup_logger()

    def setup_logger(self):
        """Thiết lập logging"""
        self.logger = logging.getLogger('WebDataCollector')
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            handler = logging.FileHandler('data/web_collector.log', encoding='utf-8')
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def load_data(self) -> Dict:
        """Tải dữ liệu đã thu thập"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return self._init_data_structure()
        return self._init_data_structure()

    def _init_data_structure(self) -> Dict:
        """Khởi tạo cấu trúc dữ liệu"""
        return {
            'vehicles': {},  # Thông tin về các phương tiện
            'modifications': {},  # Thông tin về modifications
            'market_prices': {},  # Giá cả thị trường
            'news': [],  # Tin tức và updates
            'stats': {
                'last_update': None,
                'total_vehicles': 0,
                'total_modifications': 0,
                'total_market_items': 0,
                'total_news': 0
            }
        }

    def save_data(self):
        """Lưu dữ liệu đã thu thập"""
        try:
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
                
            self.logger.info(f"Saved data successfully to {self.data_file}")
        except Exception as e:
            self.logger.error(f"Error saving data: {str(e)}")
            # Backup data
            try:
                backup_file = f"{self.data_file}.backup"
                with open(backup_file, 'w', encoding='utf-8') as f:
                    json.dump(self.data, f, ensure_ascii=False, indent=2)
                self.logger.info(f"Created backup file at {backup_file}")
            except Exception as e:
                self.logger.error(f"Error creating backup: {str(e)}")

    async def collect_vehicle_data(self, session: aiohttp.ClientSession, url: str):
        """Thu thập thông tin về phương tiện từ Wiki"""
        try:
            async with session.get(url, headers=self.headers) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Trích xuất thông tin
                    vehicle_data = {
                        'name': None,
                        'br_rating': None,
                        'repair_cost': None,
                        'modifications': [],
                        'last_update': datetime.now().isoformat()
                    }
                    
                    # Tìm tên phương tiện
                    title = soup.find('h1', class_='wiki-title')
                    if title:
                        vehicle_data['name'] = title.text.strip()
                    
                    # Tìm BR rating
                    br_text = soup.find(text=re.compile(r'BR\s*\d'))
                    if br_text:
                        br_match = re.search(self.patterns['br_rating'], br_text)
                        if br_match:
                            vehicle_data['br_rating'] = float(br_match.group(1))
                    
                    # Tìm repair cost
                    repair_text = soup.find(text=re.compile(r'Repair cost'))
                    if repair_text:
                        repair_match = re.search(self.patterns['repair_cost'], repair_text)
                        if repair_match:
                            vehicle_data['repair_cost'] = int(repair_match.group(1).replace(',', ''))
                    
                    # Tìm modifications
                    mod_elements = soup.find_all(class_='modification-card')
                    for mod in mod_elements:
                        mod_data = {
                            'name': mod.find(class_='mod-name').text.strip() if mod.find(class_='mod-name') else None,
                            'cost': None
                        }
                        cost_text = mod.find(text=re.compile(r'cost:?\s*\d'))
                        if cost_text:
                            cost_match = re.search(self.patterns['modification'], cost_text)
                            if cost_match:
                                mod_data['cost'] = int(cost_match.group(1).replace(',', ''))
                        vehicle_data['modifications'].append(mod_data)
                    
                    # Lưu dữ liệu
                    if vehicle_data['name']:
                        self.data['vehicles'][vehicle_data['name']] = vehicle_data
                        self.data['stats']['total_vehicles'] = len(self.data['vehicles'])
                        self.logger.info(f"Collected data for vehicle: {vehicle_data['name']}")
                    
        except Exception as e:
            self.logger.error(f"Error collecting vehicle data from {url}: {str(e)}")

    async def collect_market_data(self, session: aiohttp.ClientSession):
        """Thu thập thông tin giá cả từ market"""
        try:
            market_url = self.sources['game_market']['gaijin_market']
            async with session.get(market_url, headers=self.headers) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Tìm các item trên market
                    market_items = soup.find_all(class_='market-item')
                    for item in market_items:
                        item_data = {
                            'name': item.find(class_='item-name').text.strip() if item.find(class_='item-name') else None,
                            'price': None,
                            'currency': None,
                            'last_update': datetime.now().isoformat()
                        }
                        
                        # Tìm giá
                        price_text = item.find(text=re.compile(self.patterns['price']))
                        if price_text:
                            price_match = re.search(self.patterns['price'], price_text)
                            if price_match:
                                item_data['price'] = float(price_match.group(1))
                                item_data['currency'] = price_match.group(2)
                        
                        if item_data['name']:
                            self.data['market_prices'][item_data['name']] = item_data
                            
                    self.data['stats']['total_market_items'] = len(self.data['market_prices'])
                    self.logger.info(f"Collected market data: {len(market_items)} items")
                    
        except Exception as e:
            self.logger.error(f"Error collecting market data: {str(e)}")

    async def collect_news(self, session: aiohttp.ClientSession):
        """Thu thập tin tức và updates"""
        try:
            news_url = self.sources['war_thunder']['news']
            async with session.get(news_url, headers=self.headers) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Tìm các bài tin tức
                    news_items = soup.find_all(class_='news-item')
                    for item in news_items[:10]:  # Chỉ lấy 10 tin mới nhất
                        news_data = {
                            'title': item.find(class_='news-title').text.strip() if item.find(class_='news-title') else None,
                            'date': item.find(class_='news-date').text.strip() if item.find(class_='news-date') else None,
                            'url': urljoin(news_url, item.find('a')['href']) if item.find('a') else None,
                            'summary': item.find(class_='news-summary').text.strip() if item.find(class_='news-summary') else None
                        }
                        
                        if news_data['title'] and news_data not in self.data['news']:
                            self.data['news'].insert(0, news_data)
                    
                    # Giới hạn số lượng tin tức lưu trữ
                    self.data['news'] = self.data['news'][:50]
                    self.data['stats']['total_news'] = len(self.data['news'])
                    self.logger.info(f"Collected {len(news_items)} news items")
                    
        except Exception as e:
            self.logger.error(f"Error collecting news: {str(e)}")

    async def collect_all_data(self):
        """Thu thập tất cả dữ liệu"""
        try:
            async with aiohttp.ClientSession() as session:
                tasks = [
                    self.collect_vehicle_data(session, f"{self.sources['war_thunder']['wiki']}/vehicles"),
                    self.collect_market_data(session),
                    self.collect_news(session)
                ]
                await asyncio.gather(*tasks)
                
            self.data['stats']['last_update'] = datetime.now().isoformat()
            self.save_data()
            self.logger.info("Completed data collection")
            
        except Exception as e:
            self.logger.error(f"Error in collect_all_data: {str(e)}")

    def get_vehicle_info(self, name: str) -> Optional[Dict]:
        """Lấy thông tin về phương tiện"""
        return self.data['vehicles'].get(name)

    def get_market_price(self, item_name: str) -> Optional[Dict]:
        """Lấy giá thị trường của item"""
        return self.data['market_prices'].get(item_name)

    def get_latest_news(self, limit: int = 5) -> List[Dict]:
        """Lấy tin tức mới nhất"""
        return self.data['news'][:limit]

    def get_stats(self) -> Dict:
        """Lấy thống kê về dữ liệu đã thu thập"""
        return self.data['stats']

    def search_items(self, query: str) -> List[Dict]:
        """Tìm kiếm items theo từ khóa"""
        query = query.lower()
        results = []
        
        # Tìm trong vehicles
        for name, data in self.data['vehicles'].items():
            if query in name.lower():
                results.append({
                    'type': 'vehicle',
                    'name': name,
                    'data': data
                })
                
        # Tìm trong market
        for name, data in self.data['market_prices'].items():
            if query in name.lower():
                results.append({
                    'type': 'market_item',
                    'name': name,
                    'data': data
                })
                
        return results

    async def schedule_collection(self, interval_hours: int = 24):
        """Lên lịch thu thập dữ liệu định kỳ"""
        while True:
            await self.collect_all_data()
            await asyncio.sleep(interval_hours * 3600)  # Chuyển giờ sang giây
