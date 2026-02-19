import os
import discord
from discord.ext import commands
from discord import app_commands
from typing import Literal
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
                totw INTEGER DEFAULT 0,
                position TEXT
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
                division TEXT DEFAULT 'Div 1',
                FOREIGN KEY(user_id) REFERENCES player_stats(user_id)
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        # Initialize default GW and Season
        await db.execute('INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)', ('current_gw', '1'))
        await db.execute('INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)', ('current_season', '1'))
        await db.commit()

@bot.event
async def on_ready():
    print(f"{bot.user} has connected to Discord!")
    await init_db()
    await bot.tree.sync()
    print(f"Synced {len(bot.tree._get_all_commands())} command(s)")
    # Set custom status
    activity = discord.Activity(type=discord.ActivityType.watching, name="⭐ NOVA")
    await bot.change_presence(activity=activity)

# Check if user has moderator permissions
def is_moderator(interaction: discord.Interaction) -> bool:
    return interaction.user.guild_permissions.administrator or interaction.user.guild.permissions.moderate_members

# Test command (anyone can use)
@bot.tree.command(name="ping", description="Check bot latency")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"Pong! {round(bot.latency * 1000)}ms")

# Kick command
@bot.tree.command(name="kick", description="Kick a user from the server")
@app_commands.describe(member="User to kick", reason="Reason for kicking")
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    if not is_moderator(interaction):
        await interaction.response.send_message("❌ You don't have permission to use this command")
        return
    if member.guild.permissions.administrator:
        await interaction.response.send_message("Cannot kick an admin!")
        return
    await member.kick(reason=reason)
    await interaction.response.send_message(f"Kicked {member} for: {reason}")

# Ban command
@bot.tree.command(name="ban", description="Ban a user from the server")
@app_commands.describe(member="User to ban", reason="Reason for banning")
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    if not is_moderator(interaction):
        await interaction.response.send_message("❌ You don't have permission to use this command")
        return
    if member.guild.permissions.administrator:
        await interaction.response.send_message("Cannot ban an admin!")
        return
    await member.ban(reason=reason)
    await interaction.response.send_message(f"Banned {member} for: {reason}")

# Mute command
@bot.tree.command(name="mute", description="Mute a user")
@app_commands.describe(member="User to mute")
async def mute(interaction: discord.Interaction, member: discord.Member):
    if not is_moderator(interaction):
        await interaction.response.send_message("❌ You don't have permission to use this command")
        return
    await member.edit(mute=True)
    await interaction.response.send_message(f"Muted {member}")

# Unmute command
@bot.tree.command(name="unmute", description="Unmute a user")
@app_commands.describe(member="User to unmute")
async def unmute(interaction: discord.Interaction, member: discord.Member):
    if not is_moderator(interaction):
        await interaction.response.send_message("❌ You don't have permission to use this command")
        return
    await member.edit(mute=False)
    await interaction.response.send_message(f"Unmuted {member}")

# Clear messages command
@bot.tree.command(name="clear", description="Clear messages from a channel")
@app_commands.describe(amount="Number of messages to clear")
async def clear(interaction: discord.Interaction, amount: int):
    if not is_moderator(interaction):
        await interaction.response.send_message("❌ You don't have permission to use this command")
        return
    await interaction.channel.purge(limit=amount)
    await interaction.response.send_message(f"Cleared {amount} messages")

# Delete channels command
@bot.tree.command(name="deletechannels", description="Delete channels (specify a number or 'all')")
@app_commands.describe(count="Number of channels to delete or 'all' to delete all channels")
async def deletechannels(interaction: discord.Interaction, count: str):
    if not is_moderator(interaction):
        await interaction.response.send_message("❌ You don't have permission to use this command")
        return
    
    await interaction.response.defer()
    
    channels_to_delete = []
    
    if count.lower() == "all":
        # Get all channels
        channels_to_delete = interaction.guild.channels
    else:
        # Try to convert to number
        try:
            num = int(count)
            if num <= 0:
                await interaction.followup.send("❌ Number must be greater than 0")
                return
            # Get the first N channels
            channels_to_delete = interaction.guild.channels[:num]
        except ValueError:
            await interaction.followup.send("❌ Please specify a number or 'all'")
            return
    
    if not channels_to_delete:
        await interaction.followup.send("❌ No channels to delete")
        return
    
    deleted_count = 0
    for channel in channels_to_delete:
        try:
            await channel.delete()
            deleted_count += 1
        except discord.Forbidden:
            pass  # Skip channels we don't have permission to delete
        except discord.HTTPException:
            pass  # Skip channels with errors
    
    await interaction.followup.send(f"🗑️ Deleted {deleted_count} channel(s)")

# Sign command
@bot.tree.command(name="sign", description="Sign a user to a team")
@app_commands.describe(member="Player to sign", team="Team role to assign")
async def sign(interaction: discord.Interaction, member: discord.Member, team: discord.Role):
    if not is_moderator(interaction):
        await interaction.response.send_message("❌ You don't have permission to use this command")
        return
    await member.add_roles(team)
    await interaction.response.send_message(f"✅ {member} has been signed to {team.mention}")

# Release command
@bot.tree.command(name="release", description="Release a user from their team")
@app_commands.describe(member="Player to release")
async def release(interaction: discord.Interaction, member: discord.Member):
    if not is_moderator(interaction):
        await interaction.response.send_message("❌ You don't have permission to use this command")
        return
    team_roles = [role for role in member.roles if role != member.guild.default_role]
    if team_roles:
        await member.remove_roles(*team_roles)
        await interaction.response.send_message(f"📤 {member} has been released from {', '.join([r.mention for r in team_roles])}")
    else:
        await interaction.response.send_message(f"{member} is not assigned to any team")

# Welcome command
@bot.tree.command(name="welcome", description="Send a welcome message to a channel")
@app_commands.describe(channel="Channel to send welcome message", message="Welcome message")
async def welcome(interaction: discord.Interaction, channel: discord.TextChannel, message: str):
    if not is_moderator(interaction):
        await interaction.response.send_message("❌ You don't have permission to use this command")
        return
    await channel.send(f"👋 {message}")
    await interaction.response.send_message(f"✅ Welcome message sent to {channel.mention}")

# Goodbye command
@bot.tree.command(name="goodbye", description="Send a goodbye message for a user")
@app_commands.describe(member="Player leaving")
async def goodbye(interaction: discord.Interaction, member: discord.Member):
    if not is_moderator(interaction):
        await interaction.response.send_message("❌ You don't have permission to use this command")
        return
    await interaction.response.send_message(f"👋 {member.mention} has left the server. Goodbye!")

# Profile command
@bot.tree.command(name="profile", description="View a player's profile and stats")
@app_commands.describe(member="Player to view (leave empty for yourself)")
async def profile(interaction: discord.Interaction, member: discord.Member = None):
    if member is None:
        member = interaction.user
    
    # Fetch position
    async with aiosqlite.connect('vrfs_stats.db') as db:
        async with db.execute('SELECT position FROM player_stats WHERE user_id = ?', (member.id,)) as cursor:
            row = await cursor.fetchone()
            position = row[0] if row and row[0] else "Not set"
    
    async with aiosqlite.connect('vrfs_stats.db') as db:
        async with db.execute('''
            SELECT stat_type, SUM(count) as total
            FROM player_gw_stats
            WHERE user_id = ?
            GROUP BY stat_type
        ''', (member.id,)) as cursor:
            stats_data = await cursor.fetchall()
    
    stats = {
        "goal": 0,
        "assist": 0,
        "defender cleansheet": 0,
        "goalkeeper cleansheet": 0,
        "totw": 0,
        "motm": 0
    }
    
    if stats_data:
        for stat_type, total in stats_data:
            if stat_type in stats:
                stats[stat_type] = total
    
    # Point values by division and stat type
    div_points = {
        "Div 1": {"goal": 9, "assist": 7, "defender cleansheet": 10, "goalkeeper cleansheet": 12, "motm": 8, "totw": 8},
        "Div 2": {"goal": 6, "assist": 5, "defender cleansheet": 8, "goalkeeper cleansheet": 10, "motm": 6, "totw": 6},
        "Div 3": {"goal": 3, "assist": 2, "defender cleansheet": 6, "goalkeeper cleansheet": 8, "motm": 3, "totw": 3}
    }
    
    # Calculate points from player_gw_stats with division-based values
    points = 0
    if stats_data:
        async with aiosqlite.connect('vrfs_stats.db') as db:
            async with db.execute('''
                SELECT stat_type, division, SUM(count) as total
                FROM player_gw_stats
                WHERE user_id = ?
                GROUP BY stat_type, division
            ''', (member.id,)) as cursor:
                gw_stats = await cursor.fetchall()
        
        for stat_type, division, total in gw_stats:
            if division in div_points and stat_type in div_points[division]:
                points += div_points[division][stat_type] * total
    
    # Determine rank
    if points >= 300:
        rank = "🔶 Platinum"
    elif points >= 194:
        rank = "🟡 Gold"
    elif points >= 84:
        rank = "⚪ Silver"
    else:
        rank = "🟤 Bronze"
    
    embed = discord.Embed(title=member.display_name, description=f"@{member.name}", color=discord.Color.gold())
    embed.set_author(name="NOVA", icon_url=bot.user.display_avatar.url)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Rank", value=rank, inline=False)
    embed.add_field(name="Points", value=points, inline=True)
    embed.add_field(name="⚽ Goals", value=stats["goal"], inline=True)
    embed.add_field(name="🎯 Assists", value=stats["assist"], inline=True)
    embed.add_field(name="🛡️ Cleansheets (Defender)", value=stats["defender cleansheet"], inline=True)
    embed.add_field(name="🧤 Cleansheets (Goalkeeper)", value=stats["goalkeeper cleansheet"], inline=True)
    embed.add_field(name="⭐ MOTM", value=stats["motm"], inline=True)
    embed.add_field(name="📊 TOTW", value=stats["totw"], inline=True)
    embed.set_footer(text="NOVA - VRFS League")
    
    embed.insert_field_at(0, name="Position", value=position, inline=False)
    
    await interaction.response.send_message(embed=embed)

# Set current GW and Season command
@bot.tree.command(name="set", description="Set current GameWeek and Season")
@app_commands.describe(gw="GameWeek (1-22)", season="Season (1, 2, or 3)")
async def set_gw_season(interaction: discord.Interaction, gw: int, season: int):
    if not is_moderator(interaction):
        await interaction.response.send_message("❌ You don't have permission to use this command")
        return
    if not 1 <= gw <= 22:
        await interaction.response.send_message("❌ GW must be between 1 and 22")
        return
    if season not in [1, 2, 3]:
        await interaction.response.send_message("❌ Season must be 1, 2, or 3")
        return
    
    async with aiosqlite.connect('vrfs_stats.db') as db:
        await db.execute('UPDATE config SET value = ? WHERE key = ?', (str(gw), 'current_gw'))
        await db.execute('UPDATE config SET value = ? WHERE key = ?', (str(season), 'current_season'))
        await db.commit()
    
    await interaction.response.send_message(f"✅ Set current GW to {gw} and Season to {season}")

# Add stat command
@bot.tree.command(name="addstat", description="Add a stat to a player for current GW/Season")
@app_commands.describe(
    member="Player to add stats for",
    gw="GameWeek (1-22)",
    season="Season (1, 2, or 3)",
    stat_type="Type of stat (goal, assist, defender cleansheet, goalkeeper cleansheet, totw, motm)",
    count="Number of stats to add",
    division="Division (Div 1, Div 2, or Div 3)"
)
async def addstat(
    interaction: discord.Interaction,
    member: discord.Member,
    gw: int,
    season: int,
    stat_type: str,
    count: int,
    division: Literal["Div 1", "Div 2", "Div 3"] = "Div 1"
):
    if not is_moderator(interaction):
        await interaction.response.send_message("❌ You don't have permission to use this command")
        return
    
    if not 1 <= gw <= 22:
        await interaction.response.send_message("❌ GW must be between 1 and 22")
        return
    if season not in [1, 2, 3]:
        await interaction.response.send_message("❌ Season must be 1, 2, or 3")
        return
    
    valid_stats = ["goal", "assist", "defender cleansheet", "goalkeeper cleansheet", "totw", "motm"]
    if stat_type.lower() not in valid_stats:
        await interaction.response.send_message(f"❌ Stat type must be one of: {', '.join(valid_stats)}")
        return
    
    if count <= 0:
        await interaction.response.send_message("❌ Count must be greater than 0")
        return
    
    async with aiosqlite.connect('vrfs_stats.db') as db:
        async with db.execute('SELECT value FROM config WHERE key = ?', ('current_gw',)) as cursor:
            current_gw = int((await cursor.fetchone())[0])
        async with db.execute('SELECT value FROM config WHERE key = ?', ('current_season',)) as cursor:
            current_season = int((await cursor.fetchone())[0])
    
    if gw != current_gw or season != current_season:
        await interaction.response.send_message(f"❌ You can only add stats to the current GW! Current: GW{current_gw} Season {current_season}")
        return
    
    async with aiosqlite.connect('vrfs_stats.db') as db:
        await db.execute('INSERT OR IGNORE INTO player_stats (user_id) VALUES (?)', (member.id,))
        await db.execute('''
            INSERT INTO player_gw_stats (user_id, gw, season, stat_type, count, division)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (member.id, gw, season, stat_type.lower(), count, division))
        await db.commit()
    
    # DM the user about the stat update
    try:
        # Get new totals for this division
        async with aiosqlite.connect('vrfs_stats.db') as db:
            async with db.execute('''
                SELECT stat_type, SUM(count) as total
                FROM player_gw_stats
                WHERE user_id = ? AND division = ?
                GROUP BY stat_type
            ''', (member.id, division)) as cursor:
                div_stats = {row[0]: row[1] for row in await cursor.fetchall()}
        # Points for this stat
        div_points = {
            "Div 1": {"goal": 9, "assist": 7, "defender cleansheet": 10, "goalkeeper cleansheet": 12, "motm": 8, "totw": 8},
            "Div 2": {"goal": 6, "assist": 5, "defender cleansheet": 8, "goalkeeper cleansheet": 10, "motm": 6, "totw": 6},
            "Div 3": {"goal": 3, "assist": 2, "defender cleansheet": 6, "goalkeeper cleansheet": 8, "motm": 3, "totw": 3}
        }
        stat_points = div_points[division][stat_type.lower()] * count
        # Emoji map
        stat_emojis = {
            "goal": "⚽",
            "assist": "🎯",
            "defender cleansheet": "🛡️",
            "goalkeeper cleansheet": "🧤",
            "totw": "📊",
            "motm": "⭐"
        }
        # Compose DM
        embed = discord.Embed(title="\U0001F441\uFE0F Profile Viewed", color=discord.Color.purple(), timestamp=interaction.created_at)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        embed.add_field(name="\U0001F514 Stat Update Notification", value=f"Your stats in **{division}** have just been updated.", inline=False)
        embed.add_field(name="\U0001F4F0 Latest change", value=f"{stat_emojis.get(stat_type.lower(), '')} {stat_type.capitalize()}: +{count}  (**+{stat_points} pts**)", inline=False)
        # Totals
        embed.add_field(
            name=f"Your current totals in {division}",
            value=f"⚽ Goals: {div_stats.get('goal', 0)}\n🎯 Assists: {div_stats.get('assist', 0)}\n🧤 GK Clean Sheets: {div_stats.get('goalkeeper cleansheet', 0)}\n🛡️ Defender Clean Sheets: {div_stats.get('defender cleansheet', 0)}",
            inline=False
        )
        embed.set_footer(text="Use /profile to view your full stat and value changes.")
        await member.send(embed=embed)
    except Exception:
        pass  # Ignore if user has DMs closed

# Remove stat command
@bot.tree.command(name="removestats", description="Remove a stat from a player for a specific GW/Season")
@app_commands.describe(
    member="Player to remove stats from",
    gw="GameWeek (1-22)",
    season="Season (1, 2, or 3)",
    stat_type="Type of stat (goal, assist, defender cleansheet, goalkeeper cleansheet, totw, motm)",
    count="Number of stats to remove",
    division="Division (Div 1, Div 2, or Div 3)"
)
async def removestats(
    interaction: discord.Interaction,
    member: discord.Member,
    gw: int,
    season: int,
    stat_type: str,
    count: int,
    division: Literal["Div 1", "Div 2", "Div 3"] = "Div 1"
):
    if not is_moderator(interaction):
        await interaction.response.send_message("❌ You don't have permission to use this command")
        return
    
    if not 1 <= gw <= 22:
        await interaction.response.send_message("❌ GW must be between 1 and 22")
        return
    if season not in [1, 2, 3]:
        await interaction.response.send_message("❌ Season must be 1, 2, or 3")
        return
    
    valid_stats = ["goal", "assist", "defender cleansheet", "goalkeeper cleansheet", "totw", "motm"]
    if stat_type.lower() not in valid_stats:
        await interaction.response.send_message(f"❌ Stat type must be one of: {', '.join(valid_stats)}")
        return
    
    if count <= 0:
        await interaction.response.send_message("❌ Count must be greater than 0")
        return
    
    async with aiosqlite.connect('vrfs_stats.db') as db:
        # Check if the stat exists
        async with db.execute('''
            SELECT COUNT(*) as count FROM player_gw_stats
            WHERE user_id = ? AND gw = ? AND season = ? AND stat_type = ? AND division = ?
        ''', (member.id, gw, season, stat_type.lower(), division)) as cursor:
            result = await cursor.fetchone()
            stat_count = result[0]
        
        if stat_count == 0:
            await interaction.response.send_message(f"❌ No stats found for {member.mention} in {division} GW{gw} Season {season}")
            return
        
        # Delete the stat entry
        await db.execute('''
            DELETE FROM player_gw_stats
            WHERE user_id = ? AND gw = ? AND season = ? AND stat_type = ? AND division = ?
            LIMIT 1
        ''', (member.id, gw, season, stat_type.lower(), division))
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
    await interaction.response.send_message(f"{emoji} Removed {count} {stat_type}(s) from {member.mention} for {division} GW{gw} Season {season}!")

bot.run(TOKEN)
