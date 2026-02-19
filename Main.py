import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

@bot.event
async def on_ready():
    print(f"{bot.user} has connected to Discord!")

# Check if user has moderator permissions
async def is_moderator(ctx):
    return ctx.author.guild_permissions.administrator or ctx.author.guild_permissions.moderate_members

# Test command (anyone can use)
@bot.command(name="ping")
async def ping(ctx):
    await ctx.send(f"Pong! {round(bot.latency * 1000)}ms")

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

# Sign command - assign user to team
@bot.command(name="sign")
@commands.check(is_moderator)
async def sign(ctx, member: discord.Member, team: discord.Role):
    await member.add_roles(team)
    await ctx.send(f"✅ {member} has been signed to {team.mention}")

# Release command - remove user from team
@bot.command(name="release")
@commands.check(is_moderator)
async def release(ctx, member: discord.Member):
    # Remove all roles that could be teams (except @everyone)
    team_roles = [role for role in member.roles if role != member.guild.default_role]
    if team_roles:
        await member.remove_roles(*team_roles)
        await ctx.send(f"📤 {member} has been released from {', '.join([r.mention for r in team_roles])}")
    else:
        await ctx.send(f"{member} is not assigned to any team")

bot.run(TOKEN)
