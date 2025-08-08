import functools
from typing import Callable, List, Union
import discord

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
