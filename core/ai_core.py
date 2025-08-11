from typing import Dict, List, Optional, Tuple, Any
import random
import re
from datetime import datetime, timedelta
import json
import os
import logging
import time
import asyncio
import numpy as np
import matplotlib.pyplot as plt
import io
from collections import defaultdict
from functools import lru_cache

class CaveStoreAI:
    def __init__(self, bot):
        self.bot = bot
        
        # Tối thiểu hóa RAM usage
        self.context_history = {}
        self.max_context_history = 1
        self.max_users = 20
        self.data_file = "data/ai_data.json"
        
        # Core data với chức năng tích hợp
        self.core_data = {
            'orders': {},        # Đơn hàng đang xử lý
            'prices': {},        # Bảng giá cơ bản
            'permissions': {},    # Cache quyền hạn
            'status': {}         # Trạng thái đơn hàng
        }
        
        # Knowledge base tối giản
        self._max_items = 50
        self.knowledge = {
            'patterns': {
                'order': [
                    "đặt", "mua", "order", "book"
                ],
                'price': [
                    "giá", "báo giá", "tính", "cost"
                ],
                'status': [
                    "trạng thái", "tình trạng", "kiểm tra", "check"
                ],
                'help': [
                    "giúp", "hd", "help", "hướng dẫn"
                ]
            },
            'market_data': {},   # Giá thị trường realtime
            'interactions': []   # 100 tương tác gần nhất
        }
        
        # Sử dụng slots để giảm RAM
        self.__slots__ = ['bot', 'context_history', 'max_context_history',
                         'max_users', 'data_file', '_max_items', 
                         'knowledge', 'core_data']
        
        # Load essential data
        self._load_essential_data()
        
        # State tracking
        self._data = None
        self._last_data_load = 0
        self.data_reload_interval = 300
        
        # Response patterns
        self.style_patterns = {
            'formal': {
                'greetings': [
                    "Xin chào", "Kính chào", "Rất vui được gặp"
                ],
                'responses': [
                    "Theo phân tích của tôi", "Dựa trên dữ liệu", 
                    "Hệ thống ghi nhận"
                ],
                'conclusions': [
                    "Hy vọng thông tin hữu ích", "Cần thêm thông tin xin liên hệ",
                    "Xin vui lòng phản hồi nếu cần giải thích thêm"
                ]
            },
            'casual': {
                'greetings': [
                    "Hey", "Hi", "Chào bạn"
                ],
                'responses': [
                    "Mình thấy", "Theo mình thì", "Có vẻ như"
                ],
                'conclusions': [
                    "Bạn thấy sao?", "Mình nghĩ vậy", "Cho ý kiến nhé"
                ]
            },
            'empathetic': {
                'greetings': [
                    "Mình hiểu điều bạn quan tâm", 
                    "Mình sẽ giúp bạn",
                    "Đừng lo lắng nhé"
                ],
                'responses': [
                    "Mình nghĩ bạn sẽ thích", "Điều này có thể giúp bạn",
                    "Mình đề xuất"
                ],
                'conclusions': [
                    "Hy vọng bạn cảm thấy tốt hơn", 
                    "Mình luôn ở đây nếu cần",
                    "Đừng ngại chia sẻ thêm"
                ]
            }
        }
        
        # Initialize
        self.setup_logger()
        self.load_data()

    def setup_logger(self):
        """Thiết lập logging"""
        self.logger = logging.getLogger('CaveStoreAI')
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            handler = logging.FileHandler('data/ai.log', encoding='utf-8')
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    # Context Management
    def _load_essential_data(self):
        """Load dữ liệu cần thiết"""
        try:
            # Load giá cơ bản
            self.core_data['prices'] = {
                'sl': {'base': 100000, 'min': 50000},
                'rp': {'base': 200000, 'min': 100000},
                'premium': {'base': 500000, 'min': 300000}
            }
            
            # Load trạng thái đơn hàng
            if os.path.exists('orders.json'):
                with open('orders.json', 'r', encoding='utf-8') as f:
                    self.core_data['orders'] = json.load(f)
                    
        except Exception as e:
            print(f"Lỗi khi load dữ liệu: {e}")
            self.core_data['orders'] = {}

    def analyze_context(self, message: str, user_id: str, additional_data: Dict = None) -> Dict:
        """Phân tích context của tin nhắn"""
        # Phân tích cơ bản
        context = {
            'timestamp': time.time(),
            'user_id': user_id,
            'message': message,
            'style': self.analyze_style(message),
            'intent': self.detect_intent(message),
            'entities': self.extract_entities(message)
        }
        
        # Phân tích nâng cao cho đơn hàng
        if context['intent'] in ['order', 'price', 'status']:
            context['order_data'] = self._analyze_order_data(message)
            
        if additional_data:
            context.update(additional_data)
            
        # Update context history tối giản
        self.context_history[user_id] = [context]
            
        return context
        
    def _analyze_order_data(self, message: str) -> Dict:
        """Phân tích thông tin đơn hàng từ tin nhắn"""
        data = {
            'items': [],
            'quantity': 1,
            'urgent': False,
            'order_id': None
        }
        
        # Tìm items
        items = re.findall(r'(sl|rp|premium|vehicle|tank|plane)', message.lower())
        if items:
            data['items'] = items
            
        # Tìm số lượng
        qty = re.findall(r'(\d+)\s*(cái|individual|item|cai)', message.lower())
        if qty:
            data['quantity'] = int(qty[0][0])
            
        # Kiểm tra gấp
        if any(word in message.lower() for word in ['gấp', 'urgent', 'nhanh']):
            data['urgent'] = True
            
        # Tìm mã đơn
        order_id = re.findall(r'[A-Z0-9]{8}', message)
        if order_id:
            data['order_id'] = order_id[0]
            
        return data

    def analyze_style(self, message: str) -> str:
        """Phân tích phong cách"""
        message = message.lower()
        
        # Formal indicators
        formal_words = ['xin', 'vui lòng', 'cảm ơn', 'kính', 'thưa']
        casual_words = ['hey', 'hi', 'ê', 'ơi', 'nhé', 'nha']
        
        formal_count = sum(word in message for word in formal_words)
        casual_count = sum(word in message for word in casual_words)
        
        # Sentiment check
        negative_words = ['không', 'chán', 'buồn', 'khó', 'tệ']
        negative_count = sum(word in message for word in negative_words)
        
        if formal_count > casual_count:
            return 'formal'
        elif negative_count > 1:
            return 'empathetic'
        else:
            return 'casual'

    def detect_intent(self, message: str) -> str:
        """Phát hiện ý định của người dùng - phiên bản tối giản"""
        message = message.lower()
        
        # Chỉ giữ lại các intent chính
        core_intents = {
            'price': ['giá', 'báo giá', 'bao nhiêu', 'tính'],
            'order': ['đặt', 'mua', 'order', 'book'],
            'status': ['trạng thái', 'tình trạng', 'kiểm tra', 'check'],
            'help': ['help', 'giúp', 'hd', 'hướng dẫn']
        }
        
        # Kiểm tra từng intent
        for intent, patterns in core_intents.items():
            if any(pattern in message for pattern in patterns):
                return intent
                
        return 'general'

    def extract_entities(self, message: str) -> Dict:
        """Trích xuất thông tin quan trọng"""
        entities = {
            'items': [],
            'numbers': [],
            'currency': None,
            'time_expressions': []
        }
        
        # Extract items
        item_patterns = [
            r'(?i)(sl|rp|silver lions|research points)',
            r'(?i)(xe|vehicle|tank|plane)',
            r'(?i)(premium|event)'
        ]
        
        for pattern in item_patterns:
            matches = re.finditer(pattern, message, re.IGNORECASE)
            entities['items'].extend(match.group() for match in matches)
            
        # Extract numbers
        number_pattern = r'\d+(?:,\d{3})*(?:\.\d+)?'
        entities['numbers'] = [
            float(num.replace(',', ''))
            for num in re.findall(number_pattern, message)
        ]
        
        # Extract currency
        currency_pattern = r'(?i)(vnd|đồng|vnđ|\$|usd)'
        currency_match = re.search(currency_pattern, message)
        if currency_match:
            entities['currency'] = currency_match.group().upper()
            
        # Extract time expressions
        time_patterns = [
            r'(?i)(hôm nay|ngày mai|tuần sau|tháng sau)',
            r'(?i)(\d+\s*(?:ngày|tuần|tháng|năm))',
            r'(?i)(sáng|trưa|chiều|tối)'
        ]
        
        for pattern in time_patterns:
            matches = re.finditer(pattern, message, re.IGNORECASE)
            entities['time_expressions'].extend(match.group() for match in matches)
            
        return entities

    def analyze_sentiment(self, message: str) -> Dict:
        """Phân tích sentiment"""
        message = message.lower()
        
        # Sentiment dictionaries
        positive_words = [
            'tốt', 'hay', 'thích', 'được', 'ok', 'ổn',
            'cảm ơn', 'vui', 'giỏi', 'tuyệt'
        ]
        
        negative_words = [
            'không', 'chán', 'buồn', 'khó', 'tệ', 'kém',
            'sai', 'lỗi', 'chậm', 'đắt'
        ]
        
        # Calculate scores
        pos_score = sum(word in message for word in positive_words)
        neg_score = sum(word in message for word in negative_words)
        
        total = pos_score + neg_score
        if total == 0:
            return {'positive': 0, 'negative': 0, 'neutral': 1}
            
        return {
            'positive': pos_score / total,
            'negative': neg_score / total,
            'neutral': 1 - (pos_score + neg_score) / total
        }

    # Response Generation
    def generate_response(self, message: str, context: Dict) -> Tuple[str, float]:
        """Tạo câu trả lời thông minh dựa trên context"""
        intent = context.get('intent', 'general')
        style = context.get('style', 'casual')
        
        try:
            # Xử lý các chức năng chính
            if intent == 'order':
                response = self._handle_order_request(context)
            elif intent == 'price':
                response = self._handle_price_check(context)
            elif intent == 'status':
                response = self._handle_status_check(context)
            elif intent == 'help':
                response = self._handle_help_request(context)
            else:
                response = self._get_general_response(context)
                
            # Format response theo style
            formatted = self._format_with_style(response, style)
            confidence = self._calculate_confidence(context)
            
            return formatted, confidence
            
        except Exception as e:
            print(f"Lỗi khi tạo response: {e}")
            return "Xin lỗi, đã có lỗi xảy ra. Vui lòng thử lại sau.", 0.5
            
    def _handle_order_request(self, context: Dict) -> str:
        """Xử lý yêu cầu đặt hàng"""
        order_data = context.get('order_data', {})
        user_id = context['user_id']
        
        if not order_data.get('items'):
            return "Vui lòng cho biết bạn muốn đặt gì?"
            
        # Tạo đơn hàng mới
        order_id = self._generate_order_id()
        order = {
            'id': order_id,
            'user_id': user_id,
            'items': order_data['items'],
            'quantity': order_data['quantity'],
            'urgent': order_data['urgent'],
            'status': 'pending',
            'created_at': time.time()
        }
        
        # Lưu đơn hàng
        self.core_data['orders'][order_id] = order
        self._save_orders()
        
        return f"Đã tạo đơn hàng {order_id}. Tổng giá tạm tính: {self._calculate_price(order):,}đ"
        
    def _handle_price_check(self, context: Dict) -> str:
        """Xử lý yêu cầu check giá"""
        order_data = context.get('order_data', {})
        items = order_data.get('items', [])
        
        if not items:
            prices = [f"{item}: {data['base']:,}đ" 
                     for item, data in self.core_data['prices'].items()]
            return "Bảng giá hiện tại:\n" + "\n".join(prices)
            
        total = 0
        details = []
        for item in items:
            if item in self.core_data['prices']:
                price = self.core_data['prices'][item]['base']
                total += price
                details.append(f"{item}: {price:,}đ")
                
        return "Chi tiết giá:\n" + "\n".join(details) + f"\nTổng: {total:,}đ"
        
    def _handle_status_check(self, context: Dict) -> str:
        """Xử lý yêu cầu check trạng thái"""
        order_data = context.get('order_data', {})
        user_id = context['user_id']
        
        # Nếu có mã đơn cụ thể
        if order_data.get('order_id'):
            order_id = order_data['order_id']
            if order_id in self.core_data['orders']:
                order = self.core_data['orders'][order_id]
                return f"Đơn hàng {order_id}:\nTrạng thái: {order['status']}\nThời gian: {self._format_time(order['created_at'])}"
            return f"Không tìm thấy đơn hàng {order_id}"
            
        # Liệt kê đơn của user
        user_orders = [order for order in self.core_data['orders'].values()
                      if order['user_id'] == user_id]
                      
        if not user_orders:
            return "Bạn chưa có đơn hàng nào"
            
        recent = sorted(user_orders, key=lambda x: x['created_at'], reverse=True)[:3]
        return "Đơn hàng gần đây:\n" + "\n".join(
            f"{order['id']}: {order['status']} ({self._format_time(order['created_at'])})"
            for order in recent
        )
        
    def _generate_order_id(self) -> str:
        """Tạo mã đơn hàng mới"""
        import random, string
        while True:
            order_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            if order_id not in self.core_data['orders']:
                return order_id

    def _format_with_style(self, response: str, style: str, context: Dict) -> str:
        """Format response according to style"""
        patterns = self.style_patterns[style]
        
        # Add greeting if first message
        greeting = ""
        if not self.context_history.get(context['user_id'], []):
            greeting = random.choice(patterns['greetings']) + ", "
            
        # Add style-specific phrases
        transition = random.choice(patterns['responses'])
        
        # Add conclusion sometimes
        conclusion = ""
        if random.random() < 0.3:
            conclusion = f". {random.choice(patterns['conclusions'])}"
            
        return f"{greeting}{transition} {response}{conclusion}"

    def _calculate_confidence(self, message: str, response: str, context: Dict) -> float:
        """Calculate confidence score for response"""
        # Base confidence from intent matching
        if context['intent'] != 'general':
            base_confidence = 0.7
        else:
            base_confidence = 0.5
            
        # Adjust based on entities matched
        entities = context['entities']
        if entities['items'] or entities['numbers']:
            base_confidence += 0.1
            
        # Adjust based on context history
        user_history = self.context_history.get(context['user_id'], [])
        if user_history:
            base_confidence += 0.1
            
        return min(base_confidence, 1.0)

    # Market Analysis
    def _calculate_price(self, order: Dict) -> int:
        """Tính giá đơn hàng"""
        total = 0
        for item in order['items']:
            if item in self.core_data['prices']:
                price = self.core_data['prices'][item]['base']
                total += price * order['quantity']
                
        # Phụ phí cho đơn gấp
        if order['urgent']:
            total *= 1.2
            
        return int(total)
        
    def _format_time(self, timestamp: float) -> str:
        """Format thời gian"""
        from datetime import datetime
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%d/%m/%Y %H:%M")
        
    def _save_orders(self):
        """Lưu đơn hàng xuống file"""
        try:
            with open('orders.json', 'w', encoding='utf-8') as f:
                json.dump(self.core_data['orders'], f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Lỗi khi lưu orders: {e}")
            
    def analyze_market_trends(self, item: str) -> Dict:
        """Phân tích xu hướng đơn giản"""
        if item not in self.core_data['prices']:
            return None
            
        base_price = self.core_data['prices'][item]['base']
        min_price = self.core_data['prices'][item]['min']
        
        return {
            'current_price': base_price,
            'min_price': min_price,
            'trend': 'stable'
        }
        
        # Determine trend direction
        if slope > 0:
            direction = "tăng"
            strength = "mạnh" if slope > 0.1 else "nhẹ"
        else:
            direction = "giảm"
            strength = "mạnh" if slope < -0.1 else "nhẹ"
            
        return {
            'direction': direction,
            'strength': strength,
            'current_price': current_price,
            'average_price': avg_price,
            'volatility': volatility,
            'confidence': 1.0 - volatility
        }

    def predict_future_price(self, item: str, days: int = 7) -> Dict:
        """Dự đoán giá trong tương lai"""
        trends = self.analyze_market_trends(item)
        if not trends:
            return None
            
        current_price = trends['current_price']
        volatility = trends['volatility']
        
        # Simple prediction using trend direction
        if trends['direction'] == "tăng":
            multiplier = 1 + (0.1 * float(trends['strength'] == "mạnh"))
        else:
            multiplier = 1 - (0.1 * float(trends['strength'] == "mạnh"))
            
        predictions = []
        for i in range(days):
            predicted_price = current_price * (multiplier ** (i+1))
            margin = predicted_price * volatility
            
            predictions.append({
                'day': i + 1,
                'price': predicted_price,
                'lower_bound': predicted_price - margin,
                'upper_bound': predicted_price + margin
            })
            
        return predictions

    def generate_market_advice(self, item: str) -> str:
        """Tạo lời khuyên về giao dịch"""
        trends = self.analyze_market_trends(item)
        if not trends:
            return "Chưa đủ dữ liệu để đưa ra lời khuyên"
            
        advice = []
        
        # Price trend advice
        if trends['direction'] == "tăng":
            if trends['strength'] == "mạnh":
                advice.append("Giá đang tăng mạnh, nên cân nhắc mua nếu có kế hoạch dài hạn")
            else:
                advice.append("Giá tăng nhẹ, có thể theo dõi thêm")
        else:
            if trends['strength'] == "mạnh":
                advice.append("Giá đang giảm mạnh, nên chờ ổn định")
            else:
                advice.append("Giá giảm nhẹ, có thể tích lũy dần")
                
        # Volatility advice
        if trends['volatility'] > 0.2:
            advice.append("Thị trường đang biến động mạnh, cần theo dõi sát")
        else:
            advice.append("Thị trường ổn định, rủi ro thấp")
            
        return " - ".join(advice)

    # Data Management
    def save_data(self):
        """Lưu dữ liệu"""
        try:
            os.makedirs('data', exist_ok=True)
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'knowledge': self.knowledge,
                    'context_history': self.context_history
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Lỗi khi lưu dữ liệu: {str(e)}")

    def load_data(self):
        """Tải dữ liệu"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.knowledge = data.get('knowledge', self.knowledge)
                    self.context_history = data.get('context_history', {})
        except Exception as e:
            self.logger.error(f"Lỗi khi tải dữ liệu: {str(e)}")

    # Learning
    def learn(self, message: str, response: str, feedback: float, context: Dict):
        """Học từ tương tác"""
        if feedback > 0.7:  # Chỉ học từ phản hồi tích cực
            self.knowledge['interactions'].append({
                'message': message,
                'response': response,
                'feedback': feedback,
                'context': context,
                'timestamp': datetime.now().isoformat()
            })
            
            # Update patterns
            intent = context['intent']
            if intent not in self.knowledge['patterns']:
                self.knowledge['patterns'][intent] = []
            self.knowledge['patterns'][intent].append(response)
            
            # Limit stored interactions
            if len(self.knowledge['interactions']) > 1000:
                self.knowledge['interactions'] = self.knowledge['interactions'][-1000:]
                
            self.save_data()

    def cleanup(self):
        """Dọn dẹp RAM tích cực"""
        try:
            # Reset toàn bộ context quá 15 phút
            current_time = time.time()
            self.context_history = {
                user_id: [context] for user_id, contexts in self.context_history.items()
                for context in [contexts[-1]] 
                if current_time - contexts[-1]['timestamp'] < 900  # 15 phút
            }

            # Giới hạn knowledge base ở mức tối thiểu
            if len(self.knowledge['market_data']) > self._max_items:
                self.knowledge['market_data'] = dict(
                    sorted(self.knowledge['market_data'].items(),
                          key=lambda x: x[1].get('last_access', 0),
                          reverse=True)[:self._max_items]
                )

            if len(self.knowledge['interactions']) > 100:
                self.knowledge['interactions'] = self.knowledge['interactions'][-100:]

            # Xóa cache không cần thiết
            self.knowledge['user_data'] = None
            self.knowledge['trends'] = None
            
            # Tối ưu RAM tích cực
            import gc
            import sys
            
            # Force full garbage collection
            gc.collect(2)
            
            # Xóa cache của modules
            sys.modules.pop('numpy', None)
            sys.modules.pop('pandas', None)
            sys.modules.pop('matplotlib', None)
            
            # Giới hạn RAM process
            try:
                import resource
                # Giới hạn RAM ở 240MB để có buffer
                resource.setrlimit(resource.RLIMIT_AS, (240 * 1024 * 1024, -1))
            except:
                pass

            # Log memory usage
            import psutil
            process = psutil.Process()
            memory = process.memory_info().rss / 1024 / 1024
            print(f"RAM Usage: {memory:.1f}MB")

            # Nếu RAM quá cao, force cleanup mạnh hơn
            if memory > 200:
                self.knowledge['patterns'] = {}
                self.knowledge['market_data'] = {}
                self.context_history = {}
                gc.collect(2)

        except Exception as e:
            print(f"Lỗi khi cleanup RAM: {str(e)}")
            # Trong trường hợp lỗi, reset mọi thứ để giảm RAM
            self.knowledge = {
                'patterns': {},
                'market_data': {},
                'user_data': None,
                'trends': None,
                'interactions': [],
                'embeddings': None
            }
            self.context_history = {}
