

import os
import sys
import json
import logging
from datetime import datetime, timezone
import discord
from discord.ext import commands
from discord import app_commands
from core.config import load_config
from core.permissions import requires_role, ROLES

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Load config
config = load_config()
GUILD_ID = int(config.get("GUILD_ID", "0"))

# Set up logging
def log(message):
    print(message)
    logging.info(message)

import os
import sys
import json
import logging
from datetime import datetime
import time
import gc
import psutil
import discord
from discord.ext import commands
from core.ai_core import CaveStoreAI

# Simple bot class focused on order management
class CaveStoreBot(commands.Bot):
    def __init__(self):
        # Minimal intents
        intents = discord.Intents.none()
        intents.message_content = True
        intents.guilds = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            chunk_guilds_at_startup=False,
            max_messages=None  # Disable message cache
        )
        
        # Setup logging
        logging.basicConfig(
            filename='log.txt',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('CaveStoreBot')
        
    def has_role(self, member: discord.Member, role_name: str) -> bool:
        """Check if member has role"""
        role_ids = ROLES.get(role_name, [])
        return any(role.id in role_ids for role in member.roles)

    def get_permission_level(self, member: discord.Member) -> str:
        """Get highest permission level"""
        if self.has_role(member, "ADMIN"): return "ADMIN"
        if self.has_role(member, "MODERATOR"): return "MODERATOR"
        if self.has_role(member, "WORKER"): return "WORKER"
        return "ALL"

# Create bot instance
bot = CaveStoreBot()

# Load token
TOKEN = config.get("TOKEN", "")
if not TOKEN:
    raise ValueError("Bot token not found in config.json")

print(">>> Bot initialized, preparing to start...")


@bot.event
async def on_ready():
    try:
        log(f"✅ Bot logged in as: {bot.user.name}")
        
        # Essential info logging
        guild_count = len(bot.guilds)
        log(f"Bot is in {guild_count} servers")
        
        # Notify admin channel
        try:
            home_guild = bot.get_guild(GUILD_ID)
            if home_guild and config.get("ADMIN_CHANNEL_ID"):
                admin_channel = home_guild.get_channel(int(config["ADMIN_CHANNEL_ID"]))
                if admin_channel:
                    embed = discord.Embed(
                        title="✅ Bot Ready",
                        description=f"Active in {guild_count} servers",
                        color=0x00ff00
                    )
                    await admin_channel.send(embed=embed)
        except Exception as e:
            log(f"Could not send startup notification: {e}")
            
        # Start order monitoring
        try:
            from tasks.order_monitor import don_giam_sat
            bot.loop.create_task(don_giam_sat(bot))
            log("✅ Order monitoring started")
        except Exception as e:
            log(f"❌ Error starting order monitor: {e}")
            
    except Exception as e:
        log(f"❌ Error during bot startup: {str(e)}")
        import traceback
        traceback.print_exc()






# Load cogs and sync commands
@bot.event
async def setup_hook():
    try:
        log("[Setup] Loading extensions...")
        
        # Load extensions
        extensions = [
            "cogs.order_commands",
            "cogs.ai_chat"
        ]
        
        for extension in extensions:
            try:
                await bot.load_extension(extension)
                log(f"[Setup] Loaded {extension}")
            except Exception as e:
                log(f"[Setup] ❌ Error loading {extension}: {str(e)}")
        
        # Sync commands
        log("[Setup] Syncing commands...")
        guild = discord.Object(id=GUILD_ID)
        
        # Clear old commands first
        bot.tree.clear_commands(guild=guild)
        await bot.tree.sync(guild=None)  # Global sync
        
        # Sync new commands
        commands = await bot.tree.sync(guild=guild)
        log(f"[Setup] Synced {len(commands)} commands")
        
        if not commands:
            log("⚠️ WARNING: No commands were synced!")
            log("👉 Check:")
            log("  1. Bot has applications.commands scope")
            log("  2. GUILD_ID is correct")
            log("  3. Bot invite URL has proper scopes")
            log("  4. Cogs loaded correctly")
            log("  5. Required intents are enabled")
            
    except Exception as e:
        log(f"❌ Error in setup_hook: {str(e)}")
        import traceback
        traceback.print_exc()

# Error handlers
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(
            f"⏳ Please wait {error.retry_after:.1f} seconds.",
            ephemeral=True
        )
    elif isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "⛔ You don't have permission to use this command!",
            ephemeral=True
        )
    else:
        log(f"Command error: {str(error)}")
        await interaction.response.send_message(
            "❌ An error occurred while executing the command.",
            ephemeral=True
        )

# Admin Commands
@bot.tree.command(name="phanquyen", description="👑 Update role permissions (Admin)")
@app_commands.guild_only()
@requires_role("ADMIN")
@app_commands.describe(
    loai="Permission type (ADMIN/MODERATOR/WORKER)",
    role="Discord role to update (ID or @mention)",
    thao_tac="Add or remove role from permission list"
)
async def update_role_permission(
    interaction: discord.Interaction,
    loai: str,
    role: discord.Role,
    thao_tac: str
):
    """Update role permissions"""
    try:
        # Validate permission type
        loai = loai.upper()
        if loai not in ROLES:
            return await interaction.response.send_message(
                "❌ Invalid permission type. Use: ADMIN, MODERATOR or WORKER",
                ephemeral=True
            )

        # Validate action
        thao_tac = thao_tac.lower()
        if thao_tac not in ["add", "remove"]:
            return await interaction.response.send_message(
                "❌ Invalid action. Use: add or remove",
                ephemeral=True
            )

        # Perform update
        is_add = thao_tac == "add"
        role_ids = ROLES[loai]

        if is_add:
            if role.id in role_ids:
                return await interaction.response.send_message(
                    f"❌ Role {role.name} already has {loai} permission",
                    ephemeral=True
                )
            role_ids.append(role.id)
            action_text = "added to"
        else:
            if role.id not in role_ids:
                return await interaction.response.send_message(
                    f"❌ Role {role.name} doesn't have {loai} permission",
                    ephemeral=True
                )
            role_ids.remove(role.id)
            action_text = "removed from"

        # Create response embed
        embed = discord.Embed(
            title="👑 Permission Update",
            description=f"Role has been {action_text} permission list",
            color=0x00ff00
        )
        embed.add_field(name="Role", value=f"{role.name} (`{role.id}`)", inline=True)
        embed.add_field(name="Permission", value=loai, inline=True)
        embed.add_field(name="Action", value=thao_tac, inline=True)
        embed.add_field(
            name=f"Roles with {loai} permission", 
            value="\n".join([f"<@&{rid}>" for rid in ROLES[loai]]) or "None",
            inline=False
        )

        await interaction.response.send_message(embed=embed)
        log(f"[PERMS] {role.name} {action_text} {loai} by {interaction.user}")

    except Exception as e:
        log(f"[ERROR] Permission update failed: {str(e)}")
        await interaction.response.send_message(
            "❌ Error updating permissions",
            ephemeral=True
        )

@bot.tree.command(name="thongbao", description="📢 Send announcement to all servers (Admin)")
@app_commands.guild_only()
@requires_role("ADMIN")
@app_commands.describe(
    title="Announcement title",
    content="Announcement content",
    color="Color (blue/red/green/yellow)"
)
async def broadcast(
    interaction: discord.Interaction, 
    title: str,
    content: str,
    color: str = "blue"
):
    """Send announcement to all servers using the bot"""
    await interaction.response.defer(ephemeral=True)
    
    # Color mapping
    colors = {
        "blue": 0x3498db,
        "red": 0xe74c3c,
        "green": 0x2ecc71,
        "yellow": 0xf1c40f
    }
    embed_color = colors.get(color.lower(), 0x3498db)
    
    # Create announcement embed
    embed = discord.Embed(
        title=f"📢 {title}",
        description=content,
        color=embed_color,
        timestamp=datetime.now()
    )
    embed.set_footer(text=f"From: {interaction.guild.name}")
    
    # Send to all servers
    success = 0
    failed = 0
    
    for guild in bot.guilds:
        try:
            # Find suitable channel
            channel = None
            for ch in guild.text_channels:
                if not ch.permissions_for(guild.me).send_messages:
                    continue
                    
                if "system" in ch.name.lower() or "announcement" in ch.name.lower():
                    channel = ch
                    break
                    
                if not channel and ("general" in ch.name.lower() or "main" in ch.name.lower()):
                    channel = ch
                    
            if not channel:
                channel = next((ch for ch in guild.text_channels 
                              if ch.permissions_for(guild.me).send_messages), None)
                
            if channel:
                await channel.send(embed=embed)
                success += 1
            else:
                failed += 1
                log(f"[BROADCAST] Cannot send to {guild.name} - No suitable channel")
        except Exception as e:
            failed += 1
            log(f"[BROADCAST] Error sending to {guild.name}: {str(e)}")
    
    # Report results
    await interaction.followup.send(
        f"✅ Sent to {success} servers\n"
        f"❌ Failed: {failed} servers",
        ephemeral=True
    )

@bot.tree.command(name="help", description="📚 Xem hướng dẫn sử dụng")
@app_commands.guild_only()
async def help_command(interaction: discord.Interaction):
    """Hiển thị danh sách lệnh"""
    member = interaction.user
    permission_level = bot.get_permission_level(member)
    
    embed = discord.Embed(
        title="📚 Hướng dẫn sử dụng Cave Store Bot",
        description="Danh sách lệnh theo quyền hạn:",
        color=0x00ff00
    )

    # Basic commands
    basic_cmds = """
`/donhang` - Đặt đơn hàng mới
`/trangthai` - Xem trạng thái đơn
`/huydon` - Hủy đơn hàng (trước khi duyệt)
`/tinhgia` - Tính giá đơn hàng
`/help` - Xem hướng dẫn này
"""
    embed.add_field(name="🌟 Lệnh cơ bản", value=basic_cmds.strip(), inline=False)

    # Worker commands
    if permission_level in ["WORKER", "MODERATOR", "ADMIN"]:
        worker_cmds = """
`/nhancay` - Nhận đơn và đặt deadline
`/hoanthanh` - Đánh dấu hoàn thành
"""
        embed.add_field(name="💪 Lệnh Worker", value=worker_cmds.strip(), inline=False)

    # Moderator commands
    if permission_level in ["MODERATOR", "ADMIN"]:
        mod_cmds = """
`/duyetdon` - Duyệt đơn
`/danhsachdon` - Xem danh sách đơn
`/thongke` - Thống kê đơn hàng
"""
        embed.add_field(name="🛡️ Lệnh Moderator", value=mod_cmds.strip(), inline=False)

    # Admin commands
    if permission_level == "ADMIN":
        admin_cmds = """
`/xoadon` - Xóa đơn hàng
`/phanquyen` - Quản lý quyền
"""
        embed.add_field(name="👑 Lệnh Admin", value=admin_cmds.strip(), inline=False)

    # Permission level
    embed.set_footer(text=f"Cấp độ quyền: {permission_level}")

    await interaction.response.send_message(embed=embed, ephemeral=True)

# Guild events
@bot.event
async def on_guild_join(guild):
    """Event when bot joins a new server"""
    log(f"[NEW SERVER] {guild.name} (ID: {guild.id})")
    
    # Simple notification
    home_guild = bot.get_guild(GUILD_ID)
    if home_guild and config.get("ADMIN_CHANNEL_ID"):
        embed = discord.Embed(
            title="✨ Server mới",
            description=f"**{guild.name}**\nID: `{guild.id}`",
            color=0x00ff00
        )
        admin_channel = home_guild.get_channel(int(config["ADMIN_CHANNEL_ID"]))
        if admin_channel:
            await admin_channel.send(embed=embed)

@bot.event
async def on_guild_remove(guild):
    """Event when bot is removed"""
    log(f"[LEAVE] {guild.name} (ID: {guild.id})")

# Start bot
log(">>> Starting bot...")
bot.run(TOKEN)

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