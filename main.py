import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput
from PIL import Image, ImageDraw, ImageFont
import os
from flask import Flask
from threading import Thread
from io import BytesIO
from datetime import timedelta, datetime, timezone
import asyncio
import random
import json
import re

ANNOUNCEMENTS_CHANNEL_ID = 1429028560168816681
TICKET_CATEGORY_ID = None
TICKET_CHANNEL_ID = 1429030206689120306
STAFF_LOG_CHANNEL_ID = 1429052870371835944
WELCOME_CHANNEL_ID = 1429040704486637599
STAFF_ROLE_ID = 1429035155158208532
TICKET_STAFF_ROLE_ID = 1429050967881416757
BANNER_IMAGE_PATH = "startup.png"

WARNING_ROLE_1 = 1429197544499576903
WARNING_ROLE_2 = 1429197737097822388
WARNING_ROLE_3 = 1429197812012290178
WARNING_STAFF_CHANNEL = 1429197895747371008
RELEASE_LOG_CHANNEL = 1429198290833903840

SESSION_CHANNEL_ID = 1429026313007665172
SESSION_HOST_ROLE_ID = 1429081183148445806
COHOST_ROLE_ID = 1432075585990950963
STARTUP_PING_ROLES = [1429032286623498240, 1429414667226320989]
RELEASE_PING_ROLES = [1429080620742742168, 1429035519337168976]

APPLICATION_CHANNEL_ID = 1429185516649320469
APPLICATION_REVIEWER_ROLE_ID = 1429035691026808832

REACTION_ROLE_CHANNEL_ID = 1429382680633413662
REACTION_ROLE_MESSAGE_ID = None
REACTION_ROLE_EMOJI = "✅"
REACTION_ROLE_ID = 1429032286623498240

SUGGESTION_CHANNEL_ID = 1432086573985431552

TOKEN = os.environ.get('DISCORD_BOT_TOKEN') or os.environ.get('TOKEN')

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='?', intents=intents)
bot.remove_command('help')

ticket_last_activity = {}
ticket_warnings_sent = {}
ticket_creators = {}
ticket_added_users = {}
user_levels = {}
user_economy = {}
user_afk = {}
user_warnings = {}
reaction_roles = {}
active_applications = {}
active_giveaways = {}
bad_words = ["badword1", "badword2"]
latest_startup_message_id = None
latest_startup_host_id = None
latest_release_message_id = None
session_cohosts = []
required_reactions_for_release = 0
suggestion_counter = 0
suggestion_cooldowns = {}

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=5000)

Thread(target=run).start()

class ServerLinkView(View):
    def __init__(self, server_link):
        super().__init__(timeout=None)
        self.server_link = server_link
    
    @discord.ui.button(label="🔗 Server Link", style=discord.ButtonStyle.green)
    async def server_link_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🔗 Private Server Link",
            description=f"**Link:** {self.server_link}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class ReleaseModal(Modal, title="Session Release Details"):
    frp_speed = TextInput(
        label="FRP Speed",
        placeholder="Enter the FRP speed (e.g., 50 mph, 60 mph)",
        required=True,
        max_length=50
    )
    
    status = TextInput(
        label="Server Status",
        placeholder="Enter server status (e.g., Open, Full, Limited)",
        required=True,
        max_length=100
    )
    
    law_enforcement = TextInput(
        label="Law Enforcement Active?",
        placeholder="Yes or No",
        required=True,
        max_length=3
    )
    
    server_link = TextInput(
        label="Private Server Link",
        placeholder="Enter the Roblox private server link",
        required=True,
        max_length=200
    )
    
    def __init__(self, host, startup_message):
        super().__init__()
        self.host = host
        self.startup_message = startup_message
    
    async def on_submit(self, interaction: discord.Interaction):
        global latest_release_message_id
        
        ping_mentions = " ".join([f"<@&{role_id}>" for role_id in [1429032286623498240, 1429414667226320989]])
        
        try:
            file = discord.File("release.png", filename="release.png")
            embed = discord.Embed(
                title="🎉 Session Fully Released!",
                description=f"**Host:** {self.host.mention}\n\n"
                           f"**FRP Speed:** {self.frp_speed.value}\n"
                           f"**Status:** {self.status.value}\n"
                           f"**Law Enforcement:** {self.law_enforcement.value}",
                color=discord.Color.gold()
            )
            embed.set_image(url="attachment://release.png")
            
            server_link_view = ServerLinkView(self.server_link.value)
            
            release_channel = interaction.client.get_channel(RELEASE_LOG_CHANNEL)
            if release_channel:
                try:
                    file_log = discord.File("release.png", filename="release.png")
                    await release_channel.send(content=ping_mentions, embed=embed, file=file_log, view=server_link_view)
                except:
                    pass
            
            release_msg = await self.startup_message.reply(content=ping_mentions, embed=embed, file=file, view=server_link_view)
            latest_release_message_id = release_msg.id
            await interaction.response.send_message("✅ Session released successfully!", ephemeral=True)
            
        except FileNotFoundError:
            embed = discord.Embed(
                title="🎉 Session Fully Released!",
                description=f"**Host:** {self.host.mention}\n\n"
                           f"**FRP Speed:** {self.frp_speed.value}\n"
                           f"**Status:** {self.status.value}\n"
                           f"**Law Enforcement:** {self.law_enforcement.value}",
                color=discord.Color.gold()
            )
            server_link_view = ServerLinkView(self.server_link.value)
            release_msg = await self.startup_message.reply(content=ping_mentions, embed=embed, view=server_link_view)
            latest_release_message_id = release_msg.id
            
            log_channel = interaction.guild.get_channel(1429198290833903840)
            if log_channel:
                log_embed = discord.Embed(
                    title="📊 Full Session Release",
                    description=f"**Host:** {self.host.mention}\n**FRP Speed:** {self.frp_speed.value}\n**Status:** {self.status.value}",
                    color=discord.Color.gold(),
                    timestamp=datetime.now(timezone.utc)
                )
                await log_channel.send(embed=log_embed)
            
            await interaction.response.send_message("✅ Session released successfully!", ephemeral=True)

class ReleaseView(View):
    def __init__(self, host, startup_message):
        super().__init__(timeout=3600)
        self.host = host
        self.startup_message = startup_message
    
    @discord.ui.button(label="📋 Enter Release Details", style=discord.ButtonStyle.primary)
    async def release_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        host_role = interaction.guild.get_role(SESSION_HOST_ROLE_ID)
        if host_role not in interaction.user.roles:
            await interaction.response.send_message("❌ Only Session Hosts can enter release details!", ephemeral=True)
            return
        
        modal = ReleaseModal(self.host, self.startup_message)
        await interaction.response.send_modal(modal)

class EarlyReleaseView(View):
    def __init__(self, server_link, allowed_roles):
        super().__init__(timeout=3600)
        self.server_link = server_link
        self.allowed_roles = allowed_roles
    
    @discord.ui.button(label="🔗 Get Private Server Link", style=discord.ButtonStyle.green)
    async def early_release_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_role_ids = [role.id for role in interaction.user.roles]
        has_access = any(role_id in user_role_ids for role_id in self.allowed_roles)
        
        if has_access:
            embed = discord.Embed(
                title="🔗 Private Server Link",
                description=f"**Link:** {self.server_link}",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("❌ You don't have the required role to access this link!", ephemeral=True)


class CloseTicketModal(Modal, title="Close Ticket"):
    reason = TextInput(
        label="Reason for closing",
        placeholder="Enter the reason for closing this ticket...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )
    
    def __init__(self, ticket_channel, creator_id):
        super().__init__()
        self.ticket_channel = ticket_channel
        self.creator_id = creator_id
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message("🔒 Closing ticket...", ephemeral=True)
        
        log_channel = interaction.guild.get_channel(STAFF_LOG_CHANNEL_ID)
        if log_channel:
            try:
                creator = await interaction.guild.fetch_member(self.creator_id)
                creator_text = creator.mention
            except discord.NotFound:
                creator_text = f"User ID: {self.creator_id} (no longer in server)"
            
            log_embed = discord.Embed(
                title="🎫 Ticket Closed",
                color=discord.Color.red(),
                timestamp=datetime.now(timezone.utc)
            )
            log_embed.add_field(name="Ticket", value=self.ticket_channel.mention, inline=True)
            log_embed.add_field(name="Created by", value=creator_text, inline=True)
            log_embed.add_field(name="Closed by", value=interaction.user.mention, inline=True)
            log_embed.add_field(name="Reason", value=self.reason.value, inline=False)
            await log_channel.send(embed=log_embed)
        
        await self.ticket_channel.send(f"🔒 Ticket closed by {interaction.user.mention}\nReason: {self.reason.value}")
        
        if self.ticket_channel.id in ticket_last_activity:
            del ticket_last_activity[self.ticket_channel.id]
        if self.ticket_channel.id in ticket_warnings_sent:
            del ticket_warnings_sent[self.ticket_channel.id]
        if self.ticket_channel.id in ticket_creators:
            del ticket_creators[self.ticket_channel.id]
        if self.ticket_channel.id in ticket_added_users:
            del ticket_added_users[self.ticket_channel.id]
        
        await asyncio.sleep(3)
        await self.ticket_channel.delete()

class CloseTicketView(View):
    def __init__(self, creator_id):
        super().__init__(timeout=None)
        self.creator_id = creator_id
    
    @discord.ui.button(label="Close", style=discord.ButtonStyle.red, emoji="🔒")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        staff_role = interaction.guild.get_role(TICKET_STAFF_ROLE_ID)
        
        if interaction.user.id != self.creator_id and staff_role not in interaction.user.roles:
            await interaction.response.send_message("❌ Only the ticket creator or staff can close this ticket!", ephemeral=True)
            return
        
        modal = CloseTicketModal(interaction.channel, self.creator_id)
        await interaction.response.send_modal(modal)


async def check_inactive_tickets():
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            guild = bot.guilds[0]
            ticket_category = bot.get_channel(TICKET_CATEGORY_ID)
            
            if ticket_category:
                now = datetime.now(timezone.utc)
                
                for channel in ticket_category.channels:
                    if channel.id in ticket_last_activity:
                        last_activity = ticket_last_activity[channel.id]
                        time_since_activity = now - last_activity
                        
                        if time_since_activity >= timedelta(hours=5):
                            if channel.id not in ticket_warnings_sent:
                                embed = discord.Embed(
                                    title="⏰ Inactive Ticket",
                                    description="This ticket has been inactive for 5 hours. Should it be closed?\n\nReact with ✅ to close this ticket.",
                                    color=discord.Color.orange()
                                )
                                message = await channel.send(embed=embed)
                                await message.add_reaction("✅")
                                
                                ticket_warnings_sent[channel.id] = now
        except Exception as e:
            print(f"Error checking inactive tickets: {e}")
        
        await asyncio.sleep(3600)

@bot.event
async def on_ready():
    global REACTION_ROLE_MESSAGE_ID
    
    print(f'Logged in as {bot.user}')
    
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"Failed to sync slash commands: {e}")
    
    bot.loop.create_task(check_inactive_tickets())
    
    channel = bot.get_channel(TICKET_CHANNEL_ID)
    if channel:
        async for message in channel.history(limit=50):
            if message.author == bot.user and message.embeds:
                for embed in message.embeds:
                    if embed.title == "Create a Ticket":
                        await message.delete()
                        print(f"Deleted old ticket button")
        
        embed = discord.Embed(
            title="Create a Ticket",
            description="Press the button below to create a ticket.",
            color=discord.Color.orange()
        )
        button = Button(label="Create Ticket", style=discord.ButtonStyle.green)

        async def button_callback(interaction):
            modal = Modal(title="Ticket Reason")
            reason_input = TextInput(label="Reason", placeholder="Why are you opening this ticket?")
            modal.add_item(reason_input)

            async def modal_callback(modal_interaction):
                guild = interaction.guild
                category = guild.get_channel(TICKET_CATEGORY_ID)
                staff_role = guild.get_role(TICKET_STAFF_ROLE_ID)
                
                ticket_channel = await guild.create_text_channel(
                    name=f"ticket-{interaction.user.name}",
                    category=category,
                    overwrites={
                        guild.default_role: discord.PermissionOverwrite(view_channel=False),
                        interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
                        staff_role: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
                    }
                )
                
                ticket_last_activity[ticket_channel.id] = datetime.now(timezone.utc)
                ticket_creators[ticket_channel.id] = interaction.user.id
                
                ticket_embed = discord.Embed(
                    title="🎫 New Ticket",
                    description=f"**Created by:** {interaction.user.mention}\n**Reason:** {reason_input.value}",
                    color=discord.Color.orange()
                )
                close_view = CloseTicketView(interaction.user.id)
                await ticket_channel.send(
                    content=f"<@&{STAFF_ROLE_ID}>",
                    embed=ticket_embed,
                    view=close_view
                )
                
                if STAFF_LOG_CHANNEL_ID:
                    log_channel = guild.get_channel(STAFF_LOG_CHANNEL_ID)
                    await log_channel.send(f"Ticket created by {interaction.user} in {ticket_channel.mention}")
                
                await modal_interaction.response.send_message(f"Ticket created: {ticket_channel.mention}", ephemeral=True)

            modal.on_submit = modal_callback
            await interaction.response.send_modal(modal)

        button.callback = button_callback
        view = View(timeout=None)
        view.add_item(button)
        await channel.send(embed=embed, view=view)
        print(f"Ticket button sent to channel {TICKET_CHANNEL_ID}")

    
    reaction_role_channel = bot.get_channel(REACTION_ROLE_CHANNEL_ID)
    if reaction_role_channel and REACTION_ROLE_MESSAGE_ID is None:
        try:
            found_message = False
            async for message in reaction_role_channel.history(limit=20):
                if message.author == bot.user and "Welcome and thank you for joining Greenville Roleplay Prism!" in message.content:
                    REACTION_ROLE_MESSAGE_ID = message.id
                    reaction_roles[(message.id, REACTION_ROLE_EMOJI)] = REACTION_ROLE_ID
                    found_message = True
                    print(f"Found existing reaction role message with ID {message.id}")
                    break
            
            if not found_message:
                new_message = await reaction_role_channel.send("Welcome and thank you for joining Greenville Roleplay Prism!\nTo verify - react below!")
                await new_message.add_reaction(REACTION_ROLE_EMOJI)
                REACTION_ROLE_MESSAGE_ID = new_message.id
                reaction_roles[(new_message.id, REACTION_ROLE_EMOJI)] = REACTION_ROLE_ID
                print(f"Created new reaction role message with ID {new_message.id}")
        except Exception as e:
            print(f"Error setting up reaction role message: {e}")

@bot.event
async def on_member_join(member):
    if member.bot:
        return
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    try:
        if os.path.exists("welcome_banner.png"):
            banner = Image.open("welcome_banner.png").convert("RGBA")
            avatar_bytes = await member.display_avatar.read()
            avatar_io = BytesIO(avatar_bytes)
            avatar = Image.open(avatar_io).resize((200, 200)).convert("RGBA")
            
            mask = Image.new('L', (200, 200), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse([0, 0, 200, 200], fill=255)
            
            circular_avatar = Image.new('RGBA', (200, 200), (0, 0, 0, 0))
            circular_avatar.paste(avatar, (0, 0))
            circular_avatar.putalpha(mask)
            
            outline_size = 210
            avatar_with_outline = Image.new('RGBA', (outline_size, outline_size), (0, 0, 0, 0))
            outline_draw = ImageDraw.Draw(avatar_with_outline)
            outline_draw.ellipse([0, 0, outline_size-1, outline_size-1], fill=(88, 101, 242, 255))
            avatar_with_outline.paste(circular_avatar, (5, 5), circular_avatar)
            
            position = ((banner.width - outline_size) // 2, (banner.height - outline_size) // 2)
            banner.paste(avatar_with_outline, position, avatar_with_outline)
            banner.save("welcome_final.png")
            
            file = discord.File("welcome_final.png")
            embed = discord.Embed(
                title="Thank you for joining Greenville Roleplay Prism",
                description=f"{member.mention}",
                color=discord.Color.orange()
            )
            embed.set_image(url="attachment://welcome_final.png")
            await channel.send(embed=embed, file=file)
        else:
            embed = discord.Embed(
                title="Thank you for joining Greenville Roleplay Prism",
                description=f"{member.mention}",
                color=discord.Color.orange()
            )
            await channel.send(embed=embed)
    except Exception as e:
        print(f"Error in welcome message: {e}")

@bot.event
async def on_member_remove(member):
    if member.bot:
        return
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    try:
        if os.path.exists("welcome_banner.png"):
            banner = Image.open("welcome_banner.png").convert("RGBA")
            avatar_bytes = await member.display_avatar.read()
            avatar_io = BytesIO(avatar_bytes)
            avatar = Image.open(avatar_io).resize((200, 200)).convert("RGBA")
            
            mask = Image.new('L', (200, 200), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse([0, 0, 200, 200], fill=255)
            
            circular_avatar = Image.new('RGBA', (200, 200), (0, 0, 0, 0))
            circular_avatar.paste(avatar, (0, 0))
            circular_avatar.putalpha(mask)
            
            outline_size = 210
            avatar_with_outline = Image.new('RGBA', (outline_size, outline_size), (0, 0, 0, 0))
            outline_draw = ImageDraw.Draw(avatar_with_outline)
            outline_draw.ellipse([0, 0, outline_size-1, outline_size-1], fill=(88, 101, 242, 255))
            avatar_with_outline.paste(circular_avatar, (5, 5), circular_avatar)
            
            position = ((banner.width - outline_size) // 2, (banner.height - outline_size) // 2)
            banner.paste(avatar_with_outline, position, avatar_with_outline)
            banner.save("goodbye_final.png")
            
            file = discord.File("goodbye_final.png")
            embed = discord.Embed(
                title="We hope you had a great time in Greenville Roleplay Prism!",
                description=f"{member.name} has left the server",
                color=discord.Color.orange()
            )
            embed.set_image(url="attachment://goodbye_final.png")
            await channel.send(embed=embed, file=file)
        else:
            embed = discord.Embed(
                title="We hope you had a great time in Greenville Roleplay Prism!",
                description=f"{member.name} has left the server",
                color=discord.Color.orange()
            )
            await channel.send(embed=embed)
    except Exception as e:
        print(f"Error in leave message: {e}")

async def on_message_leveling(message):
    if message.author.id not in user_levels:
        user_levels[message.author.id] = {'xp': 0, 'level': 1}
    
    xp_gain = random.randint(10, 25)
    user_levels[message.author.id]['xp'] += xp_gain
    
    current_level = user_levels[message.author.id]['level']
    xp_needed = current_level * 100
    
    if user_levels[message.author.id]['xp'] >= xp_needed:
        user_levels[message.author.id]['level'] += 1
        user_levels[message.author.id]['xp'] = 0
        await message.channel.send(f"🎉 {message.author.mention} leveled up to level {user_levels[message.author.id]['level']}!", delete_after=5)

async def on_message_economy(message):
    if message.author.id not in user_economy:
        user_economy[message.author.id] = {'wallet': 0, 'bank': 0, 'last_daily': None, 'last_work': None}
    
    coins_gain = random.randint(5, 15)
    user_economy[message.author.id]['wallet'] += coins_gain

async def on_message_afk_check(message):
    if message.author.id in user_afk:
        reason = user_afk[message.author.id]
        del user_afk[message.author.id]
        await message.channel.send(f"Welcome back {message.author.mention}! I removed your AFK status.", delete_after=5)
    
    for mention in message.mentions:
        if mention.id in user_afk:
            reason = user_afk[mention.id]
            await message.channel.send(f"{mention.display_name} is currently AFK: {reason}", delete_after=10)

async def on_message_automod(message):
    if any(word in message.content.lower() for word in bad_words):
        await message.delete()
        await message.channel.send(f"{message.author.mention}, please watch your language!", delete_after=5)

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    if message.channel.category_id == TICKET_CATEGORY_ID:
        ticket_last_activity[message.channel.id] = datetime.now(timezone.utc)
        if message.channel.id in ticket_warnings_sent:
            del ticket_warnings_sent[message.channel.id]
    
    await on_message_leveling(message)
    await on_message_economy(message)
    await on_message_afk_check(message)
    await on_message_automod(message)
    
    await bot.process_commands(message)

@bot.event
async def on_reaction_add(reaction, user):
    global required_reactions_for_release, latest_startup_message_id
    
    if user.bot:
        return
    
    if (reaction.emoji == "✅" and 
        reaction.message.author == bot.user and 
        reaction.message.embeds and 
        any("inactive" in embed.title.lower() for embed in reaction.message.embeds)):
        
        channel = reaction.message.channel
        
        await channel.send("🔒 Ticket closed due to inactivity.")
        await asyncio.sleep(3)
        await channel.delete()
        
        if channel.id in ticket_last_activity:
            del ticket_last_activity[channel.id]
        if channel.id in ticket_warnings_sent:
            del ticket_warnings_sent[channel.id]
    
    if (reaction.message.id, str(reaction.emoji)) in reaction_roles:
        role_id = reaction_roles[(reaction.message.id, str(reaction.emoji))]
        role = reaction.message.guild.get_role(role_id)
        if role:
            try:
                await user.add_roles(role)
                print(f"Added role {role.name} to {user.name}")
            except Exception as e:
                print(f"Error adding role: {e}")
    
    if (reaction.emoji == "✅" and 
        reaction.message.id == latest_startup_message_id and
        required_reactions_for_release > 0):
        
        reaction_count = sum(1 for r in reaction.message.reactions if str(r.emoji) == "✅")
        if reaction_count >= required_reactions_for_release:
            session_channel = bot.get_channel(SESSION_CHANNEL_ID)
            if session_channel:
                await session_channel.send(f"🎉 The session has reached {required_reactions_for_release} reactions! Release is ready!")

@bot.event
async def on_reaction_remove(reaction, user):
    if user.bot:
        return
    
    if (reaction.message.id, str(reaction.emoji)) in reaction_roles:
        role_id = reaction_roles[(reaction.message.id, str(reaction.emoji))]
        role = reaction.message.guild.get_role(role_id)
        if role:
            try:
                await user.remove_roles(role)
                print(f"Removed role {role.name} from {user.name}")
            except Exception as e:
                print(f"Error removing role: {e}")

@bot.command()
async def adduser(ctx, member: discord.Member):
    if not ctx.channel.category_id == TICKET_CATEGORY_ID:
        await ctx.send("❌ This command can only be used in tickets!")
        return
    
    staff_role = ctx.guild.get_role(TICKET_STAFF_ROLE_ID)
    creator_id = ticket_creators.get(ctx.channel.id)
    
    if ctx.author.id != creator_id and staff_role not in ctx.author.roles:
        await ctx.send("❌ Only the ticket creator or staff can add users!")
        return
    
    await ctx.channel.set_permissions(member, view_channel=True, send_messages=True, read_message_history=True)
    
    if ctx.channel.id not in ticket_added_users:
        ticket_added_users[ctx.channel.id] = []
    ticket_added_users[ctx.channel.id].append(member.id)
    
    await ctx.send(f"✓ {member.mention} has been added to this ticket.")

@bot.command()
async def removeuser(ctx, member: discord.Member):
    if not ctx.channel.category_id == TICKET_CATEGORY_ID:
        await ctx.send("❌ This command can only be used in tickets!")
        return
    
    staff_role = ctx.guild.get_role(TICKET_STAFF_ROLE_ID)
    creator_id = ticket_creators.get(ctx.channel.id)
    
    if ctx.author.id != creator_id and staff_role not in ctx.author.roles:
        await ctx.send("❌ Only the ticket creator or staff can remove users!")
        return
    
    await ctx.channel.set_permissions(member, overwrite=None)
    
    if ctx.channel.id in ticket_added_users and member.id in ticket_added_users[ctx.channel.id]:
        ticket_added_users[ctx.channel.id].remove(member.id)
    
    await ctx.send(f"✓ {member.mention} has been removed from this ticket.")

@bot.command()
async def ticketbutton(ctx):
    staff_role = ctx.guild.get_role(STAFF_ROLE_ID)
    if staff_role not in ctx.author.roles:
        await ctx.send("❌ You don't have permission to use this command.")
        return
    
    embed = discord.Embed(
        title="Create a Ticket",
        description="Press the button below to create a ticket.",
        color=discord.Color.orange()
    )
    button = Button(label="Create Ticket", style=discord.ButtonStyle.green)

    async def button_callback(interaction):
        modal = Modal(title="Ticket Reason")
        reason_input = TextInput(label="Reason", placeholder="Why are you opening this ticket?")
        modal.add_item(reason_input)

        async def modal_callback(modal_interaction):
            guild = interaction.guild
            category = guild.get_channel(TICKET_CATEGORY_ID)
            staff_role = guild.get_role(TICKET_STAFF_ROLE_ID)
            
            ticket_channel = await guild.create_text_channel(
                name=f"ticket-{interaction.user.name}",
                category=category,
                overwrites={
                    guild.default_role: discord.PermissionOverwrite(view_channel=False),
                    interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
                    staff_role: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
                }
            )
            
            ticket_last_activity[ticket_channel.id] = datetime.now(timezone.utc)
            ticket_creators[ticket_channel.id] = interaction.user.id
            
            ticket_embed = discord.Embed(
                title="🎫 New Ticket",
                description=f"**Created by:** {interaction.user.mention}\n**Reason:** {reason_input.value}",
                color=discord.Color.orange()
            )
            close_view = CloseTicketView(interaction.user.id)
            await ticket_channel.send(
                content=f"<@&{STAFF_ROLE_ID}>",
                embed=ticket_embed,
                view=close_view
            )
            
            if STAFF_LOG_CHANNEL_ID:
                log_channel = guild.get_channel(STAFF_LOG_CHANNEL_ID)
                await log_channel.send(f"Ticket created by {interaction.user} in {ticket_channel.mention}")
            
            await modal_interaction.response.send_message(
                f"✅ Ticket created: {ticket_channel.mention}", ephemeral=True
            )

        modal.on_submit = modal_callback
        await interaction.response.send_modal(modal)

    button.callback = button_callback
    view = View(timeout=None)
    view.add_item(button)
    await ctx.send(embed=embed, view=view)
    await ctx.message.delete()

@bot.command()
async def timeout(ctx, member: discord.Member, duration: int, *, reason: str = "No reason provided"):
    staff_role = ctx.guild.get_role(STAFF_ROLE_ID)
    if staff_role not in ctx.author.roles:
        await ctx.send("❌ You don't have permission to use this command.")
        return
    
    await member.timeout(timedelta(minutes=duration), reason=reason)
    await ctx.send(f"✓ {member.mention} has been timed out for {duration} minutes. Reason: {reason}")
    
    if STAFF_LOG_CHANNEL_ID:
        log_channel = ctx.guild.get_channel(STAFF_LOG_CHANNEL_ID)
        await log_channel.send(f"🔇 {member.mention} was timed out by {ctx.author.mention} for {duration} minutes.\nReason: {reason}")

@bot.command()
async def untimeout(ctx, member: discord.Member):
    staff_role = ctx.guild.get_role(STAFF_ROLE_ID)
    if staff_role not in ctx.author.roles:
        await ctx.send("❌ You don't have permission to use this command.")
        return
    
    await member.timeout(None)
    await ctx.send(f"✓ {member.mention} has been removed from timeout.")
    
    if STAFF_LOG_CHANNEL_ID:
        log_channel = ctx.guild.get_channel(STAFF_LOG_CHANNEL_ID)
        await log_channel.send(f"🔊 {member.mention} was removed from timeout by {ctx.author.mention}.")

@bot.command()
async def kick(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    staff_role = ctx.guild.get_role(STAFF_ROLE_ID)
    if staff_role not in ctx.author.roles:
        await ctx.send("❌ You don't have permission to use this command.")
        return
    
    await member.kick(reason=reason)
    await ctx.send(f"✓ {member.mention} has been kicked. Reason: {reason}")
    
    if STAFF_LOG_CHANNEL_ID:
        log_channel = ctx.guild.get_channel(STAFF_LOG_CHANNEL_ID)
        await log_channel.send(f"👢 {member.mention} was kicked by {ctx.author.mention}.\nReason: {reason}")

@bot.command()
async def ban(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    staff_role = ctx.guild.get_role(STAFF_ROLE_ID)
    if staff_role not in ctx.author.roles:
        await ctx.send("❌ You don't have permission to use this command.")
        return
    
    await member.ban(reason=reason)
    await ctx.send(f"✓ {member.mention} has been banned. Reason: {reason}")
    
    if STAFF_LOG_CHANNEL_ID:
        log_channel = ctx.guild.get_channel(STAFF_LOG_CHANNEL_ID)
        await log_channel.send(f"🔨 {member.mention} was banned by {ctx.author.mention}.\nReason: {reason}")

@bot.command()
async def clear(ctx, amount: int = 10):
    staff_role = ctx.guild.get_role(STAFF_ROLE_ID)
    if staff_role not in ctx.author.roles:
        await ctx.send("❌ You don't have permission to use this command.")
        return
    
    deleted = await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"✓ Deleted {len(deleted)-1} messages.")
    await asyncio.sleep(3)
    await msg.delete()

class StartupModal(Modal, title="Session Startup"):
    reactions_needed = TextInput(
        label="Reactions Needed for Release",
        placeholder="Enter number of reactions (e.g., 10, 20, 30)",
        required=True,
        max_length=3
    )
    
    def __init__(self, author):
        super().__init__()
        self.author = author
    
    async def on_submit(self, interaction: discord.Interaction):
        global latest_startup_message_id, latest_startup_host_id, required_reactions_for_release, session_cohosts
        
        try:
            required_reactions_for_release = int(self.reactions_needed.value)
        except ValueError:
            await interaction.response.send_message("❌ Invalid number! Please enter a valid number.", ephemeral=True)
            return
        
        session_channel = interaction.guild.get_channel(SESSION_CHANNEL_ID)
        if not session_channel:
            await interaction.response.send_message("❌ Session channel not found!", ephemeral=True)
            return
        
        ping_mentions = " ".join([f"<@&{role_id}>" for role_id in STARTUP_PING_ROLES])
        
        try:
            if os.path.exists(BANNER_IMAGE_PATH):
                file = discord.File(BANNER_IMAGE_PATH, filename="banner.png")
                embed = discord.Embed(
                    title="🚀 Session Starting!",
                    description=f"**Host:** {self.author.mention}\n\nThe session is now starting! Please wait for further updates.\n\n**React with ✅ to show interest! ({required_reactions_for_release} reactions needed)**",
                    color=discord.Color.green()
                )
                embed.set_image(url="attachment://banner.png")
                startup_message = await session_channel.send(content=ping_mentions, embed=embed, file=file)
            else:
                embed = discord.Embed(
                    title="🚀 Session Starting!",
                    description=f"**Host:** {self.author.mention}\n\nThe session is now starting! Please wait for further updates.\n\n**React with ✅ to show interest! ({required_reactions_for_release} reactions needed)**",
                    color=discord.Color.green()
                )
                startup_message = await session_channel.send(content=ping_mentions, embed=embed)
            
            await startup_message.add_reaction("✅")
            
            latest_startup_message_id = startup_message.id
            latest_startup_host_id = self.author.id
            session_cohosts = []
            
            log_channel = interaction.guild.get_channel(1429198290833903840)
            if log_channel:
                log_embed = discord.Embed(
                    title="📊 Session Startup",
                    description=f"**Host:** {self.author.mention}\n**Reactions Required:** {required_reactions_for_release}",
                    color=discord.Color.green(),
                    timestamp=datetime.now(timezone.utc)
                )
                await log_channel.send(embed=log_embed)
            
            await interaction.response.send_message("✅ Session started successfully!", ephemeral=True)
                
        except Exception as e:
            await interaction.response.send_message(f"❌ Error starting session: {str(e)}", ephemeral=True)

@bot.command()
async def startup(ctx):
    global session_cohosts
    
    host_role = ctx.guild.get_role(SESSION_HOST_ROLE_ID)
    if host_role not in ctx.author.roles:
        await ctx.send("❌ You need the Session Host role to start a session!", delete_after=5)
        try:
            await ctx.message.delete()
        except:
            pass
        return
    
    session_cohosts = []
    
    modal = StartupModal(ctx.author)
    
    class StartupView(View):
        def __init__(self):
            super().__init__(timeout=60)
        
        @discord.ui.button(label="🚀 Start Session", style=discord.ButtonStyle.green)
        async def startup_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_modal(modal)
    
    view = StartupView()
    temp_msg = await ctx.send("Click the button to start a session:", view=view, delete_after=60)
    
    try:
        await ctx.message.delete()
    except:
        pass

class EarlyReleaseModal(Modal, title="Early Access Release"):
    server_link = TextInput(
        label="Private Server Link",
        placeholder="Enter the Roblox private server link",
        required=True,
        max_length=200
    )
    
    def __init__(self, author, startup_message):
        super().__init__()
        self.author = author
        self.startup_message = startup_message
    
    async def on_submit(self, interaction: discord.Interaction):
        global latest_release_message_id
        
        session_channel = interaction.guild.get_channel(SESSION_CHANNEL_ID)
        allowed_roles = [1429080620742742168, 1429035519337168976, 1429106576945451027, 1429032606275735583, 1429032855219994665]
        ping_mentions = " ".join([f"<@&{role_id}>" for role_id in allowed_roles])
        
        view = EarlyReleaseView(self.server_link.value, allowed_roles)
        
        try:
            file = discord.File("early_release.png", filename="early_release.png")
            embed = discord.Embed(
                title="🚀 Early Access Released!",
                description=f"**Host:** {self.author.mention}\n\nEarly Access has been released! Click the button below to get early access!",
                color=discord.Color.green()
            )
            embed.set_image(url="attachment://early_release.png")
            early_msg = await self.startup_message.reply(content=ping_mentions, embed=embed, file=file, view=view)
        except FileNotFoundError:
            embed = discord.Embed(
                title="🚀 Early Access Released!",
                description=f"**Host:** {self.author.mention}\n\nEarly Access has been released! Click the button below to get early access!",
                color=discord.Color.green()
            )
            early_msg = await self.startup_message.reply(content=ping_mentions, embed=embed, view=view)
        
        latest_release_message_id = early_msg.id
        
        log_channel = interaction.guild.get_channel(1429198290833903840)
        if log_channel:
            log_embed = discord.Embed(
                title="📊 Early Access Release",
                description=f"**Host:** {self.author.mention}",
                color=discord.Color.green(),
                timestamp=datetime.now(timezone.utc)
            )
            await log_channel.send(embed=log_embed)
        
        await interaction.response.send_message("✅ Early access released successfully!", ephemeral=True)

@bot.command()
async def release_early(ctx):
    global latest_startup_message_id, latest_startup_host_id
    
    host_role = ctx.guild.get_role(SESSION_HOST_ROLE_ID)
    if host_role not in ctx.author.roles:
        await ctx.send("❌ You need the Session Host role to use this command!", delete_after=5)
        try:
            await ctx.message.delete()
        except:
            pass
        return
    
    if not latest_startup_message_id or latest_startup_host_id != ctx.author.id:
        await ctx.send("❌ You must be the host of the latest startup!", delete_after=5)
        try:
            await ctx.message.delete()
        except:
            pass
        return
    
    session_channel = bot.get_channel(SESSION_CHANNEL_ID)
    if not session_channel:
        await ctx.send("❌ Session channel not found!", delete_after=5)
        try:
            await ctx.message.delete()
        except:
            pass
        return
    
    try:
        startup_message = await session_channel.fetch_message(latest_startup_message_id)
        
        modal = EarlyReleaseModal(ctx.author, startup_message)
        
        class EarlyReleaseButtonView(View):
            def __init__(self):
                super().__init__(timeout=60)
            
            @discord.ui.button(label="🚀 Enter Early Access Link", style=discord.ButtonStyle.green)
            async def early_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                await interaction.response.send_modal(modal)
        
        view = EarlyReleaseButtonView()
        temp_msg = await ctx.send("Click the button to release early access:", view=view, delete_after=60)
        
        try:
            await ctx.message.delete()
        except:
            pass
            
    except discord.NotFound:
        await ctx.send("❌ Startup message not found!", delete_after=5)
        try:
            await ctx.message.delete()
        except:
            pass
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}", delete_after=5)
        try:
            await ctx.message.delete()
        except:
            pass

@bot.command()
async def release(ctx):
    global latest_startup_message_id, latest_startup_host_id
    
    host_role = ctx.guild.get_role(SESSION_HOST_ROLE_ID)
    if host_role not in ctx.author.roles:
        await ctx.send("❌ You need the Session Host role to use this command!", delete_after=5)
        try:
            await ctx.message.delete()
        except:
            pass
        return
    
    if not latest_startup_message_id or latest_startup_host_id != ctx.author.id:
        await ctx.send("❌ You must be the host of the latest startup!", delete_after=5)
        try:
            await ctx.message.delete()
        except:
            pass
        return
    
    session_channel = bot.get_channel(SESSION_CHANNEL_ID)
    if not session_channel:
        await ctx.send("❌ Session channel not found!", delete_after=5)
        try:
            await ctx.message.delete()
        except:
            pass
        return
    
    try:
        startup_message = await session_channel.fetch_message(latest_startup_message_id)
        
        view = ReleaseView(ctx.author, startup_message)
        
        try:
            file = discord.File("release.png", filename="release.png")
            embed = discord.Embed(
                title="🎉 Ready to Release Session",
                description=f"**Host:** {ctx.author.mention}\n\nClick the button below to enter session details and release!",
                color=discord.Color.gold()
            )
            embed.set_image(url="attachment://release.png")
            await ctx.channel.send(embed=embed, file=file, view=view)
        except FileNotFoundError:
            embed = discord.Embed(
                title="🎉 Ready to Release Session",
                description=f"**Host:** {ctx.author.mention}\n\nClick the button below to enter session details and release!",
                color=discord.Color.gold()
            )
            await ctx.channel.send(embed=embed, view=view)
        
        try:
            await ctx.message.delete()
        except:
            pass
            
    except discord.NotFound:
        await ctx.send("❌ Startup message not found!", delete_after=5)
        try:
            await ctx.message.delete()
        except:
            pass
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}", delete_after=5)
        try:
            await ctx.message.delete()
        except:
            pass

@bot.command()
async def cohost(ctx):
    global latest_release_message_id, session_cohosts
    
    cohost_role = ctx.guild.get_role(COHOST_ROLE_ID)
    if cohost_role not in ctx.author.roles:
        await ctx.send("❌ You need the Co-Host role to use this command!", delete_after=5)
        try:
            await ctx.message.delete()
        except:
            pass
        return
    
    if len(session_cohosts) >= 3:
        await ctx.send("❌ Maximum of 3 co-hosts reached!", delete_after=5)
        try:
            await ctx.message.delete()
        except:
            pass
        return
    
    if ctx.author.id in session_cohosts:
        await ctx.send("❌ You are already a co-host!", delete_after=5)
        try:
            await ctx.message.delete()
        except:
            pass
        return
    
    if not latest_release_message_id:
        await ctx.send("❌ No recent release found!", delete_after=5)
        try:
            await ctx.message.delete()
        except:
            pass
        return
    
    session_channel = bot.get_channel(SESSION_CHANNEL_ID)
    if not session_channel:
        await ctx.send("❌ Session channel not found!", delete_after=5)
        try:
            await ctx.message.delete()
        except:
            pass
        return
    
    try:
        release_message = await session_channel.fetch_message(latest_release_message_id)
        
        session_cohosts.append(ctx.author.id)
        
        await release_message.reply(f"{ctx.author.mention} is now co-hosting this session!")
        
        log_channel = ctx.guild.get_channel(1429198290833903840)
        if log_channel:
            log_embed = discord.Embed(
                title="📊 Co-Host Added",
                description=f"**Co-Host:** {ctx.author.mention}",
                color=discord.Color.blue(),
                timestamp=datetime.now(timezone.utc)
            )
            await log_channel.send(embed=log_embed)
        
        try:
            await ctx.message.delete()
        except:
            pass
            
    except discord.NotFound:
        await ctx.send("❌ Release message not found!", delete_after=5)
        try:
            await ctx.message.delete()
        except:
            pass
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}", delete_after=5)
        try:
            await ctx.message.delete()
        except:
            pass

@bot.command()
async def sessionend(ctx):
    global latest_startup_message_id, latest_startup_host_id, session_cohosts, required_reactions_for_release
    
    host_role = ctx.guild.get_role(SESSION_HOST_ROLE_ID)
    if host_role not in ctx.author.roles:
        await ctx.send("❌ You need the Session Host role to use this command!", delete_after=5)
        try:
            await ctx.message.delete()
        except:
            pass
        return
    
    if not latest_startup_message_id or latest_startup_host_id != ctx.author.id:
        await ctx.send("❌ You must be the host of the latest startup!", delete_after=5)
        try:
            await ctx.message.delete()
        except:
            pass
        return
    
    session_channel = bot.get_channel(SESSION_CHANNEL_ID)
    if not session_channel:
        await ctx.send("❌ Session channel not found!", delete_after=5)
        try:
            await ctx.message.delete()
        except:
            pass
        return
    
    try:
        startup_message = await session_channel.fetch_message(latest_startup_message_id)
        
        try:
            file = discord.File("session_end.png", filename="session_end.png")
            embed = discord.Embed(
                title="🏁 Session Ended!",
                description=f"**Host:** {ctx.author.mention}\n\nThank you all for participating in this session! We hope you had a great time. Stay tuned for the next session!",
                color=discord.Color.red()
            )
            embed.set_image(url="attachment://session_end.png")
            await startup_message.reply(embed=embed, file=file)
        except FileNotFoundError:
            embed = discord.Embed(
                title="🏁 Session Ended!",
                description=f"**Host:** {ctx.author.mention}\n\nThank you all for participating in this session! We hope you had a great time. Stay tuned for the next session!",
                color=discord.Color.red()
            )
            await startup_message.reply(embed=embed)
        
        log_channel = ctx.guild.get_channel(1429198290833903840)
        if log_channel:
            log_embed = discord.Embed(
                title="📊 Session Ended",
                description=f"**Host:** {ctx.author.mention}",
                color=discord.Color.red(),
                timestamp=datetime.now(timezone.utc)
            )
            await log_channel.send(embed=log_embed)
        
        latest_startup_message_id = None
        latest_startup_host_id = None
        session_cohosts = []
        required_reactions_for_release = 0
        
        try:
            await ctx.message.delete()
        except:
            pass
            
    except discord.NotFound:
        await ctx.send("❌ Startup message not found!", delete_after=5)
        try:
            await ctx.message.delete()
        except:
            pass
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}", delete_after=5)
        try:
            await ctx.message.delete()
        except:
            pass

@bot.command()
async def addcohost(ctx, member: discord.Member):
    global latest_startup_message_id, latest_startup_host_id
    
    if not latest_startup_message_id or latest_startup_host_id != ctx.author.id:
        await ctx.send("❌ You must be the host of the latest startup!", delete_after=5)
        try:
            await ctx.message.delete()
        except:
            pass
        return
    
    session_channel = bot.get_channel(SESSION_CHANNEL_ID)
    if not session_channel:
        await ctx.send("❌ Session channel not found!", delete_after=5)
        try:
            await ctx.message.delete()
        except:
            pass
        return
    
    try:
        startup_message = await session_channel.fetch_message(latest_startup_message_id)
        await startup_message.reply(f"{member.mention} has been added as a co-host by {ctx.author.mention}!")
        
        try:
            await ctx.message.delete()
        except:
            pass
            
    except discord.NotFound:
        await ctx.send("❌ Startup message not found!", delete_after=5)
        try:
            await ctx.message.delete()
        except:
            pass
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}", delete_after=5)
        try:
            await ctx.message.delete()
        except:
            pass

@bot.command()
async def removecohost(ctx, member: discord.Member):
    global latest_startup_message_id, latest_startup_host_id
    
    if not latest_startup_message_id or latest_startup_host_id != ctx.author.id:
        await ctx.send("❌ You must be the host of the latest startup!", delete_after=5)
        try:
            await ctx.message.delete()
        except:
            pass
        return
    
    session_channel = bot.get_channel(SESSION_CHANNEL_ID)
    if not session_channel:
        await ctx.send("❌ Session channel not found!", delete_after=5)
        try:
            await ctx.message.delete()
        except:
            pass
        return
    
    try:
        startup_message = await session_channel.fetch_message(latest_startup_message_id)
        await startup_message.reply(f"{member.mention} has been removed as a co-host by {ctx.author.mention}.")
        
        try:
            await ctx.message.delete()
        except:
            pass
            
    except discord.NotFound:
        await ctx.send("❌ Startup message not found!", delete_after=5)
        try:
            await ctx.message.delete()
        except:
            pass
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}", delete_after=5)
        try:
            await ctx.message.delete()
        except:
            pass

@bot.command()
async def setting_up(ctx):
    global latest_startup_message_id, latest_startup_host_id
    
    if not latest_startup_message_id or not latest_startup_host_id:
        await ctx.send("❌ No recent startup found!", delete_after=5)
        try:
            await ctx.message.delete()
        except:
            pass
        return
    
    session_channel = bot.get_channel(SESSION_CHANNEL_ID)
    if not session_channel:
        await ctx.send("❌ Session channel not found!", delete_after=5)
        try:
            await ctx.message.delete()
        except:
            pass
        return
    
    try:
        startup_message = await session_channel.fetch_message(latest_startup_message_id)
        host_user = await ctx.guild.fetch_member(latest_startup_host_id)
        
        await startup_message.reply(f"{host_user.mention} is now setting up the session! Please be patient and allow them to set up to 10 minutes!")
        
        try:
            await ctx.message.delete()
        except:
            pass
            
    except discord.NotFound:
        await ctx.send("❌ Startup message not found!", delete_after=5)
        try:
            await ctx.message.delete()
        except:
            pass
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}", delete_after=5)
        try:
            await ctx.message.delete()
        except:
            pass

@bot.command()
async def apply(ctx):
    if ctx.author.id in active_applications:
        await ctx.send("❌ You already have an active application!", delete_after=5)
        return
    
    await ctx.send("✅ Check your DMs to complete your application!", delete_after=5)
    
    questions = [
        "What is your Discord username?",
        "What is your Roblox username?",
        "What is your age?",
        "What country/timezone are you in?",
        "Have you ever been staff in another Roblox/Discord server before? (if yes, tell more about it)",
        "How many hours per week can you dedicate to moderating the server?",
        "Do you have experience using moderation tools (Discord commands, Greenville commands, etc.)?",
        "If a player is FailRP'ing (e.g., reckless driving, unrealistic behavior), how would you handle the situation?",
        "If two members are arguing and it escalates, what steps would you take to calm things down?",
        "If a fellow staff member is abusing their powers, what would you do?",
        "Why do you want to join the Greenville Roleplay Prism staff team?",
        "What skills, qualities, or strengths make you a good fit for staff?",
        "What will you bring to the Greenville Roleplay Prism?",
        "Do you understand that being staff requires professionalism, responsibility, and fairness at all times?",
        "Do you agree to follow all server rules and staff guidelines if accepted?"
    ]
    
    answers = []
    
    try:
        dm_channel = await ctx.author.create_dm()
        await dm_channel.send("📋 **Staff Application Started!**\nPlease answer the following questions. Type your answer and press Enter after each question.")
        
        for i, question in enumerate(questions, 1):
            embed = discord.Embed(
                title=f"Question {i}/15",
                description=question,
                color=discord.Color.blue()
            )
            await dm_channel.send(embed=embed)
            
            def check(m):
                return m.author == ctx.author and isinstance(m.channel, discord.DMChannel)
            
            try:
                answer = await bot.wait_for('message', check=check, timeout=300.0)
                answers.append(answer.content)
            except asyncio.TimeoutError:
                await dm_channel.send("❌ Application timed out. Please use ?apply to start again.")
                return
        
        await dm_channel.send("✅ Application submitted! Staff will review it soon.")
        
        active_applications[ctx.author.id] = answers
        
        review_channel = ctx.guild.get_channel(APPLICATION_CHANNEL_ID)
        
        embed = discord.Embed(
            title="📋 New Staff Application",
            description=f"**Applicant:** {ctx.author.mention}",
            color=discord.Color.blue()
        )
        
        for i, (question, answer) in enumerate(zip(questions, answers), 1):
            if len(answer) > 1024:
                answer = answer[:1021] + "..."
            embed.add_field(name=f"Q{i}: {question[:100]}", value=answer, inline=False)
        
        class ApplicationButtons(View):
            def __init__(self, applicant_id, guild_obj):
                super().__init__(timeout=None)
                self.applicant_id = applicant_id
                self.guild_obj = guild_obj
            
            @discord.ui.button(label="Accept", style=discord.ButtonStyle.green)
            async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                reviewer_role = interaction.guild.get_role(APPLICATION_REVIEWER_ROLE_ID)
                if reviewer_role not in interaction.user.roles:
                    await interaction.response.send_message("❌ You don't have permission to review applications.", ephemeral=True)
                    return
                
                modal = Modal(title="Accept Application")
                reason_input = TextInput(label="Reason for Acceptance", style=discord.TextStyle.paragraph, placeholder="Enter reason...")
                modal.add_item(reason_input)
                
                async def modal_callback(modal_interaction):
                    applicant = await self.guild_obj.fetch_member(self.applicant_id)
                    await modal_interaction.response.send_message(f"✅ Application from {applicant.mention} has been accepted by {interaction.user.mention}!\n**Reason:** {reason_input.value}")
                    
                    try:
                        await applicant.send(f"🎉 Congratulations! Your staff application for **{self.guild_obj.name}** has been accepted!\n**Reason:** {reason_input.value}")
                    except:
                        pass
                    
                    if self.applicant_id in active_applications:
                        del active_applications[self.applicant_id]
                    
                    for item in self.children:
                        item.disabled = True
                    await interaction.message.edit(view=self)
                
                modal.on_submit = modal_callback
                await interaction.response.send_modal(modal)
            
            @discord.ui.button(label="Deny", style=discord.ButtonStyle.red)
            async def deny_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                reviewer_role = interaction.guild.get_role(APPLICATION_REVIEWER_ROLE_ID)
                if reviewer_role not in interaction.user.roles:
                    await interaction.response.send_message("❌ You don't have permission to review applications.", ephemeral=True)
                    return
                
                modal = Modal(title="Deny Application")
                reason_input = TextInput(label="Reason for Denial", style=discord.TextStyle.paragraph, placeholder="Enter reason...")
                modal.add_item(reason_input)
                
                async def modal_callback(modal_interaction):
                    applicant = await self.guild_obj.fetch_member(self.applicant_id)
                    await modal_interaction.response.send_message(f"❌ Application from {applicant.mention} has been denied by {interaction.user.mention}.\n**Reason:** {reason_input.value}")
                    
                    try:
                        await applicant.send(f"❌ Unfortunately, your staff application for **{self.guild_obj.name}** has been denied.\n**Reason:** {reason_input.value}\n\nYou can reapply in the future.")
                    except:
                        pass
                    
                    if self.applicant_id in active_applications:
                        del active_applications[self.applicant_id]
                    
                    for item in self.children:
                        item.disabled = True
                    await interaction.message.edit(view=self)
                
                modal.on_submit = modal_callback
                await interaction.response.send_modal(modal)
        
        view = ApplicationButtons(ctx.author.id, ctx.guild)
        await review_channel.send(embed=embed, view=view)
        
    except discord.Forbidden:
        await ctx.send("❌ I couldn't DM you! Please enable DMs from server members and try again.", delete_after=10)

@bot.hybrid_command()
async def giveaway(ctx):
    staff_role = ctx.guild.get_role(STAFF_ROLE_ID)
    if staff_role not in ctx.author.roles:
        if isinstance(ctx, discord.Interaction):
            await ctx.response.send_message("❌ You don't have permission to start giveaways.", ephemeral=True)
        else:
            await ctx.send("❌ You don't have permission to start giveaways.", ephemeral=True)
        return

    modal = Modal(title="Create Giveaway")
    prize_input = TextInput(label="Prize", placeholder="Enter the prize")
    duration_input = TextInput(label="Duration (minutes)", placeholder="Enter duration in minutes")
    modal.add_item(prize_input)
    modal.add_item(duration_input)

    async def modal_callback(modal_interaction):
        try:
            duration = int(duration_input.value)
        except:
            await modal_interaction.response.send_message("❌ Invalid duration!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🎉 GIVEAWAY 🎉",
            description=f"**Prize:** {prize_input.value}\n**Duration:** {duration} minutes\n**Hosted by:** {ctx.author.mention}\n\nReact with 🎉 to enter!",
            color=discord.Color.gold()
        )
        
        try:
            file = discord.File("giveaway.png", filename="giveaway.png")
            embed.set_image(url="attachment://giveaway.png")
            message = await ctx.channel.send(content="@everyone", embed=embed, file=file)
        except FileNotFoundError:
            message = await ctx.channel.send(content="@everyone", embed=embed)
        
        await message.add_reaction("🎉")
        
        active_giveaways[message.id] = {
            'prize': prize_input.value,
            'duration': duration,
            'host': ctx.author.id,
            'end_time': modal_interaction.created_at.timestamp() + (duration * 60),
            'channel_id': ctx.channel.id
        }
        
        await modal_interaction.response.send_message(f"✓ Giveaway started! It will end in {duration} minutes.", ephemeral=True)

    modal.on_submit = modal_callback
    
    class GiveawayView(View):
        def __init__(self):
            super().__init__(timeout=60)
        
        @discord.ui.button(label="Create Giveaway", style=discord.ButtonStyle.blurple)
        async def giveaway_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_modal(modal)
    
    view = GiveawayView()
    
    if isinstance(ctx, discord.Interaction):
        await ctx.response.send_message("Click to create a giveaway:", view=view, ephemeral=True)
    else:
        await ctx.message.delete()
        await ctx.send("Click to create a giveaway:", view=view, delete_after=60)

@bot.command()
async def reroll(ctx, message_id: int):
    staff_role = ctx.guild.get_role(STAFF_ROLE_ID)
    if staff_role not in ctx.author.roles:
        await ctx.send("❌ You don't have permission to reroll giveaways.")
        return
    
    try:
        message = await ctx.channel.fetch_message(message_id)
    except:
        await ctx.send("❌ Message not found!")
        return
    
    reaction = discord.utils.get(message.reactions, emoji="🎉")
    if not reaction:
        await ctx.send("❌ No giveaway found on that message!")
        return
    
    users = [user async for user in reaction.users() if not user.bot]
    if not users:
        await ctx.send("❌ No valid entries!")
        return
    
    winner = random.choice(users)
    await ctx.send(f"🎉 New winner: {winner.mention}!")

@bot.command()
async def endgiveaway(ctx, message_id: int):
    staff_role = ctx.guild.get_role(STAFF_ROLE_ID)
    if staff_role not in ctx.author.roles:
        await ctx.send("❌ You don't have permission to end giveaways.")
        return
    
    try:
        message = await ctx.channel.fetch_message(message_id)
    except:
        await ctx.send("❌ Message not found!")
        return
    
    reaction = discord.utils.get(message.reactions, emoji="🎉")
    if not reaction:
        await ctx.send("❌ No giveaway found on that message!")
        return
    
    users = [user async for user in reaction.users() if not user.bot]
    if not users:
        await ctx.send("❌ No valid entries!")
        return
    
    winner = random.choice(users)
    
    if message_id in active_giveaways:
        prize = active_giveaways[message_id]['prize']
        del active_giveaways[message_id]
    else:
        prize = "Prize"
    
    await ctx.send(f"🎉 Giveaway ended! Winner: {winner.mention} won **{prize}**!")

@bot.command()
async def warn(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    staff_role = ctx.guild.get_role(STAFF_ROLE_ID)
    if staff_role not in ctx.author.roles:
        await ctx.send("❌ You don't have permission to warn users.")
        return
    
    role1 = ctx.guild.get_role(WARNING_ROLE_1)
    role2 = ctx.guild.get_role(WARNING_ROLE_2)
    role3 = ctx.guild.get_role(WARNING_ROLE_3)
    
    current_warning_count = 0
    if role3 in member.roles:
        current_warning_count = 3
    elif role2 in member.roles:
        current_warning_count = 2
    elif role1 in member.roles:
        current_warning_count = 1
    
    warning_count = current_warning_count + 1
    user_warnings[member.id] = warning_count
    
    if warning_count == 1:
        await member.add_roles(role1)
        await ctx.send(f"⚠️ {member.mention} has been warned! (Warning 1/3)\nReason: {reason}")
    elif warning_count == 2:
        await member.remove_roles(role1)
        await member.add_roles(role2)
        await ctx.send(f"⚠️ {member.mention} has been warned! (Warning 2/3)\nReason: {reason}")
    elif warning_count >= 3:
        await member.remove_roles(role1, role2)
        await member.add_roles(role3)
        await ctx.send(f"⚠️ {member.mention} has been warned! (Warning 3/3 - FINAL WARNING)\nReason: {reason}")
        
        alarm_channel = ctx.guild.get_channel(WARNING_STAFF_CHANNEL)
        if alarm_channel:
            alarm_embed = discord.Embed(
                title="🚨 FINAL WARNING ISSUED",
                description=f"**User:** {member.mention}\n**Warning Count:** 3/3 (FINAL)\n**Reason:** {reason}\n**Warned by:** {ctx.author.mention}",
                color=discord.Color.red(),
                timestamp=ctx.message.created_at
            )
            await alarm_channel.send(f"@everyone", embed=alarm_embed)
    
    warning_channel = ctx.guild.get_channel(WARNING_STAFF_CHANNEL)
    if warning_channel:
        embed = discord.Embed(
            title="⚠️ User Warned",
            description=f"**User:** {member.mention}\n**Warning Count:** {warning_count}/3\n**Reason:** {reason}\n**Warned by:** {ctx.author.mention}",
            color=discord.Color.orange(),
            timestamp=ctx.message.created_at
        )
        await warning_channel.send(embed=embed)

@bot.command()
async def rank(ctx, member: discord.Member = None):
    if not member:
        member = ctx.author
    
    if member.id not in user_levels:
        user_levels[member.id] = {'xp': 0, 'level': 1}
    
    level = user_levels[member.id]['level']
    xp = user_levels[member.id]['xp']
    xp_needed = level * 100
    
    embed = discord.Embed(title=f"{member.display_name}'s Rank", color=discord.Color.blue())
    embed.add_field(name="Level", value=level, inline=True)
    embed.add_field(name="XP", value=f"{xp}/{xp_needed}", inline=True)
    embed.set_thumbnail(url=member.display_avatar.url)
    
    await ctx.send(embed=embed)

@bot.command()
async def balance(ctx, member: discord.Member = None):
    if not member:
        member = ctx.author
    
    if member.id not in user_economy:
        user_economy[member.id] = {'wallet': 0, 'bank': 0, 'last_daily': None, 'last_work': None}
    
    wallet = user_economy[member.id]['wallet']
    bank = user_economy[member.id]['bank']
    
    embed = discord.Embed(title=f"💰 {member.display_name}'s Balance", color=discord.Color.green())
    embed.add_field(name="Wallet", value=f"${wallet}", inline=True)
    embed.add_field(name="Bank", value=f"${bank}", inline=True)
    embed.add_field(name="Total", value=f"${wallet + bank}", inline=True)
    
    await ctx.send(embed=embed)

@bot.command()
async def daily(ctx):
    if ctx.author.id not in user_economy:
        user_economy[ctx.author.id] = {'wallet': 0, 'bank': 0, 'last_daily': None, 'last_work': None}
    
    last_daily = user_economy[ctx.author.id]['last_daily']
    now = datetime.now()
    
    if last_daily:
        time_diff = (now - last_daily).total_seconds()
        if time_diff < 86400:
            hours_left = int((86400 - time_diff) / 3600)
            await ctx.send(f"❌ You already claimed your daily reward! Come back in {hours_left} hours.")
            return
    
    reward = random.randint(100, 500)
    user_economy[ctx.author.id]['wallet'] += reward
    user_economy[ctx.author.id]['last_daily'] = now
    
    await ctx.send(f"💰 You claimed your daily reward of ${reward}!")

@bot.command()
async def work(ctx):
    if ctx.author.id not in user_economy:
        user_economy[ctx.author.id] = {'wallet': 0, 'bank': 0, 'last_daily': None, 'last_work': None}
    
    last_work = user_economy[ctx.author.id]['last_work']
    now = datetime.now()
    
    if last_work:
        time_diff = (now - last_work).total_seconds()
        if time_diff < 3600:
            minutes_left = int((3600 - time_diff) / 60)
            await ctx.send(f"❌ You're tired! Rest for {minutes_left} more minutes.")
            return
    
    reward = random.randint(50, 200)
    user_economy[ctx.author.id]['wallet'] += reward
    user_economy[ctx.author.id]['last_work'] = now
    
    jobs = ["delivery driver", "cashier", "waiter", "mechanic", "taxi driver"]
    job = random.choice(jobs)
    
    await ctx.send(f"💼 You worked as a {job} and earned ${reward}!")

@bot.command()
async def deposit(ctx, amount: str):
    if ctx.author.id not in user_economy:
        user_economy[ctx.author.id] = {'wallet': 0, 'bank': 0, 'last_daily': None, 'last_work': None}
    
    if amount.lower() == "all":
        amount = user_economy[ctx.author.id]['wallet']
    else:
        try:
            amount = int(amount)
        except:
            await ctx.send("❌ Invalid amount!")
            return
    
    if amount > user_economy[ctx.author.id]['wallet']:
        await ctx.send("❌ You don't have that much money in your wallet!")
        return
    
    user_economy[ctx.author.id]['wallet'] -= amount
    user_economy[ctx.author.id]['bank'] += amount
    
    await ctx.send(f"✓ Deposited ${amount} to your bank!")

@bot.command()
async def withdraw(ctx, amount: str):
    if ctx.author.id not in user_economy:
        user_economy[ctx.author.id] = {'wallet': 0, 'bank': 0, 'last_daily': None, 'last_work': None}
    
    if amount.lower() == "all":
        amount = user_economy[ctx.author.id]['bank']
    else:
        try:
            amount = int(amount)
        except:
            await ctx.send("❌ Invalid amount!")
            return
    
    if amount > user_economy[ctx.author.id]['bank']:
        await ctx.send("❌ You don't have that much money in your bank!")
        return
    
    user_economy[ctx.author.id]['bank'] -= amount
    user_economy[ctx.author.id]['wallet'] += amount
    
    await ctx.send(f"✓ Withdrew ${amount} from your bank!")

@bot.command()
async def afk(ctx, *, reason: str = "AFK"):
    user_afk[ctx.author.id] = reason
    await ctx.send(f"{ctx.author.mention} is now AFK: {reason}")

@bot.command()
async def suggest(ctx, *, suggestion: str):
    global suggestion_counter
    
    if SUGGESTION_CHANNEL_ID is None:
        await ctx.send("❌ Suggestion channel not configured!")
        return
    
    suggestion_channel = ctx.guild.get_channel(SUGGESTION_CHANNEL_ID)
    if not suggestion_channel:
        await ctx.send("❌ Suggestion channel not found!")
        return
    
    suggestion_counter += 1
    
    embed = discord.Embed(
        title=f"💡 Suggestion #{suggestion_counter}",
        description=suggestion,
        color=discord.Color.blue(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
    embed.set_footer(text=f"Suggested by {ctx.author}")
    
    suggestion_message = await suggestion_channel.send(embed=embed)
    await suggestion_message.add_reaction("👍")
    await suggestion_message.add_reaction("👎")
    
    await ctx.send(f"✅ Your suggestion has been submitted!", delete_after=5)
    try:
        await ctx.message.delete()
    except:
        pass

@bot.command()
async def type(ctx, channel: discord.TextChannel = None, *, message: str = None):
    if not ctx.author.guild_permissions.manage_messages and STAFF_ROLE_ID not in [role.id for role in ctx.author.roles]:
        await ctx.send("❌ You don't have permission to use this command!", delete_after=5)
        try:
            await ctx.message.delete()
        except:
            pass
        return
    
    if not channel or not message:
        await ctx.send("❌ Usage: `?type #channel message`", delete_after=5)
        try:
            await ctx.message.delete()
        except:
            pass
        return
    
    try:
        await channel.send(message)
        await ctx.send(f"✅ Message sent to {channel.mention}!", delete_after=3)
        try:
            await ctx.message.delete()
        except:
            pass
    except discord.Forbidden:
        await ctx.send(f"❌ I don't have permission to send messages in {channel.mention}!", delete_after=5)
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}", delete_after=5)

@bot.command()
async def typembed(ctx, channel: discord.TextChannel = None, *, message: str = None):
    if not ctx.author.guild_permissions.manage_messages and STAFF_ROLE_ID not in [role.id for role in ctx.author.roles]:
        await ctx.send("❌ You don't have permission to use this command!", delete_after=5)
        try:
            await ctx.message.delete()
        except:
            pass
        return
    
    if not channel or not message:
        await ctx.send("❌ Usage: `?typembed #channel message`", delete_after=5)
        try:
            await ctx.message.delete()
        except:
            pass
        return
    
    try:
        embed = discord.Embed(
            description=message,
            color=discord.Color.orange()
        )
        await channel.send(embed=embed)
        await ctx.send(f"✅ Embed sent to {channel.mention}!", delete_after=3)
        try:
            await ctx.message.delete()
        except:
            pass
    except discord.Forbidden:
        await ctx.send(f"❌ I don't have permission to send messages in {channel.mention}!", delete_after=5)
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}", delete_after=5)

@bot.command()
async def suggestion(ctx, *, suggestion_text: str = None):
    global suggestion_counter, suggestion_cooldowns
    
    if not suggestion_text:
        await ctx.send("❌ Usage: `?suggestion <your suggestion>`", delete_after=5)
        try:
            await ctx.message.delete()
        except:
            pass
        return
    
    current_time = datetime.now(timezone.utc)
    user_id = ctx.author.id
    
    if user_id in suggestion_cooldowns:
        time_passed = (current_time - suggestion_cooldowns[user_id]).total_seconds()
        if time_passed < 3600:
            time_left = 3600 - time_passed
            minutes_left = int(time_left // 60)
            seconds_left = int(time_left % 60)
            await ctx.send(f"❌ You can only submit 1 suggestion per hour! Please wait {minutes_left}m {seconds_left}s.", delete_after=10)
            try:
                await ctx.message.delete()
            except:
                pass
            return
    
    suggestion_channel = bot.get_channel(SUGGESTION_CHANNEL_ID)
    if not suggestion_channel:
        await ctx.send("❌ Suggestion channel not found!", delete_after=5)
        return
    
    try:
        suggestion_counter += 1
        
        embed = discord.Embed(
            title=f"💡 Suggestion #{suggestion_counter}",
            description=suggestion_text,
            color=discord.Color.blue(),
            timestamp=current_time
        )
        embed.set_footer(text=f"Suggested by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        
        suggestion_msg = await suggestion_channel.send(f"{ctx.author.mention}", embed=embed)
        
        await suggestion_msg.add_reaction("👍")
        await suggestion_msg.add_reaction("👎")
        
        suggestion_cooldowns[user_id] = current_time
        
        await ctx.send(f"✅ Your suggestion has been submitted to {suggestion_channel.mention}!", delete_after=5)
        try:
            await ctx.message.delete()
        except:
            pass
            
    except Exception as e:
        await ctx.send(f"❌ Error submitting suggestion: {str(e)}", delete_after=5)

@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="📚 Greenville Roleplay Prism Bot Commands",
        description="Here are all available commands:",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="🎮 Session Commands",
        value="**?startup** - Start a session (Session Host only)\n"
              "**?release_early <link>** - Early release (Session Host only)\n"
              "**?release** - Full release (Session Host only)\n"
              "**?sessionend** - End session (Session Host only)\n"
              "**?cohost @user** - Add co-host (Co-Host Role only, max 3)\n"
              "**?setting_up** - Notify session is being set up",
        inline=False
    )
    
    embed.add_field(
        name="🎫 Ticket Commands",
        value="**?adduser @user** - Add user to ticket\n"
              "**?removeuser @user** - Remove user from ticket",
        inline=False
    )
    
    embed.add_field(
        name="⚙️ Staff Commands",
        value="**?warn @user [reason]** - Warn a user\n"
              "**?timeout @user <minutes> [reason]** - Timeout user\n"
              "**?untimeout @user** - Remove timeout\n"
              "**?kick @user [reason]** - Kick user\n"
              "**?ban @user [reason]** - Ban user\n"
              "**?clear [amount]** - Clear messages",
        inline=False
    )
    
    embed.add_field(
        name="🎉 Fun Commands",
        value="**?giveaway** - Start a giveaway (Staff only)\n"
              "**?reroll <message_id>** - Reroll giveaway (Staff only)\n"
              "**?endgiveaway <message_id>** - End giveaway (Staff only)",
        inline=False
    )
    
    embed.add_field(
        name="📊 Economy & Leveling",
        value="**?rank [@user]** - Check rank\n"
              "**?balance [@user]** - Check balance\n"
              "**?daily** - Claim daily reward\n"
              "**?work** - Work for money\n"
              "**?deposit <amount|all>** - Deposit money\n"
              "**?withdraw <amount|all>** - Withdraw money",
        inline=False
    )
    
    embed.add_field(
        name="💬 Utility Commands",
        value="**?type #channel <message>** - Send message to channel (Staff)\n"
              "**?typembed #channel <message>** - Send orange embed to channel (Staff)\n"
              "**?suggestion <text>** - Submit suggestion (1 per hour)\n"
              "**?afk [reason]** - Set AFK status\n"
              "**?apply** - Apply for staff",
        inline=False
    )
    
    await ctx.send(embed=embed)

try:
    bot.run(TOKEN)
except Exception as e:
    print(f"Error running bot: {e}")
