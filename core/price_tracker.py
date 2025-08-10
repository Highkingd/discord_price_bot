import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import asyncio
import discord
from discord.ext import commands

class PriceTracker:
    def __init__(self, bot):
        self.bot = bot
        self.data_file = "data/price_tracking.json"
        self.data = self.load_data()
        self.alert_channels = {}  # channel_id: guild_id
        
    def load_data(self) -> Dict:
        """Tải dữ liệu tracking"""
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
            'tracked_items': {},  # item_name: {price, last_update, watchers: [user_ids]}
            'price_history': {},  # item_name: [{price, timestamp}]
            'user_alerts': {},    # user_id: {min_price, max_price, items: [item_names]}
            'alert_channels': {}  # guild_id: channel_id
        }
        
    def save_data(self):
        """Lưu dữ liệu tracking"""
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
            
    def add_tracking(self, item_name: str, user_id: str, min_price: float = None, max_price: float = None):
        """Thêm item vào danh sách theo dõi"""
        if item_name not in self.data['tracked_items']:
            self.data['tracked_items'][item_name] = {
                'price': None,
                'last_update': None,
                'watchers': []
            }
            self.data['price_history'][item_name] = []
            
        if user_id not in self.data['tracked_items'][item_name]['watchers']:
            self.data['tracked_items'][item_name]['watchers'].append(user_id)
            
        # Thêm alert settings cho user
        if user_id not in self.data['user_alerts']:
            self.data['user_alerts'][user_id] = {
                'min_price': {},
                'max_price': {},
                'items': []
            }
            
        if item_name not in self.data['user_alerts'][user_id]['items']:
            self.data['user_alerts'][user_id]['items'].append(item_name)
            
        if min_price is not None:
            self.data['user_alerts'][user_id]['min_price'][item_name] = min_price
        if max_price is not None:
            self.data['user_alerts'][user_id]['max_price'][item_name] = max_price
            
        self.save_data()
        
    def remove_tracking(self, item_name: str, user_id: str):
        """Xóa item khỏi danh sách theo dõi của user"""
        if item_name in self.data['tracked_items']:
            if user_id in self.data['tracked_items'][item_name]['watchers']:
                self.data['tracked_items'][item_name]['watchers'].remove(user_id)
                
            # Xóa alerts
            if user_id in self.data['user_alerts']:
                if item_name in self.data['user_alerts'][user_id]['items']:
                    self.data['user_alerts'][user_id]['items'].remove(item_name)
                if item_name in self.data['user_alerts'][user_id]['min_price']:
                    del self.data['user_alerts'][user_id]['min_price'][item_name]
                if item_name in self.data['user_alerts'][user_id]['max_price']:
                    del self.data['user_alerts'][user_id]['max_price'][item_name]
                    
            # Xóa item nếu không còn ai theo dõi
            if not self.data['tracked_items'][item_name]['watchers']:
                del self.data['tracked_items'][item_name]
                del self.data['price_history'][item_name]
                
        self.save_data()
        
    def update_price(self, item_name: str, new_price: float):
        """Cập nhật giá và kiểm tra alerts"""
        if item_name not in self.data['tracked_items']:
            return
            
        old_price = self.data['tracked_items'][item_name].get('price')
        self.data['tracked_items'][item_name]['price'] = new_price
        self.data['tracked_items'][item_name]['last_update'] = datetime.now().isoformat()
        
        # Thêm vào lịch sử giá
        self.data['price_history'][item_name].append({
            'price': new_price,
            'timestamp': datetime.now().isoformat()
        })
        
        # Giới hạn lịch sử giá
        if len(self.data['price_history'][item_name]) > 100:
            self.data['price_history'][item_name] = self.data['price_history'][item_name][-100:]
            
        # Kiểm tra alerts
        alerts = []
        for user_id in self.data['tracked_items'][item_name]['watchers']:
            if user_id in self.data['user_alerts']:
                user_alerts = self.data['user_alerts'][user_id]
                
                # Kiểm tra min price
                if (item_name in user_alerts['min_price'] and 
                    new_price <= user_alerts['min_price'][item_name] and
                    (old_price is None or old_price > user_alerts['min_price'][item_name])):
                    alerts.append({
                        'user_id': user_id,
                        'type': 'min_price',
                        'price': new_price,
                        'threshold': user_alerts['min_price'][item_name]
                    })
                    
                # Kiểm tra max price
                if (item_name in user_alerts['max_price'] and 
                    new_price >= user_alerts['max_price'][item_name] and
                    (old_price is None or old_price < user_alerts['max_price'][item_name])):
                    alerts.append({
                        'user_id': user_id,
                        'type': 'max_price',
                        'price': new_price,
                        'threshold': user_alerts['max_price'][item_name]
                    })
                    
        self.save_data()
        return alerts
        
    def get_price_history(self, item_name: str, limit: int = 10) -> List[Dict]:
        """Lấy lịch sử giá của item"""
        if item_name in self.data['price_history']:
            return self.data['price_history'][item_name][-limit:]
        return []
        
    def get_tracked_items(self, user_id: str = None) -> List[str]:
        """Lấy danh sách items đang theo dõi"""
        if user_id:
            if user_id in self.data['user_alerts']:
                return self.data['user_alerts'][user_id]['items']
            return []
        return list(self.data['tracked_items'].keys())
        
    def set_alert_channel(self, guild_id: str, channel_id: str):
        """Thiết lập kênh nhận thông báo cho server"""
        self.data['alert_channels'][guild_id] = channel_id
        self.save_data()
        
    def get_alert_channel(self, guild_id: str) -> Optional[str]:
        """Lấy ID kênh nhận thông báo của server"""
        return self.data['alert_channels'].get(guild_id)
        
    async def send_alert(self, guild_id: str, item_name: str, alert_data: Dict):
        """Gửi thông báo về giá"""
        channel_id = self.get_alert_channel(guild_id)
        if not channel_id:
            return
            
        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            return
            
        user = self.bot.get_user(int(alert_data['user_id']))
        if not user:
            return
            
        alert_type = "giảm xuống dưới" if alert_data['type'] == 'min_price' else "tăng lên trên"
        
        embed = discord.Embed(
            title=f"⚠️ Thông báo giá: {item_name}",
            description=f"{user.mention}, giá đã {alert_type} ngưỡng bạn đặt!",
            color=0xe74c3c
        )
        embed.add_field(
            name="Giá hiện tại",
            value=f"{alert_data['price']:,.2f}",
            inline=True
        )
        embed.add_field(
            name="Ngưỡng cài đặt",
            value=f"{alert_data['threshold']:,.2f}",
            inline=True
        )
        
        await channel.send(embed=embed)
