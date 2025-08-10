import json
import os
from datetime import datetime
import random
from typing import Dict, List, Tuple
from .ai_patterns import get_all_patterns  # Import patterns mới
from .nlp_processor import NLPProcessor  # Import NLP processor

class BotAI:
    def __init__(self):
        self.data_file = "data/bot_memory.json"
        self.interactions = self.load_data()
        self.keywords = {}
        
        # Khởi tạo NLP processor
        self.nlp = NLPProcessor()
        
        # Load sẵn patterns từ file
        self.predefined_patterns = get_all_patterns()
        
        # Thêm patterns vào interactions
        if "patterns" not in self.interactions:
            self.interactions["patterns"] = {}
        self.interactions["patterns"].update(self.predefined_patterns)
        
        self.build_keywords()
    
    def load_data(self) -> Dict:
        """Tải dữ liệu từ file"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {"interactions": [], "patterns": {}}
        return {"interactions": [], "patterns": {}}

    def save_data(self):
        """Lưu dữ liệu vào file"""
        try:
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.interactions, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Save Data Error: {str(e)}")
            # Backup data to temporary file
            try:
                backup_file = f"{self.data_file}.backup"
                with open(backup_file, 'w', encoding='utf-8') as f:
                    json.dump(self.interactions, f, ensure_ascii=False, indent=2)
            except:
                print("Failed to create backup file")

    def build_keywords(self):
        """Xây dựng từ điển keywords từ các tương tác"""
        self.keywords = {}
        # Giới hạn số lượng tương tác để tránh quá tải
        max_interactions = 1000
        recent_interactions = self.interactions.get("interactions", [])[-max_interactions:]
        
        for interaction in recent_interactions:
            words = interaction["input"].lower().split()
            for word in words:
                if word not in self.keywords:
                    self.keywords[word] = []
                if len(self.keywords[word]) < 100:  # Giới hạn số responses cho mỗi keyword
                    self.keywords[word].append(interaction["output"])

    def learn(self, input_text: str, output_text: str, context: Dict = None):
        """Học từ tương tác mới với phân tích NLP"""
        if "interactions" not in self.interactions:
            self.interactions["interactions"] = []
            
        # Rate limiting: kiểm tra số lượng học trong 1 phút
        current_time = datetime.now()
        recent_learnings = [
            i for i in self.interactions.get("interactions", [])
            if (current_time - datetime.fromisoformat(i["timestamp"])).total_seconds() < 60
        ]
        if len(recent_learnings) >= 10:  # Giới hạn 10 lần học/phút
            print("Rate limit exceeded for learning")
            return
            
        try:
            # Phân tích NLP cho input
            intent, entities = self.nlp.analyze(input_text)
            emotion = self.nlp.detect_emotion(input_text)
        except Exception as e:
            print(f"Learning NLP Error: {str(e)}")
            intent, entities = None, []
            emotion = None
        
        interaction = {
            "timestamp": datetime.now().isoformat(),
            "input": input_text,
            "output": output_text,
            "context": context or {},
            "nlp_data": {
                "intent": intent,
                "entities": entities,
                "emotion": emotion
            }
        }
        
        self.interactions["interactions"].append(interaction)
        
        # Cập nhật model NLP nếu cần
        self.nlp.update_model(input_text, output_text, intent, entities)
        
        self.save_data()
        self.build_keywords()

    def find_best_response(self, input_text: str, context: Dict = None) -> Tuple[str, float]:
        """Tìm câu trả lời phù hợp nhất sử dụng NLP và pattern matching"""
        try:
            # Phân tích NLP
            intent, entities = self.nlp.analyze(input_text)
            emotion = self.nlp.detect_emotion(input_text)
        except Exception as e:
            print(f"NLP Error: {str(e)}")
            intent, entities = None, []
            emotion = None
        
        # Kiểm tra patterns trước
        patterns = self.interactions.get("patterns", {})
        best_pattern_score = 0
        best_pattern_response = None
        
        # Kiểm tra exact match trước
        input_lower = input_text.lower()
        for pattern, responses in patterns.items():
            if pattern.lower() == input_lower:
                response = random.choice(responses)
                if emotion:
                    response = self.nlp.adjust_response_tone(response, emotion)
                return response, 1.0
                
        # Nếu không có exact match, tìm pattern gần đúng nhất
        for pattern, responses in patterns.items():
            pattern_score = self.nlp.calculate_similarity(pattern, input_text)
            if pattern_score > 0.8 and pattern_score > best_pattern_score:  # Threshold cao hơn cho pattern matching
                best_pattern_score = pattern_score
                best_pattern_response = random.choice(responses)
                
        if best_pattern_response:
            if emotion:
                best_pattern_response = self.nlp.adjust_response_tone(best_pattern_response, emotion)
            return best_pattern_response, best_pattern_score

        # Tìm trong interactions với NLP
        best_match = None
        best_score = 0
        
        for interaction in self.interactions.get("interactions", []):
            # Tính điểm tương đồng ngữ nghĩa
            similarity = self.nlp.calculate_similarity(interaction["input"], input_text)
            
            # Tính điểm intent và entities
            try:
                interaction_intent = self.nlp.analyze(interaction["input"])[0]
                interaction_entities = self.nlp.analyze(interaction["input"])[1]
                intent_match = interaction_intent == intent
                entity_score = self.nlp.compare_entities(interaction_entities, entities)
            except Exception as e:
                print(f"Interaction Analysis Error: {str(e)}")
                intent_match = False
                entity_score = 0.0
            
            # Tổng hợp điểm
            score = similarity * 0.6  # Trọng số cho độ tương đồng ngữ nghĩa
            if intent_match:
                score += 0.2  # Trọng số cho intent matching
            score += entity_score * 0.2  # Trọng số cho entity matching
            
            # Tăng điểm nếu context giống nhau
            if context and interaction.get("context"):
                matching_context = sum(1 for k, v in context.items() 
                                    if k in interaction["context"] 
                                    and interaction["context"][k] == v)
                score += matching_context * 0.1

            if score > best_score:
                best_score = score
                best_match = interaction["output"]

        if best_match and best_score >= 0.6:  # Threshold thấp hơn cho NLP matching
            # Điều chỉnh response dựa trên emotion
            if emotion:
                best_match = self.nlp.adjust_response_tone(best_match, emotion)
            return best_match, best_score
            
        # Tạo câu trả lời mới nếu không tìm được kết quả tốt
        generated_response = self.nlp.generate_response(input_text, intent, entities, emotion)
        if generated_response:
            return generated_response, 0.5
            
        # Fallback to default responses
        default_responses = [
            "Tôi không chắc mình hiểu ý bạn. Bạn có thể giải thích rõ hơn được không?",
            "Xin lỗi, tôi chưa học được cách trả lời câu hỏi này.",
            "Hãy thử diễn đạt theo cách khác nhé!",
            "Tôi đang học hỏi thêm để trả lời tốt hơn."
        ]
        return random.choice(default_responses), 0.0

    def add_pattern(self, pattern: str, responses: List[str]):
        """Thêm pattern và câu trả lời tương ứng"""
        if "patterns" not in self.interactions:
            self.interactions["patterns"] = {}
        self.interactions["patterns"][pattern] = responses
        self.save_data()

    def get_stats(self) -> Dict:
        """Lấy thống kê về dữ liệu học tập"""
        return {
            "total_interactions": len(self.interactions.get("interactions", [])),
            "total_patterns": len(self.interactions.get("patterns", {})),
            "unique_keywords": len(self.keywords),
            "last_interaction": (self.interactions.get("interactions", [{}])[-1].get("timestamp")
                               if self.interactions.get("interactions") else None)
        }
