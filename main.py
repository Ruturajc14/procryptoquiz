import discord
from discord import app_commands
import os, random, requests
from flask import Flask
from threading import Thread
from openai import OpenAI

# ---------- CONFIG ----------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai_client = OpenAI(api_key=OPENAI_API_KEY)

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# ---------- DATA ----------
scores = {}
scam_count = 0

quiz_questions = [
    ("Tempo is mainly designed for?", ["Gaming", "Payments & Stablecoins", "NFTs"], 1),
    ("What is a stablecoin?", ["Volatile coin", "Fixed value crypto", "Meme coin"], 1),
    ("USDC is pegged to?", ["BTC", "USD", "ETH"], 1)
]

scam_words = [
    "free crypto", "airdrop", "verify wallet",
    "double your money", "bit.ly", "tinyurl"
]

# ---------- DISCORD EVENTS ----------
@client.event
async def on_ready():
    await tree.sync()
    print("✅ Bot is online")

@client.event
async def on_message(message):
    global scam_count
    if message.author.bot:
        return

    text = message.content.lower()
    if "http" in text or any(w in text for w in scam_words):
        scam_count += 1
        await message.delete()
        await message.channel.send(
            f"🚨 {message.author.mention} scam message removed"
        )

# ---------- SLASH COMMANDS ----------
@tree.command(name="ask", description="Ask AI about Tempo / crypto")
async def ask(interaction: discord.Interaction, question: str):
    await interaction.response.defer()
    res = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a Tempo blockchain assistant."},
            {"role": "user", "content": question}
        ],
        max_tokens=120
    )
    await interaction.followup.send(res.choices[0].message.content)

@tree.command(name="price", description="Get crypto price")
async def price(interaction: discord.Interaction, coin: str):
    data = requests.get(
        "https://api.coingecko.com/api/v3/simple/price",
        params={"ids": coin, "vs_currencies": "usd"}
    ).json()

    if coin not in data:
        await interaction.response.send_message("❌ Coin not found")
        return

    await interaction.response.send_message(
        f"💰 {coin.upper()} = ${data[coin]['usd']}"
    )

@tree.command(name="quiz", description="Play quiz")
async def quiz(interaction: discord.Interaction):
    q, options, correct = random.choice(quiz_questions)
    scores.setdefault(interaction.user.id, 0)

    text = f"🧠 **{q}**\n"
    for i, opt in enumerate(options):
        text += f"{i+1}. {opt}\n"

    await interaction.response.send_message(text)
    client.correct = correct
    client.last_user = interaction.user.id

@tree.command(name="leaderboard", description="Show leaderboard")
async def leaderboard(interaction: discord.Interaction):
    if not scores:
        await interaction.response.send_message("No scores yet")
        return

    msg = "🏆 **Leaderboard**\n"
    for uid, sc in sorted(scores.items(), key=lambda x: x[1], reverse=True):
        user = await client.fetch_user(uid)
        msg += f"{user.name} : {sc}\n"

    await interaction.response.send_message(msg)

# ---------- DASHBOARD ----------
app = Flask(__name__)

@app.route("/")
def home():
    return f"""
    <h1>Tempo Bot Dashboard</h1>
    <p>Bot: Online</p>
    <p>Scam blocked: {scam_count}</p>
    <p>Users played quiz: {len(scores)}</p>
    """

def run_dashboard():
    app.run(host="0.0.0.0", port=8080)

Thread(target=run_dashboard).start()
client.run(DISCORD_TOKEN)
