import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.ensemble import RandomForestRegressor
from datetime import datetime, timedelta
import pandas as pd
from typing import Dict, List, Tuple, Optional
import logging

class PricePredictor:
    def __init__(self):
        self.models = {}  # item_name: trained_model
        self.features = {}  # item_name: feature_data
        self.setup_logger()
        
    def setup_logger(self):
        """Thiết lập logging"""
        self.logger = logging.getLogger('PricePredictor')
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            handler = logging.FileHandler('data/price_predictor.log', encoding='utf-8')
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def prepare_data(self, 
                    price_history: List[Dict],
                    vehicle_data: Optional[Dict] = None,
                    game_events: Optional[List[Dict]] = None) -> Tuple[np.ndarray, np.ndarray]:
        """Chuẩn bị dữ liệu cho model"""
        if not price_history:
            return None, None
            
        # Chuyển đổi lịch sử giá thành DataFrame
        df = pd.DataFrame(price_history)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Tính toán các features thời gian
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['month'] = df['timestamp'].dt.month
        df['day_of_month'] = df['timestamp'].dt.day
        
        # Thêm features từ vehicle data nếu có
        if vehicle_data:
            df['br_rating'] = vehicle_data.get('br_rating', 0)
            df['repair_cost'] = vehicle_data.get('repair_cost', 0)
            df['num_modifications'] = len(vehicle_data.get('modifications', []))
            
        # Thêm features từ game events nếu có
        if game_events:
            df['active_events'] = 0
            for event in game_events:
                event_start = pd.to_datetime(event['start_date'])
                event_end = pd.to_datetime(event['end_date'])
                mask = (df['timestamp'] >= event_start) & (df['timestamp'] <= event_end)
                df.loc[mask, 'active_events'] += 1
                
        # Tính các statistical features
        df['rolling_mean'] = df['price'].rolling(window=5, min_periods=1).mean()
        df['rolling_std'] = df['price'].rolling(window=5, min_periods=1).std()
        df['price_change'] = df['price'].pct_change()
        
        # Tạo lag features
        for i in range(1, 4):
            df[f'price_lag_{i}'] = df['price'].shift(i)
            
        # Drop NA và chuyển đổi thành numpy arrays
        df = df.dropna()
        
        if len(df) < 2:
            return None, None
            
        X = df[[col for col in df.columns if col not in ['timestamp', 'price']]].values
        y = df['price'].values
        
        return X, y

    def train_model(self, 
                   item_name: str,
                   price_history: List[Dict],
                   vehicle_data: Optional[Dict] = None,
                   game_events: Optional[List[Dict]] = None):
        """Train model dự đoán giá"""
        try:
            X, y = self.prepare_data(price_history, vehicle_data, game_events)
            if X is None or y is None:
                self.logger.warning(f"Không đủ dữ liệu để train model cho {item_name}")
                return False
                
            # Sử dụng RandomForest vì nó xử lý tốt dữ liệu phi tuyến và nhiễu
            model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42
            )
            model.fit(X, y)
            
            # Lưu model và features
            self.models[item_name] = model
            self.features[item_name] = list(range(X.shape[1]))  # Lưu số lượng features
            
            self.logger.info(f"Đã train model thành công cho {item_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Lỗi khi train model cho {item_name}: {str(e)}")
            return False

    def predict_price(self, 
                     item_name: str,
                     price_history: List[Dict],
                     vehicle_data: Optional[Dict] = None,
                     game_events: Optional[List[Dict]] = None,
                     days_ahead: int = 7) -> List[Dict]:
        """Dự đoán giá trong tương lai"""
        if item_name not in self.models:
            if not self.train_model(item_name, price_history, vehicle_data, game_events):
                return []
                
        try:
            # Chuẩn bị dữ liệu cho dự đoán
            last_timestamp = datetime.fromisoformat(price_history[-1]['timestamp'])
            predictions = []
            
            # Tạo dữ liệu dự đoán cho từng ngày
            current_history = price_history.copy()
            for day in range(1, days_ahead + 1):
                predict_time = last_timestamp + timedelta(days=day)
                
                # Tạo điểm dữ liệu mới
                new_point = {
                    'timestamp': predict_time.isoformat(),
                    'price': None  # Sẽ được điền sau
                }
                temp_history = current_history + [new_point]
                
                # Chuẩn bị features
                X, _ = self.prepare_data(temp_history, vehicle_data, game_events)
                if X is None:
                    continue
                    
                # Chỉ lấy điểm cuối cùng để dự đoán
                X = X[-1:]
                
                # Dự đoán giá
                predicted_price = self.models[item_name].predict(X)[0]
                
                # Tính confidence interval
                predictions_all = []
                n_trees = 100
                for tree in self.models[item_name].estimators_:
                    predictions_all.append(tree.predict(X)[0])
                std = np.std(predictions_all)
                
                prediction = {
                    'timestamp': predict_time.isoformat(),
                    'price': predicted_price,
                    'lower_bound': predicted_price - 1.96 * std,
                    'upper_bound': predicted_price + 1.96 * std,
                    'confidence': 1.0 - (std / predicted_price if predicted_price != 0 else 1)
                }
                
                predictions.append(prediction)
                
                # Thêm dự đoán vào lịch sử để dự đoán điểm tiếp theo
                current_history.append({
                    'timestamp': predict_time.isoformat(),
                    'price': predicted_price
                })
                
            return predictions
            
        except Exception as e:
            self.logger.error(f"Lỗi khi dự đoán giá cho {item_name}: {str(e)}")
            return []

    def get_price_trends(self, 
                        item_name: str, 
                        predictions: List[Dict]) -> Dict:
        """Phân tích xu hướng giá"""
        if not predictions:
            return {}
            
        prices = [p['price'] for p in predictions]
        
        # Tính xu hướng
        trend = np.polyfit(range(len(prices)), prices, 1)[0]
        
        # Tính volatility
        volatility = np.std(prices) / np.mean(prices) if prices else 0
        
        # Tính các mốc giá quan trọng
        min_price = min(prices)
        max_price = max(prices)
        avg_price = sum(prices) / len(prices)
        
        # Xác định xu hướng
        if trend > 0:
            trend_direction = "tăng"
            strength = "mạnh" if trend > avg_price * 0.05 else "nhẹ"
        elif trend < 0:
            trend_direction = "giảm"
            strength = "mạnh" if abs(trend) > avg_price * 0.05 else "nhẹ"
        else:
            trend_direction = "ổn định"
            strength = "không đáng kể"
            
        return {
            'direction': trend_direction,
            'strength': strength,
            'volatility': volatility,
            'min_predicted': min_price,
            'max_predicted': max_price,
            'avg_predicted': avg_price,
            'confidence': np.mean([p['confidence'] for p in predictions])
        }

    def analyze_market_factors(self, 
                             item_name: str,
                             vehicle_data: Optional[Dict] = None,
                             game_events: Optional[List[Dict]] = None) -> List[str]:
        """Phân tích các yếu tố ảnh hưởng đến giá"""
        factors = []
        
        if vehicle_data:
            # Phân tích BR rating
            if vehicle_data.get('br_rating'):
                if vehicle_data['br_rating'] >= 9.0:
                    factors.append("🎯 BR cao (>= 9.0) có thể làm tăng giá")
                elif vehicle_data['br_rating'] <= 3.0:
                    factors.append("🎯 BR thấp (<= 3.0) có thể làm giảm giá")
                    
            # Phân tích repair cost
            if vehicle_data.get('repair_cost'):
                if vehicle_data['repair_cost'] > 10000:
                    factors.append("💰 Chi phí sửa chữa cao có thể làm giảm nhu cầu")
                    
            # Phân tích modifications
            num_mods = len(vehicle_data.get('modifications', []))
            if num_mods > 10:
                factors.append("🔧 Nhiều modifications có thể tăng giá trị")
                
        if game_events:
            active_events = [
                event for event in game_events 
                if datetime.now() >= datetime.fromisoformat(event['start_date'])
                and datetime.now() <= datetime.fromisoformat(event['end_date'])
            ]
            if active_events:
                factors.append(f"🎮 {len(active_events)} sự kiện đang diễn ra có thể ảnh hưởng đến giá")
                
        # Thêm các yếu tố thời gian
        current_month = datetime.now().month
        if current_month in [6, 7, 8]:
            factors.append("📅 Mùa hè thường có nhiều người chơi, có thể ảnh hưởng đến giá")
        elif current_month in [11, 12]:
            factors.append("🎄 Gần các sự kiện cuối năm, giá có thể biến động")
            
        return factors

    def get_trading_advice(self, 
                          item_name: str,
                          predictions: List[Dict],
                          current_price: float,
                          trend_data: Dict) -> str:
        """Đưa ra lời khuyên về giao dịch"""
        if not predictions:
            return "⚠️ Chưa đủ dữ liệu để đưa ra lời khuyên"
            
        advice = []
        
        # Phân tích xu hướng
        if trend_data['direction'] == "tăng":
            if trend_data['strength'] == "mạnh":
                advice.append("📈 Xu hướng tăng mạnh, có thể cân nhắc mua vào")
            else:
                advice.append("📈 Xu hướng tăng nhẹ, theo dõi thêm")
        elif trend_data['direction'] == "giảm":
            if trend_data['strength'] == "mạnh":
                advice.append("📉 Xu hướng giảm mạnh, nên chờ giá ổn định")
            else:
                advice.append("📉 Xu hướng giảm nhẹ, có thể chờ cơ hội mua vào")
                
        # So sánh với giá hiện tại
        avg_predicted = trend_data['avg_predicted']
        if current_price < avg_predicted * 0.9:
            advice.append("💰 Giá hiện tại thấp hơn dự đoán, có thể là cơ hội mua vào")
        elif current_price > avg_predicted * 1.1:
            advice.append("💰 Giá hiện tại cao hơn dự đoán, cân nhắc đợi giá giảm")
            
        # Phân tích độ biến động
        if trend_data['volatility'] > 0.2:
            advice.append("⚠️ Giá có độ biến động cao, giao dịch cần thận trọng")
        else:
            advice.append("✅ Giá tương đối ổn định")
            
        # Đánh giá độ tin cậy
        if trend_data['confidence'] < 0.7:
            advice.append("⚠️ Độ tin cậy dự đoán thấp, nên theo dõi thêm")
            
        return "\n".join(advice)
