
"""
Gary - SolarVox
Open Source Discord Bot

Copyright (c) 2025 SolarVox Development

Licensed under the MIT License. See LICENSE file for details.
"""

import discord
from discord import Embed
from discord.ext import commands, tasks
from discord import app_commands
from discord.ui import Button, View
import json
import random
import logging
from datetime import timedelta
import asyncio

# -------------------------------
# Optional MariaDB / MySQL setup
# -------------------------------
# import mysql.connector
# db = mysql.connector.connect(
#     host="localhost",
#     user="root",
#     password="password",
#     database="solarvox_db"
# )
# cursor = db.cursor()
# Use this for storing persistent data instead of JSON if desired.

footer = "COPYRIGHT"
footer_text = "© SolarVox 2025" if footer == "COPYRIGHT" else footer

CONFIG_FILE = "config.json"

def load_config():
    try:
        with open(CONFIG_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

config = load_config()

def save_config():
    with open(CONFIG_FILE, "w") as file:
        json.dump(config, file, indent=4)

# Add default server config
async def add_server_config(guild):
    if str(guild.id) not in config:
        config[str(guild.id)] = {
            "prefix": "C!",
            "welcome_channel": 0,
            "log_channel": 0,
            "ticket_category": 0,
            "admin_role": 0,
            "anti_link": True,
            "welcome_message": "Welcome to {guild.name}, {user}!",
            "leave_message": "Goodbye, {user}!"
        }
        save_config()
        print(f" Added default config for server: {guild.name} ({guild.id})")

# Bot setup
intents = discord.Intents.all()
intents.message_content = True 
bot = commands.Bot(command_prefix=config.get("prefix", "C!"), intents=intents)

def parse_time(duration: str) -> timedelta:
    units = {"s": "seconds", "m": "minutes", "h": "hours"}
    unit = duration[-1]
    amount = int(duration[:-1])
    return timedelta(**{units[unit]: amount})

@bot.event
async def on_guild_join(guild):
    await add_server_config(guild)


statuses = [
    "/trivia test ur brain! ",
    "Gary oveerses {guild_count} guilds",
    "C!8ball Test your luck!",
    "Do /help for cmds",
    "30 Commands C! and /"
]


@bot.event
async def on_ready():
    print(f" Gary is online as {bot.user}!")
    for guild in bot.guilds:
        await add_server_config(guild)
    try:
        synced = await bot.tree.sync()
        print(f" Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f" Error syncing commands: {e}")
    rotate_status.start()

@tasks.loop(seconds=20)
async def rotate_status():
    for status in statuses:
        guild_count = len(bot.guilds)
        activity = discord.CustomActivity(name=status.format(guild_count=guild_count))
        await bot.change_presence(status=discord.Status.dnd, activity=activity)
        await asyncio.sleep(20)  



# Welcome and Leave Messages
@bot.event
async def on_member_join(member):
    channel = bot.get_channel(config["welcome_channel"])
    if channel:
        welcome_message = config["welcome_message"].replace("{user}", member.mention)
        await channel.send(embed=discord.Embed(
            title="Welcome!",
            description=welcome_message,
            color=0x00FF00).set_footer(text=footer_text))

@bot.event
async def on_member_remove(member):
    channel = bot.get_channel(config["welcome_channel"])
    if channel:
        leave_message = config["leave_message"].replace("{user}", member.name)
        await channel.send(embed=discord.Embed(
            title="Farewell!",
            description=leave_message,
            color=0xFF0000).set_footer(text=footer_text))

# Logging Events
@bot.event
async def on_message_delete(message):
    channel = bot.get_channel(config["log_channel"])
    if channel:
        embed = discord.Embed(title="🗑️ Message Deleted", description=f"**Content:** {message.content}", color=0xFF4500)
        embed.set_author(name=message.author.name, icon_url=message.author.display_avatar.url)
        embed.set_footer(text=f"{footer_text} | Channel: {message.channel.name}")
        await channel.send(embed=embed)

# Moderation Commands (Prefix & Slash)
async def ban_member(interaction, member, reason):
    await member.ban(reason=reason)
    await interaction.response.send_message(embed=discord.Embed(
        title="🔨 User Banned",
        description=f"Banned {member.mention} for: {reason}",
        color=0xFF0000).set_footer(text=footer_text)) 

@bot.tree.command(name="ban", description="Ban a user from the server.")
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    await ban_member(interaction, member, reason)

@bot.command(name="ban")
async def ban_prefix(ctx, member: discord.Member, *, reason="No reason provided"):
    await ban_member(ctx, member, reason)

async def kick_member(interaction, member, reason):
    await member.kick(reason=reason)
    await interaction.response.send_message(embed=discord.Embed(
        title="👢 User Kicked",
        description=f"Kicked {member.mention} for: {reason}",
        color=0xFFAA00).set_footer(text=footer_text))

@bot.tree.command(name="kick", description="Kick a user from the server.")
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    await kick_member(interaction, member, reason)

@bot.command(name="kick")
async def kick_prefix(ctx, member: discord.Member, *, reason="No reason provided"):
    await kick_member(ctx, member, reason)

# Unban Command
async def unban_member(interaction, user_id, reason):
    user = await bot.fetch_user(user_id)
    await bot.unban(user)
    await interaction.response.send_message(embed=discord.Embed(
        title="🔓 User Unbanned",
        description=f"Unbanned {user.mention} for: {reason}",
        color=0x00FF00).set_footer(text=footer_text))

@bot.tree.command(name="unban", description="Unban a user from the server.")
async def unban(interaction: discord.Interaction, user_id: int, reason: str = "No reason provided"):
    await unban_member(interaction, user_id, reason)

@bot.command(name="unban")
async def unban_prefix(ctx, user_id: int, *, reason="No reason provided"):
    await unban_member(ctx, user_id, reason)

# Mute Command (Prefix & Slash)
async def mute_member(interaction, member, reason):
    role = discord.utils.get(member.guild.roles, name="Muted")
    if not role:
        role = await member.guild.create_role(name="Muted", permissions=discord.Permissions(send_messages=False))
    await member.add_roles(role)
    await interaction.response.send_message(embed=discord.Embed(
        title="🔇 User Muted",
        description=f"Muted {member.mention} for: {reason}",
        color=0xFF0000).set_footer(text=footer_text))

@bot.tree.command(name="mute", description="Mute a user.")
async def mute(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    await mute_member(interaction, member, reason)

@bot.command(name="mute")
async def mute_prefix(ctx, member: discord.Member, *, reason="No reason provided"):
    await mute_member(ctx, member, reason)

# Unmute Command (Prefix & Slash)
async def unmute_member(interaction, member):
    role = discord.utils.get(member.guild.roles, name="Muted")
    if role:
        await member.remove_roles(role)
    await interaction.response.send_message(embed=discord.Embed(
        title="🔊 User Unmuted",
        description=f"Unmuted {member.mention}",
        color=0x00FF00).set_footer(text=footer_text))

@bot.tree.command(name="unmute", description="Unmute a user.")
async def unmute(interaction: discord.Interaction, member: discord.Member):
    await unmute_member(interaction, member)

@bot.command(name="unmute")
async def unmute_prefix(ctx, member: discord.Member):
    await unmute_member(ctx, member)

@bot.tree.command(name="ping", description="Check the bot's latency.")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"🏓 Pong! Latency: '''{latency}ms'''")

@bot.command(name="ping")
async def ping_prefix(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! Latency: '''{latency}ms'''")

@bot.tree.command(name="8ball", description="Ask the magic 8-ball a question.")
async def eight_ball(interaction: discord.Interaction, question: str):
    responses = ["Yes", "No", "Maybe", "Definitely", "I don't know"]
    await interaction.response.send_message(embed=discord.Embed(
        title="🎱 Magic 8-Ball",
        description=f"Question: {question}\nAnswer: {random.choice(responses)}",
        color=0x2ECC71).set_footer(text=footer_text))

@bot.command(name="8ball")
async def eightball_prefix(ctx, question: str):
    responses = ["Yes", "No", "Maybe", "Definitely", "I don't know"]
    await ctx.send(f"🎱 Magic 8-Ball says: {random.choice(responses)}")

# Image Manipulation Command (PFP Steal)
@bot.tree.command(name="pfp_steal", description="Steal someone's profile picture.")
async def pfp_steal(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.send_message(embed=discord.Embed(
        title=f"🖼️ {member.name}'s Profile Picture",
        description=f"Here's {member.name}'s profile picture:",
        color=0xFF69B4).set_image(url=member.display_avatar.url).set_footer(text=footer_text))

@bot.command(name="pfp_steal")
async def pfp_steal_prefix(ctx, member: discord.Member):
    await ctx.send(f"🖼️ {member.name}'s Profile Picture: {member.display_avatar.url}")

# Configuration Command (Prefix & Slash)
async def update_config(interaction, key, value):
    config[key] = int(value) if value.isdigit() else value
    with open(CONFIG_FILE, "w") as file:
        json.dump(config, file, indent=4)
    await interaction.response.send_message(f"✅ Configuration updated: {key} = {value}")





@bot.tree.command(name="config", description="Update bot settings.")
async def config_cmd(interaction: discord.Interaction, key: str, value: str):
    await update_config(interaction, key, value)

@bot.command(name="config")
async def config_prefix(ctx, key: str, value: str):
    await update_config(ctx, key, value)

async def timeout_member(interaction, member, duration, reason="No reason provided"):
    try:
        await member.timeout(parse_time(duration), reason=reason)
        await interaction.response.send_message(embed=discord.Embed(
            title="⏲️ User Timed Out",
            description=f"Timed out {member.mention} for {duration}. Reason: {reason}",
            color=0xFF0000).set_footer(text=footer_text))
    except Exception as e:
        await interaction.response.send_message(f"Error: {str(e)}")

@bot.tree.command(name="timeout", description="Timeout a user for a specific duration.")
async def timeout(interaction: discord.Interaction, member: discord.Member, duration: str, reason: str = "No reason provided"):
    await timeout_member(interaction, member, duration, reason)

@bot.command(name="timeout")
async def timeout_prefix(ctx, member: discord.Member, duration: str, *, reason="No reason provided"):
    await timeout_member(ctx, member, duration, reason)

# ✅ Untimeout Command
async def untimeout_member(interaction, member):
    try:
        await member.timeout(None)
        await interaction.response.send_message(embed=discord.Embed(
            title="✅ User Untimed Out",
            description=f"Removed timeout from {member.mention}.",
            color=0x00FF00).set_footer(text=footer_text))
    except Exception as e:
        await interaction.response.send_message(f"Error: {str(e)}")

@bot.tree.command(name="untimeout", description="Remove timeout from a user.")
async def untimeout(interaction: discord.Interaction, member: discord.Member):
    await untimeout_member(interaction, member)

@bot.command(name="untimeout")
async def untimeout_prefix(ctx, member: discord.Member):
    await untimeout_member(ctx, member)


@bot.tree.command(name="rps", description="Play Rock, Paper, Scissors.")
async def rps(interaction: discord.Interaction, choice: str):
    choices = ["rock", "paper", "scissors"]
    bot_choice = random.choice(choices)
    result = "It's a tie!" if choice == bot_choice else "You win!" if (choice, bot_choice) in [("rock", "scissors"), ("paper", "rock"), ("scissors", "paper")] else "You lose!"
    await interaction.response.send_message(f"🪨 {choice.capitalize()} vs {bot_choice.capitalize()} - {result}")

@bot.tree.command(name="coinflip", description="Flip a coin.")
async def coinflip(interaction: discord.Interaction):
    result = random.choice(["Heads", "Tails"])
    await interaction.response.send_message(f"🪙 Coin flip: **{result}**")

@bot.tree.command(name="roll", description="Roll a 6-sided dice.")
async def roll(interaction: discord.Interaction):
    result = random.randint(1, 6)
    await interaction.response.send_message(f"🎲 You rolled a **{result}**!")

trivia_questions = [
    ("What is the capital of France?", "Paris"),
    ("Who wrote 'To Kill a Mockingbird'?", "Harper Lee"),
    ("What planet is known as the Red Planet?", "Mars"),
    ("What is the largest mammal?", "Blue whale"),
    ("In which year did the Titanic sink?", "1912"),
    ("What is the smallest country in the world?", "Vatican City"),
    ("Who painted the Mona Lisa?", "Leonardo da Vinci"),
    ("What is the longest river in the world?", "Amazon River"),
    ("Which country is known as the Land of the Rising Sun?", "Japan"),
    ("Who was the first president of the United States?", "George Washington"),
    ("What is the hardest natural substance on Earth?", "Diamond"),
    ("Which element has the chemical symbol 'O'?", "Oxygen"),
    ("What is the capital of Australia?", "Canberra"),
    ("Which ocean is the largest?", "Pacific Ocean"),
    ("In which year did World War II end?", "1945"),
    ("Who developed the theory of relativity?", "Albert Einstein"),
    ("What is the name of the first man to walk on the moon?", "Neil Armstrong"),
    ("What is the tallest mountain in the world?", "Mount Everest"),
    ("Which animal is known as the King of the Jungle?", "Lion"),
    ("Which planet is closest to the sun?", "Mercury"),
    ("What is the longest bone in the human body?", "Femur"),
    ("Who wrote 'Romeo and Juliet'?", "William Shakespeare"),
    ("What is the capital of Japan?", "Tokyo"),
    ("Which country invented the pizza?", "Italy"),
    ("What is the largest desert in the world?", "Sahara Desert"),
    ("In what year did the first manned moon landing take place?", "1969"),
    ("Who discovered penicillin?", "Alexander Fleming"),
    ("Which country is the largest by land area?", "Russia"),
    ("What is the national flower of Japan?", "Cherry Blossom"),
    ("Who was the first woman to win a Nobel Prize?", "Marie Curie"),
    ("What is the chemical symbol for gold?", "Au"),
    ("Which planet is known for its rings?", "Saturn"),
    ("What is the main ingredient in guacamole?", "Avocado"),
    ("Which ocean separates the United States from Europe?", "Atlantic Ocean"),
    ("Which famous scientist developed the laws of motion?", "Isaac Newton"),
    ("Who painted the Sistine Chapel ceiling?", "Michelangelo"),
    ("What year did the Berlin Wall fall?", "1989"),
    ("What is the world's most widely spoken language?", "Mandarin Chinese"),
    ("Who is the author of the Harry Potter series?", "J.K. Rowling"),
    ("Which animal can be seen on the Porsche logo?", "Horse"),
    ("What is the capital of Canada?", "Ottawa"),
    ("What is the world's largest island?", "Greenland"),
    ("Which famous ship sank on its maiden voyage in 1912?", "Titanic"),
    ("Which country is known as the 'Land of the Midnight Sun'?", "Norway"),
    ("What element is represented by the symbol 'Na'?", "Sodium"),
    ("What is the tallest building in the world?", "Burj Khalifa"),
    ("Which continent is the Sahara Desert located on?", "Africa"),
    ("Which chemical element has the atomic number 1?", "Hydrogen"),
    ("What is the name of the fairy in Peter Pan?", "Tinker Bell"),
    ("What is the smallest bone in the human body?", "Stapes"),
    ("Who was the first woman to fly solo across the Atlantic Ocean?", "Amelia Earhart"),
    ("What is the most common blood type?", "O positive"),
    ("Which city is known as the Big Apple?", "New York City"),
    ("Which country is known as the birthplace of democracy?", "Greece"),
    ("Which animal is the largest land mammal?", "Elephant"),
    ("What is the capital of Egypt?", "Cairo"),
    ("Who invented the lightbulb?", "Thomas Edison"),
    ("In what year did the first iPhone launch?", "2007"),
    ("What is the largest volcano in the world?", "Mauna Loa"),
    ("Which planet is known as the 'Giant Planet'?", "Jupiter"),
    ("Which sea is the saltiest?", "Dead Sea"),
    ("Who was the first emperor of China?", "Qin Shi Huang"),
    ("What is the capital of Italy?", "Rome"),
    ("Who was the first female Prime Minister of the United Kingdom?", "Margaret Thatcher"),
    ("Which country has the most pyramids?", "Sudan"),
    ("What is the capital of Brazil?", "Brasília"),
    ("Which country is home to the Great Barrier Reef?", "Australia"),
    ("Which sport is known as 'the king of sports'?", "Soccer"),
    ("Who was the first African-American president of the United States?", "Barack Obama"),
    ("What is the tallest waterfall in the world?", "Angel Falls"),
    ("Which city is famous for its canals and gondolas?", "Venice"),
    ("Which country is known as the Land of Ice and Fire?", "Iceland"),
    ("Which country has the most official languages?", "South Africa"),
    ("What is the capital of Spain?", "Madrid"),
    ("What is the world's largest coral reef system?", "Great Barrier Reef"),
    ("What is the national sport of Canada?", "Hockey"),
    ("Who was the first man to climb Mount Everest?", "Sir Edmund Hillary"),
    ("Which country is known for the invention of paper?", "China"),
    ("What is the main ingredient of tofu?", "Soybeans"),
    ("Who was the first person to reach the South Pole?", "Roald Amundsen"),
    ("What is the smallest planet in our solar system?", "Mercury"),
    ("Which bird is known for its colorful feathers and mimicking sounds?", "Parrot"),
    ("Who discovered America?", "Christopher Columbus"),
    ("What is the capital of Mexico?", "Mexico City"),
    ("What does the acronym 'HTML' stand for?", "HyperText Markup Language"),
    ("Which fruit has its seeds on the outside?", "Strawberry"),
    ("What is the symbol for the chemical element carbon?", "C"),
    ("What animal is featured in the logo of Ferrari?", "Horse"),
    ("What is the largest country in Africa?", "Algeria"),
    ("What is the national animal of Canada?", "Beaver"),
    ("Who wrote 'Pride and Prejudice'?", "Jane Austen"),
    ("Which country is famous for sushi?", "Japan"),
    ("What is the highest recorded temperature on Earth?", "134°F (56.7°C)"),
    ("What is the currency of the United Kingdom?", "Pound Sterling"),
    ("What is the capital of India?", "New Delhi"),
    ("Which planet is known as the Morning Star?", "Venus"),
    ("Which element is represented by the symbol 'Fe'?", "Iron"),
    ("What is the only continent without a desert?", "Europe"),
    ("Who is known as the 'Father of Modern Physics'?", "Albert Einstein"),
    ("Which country is the largest producer of coffee?", "Brazil"),
    ("Which fruit is known as the king of fruits?", "Durian"),
    ("What is the name of the largest moon of Saturn?", "Titan"),
    ("Which American president issued the Emancipation Proclamation?", "Abraham Lincoln"),
    ("What is the capital of South Korea?", "Seoul"),
    ("Which country is famous for its ancient pyramids?", "Egypt")
]



@bot.tree.command(name="trivia", description="Answer a random trivia question.")
async def trivia(interaction: discord.Interaction):
    question, answer = random.choice(trivia_questions)  # Choose a random question-answer pair
    bot.current_question = (question, answer)  # Store the current question and answer
    await interaction.response.send_message(f"❓ {question}\n*(Type your answer below)*")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Check if there is a current question stored
    if hasattr(bot, "current_question"):
        question, correct_answer = bot.current_question

        # Check the answer (case insensitive)
        if message.content.strip().lower() == correct_answer.lower():
            await message.channel.send("✅ Correct!")
            bot.current_question = None  # Clear after correct answer
        else:
            await message.channel.send(f"❌ Incorrect. The correct answer was: {correct_answer}.")
            bot.current_question = None

    await bot.process_commands(message)


@bot.event
async def on_message(message):
    # Avoid the bot responding to itself or other bots
    if message.author.bot:
        return

    # Anti-link check (if enabled)
    if config["anti_link"] and "http" in message.content and not message.author.guild_permissions.administrator:
        await message.delete()
        await message.channel.send(embed=discord.Embed(
            title="🚫 Anti-Link Protection",
            description=f"{message.author.mention}, links are not allowed!",
            color=0xFF0000).set_footer(text=footer_text))
        return

   
    # Trivia answer check
    for question, answer in trivia_questions:
        if message.content.lower() == answer.lower():
            await message.channel.send(f"🎉 Correct! The answer is **{answer}**.")
            return

    # Process other commands normally
    await bot.process_commands(message)


    # Process other bot commands
    await bot.process_commands(message)



# Help Command with two pages
@bot.tree.command(name="help", description="Show help for commands.")
async def help_cmd(interaction: discord.Interaction):
    # Define the help pages
    page1 = """
    **Bot - Prefix Commands (C!)**:
    - `C!ping` - Check the bot's latency.
    - `C!8ball [question]` - Ask the magic 8-ball a question.
    - `C!ban [user] [reason]` - Ban a user.
    - `C!kick [user] [reason]` - Kick a user.
    - `C!mute [user] [reason]` - Mute a user.
    - `C!unmute [user]` - Unmute a user.
    - `C!unban [user_id] [reason]` - Unban a user.
    - `C!timeout [user] [duration] [reason]` - Timeout a user.
    - `C!untimeout [user]` - Remove timeout from a user.
    - `C!setup_ticket` - Set up the ticket panel.
    - `C!config [key] [value]` - Update bot configuration.
    - `C!pfp_steal [user]` - Steal someone's profile picture.
    """

    page2 = """
    **Bot - Slash Commands (/)**:
    - `/ping` - Check the bot's latency.
    - `/8ball [question]` - Ask the magic 8-ball a question.
    - `/ban [user] [reason]` - Ban a user.
    - `/kick [user] [reason]` - Kick a user.
    - `/mute [user] [reason]` - Mute a user.
    - `/unmute [user]` - Unmute a user.
    - `/unban [user_id] [reason]` - Unban a user.
    - `/timeout [user] [duration] [reason]` - Timeout a user.
    - `/untimeout [user]` - Remove timeout from a user.
    - `/rps [choice]` - Play Rock, Paper, Scissors.
    - `/coinflip` - Flip a coin.
    - `/roll` - Roll a 6-sided dice.
    - `/trivia` - Answer a random trivia question.
    - `/config [key] [value]` - Update bot configuration.
    - `/pfp_steal [user]` - Steal someone's profile picture.
    """

    # Create the first page embed
    embed1 = discord.Embed(
        title="Help (Page 1)",
        description=page1,
        color=0x3498DB
    ).set_footer(text="Use the buttons below to navigate pages.")

    embed2 = discord.Embed(
        title="Help (Page 2)",
        description=page2,
        color=0x3498DB
    ).set_footer(text="Use the buttons below to navigate pages.")

    # Create the buttons
    button_prev = Button(label="< Previous", style=discord.ButtonStyle.primary)
    button_next = Button(label="Next >", style=discord.ButtonStyle.primary)

    # Create the view
    view = View()

    # Define button actions
    async def on_prev_click(interaction: discord.Interaction):
        await interaction.response.edit_message(embed=embed1, view=view)

    async def on_next_click(interaction: discord.Interaction):
        await interaction.response.edit_message(embed=embed2, view=view)

    # Add actions to buttons
    button_prev.callback = on_prev_click
    button_next.callback = on_next_click

    # Add buttons to view
    view.add_item(button_prev)
    view.add_item(button_next)

    # Send the initial help message
    await interaction.response.send_message(embed=embed1, view=view)


# Error Handling
@bot.event
async def on_command_error(ctx, error):
    await ctx.send(f"⚠️ Error: {str(error)}")

# Run the bot

bot.run("") # Put You Discord Bot Token Here
