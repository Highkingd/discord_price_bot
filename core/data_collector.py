import discord
from typing import Dict, List, Optional
import json
import os
from datetime import datetime
import re
from collections import defaultdict

class DataCollector:
    def __init__(self):
        self.data_file = "data/collected_data.json"
        self.min_message_length = 5  # Tin nhắn tối thiểu 5 ký tự
        self.max_messages_per_topic = 1000  # Giới hạn số lượng tin nhắn mỗi chủ đề
        self.data = self.load_data()
        
        # Các từ khóa theo chủ đề để phân loại tin nhắn
        self.topic_keywords = {
            'price_discussion': [
                'giá', 'price', 'cost', 'bao nhiêu', 'đắt', 'rẻ', 'sl', 'rp',
                'silver lions', 'research points', 'đồng', 'tiền'
            ],
            'order_process': [
                'đặt', 'mua', 'order', 'book', 'đơn hàng', 'deposit', 'thanh toán',
                'payment', 'chuyển khoản'
            ],
            'technical_support': [
                'lỗi', 'error', 'bug', 'issue', 'problem', 'help', 'support',
                'không được', 'fail', 'failed'
            ],
            'game_discussion': [
                'war thunder', 'game', 'tank', 'plane', 'xe tăng', 'máy bay',
                'module', 'event', 'battle', 'mission'
            ]
        }
        
        # Patterns cho việc nhận diện câu hỏi-trả lời
        self.question_patterns = [
            r'\?$',
            r'^(what|how|why|when|where|who|whose|which|will|can|could|làm sao|như thế nào|khi nào|bao giờ|ai|ở đâu|tại sao)',
            r'(cho hỏi|xin hỏi|hỏi chút|tell me|explain)'
        ]
        
        # Patterns cho việc nhận diện câu trả lời
        self.answer_patterns = [
            r'^(here|này|đây|okay|ok|được|yes|yeah|uhm|à|ừ)',
            r'(như sau|as follows|you can|bạn có thể|should|nên)',
            r'(đúng vậy|chính xác|correct|right|true)'
        ]

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
            'conversations': [],
            'qa_pairs': [],
            'topics': defaultdict(list),
            'stats': {
                'total_messages': 0,
                'total_conversations': 0,
                'total_qa_pairs': 0,
                'last_update': None
            }
        }

    def save_data(self):
        """Lưu dữ liệu đã thu thập"""
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        try:
            # Convert defaultdict to regular dict for JSON serialization
            data_to_save = self.data.copy()
            data_to_save['topics'] = dict(data_to_save['topics'])
            
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving data: {str(e)}")
            # Backup data
            backup_file = f"{self.data_file}.backup"
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)

    def collect_message(self, message: discord.Message):
        """Thu thập và phân tích tin nhắn"""
        if len(message.content) < self.min_message_length:
            return
            
        # Chuẩn bị dữ liệu tin nhắn
        msg_data = {
            'content': message.content,
            'author_id': str(message.author.id),
            'timestamp': datetime.now().isoformat(),
            'channel_id': str(message.channel.id),
            'guild_id': str(message.guild.id) if message.guild else None,
            'reference_id': str(message.reference.message_id) if message.reference else None
        }

        # Phân loại chủ đề
        detected_topics = self._detect_topics(message.content)
        for topic in detected_topics:
            if len(self.data['topics'][topic]) < self.max_messages_per_topic:
                self.data['topics'][topic].append(msg_data)

        # Kiểm tra nếu là một phần của cuộc trò chuyện
        if message.reference:
            self._process_conversation(message, msg_data)

        # Kiểm tra và lưu cặp Q&A
        if self._is_question(message.content):
            self._track_question(msg_data)
        elif message.reference and self._is_answer(message.content):
            self._track_answer(message, msg_data)

        # Cập nhật thống kê
        self.data['stats']['total_messages'] += 1
        self.data['stats']['last_update'] = datetime.now().isoformat()
        
        # Tự động lưu sau mỗi 100 tin nhắn
        if self.data['stats']['total_messages'] % 100 == 0:
            self.save_data()

    def _detect_topics(self, content: str) -> List[str]:
        """Phát hiện chủ đề của tin nhắn"""
        content = content.lower()
        topics = []
        for topic, keywords in self.topic_keywords.items():
            if any(keyword in content for keyword in keywords):
                topics.append(topic)
        return topics

    def _is_question(self, content: str) -> bool:
        """Kiểm tra xem có phải câu hỏi không"""
        content = content.lower().strip()
        return any(re.search(pattern, content) for pattern in self.question_patterns)

    def _is_answer(self, content: str) -> bool:
        """Kiểm tra xem có phải câu trả lời không"""
        content = content.lower().strip()
        return any(re.search(pattern, content) for pattern in self.answer_patterns)

    def _process_conversation(self, message: discord.Message, msg_data: Dict):
        """Xử lý và lưu trữ cuộc trò chuyện"""
        # Tìm hoặc tạo cuộc trò chuyện mới
        conversation = None
        for conv in self.data['conversations']:
            if message.reference.message_id in [msg['id'] for msg in conv['messages']]:
                conversation = conv
                break

        if not conversation:
            conversation = {
                'id': str(datetime.now().timestamp()),
                'messages': [],
                'participants': set(),
                'start_time': datetime.now().isoformat()
            }
            self.data['conversations'].append(conversation)
            self.data['stats']['total_conversations'] += 1

        # Thêm tin nhắn vào cuộc trò chuyện
        msg_data['id'] = str(message.id)
        conversation['messages'].append(msg_data)
        conversation['participants'].add(str(message.author.id))
        # Convert participants set to list for JSON serialization
        conversation['participants'] = list(conversation['participants'])

    def _track_question(self, msg_data: Dict):
        """Theo dõi câu hỏi để ghép cặp Q&A"""
        self.data['qa_pairs'].append({
            'question': msg_data,
            'answer': None,
            'timestamp': datetime.now().isoformat()
        })

    def _track_answer(self, message: discord.Message, msg_data: Dict):
        """Theo dõi và ghép cặp câu trả lời với câu hỏi"""
        # Tìm câu hỏi tương ứng
        for qa in self.data['qa_pairs']:
            if (qa['answer'] is None and 
                qa['question']['id'] == str(message.reference.message_id)):
                qa['answer'] = msg_data
                self.data['stats']['total_qa_pairs'] += 1
                break

    def get_topic_data(self, topic: str, limit: int = 100) -> List[Dict]:
        """Lấy dữ liệu theo chủ đề"""
        return self.data['topics'].get(topic, [])[:limit]

    def get_qa_pairs(self, limit: int = 100) -> List[Dict]:
        """Lấy các cặp Q&A đã thu thập"""
        return [qa for qa in self.data['qa_pairs'] 
                if qa['answer'] is not None][:limit]

    def get_stats(self) -> Dict:
        """Lấy thống kê về dữ liệu đã thu thập"""
        return self.data['stats']

    def export_training_data(self, format: str = 'json') -> str:
        """Xuất dữ liệu để training"""
        training_data = {
            'qa_pairs': self.get_qa_pairs(),
            'topic_samples': {
                topic: self.get_topic_data(topic)
                for topic in self.topic_keywords.keys()
            }
        }
        
        if format == 'json':
            return json.dumps(training_data, ensure_ascii=False, indent=2)
        # Có thể thêm các format khác (csv, xml, etc.)
        return json.dumps(training_data, ensure_ascii=False, indent=2)
