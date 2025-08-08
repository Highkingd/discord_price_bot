from datetime import datetime, timezone, timedelta
import pytz

def convert_to_local_time(utc_time: datetime, timezone_str: str = 'Asia/Ho_Chi_Minh') -> tuple[datetime, str]:
    """Chuyển đổi thời gian UTC sang múi giờ địa phương"""
    try:
        local_tz = pytz.timezone(timezone_str)
        local_time = utc_time.replace(tzinfo=timezone.utc).astimezone(local_tz)
        tz_name = local_time.tzname()
        return local_time, tz_name
    except Exception:
        return utc_time, 'UTC'

def format_time_remaining(deadline: datetime) -> str:
    """Tính và định dạng thời gian còn lại"""
    now = datetime.now(timezone.utc)
    if not deadline.tzinfo:
        deadline = deadline.replace(tzinfo=timezone.utc)
    
    remaining = deadline - now
    
    if remaining.total_seconds() <= 0:
        return "Đã hết hạn"
    
    days = remaining.days
    hours = remaining.seconds // 3600
    minutes = (remaining.seconds % 3600) // 60
    
    parts = []
    if days > 0:
        parts.append(f"{days} ngày")
    if hours > 0:
        parts.append(f"{hours} giờ")
    if minutes > 0:
        parts.append(f"{minutes} phút")
        
    return "Còn " + " ".join(parts)

def format_deadline(hours: int) -> tuple[datetime, str]:
    """Tạo thời hạn từ số giờ"""
    deadline = datetime.now(timezone.utc) + timedelta(hours=hours)
    return deadline, deadline.strftime("%Y-%m-%d %H:%M:%S UTC")
