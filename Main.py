import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"{bot.user} has connected to Discord!")

# Check if user has moderator permissions
async def is_moderator(ctx):
    return ctx.author.guild_permissions.administrator or ctx.author.guild_permissions.moderate_members

# Kick command
@bot.command(name="kick")
@commands.check(is_moderator)
async def kick(ctx, member: discord.Member, *, reason=None):
    if member.guild_permissions.administrator:
        await ctx.send("Cannot kick an admin!")
        return
    await member.kick(reason=reason)
    await ctx.send(f"Kicked {member} for: {reason}")

# Ban command
@bot.command(name="ban")
@commands.check(is_moderator)
async def ban(ctx, member: discord.Member, *, reason=None):
    if member.guild_permissions.administrator:
        await ctx.send("Cannot ban an admin!")
        return
    await member.ban(reason=reason)
    await ctx.send(f"Banned {member} for: {reason}")

# Mute command
@bot.command(name="mute")
@commands.check(is_moderator)
async def mute(ctx, member: discord.Member):
    await member.edit(mute=True)
    await ctx.send(f"Muted {member}")

# Unmute command
@bot.command(name="unmute")
@commands.check(is_moderator)
async def unmute(ctx, member: discord.Member):
    await member.edit(mute=False)
    await ctx.send(f"Unmuted {member}")

# Clear messages command
@bot.command(name="clear")
@commands.check(is_moderator)
async def clear(ctx, amount: int):
    await ctx.channel.purge(limit=amount)
    await ctx.send(f"Cleared {amount} messages")

bot.run(TOKEN)
