

import os
import sys
import functools
from typing import Callable, List, Union
from datetime import datetime
import pytz
from datetime import datetime, timezone, timedelta

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

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

import discord
from discord.ext import commands
from discord import app_commands
from core.config import load_config
from core.logger import log
from core.orders import orders, save_orders, generate_order_id

def requires_role(roles: Union[str, List[str]]):
    """Decorator để kiểm tra role cho slash commands"""
    if isinstance(roles, str):
        roles = [roles]
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
            member = interaction.user
            if not any(self.bot.has_role(member, role) for role in roles):
                role_names = ", ".join(roles)
                await interaction.response.send_message(
                    f"❌ Bạn cần role {role_names} để sử dụng lệnh này.",
                    ephemeral=True
                )
                return
            return await func(self, interaction, *args, **kwargs)
        return wrapper
    return decorator

import discord
from discord.ext import commands
import json
import logging
from datetime import datetime
from core.smart_response import SmartResponseGenerator

# Load config
with open('config.json', 'r') as f:
    config = json.load(f)

# Setup logging
logging.basicConfig(
    filename='log.txt',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Initialize smart response generator
response_generator = SmartResponseGenerator()

# Các role ID
ROLES = {
    "ADMIN": [1345365308462071891],
    "MODERATOR": [1345678008073326592],
    "WORKER": [1345364282539376742]
}

# Set up intents
intents = discord.Intents.all()  # Enable all intents
intents.message_content = True
intents.members = True

class Bot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix='!',
            intents=intents
        )
        
        # Add smart response generator
        self.response_generator = response_generator
        
    def has_role(self, member: discord.Member, role_name: str) -> bool:
        """Kiểm tra xem thành viên có role không"""
        role_ids = self.roles.get(role_name, [])
        return any(role.id in role_ids for role in member.roles)

    def get_permission_level(self, member: discord.Member) -> str:
        """Lấy cấp độ quyền cao nhất của thành viên"""
        if self.has_role(member, "ADMIN"): return "ADMIN"
        if self.has_role(member, "MODERATOR"): return "MODERATOR"
        if self.has_role(member, "WORKER"): return "WORKER"
        return "ALL"

bot = CaveStoreBot()
print(">>> Đã tạo bot, chuẩn bị khởi động...")


@bot.event
async def on_ready():
    try:
        print(f"✅ Bot đã đăng nhập với tên: {bot.user.name}")
        print(f"✅ Bot ID: {bot.user.id}")
        print(f"✅ Server ID: {GUILD_ID}")
        
        # Print all servers the bot is in
        guilds = bot.guilds
        print(f"Bot đang ở trong {len(guilds)} server:")
        for guild in guilds:
            print(f"  - {guild.name} (ID: {guild.id})")
            # Thông báo cho server gốc về các server khác đang dùng bot
            if guild.id != GUILD_ID:
                home_guild = bot.get_guild(GUILD_ID)
                if home_guild:
                    embed = discord.Embed(
                        title="🌐 Server đang sử dụng bot",
                        description=f"Server: **{guild.name}**\nID: `{guild.id}`\nThành viên: {guild.member_count}",
                        color=0x00ff00
                    )
                    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
                    embed.add_field(name="Chủ server", value=f"{guild.owner.name} ({guild.owner.id})")
                    # Gửi thông báo vào kênh admin
                    admin_channel = home_guild.get_channel(int(config["ADMIN_CHANNEL_ID"]))
                    if admin_channel:
                        await admin_channel.send(embed=embed)
            
        # Print all registered commands
        commands = bot.tree.get_commands()
        print(f"Các lệnh đã đăng ký ({len(commands)}):")
        for cmd in commands:
            print(f"  /{cmd.name} - {cmd.description}")
            
    except Exception as e:
        print(f"❌ Lỗi khi khởi động bot: {e}")
        import traceback
        traceback.print_exc()
        return
        
    log("Bot đã sẵn sàng.")
    
    # Start order monitoring task
    try:
        from tasks.order_monitor import don_giam_sat
        bot.loop.create_task(don_giam_sat(bot))
        print("✅ Đã khởi động giám sát đơn hàng")
    except Exception as e:
        print(f"❌ Lỗi khi khởi động giám sát: {e}")






# Load cogs and sync commands
@bot.event
async def setup_hook():
    try:
        print("[Setup] Đang tải extensions...")
        
        # Load order commands
        await bot.load_extension("cogs.order_commands")
        print("[Setup] Đã tải order_commands thành công")
        
        # Load AI chat commands
        try:
            await bot.load_extension("cogs.ai_chat")
            print("[Setup] Đã tải ai_chat thành công")
        except Exception as e:
            print(f"[Setup] ❌ Lỗi khi tải ai_chat: {str(e)}")
        
        print("[Setup] Đang đồng bộ lệnh...")
        guild = discord.Object(id=GUILD_ID)
        
        # Clear and sync commands
        print("[Setup] Xóa lệnh cũ...")
        bot.tree.clear_commands(guild=guild)
        await bot.tree.sync(guild=None)  # Sync globally first
        
        print("[Setup] Đồng bộ lệnh mới...")
        commands = await bot.tree.sync(guild=guild)
        print(f"[Setup] Đã đồng bộ {len(commands)} lệnh cho server")
        
        # Show warning if no commands were synced
        if len(commands) == 0:
            print("⚠️ CẢNH BÁO: Không có lệnh nào được đồng bộ!")
            print("👉 Kiểm tra:")
            print("  1. Bot có quyền applications.commands")
            print("  2. GUILD_ID đúng")
            print("  3. Bot đã được mời với đủ scope")
            print("  4. Cogs đã được tải đúng")
            print("  5. Các intents đã được bật")
    except Exception as e:
        print(f"❌ Lỗi trong setup_hook: {e}")
        import traceback
        traceback.print_exc()

# Error handler for slash commands
@bot.tree.command(name="phanquyen", description="👑 Cập nhật quyền cho role (Admin)")
@app_commands.guild_only()
@requires_role("ADMIN")
@app_commands.describe(
    loai="Loại quyền (ADMIN/MODERATOR/WORKER)",
    role="Role Discord cần cấp quyền (ID hoặc @mention)",
    thao_tac="Thêm hoặc xóa role khỏi danh sách quyền"
)
async def update_role_permission(
    interaction: discord.Interaction,
    loai: str,
    role: discord.Role,
    thao_tac: str
):
    """Cập nhật quyền cho role"""
    try:
        # Kiểm tra loại quyền hợp lệ
        loai = loai.upper()
        if loai not in ROLES:
            return await interaction.response.send_message(
                "❌ Loại quyền không hợp lệ. Sử dụng: ADMIN, MODERATOR hoặc WORKER",
                ephemeral=True
            )

        # Kiểm tra thao tác hợp lệ
        thao_tac = thao_tac.lower()
        if thao_tac not in ["thêm", "them", "add", "xóa", "xoa", "remove"]:
            return await interaction.response.send_message(
                "❌ Thao tác không hợp lệ. Sử dụng: thêm/add hoặc xóa/remove",
                ephemeral=True
            )

        # Thực hiện thao tác
        is_add = thao_tac in ["thêm", "them", "add"]
        role_ids = ROLES[loai]

        if is_add:
            if role.id in role_ids:
                return await interaction.response.send_message(
                    f"❌ Role {role.name} đã có quyền {loai}",
                    ephemeral=True
                )
            role_ids.append(role.id)
            action_text = "thêm vào"
        else:
            if role.id not in role_ids:
                return await interaction.response.send_message(
                    f"❌ Role {role.name} không có quyền {loai}",
                    ephemeral=True
                )
            role_ids.remove(role.id)
            action_text = "xóa khỏi"

        # Cập nhật lại roles trong bot
        bot.roles = ROLES

        # Tạo embed thông báo
        embed = discord.Embed(
            title="👑 Cập nhật quyền",
            description=f"Đã {action_text} danh sách quyền",
            color=0x00ff00
        )
        embed.add_field(name="Role", value=f"{role.name} (`{role.id}`)", inline=True)
        embed.add_field(name="Quyền", value=loai, inline=True)
        embed.add_field(name="Thao tác", value=thao_tac, inline=True)
        embed.add_field(
            name="Danh sách role có quyền " + loai, 
            value="\n".join([f"<@&{rid}>" for rid in ROLES[loai]]) or "Không có",
            inline=False
        )

        await interaction.response.send_message(embed=embed)

    except Exception as e:
        await interaction.response.send_message(
            f"❌ Lỗi khi cập nhật quyền: {str(e)}",
            ephemeral=True
        )

@bot.tree.command(name="thongbao", description="📢 Gửi thông báo tới tất cả server (Admin)")
@app_commands.guild_only()
@requires_role("ADMIN")
@app_commands.describe(
    tieude="Tiêu đề thông báo",
    noidung="Nội dung thông báo",
    mau="Màu thông báo (default: blue, red, green, yellow)"
)
async def broadcast_command(
    interaction: discord.Interaction, 
    tieude: str,
    noidung: str,
    mau: str = "blue"
):
    """Gửi thông báo tới tất cả server đang sử dụng bot"""
    await interaction.response.defer(ephemeral=True)
    
    # Chuyển đổi màu
    colors = {
        "blue": 0x3498db,
        "red": 0xe74c3c,
        "green": 0x2ecc71,
        "yellow": 0xf1c40f
    }
    color = colors.get(mau.lower(), 0x3498db)
    
    # Tạo embed thông báo
    embed = discord.Embed(
        title=f"📢 {tieude}",
        description=noidung,
        color=color,
        timestamp=datetime.now()
    )
    embed.set_footer(text=f"Từ: {interaction.guild.name}")
    
    # Gửi thông báo tới tất cả server
    success = 0
    failed = 0
    
    for guild in bot.guilds:
        try:
            # Tìm kênh system hoặc general hoặc kênh đầu tiên có thể gửi
            channel = None
            for ch in guild.text_channels:
                if ch.permissions_for(guild.me).send_messages:
                    if "system" in ch.name.lower() or "thông-báo" in ch.name.lower():
                        channel = ch
                        break
            if not channel:
                for ch in guild.text_channels:
                    if ch.permissions_for(guild.me).send_messages:
                        if "general" in ch.name.lower() or "chung" in ch.name.lower():
                            channel = ch
                            break
            if not channel:
                for ch in guild.text_channels:
                    if ch.permissions_for(guild.me).send_messages:
                        channel = ch
                        break
                        
            if channel:
                await channel.send(embed=embed)
                success += 1
            else:
                failed += 1
                log(f"[THÔNG BÁO] Không thể gửi tới {guild.name} - Không tìm thấy kênh phù hợp")
        except Exception as e:
            failed += 1
            log(f"[THÔNG BÁO] Lỗi khi gửi tới {guild.name}: {str(e)}")
    
    # Báo cáo kết quả
    await interaction.followup.send(
        f"✅ Đã gửi thông báo tới {success} server\n"
        f"❌ Thất bại: {failed} server",
        ephemeral=True
    )

@bot.tree.command(name="help", description="📚 Hiển thị danh sách lệnh và hướng dẫn")
@app_commands.guild_only()
async def help_command(interaction: discord.Interaction):
    """Hiển thị danh sách lệnh và hướng dẫn sử dụng"""
    member = interaction.user
    permission_level = bot.get_permission_level(member)
    
    embed = discord.Embed(
        title="📚 Hướng dẫn sử dụng Cave Store Bot",
        description="Danh sách các lệnh có sẵn theo quyền của bạn:",
        color=0x00ff00
    )

    # Basic commands - everyone can use
    basic_cmds = """
`/donhang` - Mở form đặt đơn hàng mới
`/trangthai` - Xem trạng thái đơn hàng
`/huydon` - Huỷ đơn hàng của bạn (chỉ khi chưa duyệt)
`/tinhgia` - Tính giá trị đơn hàng
`/help` - Hiển thị hướng dẫn này
"""
    embed.add_field(name="🌟 Lệnh cơ bản", value=basic_cmds, inline=False)

    # Worker commands
    if permission_level in ["WORKER", "MODERATOR", "ADMIN"]:
        worker_cmds = """
`/nhancay` - Nhận đơn và chốt thời hạn
`/hoanthanh` - Đánh dấu đơn đã hoàn thành
`/suadon` - Chỉnh sửa ghi chú đơn
"""
        embed.add_field(name="💪 Lệnh cho Worker", value=worker_cmds, inline=False)

    # Moderator commands
    if permission_level in ["MODERATOR", "ADMIN"]:
        mod_cmds = """
`/duyetdon` - Duyệt đơn hàng
`/danhsachdon` - Xem danh sách đơn hàng
`/thongke` - Xem thống kê đơn hàng
`/giahan` - Gia hạn thời gian cho đơn
"""
        embed.add_field(name="🛡️ Lệnh cho Moderator", value=mod_cmds, inline=False)

    # Admin commands
    if permission_level == "ADMIN":
        admin_cmds = """
`/xoadon` - Xoá đơn hàng
`/thongbao` - Gửi thông báo tới tất cả server
`/phanquyen` - Cấp quyền cho role
"""
        embed.add_field(name="👑 Lệnh cho Admin", value=admin_cmds, inline=False)

    # Add current role info
    embed.add_field(
        name="🎭 Quyền của bạn", 
        value=f"Cấp độ quyền hiện tại: **{permission_level}**",
        inline=False
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(
            f"⏳ Vui lòng đợi {error.retry_after:.2f} giây nữa.",
            ephemeral=True
        )
    elif isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "⛔ Bạn không có quyền sử dụng lệnh này!",
            ephemeral=True
        )
    else:
        print(f"Lỗi khi thực thi lệnh: {str(error)}")
        await interaction.response.send_message(
            "❌ Đã xảy ra lỗi khi thực thi lệnh.",
            ephemeral=True
        )

@bot.event
async def on_guild_join(guild):
    """Event khi bot được thêm vào server mới"""
    log(f"[NEW SERVER] Bot được thêm vào {guild.name} (ID: {guild.id})")
    
    # Thông báo cho server gốc
    home_guild = bot.get_guild(GUILD_ID)
    if home_guild:
        embed = discord.Embed(
            title="✨ Bot được thêm vào server mới!",
            description=f"Server: **{guild.name}**\nID: `{guild.id}`\nThành viên: {guild.member_count}",
            color=0x00ff00,
            timestamp=datetime.now()
        )
        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        embed.add_field(name="Chủ server", value=f"{guild.owner.name} ({guild.owner.id})")
        
        # Gửi thông báo vào kênh admin
        admin_channel = home_guild.get_channel(int(config["ADMIN_CHANNEL_ID"]))
        if admin_channel:
            await admin_channel.send(embed=embed)

@bot.event
async def on_guild_remove(guild):
    """Event khi bot bị xóa khỏi server"""
    log(f"[LEAVE SERVER] Bot bị xóa khỏi {guild.name} (ID: {guild.id})")
    
    # Thông báo cho server gốc
    home_guild = bot.get_guild(GUILD_ID)
    if home_guild:
        embed = discord.Embed(
            title="❌ Bot bị xóa khỏi server",
            description=f"Server: **{guild.name}**\nID: `{guild.id}`",
            color=0xff0000,
            timestamp=datetime.now()
        )
        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        
        # Gửi thông báo vào kênh admin
        admin_channel = home_guild.get_channel(int(config["ADMIN_CHANNEL_ID"]))
        if admin_channel:
            await admin_channel.send(embed=embed)

print(">>> Bot đã sẵn sàng, đang khởi động...") 
bot.run(TOKEN)