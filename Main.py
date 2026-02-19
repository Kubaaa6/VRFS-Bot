import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import aiosqlite

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

# Initialize database
async def init_db():
    async with aiosqlite.connect('vrfs_stats.db') as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS player_stats (
                user_id INTEGER PRIMARY KEY,
                goals INTEGER DEFAULT 0,
                assists INTEGER DEFAULT 0,
                cleansheets_defender INTEGER DEFAULT 0,
                cleansheets_goalkeeper INTEGER DEFAULT 0,
                motm INTEGER DEFAULT 0,
                totw INTEGER DEFAULT 0
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS player_gw_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                gw INTEGER,
                season INTEGER,
                stat_type TEXT,
                count INTEGER,
                FOREIGN KEY(user_id) REFERENCES player_stats(user_id)
            )
        ''')
        await db.commit()

@bot.event
async def on_ready():
    print(f"{bot.user} has connected to Discord!")
    await init_db()

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

# Welcome command - send welcome message to channel
@bot.command(name="welcome")
@commands.check(is_moderator)
async def welcome(ctx, channel: discord.TextChannel, *, message: str):
    await channel.send(f"👋 {message}")
    await ctx.send(f"✅ Welcome message sent to {channel.mention}")

# Goodbye command - send goodbye message for a user
@bot.command(name="goodbye")
@commands.check(is_moderator)
async def goodbye(ctx, member: discord.Member):
    await ctx.send(f"👋 {member.mention} has left the server. Goodbye!")

# Profile command - show player stats
@bot.command(name="profile")
async def profile(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author
    
    async with aiosqlite.connect('vrfs_stats.db') as db:
        # Get totals from GW stats
        async with db.execute('''
            SELECT stat_type, SUM(count) as total
            FROM player_gw_stats
            WHERE user_id = ?
            GROUP BY stat_type
        ''', (member.id,)) as cursor:
            stats_data = await cursor.fetchall()
    
    # Initialize all stats to 0
    stats = {
        "goal": 0,
        "assist": 0,
        "defender cleansheet": 0,
        "goalkeeper cleansheet": 0,
        "totw": 0,
        "motm": 0
    }
    
    # Update with actual values
    if stats_data:
        for stat_type, total in stats_data:
            if stat_type in stats:
                stats[stat_type] = total
    
    embed = discord.Embed(title=f"{member.name}'s Profile", color=discord.Color.blue())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="⚽ Goals", value=stats["goal"], inline=True)
    embed.add_field(name="🎯 Assists", value=stats["assist"], inline=True)
    embed.add_field(name="🛡️ Cleansheets (Defender)", value=stats["defender cleansheet"], inline=True)
    embed.add_field(name="🧤 Cleansheets (Goalkeeper)", value=stats["goalkeeper cleansheet"], inline=True)
    embed.add_field(name="⭐ MOTM", value=stats["motm"], inline=True)
    embed.add_field(name="📊 TOTW", value=stats["totw"], inline=True)
    

    await ctx.send(embed=embed)

# Add stat command (moderator only)
@bot.command(name="addstat")
@commands.check(is_moderator)
async def addstat(ctx, member: discord.Member, gw: int, season: int, stat_type: str, count: int):
    # Validate inputs
    if not 1 <= gw <= 22:
        await ctx.send("❌ GW must be between 1 and 22")
        return
    if season not in [1, 2, 3]:
        await ctx.send("❌ Season must be 1, 2, or 3")
        return
    
    valid_stats = ["goal", "assist", "defender cleansheet", "goalkeeper cleansheet", "totw", "motm"]
    if stat_type.lower() not in valid_stats:
        await ctx.send(f"❌ Stat type must be one of: {', '.join(valid_stats)}")
        return
    
    if count <= 0:
        await ctx.send("❌ Count must be greater than 0")
        return
    
    # Insert into database
    async with aiosqlite.connect('vrfs_stats.db') as db:
        await db.execute('INSERT OR IGNORE INTO player_stats (user_id) VALUES (?)', (member.id,))
        await db.execute('''
            INSERT INTO player_gw_stats (user_id, gw, season, stat_type, count)
            VALUES (?, ?, ?, ?, ?)
        ''', (member.id, gw, season, stat_type.lower(), count))
        await db.commit()
    
    stat_emojis = {
        "goal": "⚽",
        "assist": "🎯",
        "defender cleansheet": "🛡️",
        "goalkeeper cleansheet": "🧤",
        "totw": "📊",
        "motm": "⭐"
    }
    emoji = stat_emojis.get(stat_type.lower(), "")
    await ctx.send(f"{emoji} Added {count} {stat_type}(s) to {member.mention} for GW{gw} Season {season}!")

bot.run(TOKEN)
