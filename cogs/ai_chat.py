import discord
from discord import app_commands
from discord.ext import commands
from core.ai_handler import BotAI
from core.data_collector import DataCollector
from core.web_collector import WebDataCollector
from core.price_tracker import PriceTracker
from core.price_predictor import PricePredictor
from datetime import datetime
import matplotlib.pyplot as plt
import io
import aiohttp
import numpy as np
import asyncio
import json
import os

class AIChatCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ai = BotAI()
        self.collector = DataCollector()  # Khởi tạo data collector
        self.web_collector = WebDataCollector()  # Khởi tạo web collector
        self.price_tracker = PriceTracker(bot)  # Khởi tạo price tracker
        self.price_predictor = PricePredictor()  # Khởi tạo price predictor
        self.chat_channels = set()  # Lưu trữ ID các kênh chat được kích hoạt
        
        # Start web data collection task
        self.bot.loop.create_task(self.web_collector.schedule_collection(interval_hours=12))
        # Start price update task
        self.bot.loop.create_task(self._price_update_task())
        
        # Patterns chào hỏi
        self.ai.add_pattern("xin chào", [
            "Xin chào! Tôi có thể giúp gì cho bạn? 😊",
            "Chào bạn! Rất vui được gặp bạn 👋",
            "Xin chào! Chúc bạn một ngày tốt lành! ✨"
        ])
        
        self.ai.add_pattern("chào", [
            "Chào bạn! 👋",
            "Hey! Bạn khỏe không? 😊",
            "Chào! Mình có thể giúp gì cho bạn? 🌟"
        ])
        
        self.ai.add_pattern("hi|hello|hey", [
            "Hi there! 👋",
            "Hello! How are you? 😊",
            "Hey! Mình có thể giúp gì không? ✨"
        ])
        
        # Patterns cảm ơn/tạm biệt
        self.ai.add_pattern("cảm ơn|thank", [
            "Không có gì! Rất vui được giúp bạn 😊",
            "Không có chi! Bạn cần gì cứ nói nhé 👋",
            "Rất vui khi có thể giúp được bạn! ❤️"
        ])
        
        self.ai.add_pattern("tạm biệt|bye|bai", [
            "Tạm biệt bạn! Hẹn gặp lại 👋",
            "Bye bye! Chúc bạn một ngày tốt lành 😊",
            "Hẹn gặp lại bạn sau nhé! 👋"
        ])
        
        # Patterns về đơn hàng
        self.ai.add_pattern("giá|báo giá|bao nhiêu", [
            "Để xem giá, bạn có thể dùng lệnh `/tinhgia` với các thông số sau:\n• Hình thức: SL/RP/Event/Modul\n• Loại (nếu có)\n• Số lượng\n\nVí dụ: `/tinhgia SL 1000000` 💰",
            "Bạn có thể kiểm tra giá bằng lệnh `/tinhgia`.\nGiá sẽ phụ thuộc vào hình thức và số lượng bạn cần 📊",
            "Mình có thể giúp bạn tính giá. Hãy cho mình biết:\n1. Hình thức (SL/RP/Event/Modul)\n2. Số lượng\nHoặc dùng lệnh `/tinhgia` nhé! 💫"
        ])
        
        self.ai.add_pattern("đặt đơn|order|mua", [
            "Để đặt đơn, bạn dùng lệnh `/donhang` nhé! Mình sẽ mở form để bạn điền thông tin chi tiết 📝",
            "Bạn có thể đặt đơn bằng cách sử dụng lệnh `/donhang`. Sau đó điền các thông tin cần thiết vào form nhé! ✍️",
            "Dùng `/donhang` để bắt đầu đặt đơn. Mình sẽ hướng dẫn bạn các bước tiếp theo 🌟"
        ])
        
        self.ai.add_pattern("trạng thái|tình trạng|kiểm tra", [
            "Để xem trạng thái đơn, bạn dùng lệnh `/trangthai` kèm mã đơn nhé! 🔍",
            "Bạn có thể kiểm tra trạng thái đơn bằng lệnh `/trangthai` và mã đơn của bạn 📋",
            "Dùng `/trangthai` + mã đơn để xem tình trạng đơn hàng hiện tại nhé! 🔎"
        ])
        
        # Patterns về thông tin bot
        self.ai.add_pattern("bạn là ai|là gì|giới thiệu", [
            "Mình là Cave Store Bot, một trợ lý ảo giúp quản lý đơn hàng và hỗ trợ khách hàng. Rất vui được phục vụ bạn! 🤖",
            "Xin chào! Mình là bot hỗ trợ của Cave Store. Mình có thể giúp bạn đặt đơn, kiểm tra giá và nhiều thứ khác nữa! ✨",
            "Mình là AI assistant của Cave Store, được tạo ra để hỗ trợ bạn 24/7. Bạn cần giúp đỡ gì nào? 🌟"
        ])
        
        self.ai.add_pattern("help|giúp|hướng dẫn", [
            "Mình có thể giúp bạn với các việc sau:\n• `/donhang` - Đặt đơn mới\n• `/trangthai` - Kiểm tra đơn\n• `/tinhgia` - Xem báo giá\n• `/help` - Xem hướng dẫn đầy đủ\nBạn cần mình giúp gì nào? 📚",
            "Để xem hướng dẫn đầy đủ, bạn dùng lệnh `/help` nhé! Mình sẽ hiển thị danh sách các lệnh và cách sử dụng 📖",
            "Bạn có thể xem danh sách lệnh và hướng dẫn bằng `/help`. Hoặc cứ chat với mình, mình sẽ cố gắng giúp bạn! 💫"
        ])
        
        # Patterns về vấn đề/khiếu nại
        self.ai.add_pattern("lỗi|sai|vấn đề|khiếu nại", [
            "Rất tiếc về vấn đề bạn gặp phải 😔 Bạn có thể liên hệ admin để được hỗ trợ trực tiếp nhé!",
            "Mình xin lỗi vì sự bất tiện này 😥 Để được hỗ trợ tốt nhất, bạn hãy liên hệ admin hoặc mod nhé!",
            "Cảm ơn bạn đã phản hồi! Mình sẽ chuyển thông tin này đến admin để được hỗ trợ sớm nhất 🔔"
        ])
        
        # Patterns về thời gian/deadline
        self.ai.add_pattern("thời hạn|bao lâu|khi nào", [
            "Thời gian xử lý sẽ phụ thuộc vào loại đơn và số lượng. Bạn có thể xem deadline cụ thể trong `/trangthai` của đơn hàng ⏰",
            "Mỗi đơn sẽ có thời hạn riêng, được thông báo sau khi đơn được duyệt. Bạn có thể theo dõi qua lệnh `/trangthai` 📅",
            "Thời gian hoàn thành sẽ được cập nhật khi đơn được xác nhận. Bạn sẽ nhận được thông báo về deadline cụ thể 🕒"
        ])
        
        # Patterns tương tác vui vẻ
        self.ai.add_pattern("haha|hihi|=))|😄|😂|🤣", [
            "Vui quá ha! 😄",
            "Hehe, vui thật! 😊",
            "Cười lây với bạn nè 😆"
        ])
        
        self.ai.add_pattern("buồn|huhu|sad|:(", [
            "Đừng buồn nha bạn ơi! Mọi chuyện rồi sẽ ổn thôi 🌟",
            "Buồn gì vậy bạn? Kể mình nghe được không? 🤗",
            "Mình ở đây lắng nghe bạn nè! Cần người tâm sự không? 💕"
        ])

        # Patterns về thanh toán và giá cả chi tiết
        self.ai.add_pattern("thanh toán|payment|chuyển khoản", [
            "Để thanh toán, bạn có thể chuyển khoản vào tài khoản sau khi đơn được duyệt. Admin sẽ gửi thông tin chi tiết cho bạn 💳",
            "Thông tin thanh toán sẽ được gửi sau khi đơn được xác nhận. Bạn sẽ nhận được hướng dẫn cụ thể qua DM 🏦",
            "Vui lòng chờ admin duyệt đơn và gửi thông tin thanh toán nhé! Mọi giao dịch đều được bảo đảm an toàn 🔒"
        ])

        # Patterns về cách tính giá chi tiết
        self.ai.add_pattern("sl là gì|silver lions", [
            "SL (Silver Lions) là đơn vị tiền tệ trong game. Tỷ lệ quy đổi là 1 triệu SL = 100.000 VNĐ 💰",
            "Silver Lions (SL) dùng để mua xe, nâng cấp trong game. Giá: 1M SL = 100k VNĐ 🦁",
            "SL là Silver Lions - tiền trong game. Bạn có thể dùng /tinhgia SL [số lượng] để xem giá cụ thể 📊"
        ])

        self.ai.add_pattern("rp là gì|research points", [
            "RP (Research Points) dùng để nghiên cứu xe mới. Giá premium: 100k RP = 120k VNĐ, thường: 100k RP = 140k VNĐ 🔬",
            "Research Points (RP) là điểm nghiên cứu, dùng để mở khóa xe mới. Dùng /tinhgia RP [số lượng] để xem giá 📈",
            "RP dùng để nghiên cứu. Có 2 loại:\n• Premium: 120k VNĐ/100k RP\n• Thường: 140k VNĐ/100k RP\nDùng /tinhgia để xem chi tiết 🎯"
        ])

        # Patterns về hướng dẫn chi tiết
        self.ai.add_pattern("premium|ưu đãi", [
            "Premium RP sẽ có giá tốt hơn (120k/100k RP) so với thường (140k/100k RP). Bạn có thể dùng /tinhgia để so sánh 💎",
            "Khi đặt đơn RP, bạn có thể chọn Premium để được giá ưu đãi hơn. Dùng /tinhgia RP [số lượng] premium yes để xem chi tiết ⭐",
            "Premium là gói ưu đãi cho RP với giá tốt hơn 20k/100k RP. Liên hệ admin để biết thêm chi tiết về các ưu đãi khác 🌟"
        ])

        # Patterns về thời gian xử lý
        self.ai.add_pattern("nhanh|gấp|urgent", [
            "Đơn hàng sẽ được xử lý theo thứ tự. Nếu gấp, hãy ghi chú trong đơn để được ưu tiên xử lý sớm ⚡",
            "Thông thường đơn được xử lý trong 24h. Nếu cần gấp, vui lòng thêm ghi chú khi đặt đơn nhé! 🏃",
            "Để được xử lý nhanh hơn, bạn có thể:\n1. Thêm ghi chú 'urgent' trong đơn\n2. Liên hệ admin trực tiếp\n3. Đảm bảo thanh toán nhanh chóng ⚡"
        ])

        # Patterns về bảo hành và hỗ trợ
        self.ai.add_pattern("bảo hành|đảm bảo|an toàn", [
            "Mọi đơn hàng đều được bảo đảm hoàn thành đúng yêu cầu. Nếu có vấn đề, bạn sẽ được hỗ trợ ngay lập tức 🛡️",
            "Chúng mình cam kết:\n• Hoàn thành đúng yêu cầu\n• Bảo mật thông tin\n• Hỗ trợ 24/7\n• Hoàn tiền nếu không hài lòng ✅",
            "An toàn là ưu tiên hàng đầu. Mọi giao dịch đều được bảo đảm và có admin hỗ trợ trực tiếp 🔒"
        ])

        # Patterns về các trường hợp đặc biệt
        self.ai.add_pattern("hủy đơn|cancel|hoàn tiền", [
            "Để hủy đơn, bạn có thể:\n1. Dùng lệnh /huydon + mã đơn (nếu chưa duyệt)\n2. Liên hệ admin (nếu đã duyệt)\nHoàn tiền trong vòng 24h 💯",
            "Bạn có thể hủy đơn chưa duyệt bằng /huydon. Nếu đã duyệt, hãy liên hệ admin để được hỗ trợ ↩️",
            "Quy trình hủy đơn và hoàn tiền:\n1. Gửi yêu cầu hủy\n2. Xác nhận với admin\n3. Nhận lại tiền trong 24h\nDùng /huydon hoặc liên hệ admin nhé! 🔄"
        ])

        # Patterns cho các câu hỏi về server Discord
        self.ai.add_pattern("server|discord|invite", [
            "Bạn có thể tham gia server chính của Cave Store để được hỗ trợ tốt nhất và nhận các thông báo mới nhất! 🌐",
            "Server Discord chính thức có nhiều ưu đãi và thông tin hữu ích. Hãy liên hệ admin để nhận invite link nhé! 🎮",
            "Tham gia server để:\n• Nhận thông báo mới nhất\n• Tương tác với cộng đồng\n• Được hỗ trợ trực tiếp\n• Nhận các ưu đãi đặc biệt 🌟"
        ])

        # Patterns về vấn đề upload file
        self.ai.add_pattern("upload|fps.ms|file|lỗi upload", [
            "Khi gặp lỗi upload lên fps.ms, bạn có thể thử các cách sau:\n1. Kiểm tra kích thước file (tối đa 500MB)\n2. Đổi tên file (chỉ dùng chữ và số)\n3. Nén file trước khi upload\n4. Dùng link Google Drive thay thế 📁",
            "Để upload file thành công:\n• Đảm bảo file không quá 500MB\n• Tên file không có ký tự đặc biệt\n• Thử nén file (.zip hoặc .rar)\n• Hoặc dùng Google Drive/Mega để chia sẻ 🔄",
            "Tips để fix lỗi upload:\n1. Xóa ký tự đặc biệt trong tên file\n2. Nén file để giảm dung lượng\n3. Kiểm tra kết nối mạng\n4. Thử lại sau vài phút\nNếu vẫn lỗi, bạn có thể dùng Google Drive và gửi link 🛠️"
        ])

        # Pattern về các dịch vụ chia sẻ file thay thế
        self.ai.add_pattern("file lớn|chia sẻ|drive|mega", [
            "Với file lớn, bạn có thể dùng:\n1. Google Drive\n2. Mega.nz\n3. MediaFire\nSau đó gửi link chia sẻ cho admin nhé! 📤",
            "Các cách chia sẻ file thay thế:\n• Google Drive (15GB miễn phí)\n• Mega.nz (20GB miễn phí)\n• MediaFire (10GB miễn phí)\nChọn dịch vụ phù hợp và gửi link công khai nhé! 💾",
            "Tips chia sẻ file:\n1. Upload lên Google Drive\n2. Tạo link chia sẻ công khai\n3. Gửi link cho admin\n4. Đảm bảo không xóa file đến khi hoàn tất đơn 📋"
        ])

    @commands.Cog.listener()
    async def on_message(self, message):
        # Bỏ qua tin nhắn từ bot
        if message.author.bot:
            return
            
        # Thu thập dữ liệu từ tất cả tin nhắn (không chỉ trong chat channels)
        self.collector.collect_message(message)
            
        # Chỉ phản hồi trong kênh được kích hoạt hoặc khi được mention
        if (message.channel.id not in self.chat_channels and 
            self.bot.user not in message.mentions):
            return
            
        # Xóa mention khỏi nội dung tin nhắn
        content = message.content
        for mention in message.mentions:
            content = content.replace(f'<@{mention.id}>', '').replace(f'<@!{mention.id}>', '')
        content = content.strip()
        
        if not content:  # Nếu tin nhắn chỉ có mention
            return
            
        # Bắt đầu typing để tạo cảm giác tự nhiên
        async with message.channel.typing():
            # Thu thập context
            context = {
                "user_id": str(message.author.id),
                "guild_id": str(message.guild.id) if message.guild else None,
                "channel_id": str(message.channel.id),
                "timestamp": datetime.now().isoformat()
            }
            
            # Lấy câu trả lời từ AI
            response, confidence = self.ai.find_best_response(content, context)
            
            # Đợi một chút để tạo cảm giác tự nhiên
            await asyncio.sleep(1.5)
            
            # Gửi response
            sent_msg = await message.reply(response)
            
            # Thêm reaction để người dùng có thể đánh giá
            await sent_msg.add_reaction('👍')
            await sent_msg.add_reaction('👎')
            
            # Theo dõi reaction để học
            def check(reaction, user):
                return (user == message.author and 
                       reaction.message.id == sent_msg.id and
                       str(reaction.emoji) in ['👍', '👎'])
                       
            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
                if str(reaction.emoji) == '👍':
                    self.ai.learn(content, response, context)
                    await sent_msg.add_reaction('📝')
            except:
                pass

    @app_commands.command(name="chat", description="💭 Trò chuyện với bot")
    @app_commands.describe(noi_dung="Nội dung bạn muốn nói với bot")
    async def chat(self, interaction: discord.Interaction, noi_dung: str):
        await interaction.response.defer()
        
        # Thu thập context
        context = {
            "user_id": str(interaction.user.id),
            "guild_id": str(interaction.guild.id) if interaction.guild else None,
            "channel_id": str(interaction.channel.id),
            "timestamp": datetime.now().isoformat()
        }
        
        # Lấy câu trả lời từ AI
        response, confidence = self.ai.find_best_response(noi_dung, context)
        
        # Tạo embed response
        embed = discord.Embed(
            title="🤖 Cave Store AI",
            description=response,
            color=0x3498db if confidence >= 0.5 else 0xe74c3c
        )
        embed.set_footer(text=f"Độ tin cậy: {confidence*100:.1f}%")
        
        # Gửi response
        await interaction.followup.send(embed=embed)
        
        # Nếu người dùng phản hồi, bot sẽ học
        def check(m):
            return (m.author == interaction.user and 
                   m.channel == interaction.channel and
                   m.reference and m.reference.message_id == interaction.message.id)
                   
        try:
            reply_msg = await self.bot.wait_for('message', timeout=60.0, check=check)
            if reply_msg.content.startswith(('👍', '✅', 'đúng', 'chính xác')):
                self.ai.learn(noi_dung, response, context)
                await reply_msg.add_reaction('📝')
            elif reply_msg.content.startswith(('👎', '❌', 'sai')):
                correct_response = reply_msg.content.replace('👎', '').replace('❌', '').replace('sai', '').strip()
                if correct_response:
                    self.ai.learn(noi_dung, correct_response, context)
                    await reply_msg.add_reaction('📚')
        except:
            pass

    def save_chat_channels(self):
        """Lưu danh sách kênh chat được kích hoạt"""
        data_dir = "data"
        os.makedirs(data_dir, exist_ok=True)
        with open(os.path.join(data_dir, "chat_channels.json"), "w") as f:
            json.dump(list(self.chat_channels), f)

    def load_chat_channels(self):
        """Tải danh sách kênh chat được kích hoạt"""
        try:
            with open("data/chat_channels.json", "r") as f:
                self.chat_channels = set(json.load(f))
        except:
            self.chat_channels = set()

    @app_commands.command(name="batai", description="🤖 Bật chế độ chat với AI trong kênh này")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_channels=True)
    async def enable_ai(self, interaction: discord.Interaction):
        """Bật chế độ chat với AI trong kênh hiện tại"""
        channel_id = interaction.channel.id
        if channel_id in self.chat_channels:
            await interaction.response.send_message("❌ AI đã được bật trong kênh này rồi!", ephemeral=True)
            return
            
        self.chat_channels.add(channel_id)
        self.save_chat_channels()
        
        embed = discord.Embed(
            title="🤖 AI Chat đã được kích hoạt!",
            description="Bot sẽ tự động trả lời tin nhắn trong kênh này.\n"
                       "• Nhắn tin bình thường để chat với bot\n"
                       "• React 👍 để bot học câu trả lời đúng\n"
                       "• React 👎 nếu câu trả lời chưa phù hợp\n"
                       "• Dùng `/tatai` để tắt chế độ chat",
            color=0x2ecc71
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="tatai", description="🔕 Tắt chế độ chat với AI trong kênh này")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_channels=True)
    async def disable_ai(self, interaction: discord.Interaction):
        """Tắt chế độ chat với AI trong kênh hiện tại"""
        channel_id = interaction.channel.id
        if channel_id not in self.chat_channels:
            await interaction.response.send_message("❌ AI chưa được bật trong kênh này!", ephemeral=True)
            return
            
        self.chat_channels.remove(channel_id)
        self.save_chat_channels()
        
        embed = discord.Embed(
            title="🔕 AI Chat đã được tắt",
            description="Bot sẽ không còn tự động trả lời tin nhắn trong kênh này.\n"
                       "Dùng `/batai` để bật lại chế độ chat.",
            color=0xe74c3c
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="news", description="📰 Xem tin tức mới nhất từ War Thunder")
    async def news(self, interaction: discord.Interaction):
        """Hiển thị tin tức mới nhất từ War Thunder"""
        await interaction.response.defer()
        
        news = self.web_collector.get_latest_news(5)
        if not news:
            await interaction.followup.send("❌ Hiện chưa có tin tức mới!", ephemeral=True)
            return
            
        embed = discord.Embed(
            title="📰 Tin tức War Thunder mới nhất",
            color=0x3498db
        )
        
        for item in news:
            embed.add_field(
                name=f"📌 {item['title']}",
                value=f"📅 {item['date']}\n{item['summary']}\n[Đọc thêm]({item['url']})",
                inline=False
            )
            
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="market", description="💰 Xem giá thị trường")
    @app_commands.describe(item="Tên item cần tìm")
    @app_commands.command(name="track", description="📈 Theo dõi giá của item")
    @app_commands.describe(
        item="Tên item cần theo dõi",
        min_price="Thông báo khi giá thấp hơn giá này",
        max_price="Thông báo khi giá cao hơn giá này"
    )
    async def track(
        self, 
        interaction: discord.Interaction, 
        item: str,
        min_price: float = None,
        max_price: float = None
    ):
        """Thêm item vào danh sách theo dõi giá"""
        await interaction.response.defer()
        
        # Kiểm tra xem item có tồn tại không
        results = self.web_collector.search_items(item)
        if not results:
            await interaction.followup.send(
                f"❌ Không tìm thấy thông tin về '{item}'!", 
                ephemeral=True
            )
            return
            
        # Lấy item đầu tiên tìm được
        found_item = results[0]
        
        # Thêm vào tracking
        self.price_tracker.add_tracking(
            found_item['name'],
            str(interaction.user.id),
            min_price,
            max_price
        )
        
        # Tạo embed thông báo
        embed = discord.Embed(
            title="📈 Đã thêm vào danh sách theo dõi",
            description=f"Item: {found_item['name']}",
            color=0x2ecc71
        )
        
        if min_price:
            embed.add_field(
                name="⬇️ Ngưỡng giá thấp",
                value=f"{min_price:,.2f}",
                inline=True
            )
            
        if max_price:
            embed.add_field(
                name="⬆️ Ngưỡng giá cao",
                value=f"{max_price:,.2f}",
                inline=True
            )
            
        current_price = (
            found_item['data']['price'] 
            if found_item['type'] == 'market_item' 
            else None
        )
        if current_price:
            embed.add_field(
                name="💰 Giá hiện tại",
                value=f"{current_price:,.2f}",
                inline=True
            )
            
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="untrack", description="🚫 Dừng theo dõi giá của item")
    @app_commands.describe(item="Tên item muốn dừng theo dõi")
    async def untrack(self, interaction: discord.Interaction, item: str):
        """Xóa item khỏi danh sách theo dõi"""
        self.price_tracker.remove_tracking(item, str(interaction.user.id))
        
        embed = discord.Embed(
            title="🚫 Đã dừng theo dõi",
            description=f"Đã xóa '{item}' khỏi danh sách theo dõi của bạn.",
            color=0xe74c3c
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="tracking", description="📋 Xem danh sách items đang theo dõi")
    async def tracking(self, interaction: discord.Interaction):
        """Hiển thị danh sách items đang theo dõi"""
        items = self.price_tracker.get_tracked_items(str(interaction.user.id))
        
        if not items:
            await interaction.response.send_message(
                "❌ Bạn chưa theo dõi item nào!", 
                ephemeral=True
            )
            return
            
        embed = discord.Embed(
            title="📋 Items đang theo dõi",
            color=0x3498db
        )
        
        for item in items:
            tracked_data = self.price_tracker.data['tracked_items'][item]
            user_alerts = self.price_tracker.data['user_alerts'][str(interaction.user.id)]
            
            value = []
            if tracked_data['price']:
                value.append(f"💰 Giá: {tracked_data['price']:,.2f}")
            if item in user_alerts['min_price']:
                value.append(f"⬇️ Alert: {user_alerts['min_price'][item]:,.2f}")
            if item in user_alerts['max_price']:
                value.append(f"⬆️ Alert: {user_alerts['max_price'][item]:,.2f}")
                
            embed.add_field(
                name=item,
                value="\n".join(value) or "Chưa có dữ liệu",
                inline=False
            )
            
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="price_history", description="📊 Xem lịch sử giá của item")
    @app_commands.describe(item="Tên item cần xem lịch sử")
    @app_commands.command(name="predict", description="🔮 Dự đoán giá trong tương lai")
    @app_commands.describe(
        item="Tên item cần dự đoán",
        days="Số ngày dự đoán (mặc định: 7)"
    )
    async def predict(self, interaction: discord.Interaction, item: str, days: int = 7):
        """Dự đoán giá trong tương lai"""
        await interaction.response.defer()
        
        # Kiểm tra item
        results = self.web_collector.search_items(item)
        if not results:
            await interaction.followup.send(
                f"❌ Không tìm thấy thông tin về '{item}'!",
                ephemeral=True
            )
            return
            
        found_item = results[0]
        item_name = found_item['name']
        
        # Lấy dữ liệu lịch sử
        history = self.price_tracker.get_price_history(item_name)
        if not history:
            await interaction.followup.send(
                f"❌ Chưa có đủ dữ liệu lịch sử cho '{item_name}'!",
                ephemeral=True
            )
            return
            
        # Lấy dữ liệu vehicle và events
        vehicle_data = self.web_collector.data['vehicles'].get(item_name)
        game_events = self.web_collector.data.get('news', [])
        
        # Dự đoán giá
        predictions = self.price_predictor.predict_price(
            item_name,
            history,
            vehicle_data,
            game_events,
            days
        )
        
        if not predictions:
            await interaction.followup.send(
                "❌ Không thể dự đoán giá! Vui lòng thử lại sau.",
                ephemeral=True
            )
            return
            
        # Phân tích xu hướng
        trend_data = self.price_predictor.get_price_trends(item_name, predictions)
        
        # Phân tích các yếu tố thị trường
        market_factors = self.price_predictor.analyze_market_factors(
            item_name,
            vehicle_data,
            game_events
        )
        
        # Lấy lời khuyên giao dịch
        current_price = history[-1]['price'] if history else None
        trading_advice = self.price_predictor.get_trading_advice(
            item_name,
            predictions,
            current_price,
            trend_data
        )
        
        # Vẽ biểu đồ
        plt.figure(figsize=(12, 6))
        
        # Vẽ dữ liệu lịch sử
        history_dates = [datetime.fromisoformat(h['timestamp']) for h in history]
        history_prices = [h['price'] for h in history]
        plt.plot(history_dates, history_prices, 'b-', label='Lịch sử', alpha=0.7)
        
        # Vẽ dự đoán
        pred_dates = [datetime.fromisoformat(p['timestamp']) for p in predictions]
        pred_prices = [p['price'] for p in predictions]
        pred_lower = [p['lower_bound'] for p in predictions]
        pred_upper = [p['upper_bound'] for p in predictions]
        
        plt.plot(pred_dates, pred_prices, 'r--', label='Dự đoán')
        plt.fill_between(pred_dates, pred_lower, pred_upper, color='r', alpha=0.2)
        
        plt.title(f'Dự đoán giá: {item_name}')
        plt.xlabel('Thời gian')
        plt.ylabel('Giá')
        plt.xticks(rotation=45)
        plt.grid(True)
        plt.legend()
        
        # Lưu biểu đồ
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        plt.close()
        
        # Tạo file discord
        chart_file = discord.File(buf, filename='prediction.png')
        
        # Tạo embed
        embed = discord.Embed(
            title=f"🔮 Dự đoán giá: {item_name}",
            color=0x9b59b6
        )
        embed.set_image(url="attachment://prediction.png")
        
        # Thêm thông tin xu hướng
        embed.add_field(
            name="📈 Xu hướng",
            value=(
                f"• Hướng: {trend_data['direction']}\n"
                f"• Mức độ: {trend_data['strength']}\n"
                f"• Độ biến động: {trend_data['volatility']:.2%}\n"
                f"• Độ tin cậy: {trend_data['confidence']:.2%}"
            ),
            inline=False
        )
        
        # Thêm dự đoán giá
        embed.add_field(
            name="💰 Dự đoán giá",
            value=(
                f"• Thấp nhất: {trend_data['min_predicted']:,.2f}\n"
                f"• Cao nhất: {trend_data['max_predicted']:,.2f}\n"
                f"• Trung bình: {trend_data['avg_predicted']:,.2f}"
            ),
            inline=False
        )
        
        # Thêm các yếu tố thị trường
        if market_factors:
            embed.add_field(
                name="📊 Yếu tố thị trường",
                value="\n".join(market_factors),
                inline=False
            )
            
        # Thêm lời khuyên
        embed.add_field(
            name="💡 Lời khuyên",
            value=trading_advice,
            inline=False
        )
        
        await interaction.followup.send(embed=embed, file=chart_file)

    async def price_history(self, interaction: discord.Interaction, item: str):
        """Hiển thị lịch sử giá của item"""
        await interaction.response.defer()
        
        history = self.price_tracker.get_price_history(item)
        if not history:
            await interaction.followup.send(
                f"❌ Không có dữ liệu lịch sử giá cho '{item}'!",
                ephemeral=True
            )
            return
            
        # Tạo biểu đồ
        plt.figure(figsize=(10, 6))
        prices = [entry['price'] for entry in history]
        times = [datetime.fromisoformat(entry['timestamp']) for entry in history]
        
        plt.plot(times, prices, marker='o')
        plt.title(f'Lịch sử giá: {item}')
        plt.xlabel('Thời gian')
        plt.ylabel('Giá')
        plt.xticks(rotation=45)
        plt.grid(True)
        
        # Lưu biểu đồ vào buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        plt.close()
        
        # Tạo file discord
        chart_file = discord.File(buf, filename='price_history.png')
        
        # Tạo embed
        embed = discord.Embed(
            title=f"📊 Lịch sử giá: {item}",
            color=0x3498db
        )
        embed.set_image(url="attachment://price_history.png")
        
        # Thêm thống kê
        prices = [entry['price'] for entry in history]
        embed.add_field(
            name="📈 Thống kê",
            value=(
                f"• Cao nhất: {max(prices):,.2f}\n"
                f"• Thấp nhất: {min(prices):,.2f}\n"
                f"• Trung bình: {sum(prices)/len(prices):,.2f}\n"
                f"• Số điểm dữ liệu: {len(prices)}"
            ),
            inline=False
        )
        
        await interaction.followup.send(embed=embed, file=chart_file)

    @app_commands.command(name="setalerts", description="⚙️ Thiết lập kênh nhận thông báo")
    @app_commands.default_permissions(manage_channels=True)
    async def setalerts(self, interaction: discord.Interaction):
        """Thiết lập kênh hiện tại làm kênh nhận thông báo về giá"""
        self.price_tracker.set_alert_channel(
            str(interaction.guild_id),
            str(interaction.channel_id)
        )
        
        embed = discord.Embed(
            title="⚙️ Đã thiết lập kênh thông báo",
            description="Kênh này sẽ nhận các thông báo về thay đổi giá.",
            color=0x2ecc71
        )
        await interaction.response.send_message(embed=embed)

    async def _price_update_task(self):
        """Task cập nhật giá và gửi thông báo"""
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                # Lấy dữ liệu market mới
                async with aiohttp.ClientSession() as session:
                    await self.web_collector.collect_market_data(session)
                
                # Cập nhật giá cho các items đang theo dõi
                market_data = self.web_collector.data['market_prices']
                for item_name, data in market_data.items():
                    if item_name in self.price_tracker.get_tracked_items():
                        alerts = self.price_tracker.update_price(
                            item_name,
                            data['price']
                        )
                        
                        # Gửi thông báo nếu có
                        for alert in alerts:
                            for guild_id in self.bot.guilds:
                                await self.price_tracker.send_alert(
                                    str(guild_id),
                                    item_name,
                                    alert
                                )
                                
            except Exception as e:
                print(f"Error in price update task: {str(e)}")
                
            await asyncio.sleep(300)  # Cập nhật mỗi 5 phút

    async def market(self, interaction: discord.Interaction, item: str):
        """Tìm kiếm và hiển thị giá thị trường của items"""
        await interaction.response.defer()
        
        results = self.web_collector.search_items(item)
        if not results:
            await interaction.followup.send(f"❌ Không tìm thấy thông tin về '{item}'!", ephemeral=True)
            return
            
        embed = discord.Embed(
            title=f"🔍 Kết quả tìm kiếm cho '{item}'",
            color=0x2ecc71
        )
        
        for result in results[:5]:  # Giới hạn 5 kết quả
            if result['type'] == 'vehicle':
                data = result['data']
                embed.add_field(
                    name=f"🚀 {result['name']}",
                    value=(
                        f"• BR: {data['br_rating']}\n"
                        f"• Repair cost: {data['repair_cost']:,} SL\n"
                        f"• Số modifications: {len(data['modifications'])}"
                    ),
                    inline=False
                )
            elif result['type'] == 'market_item':
                data = result['data']
                embed.add_field(
                    name=f"📦 {result['name']}",
                    value=f"Giá: {data['price']} {data['currency']}",
                    inline=False
                )
                
        embed.set_footer(text="Cập nhật lần cuối: " + 
                        datetime.fromisoformat(self.web_collector.get_stats()['last_update'])
                        .strftime('%d/%m/%Y %H:%M:%S'))
                        
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="aistats", description="📊 Xem thống kê AI")
    @app_commands.guild_only()
    async def aistats(self, interaction: discord.Interaction):
        ai_stats = self.ai.get_stats()
        collector_stats = self.collector.get_stats()
        
        embed = discord.Embed(
            title="📊 Thống kê Hệ thống AI",
            description="Thông tin về dữ liệu và hoạt động của AI",
            color=0x3498db
        )
        
        # AI Stats
        embed.add_field(
            name="🤖 Thống kê AI",
            value=(
                f"• Tương tác: `{ai_stats['total_interactions']}`\n"
                f"• Patterns: `{ai_stats['total_patterns']}`\n"
                f"• Từ khóa: `{ai_stats['unique_keywords']}`\n"
                f"• Kênh chat: `{len(self.chat_channels)}`"
            ),
            inline=False
        )
        
        # Collector Stats
        embed.add_field(
            name="� Dữ liệu đã thu thập",
            value=(
                f"• Tin nhắn: `{collector_stats['total_messages']}`\n"
                f"• Cuộc hội thoại: `{collector_stats['total_conversations']}`\n"
                f"• Cặp Q&A: `{collector_stats['total_qa_pairs']}`"
            ),
            inline=False
        )
        
        # Last Update Info
        if ai_stats['last_interaction']:
            ai_last = datetime.fromisoformat(ai_stats['last_interaction'])
            collector_last = datetime.fromisoformat(collector_stats['last_update']) if collector_stats['last_update'] else None
            
            embed.add_field(
                name="⏰ Cập nhật gần nhất",
            value=(
                f"• AI: `{ai_last.strftime('%d/%m/%Y %H:%M:%S')}`\n"
                f"• Collector: `{collector_last.strftime('%d/%m/%Y %H:%M:%S') if collector_last else 'N/A'}`"
            ),
            inline=False
        )
        
        # Web Data Stats
        web_stats = self.web_collector.get_stats()
        embed.add_field(
            name="🌐 Dữ liệu Web",
            value=(
                f"• Phương tiện: `{web_stats['total_vehicles']}`\n"
                f"• Items thị trường: `{web_stats['total_market_items']}`\n"
                f"• Tin tức: `{web_stats['total_news']}`\n"
                f"• Cập nhật: `{datetime.fromisoformat(web_stats['last_update']).strftime('%d/%m/%Y %H:%M:%S') if web_stats['last_update'] else 'N/A'}`"
            ),
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    cog = AIChatCommands(bot)
    cog.load_chat_channels()  # Load danh sách kênh chat khi khởi động
    await bot.add_cog(cog)
    print("[SETUP] AIChatCommands loaded successfully")
