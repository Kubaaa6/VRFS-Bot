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
                cleansheets INTEGER DEFAULT 0,
                motm INTEGER DEFAULT 0,
                totw INTEGER DEFAULT 0
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
        async with db.execute('SELECT * FROM player_stats WHERE user_id = ?', (member.id,)) as cursor:
            row = await cursor.fetchone()
    
    if row is None:
        # Create new player profile
        async with aiosqlite.connect('vrfs_stats.db') as db:
            await db.execute('INSERT INTO player_stats (user_id) VALUES (?)', (member.id,))
            await db.commit()
        row = (member.id, 0, 0, 0, 0, 0, 0)
    
    embed = discord.Embed(title=f"{member.name}'s Profile", color=discord.Color.blue())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="⚽ Goals", value=row[1], inline=True)
    embed.add_field(name="🎯 Assists", value=row[2], inline=True)
    embed.add_field(name="🛡️ Cleansheets (Defender)", value=row[3], inline=True)
    embed.add_field(name="🛡️ Cleansheets", value=row[4], inline=True)
    embed.add_field(name="⭐ MOTM", value=row[5], inline=True)
    embed.add_field(name="📊 TOTW", value=row[6], inline=True)
    
    await ctx.send(embed=embed)

# Add stat commands (moderator only)
@bot.command(name="addgoal")
@commands.check(is_moderator)
async def addgoal(ctx, member: discord.Member):
    async with aiosqlite.connect('vrfs_stats.db') as db:
        await db.execute('INSERT OR IGNORE INTO player_stats (user_id) VALUES (?)', (member.id,))
        await db.execute('UPDATE player_stats SET goals = goals + 1 WHERE user_id = ?', (member.id,))
        await db.commit()
    await ctx.send(f"⚽ Added goal to {member.mention}!")

@bot.command(name="addassist")
@commands.check(is_moderator)
async def addassist(ctx, member: discord.Member):
    async with aiosqlite.connect('vrfs_stats.db') as db:
        await db.execute('INSERT OR IGNORE INTO player_stats (user_id) VALUES (?)', (member.id,))
        await db.execute('UPDATE player_stats SET assists = assists + 1 WHERE user_id = ?', (member.id,))
        await db.commit()
    await ctx.send(f"🎯 Added assist to {member.mention}!")

@bot.command(name="addmotm")
@commands.check(is_moderator)
async def addmotm(ctx, member: discord.Member):
    async with aiosqlite.connect('vrfs_stats.db') as db:
        await db.execute('INSERT OR IGNORE INTO player_stats (user_id) VALUES (?)', (member.id,))
        await db.execute('UPDATE player_stats SET motm = motm + 1 WHERE user_id = ?', (member.id,))
        await db.commit()
    await ctx.send(f"⭐ Added MOTM to {member.mention}!")

@bot.command(name="addcleansheet")
@commands.check(is_moderator)
async def addcleansheet(ctx, member: discord.Member):
    async with aiosqlite.connect('vrfs_stats.db') as db:
        await db.execute('INSERT OR IGNORE INTO player_stats (user_id) VALUES (?)', (member.id,))
        await db.execute('UPDATE player_stats SET cleansheets = cleansheets + 1 WHERE user_id = ?', (member.id,))
        await db.commit()
    await ctx.send(f"🛡️ Added cleansheet to {member.mention}!")

@bot.command(name="adddefendercleansheet")
@commands.check(is_moderator)
async def adddefendercleansheet(ctx, member: discord.Member):
    async with aiosqlite.connect('vrfs_stats.db') as db:
        await db.execute('INSERT OR IGNORE INTO player_stats (user_id) VALUES (?)', (member.id,))
        await db.execute('UPDATE player_stats SET cleansheets_defender = cleansheets_defender + 1 WHERE user_id = ?', (member.id,))
        await db.commit()
    await ctx.send(f"🛡️ Added defender cleansheet to {member.mention}!")

@bot.command(name="addtotw")
@commands.check(is_moderator)
async def addtotw(ctx, member: discord.Member):
    async with aiosqlite.connect('vrfs_stats.db') as db:
        await db.execute('INSERT OR IGNORE INTO player_stats (user_id) VALUES (?)', (member.id,))
        await db.execute('UPDATE player_stats SET totw = totw + 1 WHERE user_id = ?', (member.id,))
        await db.commit()
    await ctx.send(f"📊 Added TOTW to {member.mention}!")

bot.run(TOKEN)
