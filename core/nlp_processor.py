import re
from typing import Dict, List, Tuple
from datetime import datetime
import random

from functools import lru_cache

class NLPProcessor:
    def __init__(self):
        # Cache cho các kết quả phân tích
        self._cache = {}
        self._cache_size = 1000
        
        # Từ khóa theo chủ đề
        self.topic_keywords = {
            'greeting': ['chào', 'hi', 'hello', 'hey', 'good'],
            'price': ['giá', 'price', 'cost', 'bao nhiêu', 'đắt', 'rẻ'],
            'order': ['đặt', 'mua', 'order', 'book', 'đơn hàng'],
            'status': ['trạng thái', 'tình trạng', 'status', 'kiểm tra'],
            'help': ['giúp', 'help', 'hướng dẫn', 'guide', 'support'],
            'game': ['war thunder', 'game', 'tank', 'plane', 'xe tăng', 'máy bay'],
            'time': ['khi nào', 'bao lâu', 'thời gian', 'deadline', 'hạn'],
            'payment': ['thanh toán', 'payment', 'chuyển khoản', 'tiền'],
        }

        # Ngữ cảnh cảm xúc
        self.emotion_keywords = {
            'positive': ['vui', 'tốt', 'thích', 'hay', 'được', 'ok', 'oke', 'yes', 'thế', 'đúng'],
            'negative': ['buồn', 'không', 'chưa', 'sai', 'lỗi', 'khó', 'vấn đề'],
            'urgent': ['gấp', 'nhanh', 'urgent', 'sớm', 'càng sớm càng tốt'],
            'confused': ['sao', 'làm sao', 'thế nào', 'như nào', 'không hiểu', 'khó hiểu'],
        }

        # Context lịch sử
        self.conversation_history = []
        self.max_history = 5

    @lru_cache(maxsize=1000)
    def analyze_intent(self, text: str) -> Dict[str, float]:
        """Phân tích ý định của câu hỏi với cache và context"""
        text = text.lower()
        scores = {}
        
        # Lấy top 3 intent có điểm cao nhất để tránh lặp lại
        top_intents = []
        
        # Tính điểm cho từng chủ đề và lưu top 3
        for topic, keywords in self.topic_keywords.items():
            score = sum(1.0 for word in keywords if word in text)
            if score > 0:
                score = score / len(text.split())
                scores[topic] = score
                top_intents.append((topic, score))
        
        # Sắp xếp và chỉ giữ lại top intent có điểm cao nhất
        if top_intents:
            top_intents.sort(key=lambda x: x[1], reverse=True)
            top_intent = top_intents[0]
            scores = {top_intent[0]: top_intent[1]}

        # Phân tích cảm xúc
        for emotion, keywords in self.emotion_keywords.items():
            score = sum(1.0 for word in keywords if word in text)
            if score > 0:
                scores[f"emotion_{emotion}"] = score / len(text.split())

        return scores

    def generate_contextual_response(self, 
                                   text: str, 
                                   base_response: str, 
                                   context: Dict) -> str:
        """Tạo câu trả lời có ngữ cảnh"""
        intent_scores = self.analyze_intent(text)
        
        # Thêm vào lịch sử
        self.conversation_history.append({
            'text': text,
            'intent': intent_scores,
            'timestamp': datetime.now().isoformat()
        })
        if len(self.conversation_history) > self.max_history:
            self.conversation_history.pop(0)

        # Điều chỉnh câu trả lời dựa trên ngữ cảnh
        response = base_response

        # Xử lý cảm xúc
        if 'emotion_positive' in intent_scores:
            response = self._add_positive_tone(response)
        elif 'emotion_negative' in intent_scores:
            response = self._add_empathy(response)
        elif 'emotion_urgent' in intent_scores:
            response = self._add_urgency(response)
        elif 'emotion_confused' in intent_scores:
            response = self._add_explanation(response)

        # Thêm ngữ cảnh thời gian
        hour = datetime.now().hour
        if 5 <= hour < 12:
            response = self._add_time_context(response, "morning")
        elif 12 <= hour < 18:
            response = self._add_time_context(response, "afternoon")
        else:
            response = self._add_time_context(response, "evening")

        # Thêm tính liên tục nếu có lịch sử
        if len(self.conversation_history) > 1:
            response = self._add_conversation_continuity(response)

        return response

    def _add_positive_tone(self, text: str) -> str:
        """Thêm giọng điệu tích cực"""
        positive_additions = [
            "Rất vui khi ",
            "Tuyệt vời! ",
            "Thật tốt! ",
            "Tôi rất vui ",
        ]
        return random.choice(positive_additions) + text

    def _add_empathy(self, text: str) -> str:
        """Thêm sự đồng cảm"""
        empathy_additions = [
            "Tôi hiểu cảm giác của bạn. ",
            "Đừng lo lắng! ",
            "Để tôi giúp bạn nhé. ",
            "Tôi sẽ cố gắng giúp bạn. ",
        ]
        return random.choice(empathy_additions) + text

    def _add_urgency(self, text: str) -> str:
        """Thêm tính khẩn cấp"""
        urgency_additions = [
            "Tôi sẽ xử lý ngay cho bạn. ",
            "Để tôi ưu tiên giúp bạn. ",
            "Sẽ xử lý gấp cho bạn. ",
            "Tôi sẽ làm nhanh nhất có thể. ",
        ]
        return random.choice(urgency_additions) + text

    def _add_explanation(self, text: str) -> str:
        """Thêm giải thích chi tiết"""
        explanation_additions = [
            "Để tôi giải thích rõ hơn: ",
            "Tôi sẽ giải thích chi tiết nhé. ",
            "Bạn có thể hiểu đơn giản là: ",
            "Nói một cách dễ hiểu thì: ",
        ]
        return random.choice(explanation_additions) + text

    def _add_time_context(self, text: str, time_of_day: str) -> str:
        """Thêm ngữ cảnh thời gian"""
        if "chào" not in text.lower():
            return text
            
        time_additions = {
            "morning": ["buổi sáng", "☀️"],
            "afternoon": ["buổi chiều", "🌤️"],
            "evening": ["buổi tối", "🌙"]
        }
        addition = time_additions.get(time_of_day, [""])[0]
        emoji = time_additions.get(time_of_day, [""])[1]
        return f"Chào {addition}! {emoji} " + text.replace("Chào", "", 1).strip()

    def _add_conversation_continuity(self, text: str) -> str:
        """Thêm tính liên tục cho cuộc trò chuyện"""
        last_topic = None
        for history in reversed(self.conversation_history[:-1]):
            intent_scores = history['intent']
            if intent_scores:
                last_topic = max(intent_scores.items(), key=lambda x: x[1])[0]
                break

        if last_topic and last_topic in self.topic_keywords:
            continuity_phrases = [
                f"Tiếp theo về {last_topic}, ",
                f"Ngoài ra, ",
                f"Thêm nữa, ",
                f"Nói thêm về vấn đề này, ",
            ]
            return random.choice(continuity_phrases) + text

        return text

    # === Methods required for ai_handler.py integration ===
    def analyze(self, text: str):
        """Return (intent, entities) tuple."""
        intent_scores = self.analyze_intent(text)
        # Pick the highest scoring intent as main intent
        intent = None
        max_score = 0
        for k, v in intent_scores.items():
            if not k.startswith('emotion_') and v > max_score:
                intent = k
                max_score = v
        # Simple entity extraction: return keywords found
        entities = [word for topic in self.topic_keywords.values() for word in topic if word in text.lower()]
        return intent, entities

    def detect_emotion(self, text: str):
        """Detect emotion from text using emotion_keywords."""
        text = text.lower()
        for emotion, keywords in self.emotion_keywords.items():
            for word in keywords:
                if word in text:
                    return emotion
        return None

    @lru_cache(maxsize=1000)
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Rudimentary similarity: Jaccard index of word sets with cache."""
        # Convert to frozen sets for hashability in cache
        set1 = frozenset(text1.lower().split())
        set2 = frozenset(text2.lower().split())
        if not set1 or not set2:
            return 0.0
        return len(set1 & set2) / len(set1 | set2)

    def compare_entities(self, entities1, entities2) -> float:
        """Return ratio of shared entities."""
        if not entities1 or not entities2:
            return 0.0
        set1 = set(entities1)
        set2 = set(entities2)
        return len(set1 & set2) / max(len(set1 | set2), 1)

    def adjust_response_tone(self, response: str, emotion: str) -> str:
        """Adjust response tone based on emotion."""
        if emotion == 'positive':
            return self._add_positive_tone(response)
        elif emotion == 'negative':
            return self._add_empathy(response)
        elif emotion == 'urgent':
            return self._add_urgency(response)
        elif emotion == 'confused':
            return self._add_explanation(response)
        return response

    def generate_response(self, input_text: str, intent, entities, emotion=None):
        """Generate a smart contextual response."""
        # Các mẫu câu trả lời theo intent
        intent_responses = {
            'greeting': [
                "Xin chào! Mình có thể giúp gì cho bạn?",
                "Hey! Bạn cần hỗ trợ gì không?",
                "Chào bạn! Mình đang lắng nghe nè"
            ],
            'price': [
                "Để xem giá chính xác, bạn dùng lệnh /tinhgia nhé!",
                "Mình có thể giúp bạn tính giá. Bạn cần báo giá cho dịch vụ nào?",
                "Bạn muốn xem báo giá cho dịch vụ nào?"
            ],
            'order': [
                "Để đặt đơn, bạn dùng lệnh /donhang nhé!",
                "Mình sẽ hướng dẫn bạn quy trình đặt đơn",
                "Bạn muốn đặt đơn? Mình sẽ giúp bạn!"
            ],
            'status': [
                "Kiểm tra trạng thái đơn bằng lệnh /trangthai nhé!",
                "Bạn cần mã đơn để kiểm tra trạng thái",
                "Mình có thể giúp bạn xem trạng thái đơn"
            ],
            'help': [
                "Bạn cần giúp đỡ gì? Mình luôn sẵn sàng!",
                "Mình có thể giải đáp thắc mắc cho bạn",
                "Hãy cho mình biết bạn cần hỗ trợ gì nhé"
            ],
            'game': [
                "Bạn quan tâm đến phần nào của game?",
                "Mình có thể tư vấn về các tính năng trong game",
                "Cần thông tin gì về game, bạn cứ hỏi nhé!"
            ],
            'payment': [
                "Thông tin thanh toán sẽ được gửi sau khi đơn được duyệt",
                "Bạn sẽ nhận hướng dẫn thanh toán qua DM",
                "Mọi giao dịch đều được bảo đảm an toàn"
            ]
        }

        # Chọn response dựa trên intent và context
        if intent and intent in intent_responses:
            base = random.choice(intent_responses[intent])
        else:
            # Fallback responses thông minh hơn
            fallbacks = [
                "Mình hiểu bạn đang cần hỗ trợ. Bạn có thể nói rõ hơn được không?",
                "Bạn cần tìm hiểu thêm về vấn đề gì?",
                "Mình muốn hiểu rõ hơn nhu cầu của bạn",
                "Bạn có thể chia sẻ thêm không? Mình sẽ cố gắng giúp bạn"
            ]
            base = random.choice(fallbacks)

        # Thêm thông tin hữu ích nếu phát hiện entities quan trọng
        if entities:
            useful_info = {
                'sl': " (Tip: 1M SL = 100k VNĐ)",
                'rp': " (Tip: Premium RP có giá tốt hơn)",
                'module': " (Tip: Có nhiều loại module khác nhau)",
                'event': " (Tip: Thời gian event có hạn)"
            }
            for entity in entities:
                if entity.lower() in useful_info:
                    base += useful_info[entity.lower()]

        # Điều chỉnh giọng điệu dựa trên emotion
        if emotion:
            base = self.adjust_response_tone(base, emotion)

        return base.strip()

    def update_model(self, input_text, output_text, intent, entities):
        """Stub for model update (no-op for now)."""
        pass
