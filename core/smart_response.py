from typing import Dict, List, Optional, Tuple
import random
import re
from datetime import datetime
import json
import os
import logging
import time
import gc
from collections import defaultdict
from functools import lru_cache

class SmartResponseGenerator:
    def __init__(self):
        # Simple storage
        self.context_history = {}
        self.max_context_history = 5
        self.max_users = 100
        
        # Response data
        self.data_file = "data/smart_responses.json"
        self._data = None
        self._last_data_load = 0
        self.data_reload_interval = 300
        
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity"""
        # Convert to sets of words
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        # Calculate Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        if union == 0:
            return 0.0
            
        return intersection / union
        
    @property
    def data(self):
        current_time = time.time()
        if self._data is None or (current_time - self._last_data_load) > self.data_reload_interval:
            self._data = self.load_data()
            self._last_data_load = current_time
        return self._data
        self.setup_logger()
        
        # Từ điển phong cách và cảm xúc
        self.style_patterns = {
            'formal': {
                'greetings': [
                    "Xin chào", "Kính chào", "Rất vui được gặp"
                ],
                'responses': [
                    "Theo thông tin hiện có", "Dựa trên dữ liệu phân tích",
                    "Hệ thống ghi nhận rằng"
                ],
                'conclusions': [
                    "Hy vọng thông tin trên hữu ích", "Nếu cần thêm thông tin",
                    "Xin vui lòng cho biết nếu cần giải thích thêm"
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
                    "Bạn thấy sao?", "Mình nghĩ vậy đó", "Cho mình biết ý kiến nhé"
                ]
            },
            'empathetic': {
                'greetings': [
                    "Mình hiểu điều bạn đang quan tâm", 
                    "Mình sẽ cố gắng giúp bạn",
                    "Đừng lo lắng nhé"
                ],
                'responses': [
                    "Mình nghĩ bạn sẽ thích", "Điều này có thể giúp bạn",
                    "Mình đề xuất"
                ],
                'conclusions': [
                    "Hy vọng bạn cảm thấy tốt hơn", 
                    "Mình luôn ở đây nếu bạn cần",
                    "Đừng ngại chia sẻ thêm nhé"
                ]
            }
        }
        
        # Mẫu câu động cho các chủ đề
        self.topic_templates = {
            'price_info': [
                "Hiện tại {item} có giá {price}",
                "Giá của {item} đang là {price}",
                "Theo thị trường, {item} đang được giao dịch ở mức {price}",
                "Mình vừa kiểm tra, {item} có giá {price}",
                "{item} hiện đang được bán với giá {price}"
            ],
            'price_change': [
                "Giá đã {direction} {percent}% so với {time_ago}",
                "So với {time_ago}, giá đã {direction} {percent}%",
                "Biến động giá: {direction} {percent}% trong {time_ago}",
                "Mình thấy giá {direction} khoảng {percent}% từ {time_ago}",
                "Theo dõi từ {time_ago}, giá đã {direction} {percent}%"
            ],
            'market_analysis': [
                "Thị trường đang {trend}, {reason}",
                "Theo phân tích, {trend} do {reason}",
                "Mình nhận thấy thị trường {trend}, nguyên nhân là {reason}",
                "Dựa trên dữ liệu, {trend} bởi vì {reason}",
                "Phân tích cho thấy {trend}, điều này do {reason}"
            ]
        }
        
        # Context triggers cho các phản hồi đặc biệt
        self.context_triggers = {
            'user_confused': [
                "không hiểu", "khó hiểu", "là sao", "không rõ"
            ],
            'user_frustrated': [
                "khó chịu", "bực", "tức", "chán"
            ],
            'user_happy': [
                "tốt", "hay", "thích", "được"
            ]
        }

    def setup_logger(self):
        """Thiết lập logging"""
        self.logger = logging.getLogger('SmartResponseGenerator')
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            handler = logging.FileHandler('data/smart_response.log', encoding='utf-8')
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def load_data(self) -> Dict:
        """Tải dữ liệu phản hồi"""
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
            'responses': [],  # Lưu trữ các cặp Q&A
            'contexts': {},   # Lưu trữ context cho mỗi response
            'embeddings': {}  # Cache embeddings
        }

    def save_data(self):
        """Lưu dữ liệu phản hồi"""
        try:
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Lỗi khi lưu dữ liệu: {str(e)}")

    def add_response(self, question: str, answer: str, context: Dict = None):
        """Thêm cặp Q&A mới"""
        response_data = {
            'question': question,
            'answer': answer,
            'context': context or {},
            'timestamp': datetime.now().isoformat()
        }
        
        self.data['responses'].append(response_data)
        
        if len(self.data['responses']) > 1000:  # Giới hạn số lượng
            self.data['responses'] = self.data['responses'][-1000:]
            
        self.save_data()

    def analyze_user_style(self, message: str) -> str:
        """Phân tích phong cách người dùng"""
        message = message.lower()
        
        # Kiểm tra độ formal
        formal_words = ['xin', 'vui lòng', 'cảm ơn', 'kính', 'thưa']
        casual_words = ['hey', 'hi', 'ê', 'ơi', 'nhé', 'nha']
        
        formal_count = sum(word in message for word in formal_words)
        casual_count = sum(word in message for word in casual_words)
        
        # Kiểm tra sentiment đơn giản
        negative_words = ['không', 'chán', 'buồn', 'khó', 'tệ']
        negative_count = sum(word in message for word in negative_words)
        
        if formal_count > casual_count:
            return 'formal'
        elif negative_count > 1:
            return 'empathetic'
        else:
            return 'casual'

    def detect_user_context(self, message: str, user_id: str) -> Dict:
        """Phát hiện context từ tin nhắn người dùng"""
        context = {
            'style': self.analyze_user_style(message),
            'timestamp': time.time()
        }
        
        # Kiểm tra các trigger
        message_lower = message.lower()
        for trigger_type, patterns in self.context_triggers.items():
            if any(pattern in message_lower for pattern in patterns):
                context['trigger'] = trigger_type
                break
                
        # Kiểm tra và khởi tạo history nếu cần
        if user_id not in self.context_history:
            self.context_history[user_id] = []
                
        # Thêm vào lịch sử context
        self.context_history[user_id].append(context)
        if len(self.context_history[user_id]) > self.max_context_history:
            self.context_history[user_id].pop(0)
            
        return context

    def generate_dynamic_response(self, 
                                base_response: str,
                                context: Dict,
                                data: Optional[Dict] = None) -> str:
        """Tạo câu trả lời động dựa trên context"""
        style = context.get('style', 'casual')
        style_patterns = self.style_patterns[style]
        
        # Chọn pattern phù hợp
        greeting = ""
        response = ""
        conclusion = ""
        
        # Thêm lời chào nếu là câu đầu tiên
        if not self.context_history.get(context.get('user_id', ''), []):
            greeting = random.choice(style_patterns['greetings']) + ", "
            
        # Xử lý câu trả lời chính
        if '{' in base_response and '}' in base_response and data:
            try:
                response = base_response.format(**data)
            except KeyError:
                response = base_response
        else:
            response = base_response
            
        # Thêm transition phrase
        transition = random.choice(style_patterns['responses'])
        response = f"{transition} {response}"
        
        # Thêm kết luận nếu phù hợp
        if random.random() < 0.3:  # 30% cơ hội thêm kết luận
            conclusion = f". {random.choice(style_patterns['conclusions'])}"
            
        # Kết hợp các phần
        full_response = f"{greeting}{response}{conclusion}"
        
        return full_response.strip()

    @lru_cache(maxsize=1000)
    def get_similarity_cached(self, text1: str, text2: str) -> float:
        """Cached version of text similarity"""
        return self.calculate_similarity(text1, text2)

    def cleanup_old_contexts(self):
        """Cleanup old context histories"""
        if len(self.context_history) > self.max_users:
            # Remove context history for least recently used users
            sorted_users = sorted(
                self.context_history.items(),
                key=lambda x: x[1][-1].get('timestamp', 0) if x[1] else 0
            )
            for user_id, _ in sorted_users[:-self.max_users]:
                del self.context_history[user_id]

    def find_best_response(self,
                          message: str,
                          user_id: str,
                          additional_data: Optional[Dict] = None) -> Tuple[str, float]:
        """Tìm câu trả lời phù hợp nhất với memory optimization"""
        # Cleanup old contexts periodically
        self.cleanup_old_contexts()
        
        # Phát hiện context
        context = self.detect_user_context(message, user_id)
        context['user_id'] = user_id
        context['timestamp'] = time.time()
        
        # Tối ưu tìm kiếm câu trả lời
        best_similarity = 0
        best_response = None
        
        # Batch processing để giảm memory usage
        batch_size = 50
        responses = self.data['responses']
        
        for i in range(0, len(responses), batch_size):
            batch = responses[i:i + batch_size]
            
            # Process similarity in batch
            batch_similarities = [
                (
                    self.get_semantic_similarity_cached(message, resp['question']),
                    resp
                )
                for resp in batch
            ]
            
            # Update best match
            batch_best = max(batch_similarities, key=lambda x: x[0])
            if batch_best[0] > best_similarity:
                best_similarity = batch_best[0]
                best_response = batch_best[1]
            
            # Early stopping if we found a very good match
            if best_similarity > 0.9:
                break
                
            # Garbage collection for large batches
            if i % (batch_size * 5) == 0:
                gc.collect()
        
        if not best_response or best_similarity < 0.6:
            # Không tìm thấy câu trả lời phù hợp
            # Tạo câu trả lời dựa trên templates
            if additional_data:
                for topic, templates in self.topic_templates.items():
                    if all(key in additional_data for key in re.findall(r'{(\w+)}', templates[0])):
                        base_response = random.choice(templates)
                        response = self.generate_dynamic_response(
                            base_response,
                            context,
                            additional_data
                        )
                        
                        # Clear cache periodically
                        if random.random() < 0.1:  # 10% chance to clear cache
                            self.get_semantic_similarity_cached.cache_clear()
                            
                        return response, 0.5
                        
            # Fallback response
            base_response = "Xin lỗi, mình chưa có thông tin về vấn đề này"
            response = self.generate_dynamic_response(base_response, context)
            return response, 0.0
            
        # Tìm thấy câu trả lời phù hợp
        response = self.generate_dynamic_response(
            best_response['answer'],
            context,
            additional_data
        )
        
        # Memory optimization
        del best_response
        gc.collect()
        
        return response, best_similarity

    def learn_from_conversation(self,
                              messages: List[Dict],
                              feedback: Optional[float] = None):
        """Học từ cuộc trò chuyện"""
        for i in range(len(messages) - 1):
            question = messages[i]['content']
            answer = messages[i + 1]['content']
            
            # Chỉ học từ các cặp Q&A có feedback tốt
            if feedback and feedback > 0.7:
                self.add_response(question, answer, {
                    'feedback': feedback,
                    'timestamp': datetime.now().isoformat()
                })

    def get_conversation_suggestions(self, 
                                   current_context: Dict,
                                   history: List[Dict]) -> List[str]:
        """Đề xuất các câu trả lời tiếp theo"""
        suggestions = []
        
        # Phân tích context hiện tại
        current_style = current_context.get('style', 'casual')
        current_sentiment = current_context.get('sentiment', {}).get('compound', 0)
        
        # Tìm các câu trả lời phù hợp với context
        for response_data in self.data['responses']:
            if len(suggestions) >= 3:  # Giới hạn số lượng đề xuất
                break
                
            # Kiểm tra độ phù hợp với context
            if response_data.get('context', {}).get('style') == current_style:
                suggestion = self.generate_dynamic_response(
                    response_data['answer'],
                    current_context
                )
                if suggestion not in suggestions:
                    suggestions.append(suggestion)
                    
        return suggestions
