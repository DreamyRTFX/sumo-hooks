import asyncio
import discord
from discord.ext import commands, tasks
import discord.app_commands as app_commands

import threading
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import os
import requests
import json
from datetime import datetime, timezone
import hmac
import hashlib
import base64

load_dotenv()
_secret = os.getenv('SECRET')
host = os.getenv('MYIP')
port = os.getenv('PORT')
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# Discord bot setup with hybrid commands
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

async def smokeyBot():
    await bot.start(DISCORD_TOKEN)

@bot.event
async def on_ready():
    print(f'Bot logged in as {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash command(s)")

    except Exception as e:
        print(f"Error syncing commands: {e}")

@bot.command()
async def hello(ctx):

    for guild in bot.guilds:
        # Try to find #general channel
        try:
            channel = discord.utils.get(guild.text_channels, name="sumo")
        except Exception as e:
            print(f"Error finding #sumo channel in server {guild.name}: {e}")
        # Fallback to system channel if #general not found
        if channel:
            await channel.send("Hello, Sumo World!")
        if not channel and guild.system_channel:
            channel = guild.system_channel
            await channel.send("Hello, General World!")
        else:
            print(f"No suitable channel found in server {guild.name}")

@bot.command()
async def torikumi(ctx):
    try:
        tk = load_data("latest_newMatches.json")
        t = format_match(tk)
        print (t)
    except Exception as e:
        print("Exception while load/format ", e)
    for guild in bot.guilds:
        # Try to find #general channel
        try:
            channel = discord.utils.get(guild.text_channels, name="sumo")
        except Exception as e:
            print(f"Error finding #sumo channel in server {guild.name}: {e}")
        # Fallback to system channel if #general not found
        if channel:
            await channel.send(f"""'''Today's torikumi:\n {t}'''""")

        else:
            print(f"No suitable channel found in server {guild.name}")

app = Flask(__name__)

def run_flask():
    app.run(host=host, port=port)

@app.route("/matchresults", methods=["POST"])
def matchresults():
    
    global _secret
    content = request.json
    payload: bytes = content.get("payload")
    decoded_bytes = base64.b64decode(payload)
    decoded_json = json.loads(decoded_bytes.decode("utf-8"))
    sig = request.headers.get("X-Webhook-Signature")
    print(sig)
    print(calc_sig(request.base_url, decoded_bytes, _secret))
    print(decoded_json)
    today = datetime.date.today().isoformat()

    save_data(decoded_json, f"{today}_matchResults.json")    #save today's data separately
    save_data(decoded_json, "latest_matchResults.json")
    #accumulate_data(decoded_json, "matchResults.json")

    return jsonify(message={"state": "succeeded"}, status=204), 204

@app.route("/newmatches", methods=["POST"])
def newmatches():
    
    global _secret
    content = request.json
    payload: bytes = content.get("payload")
    decoded_bytes = base64.b64decode(payload)
    decoded_json = json.loads(decoded_bytes.decode("utf-8"))
    sig = request.headers.get("X-Webhook-Signature")
    print(sig)
    print(calc_sig(request.base_url, decoded_bytes, _secret))
    print(decoded_json)

    today = datetime.date.today().isoformat()
    save_data(decoded_json, f"{today}_newMatches.json")    #save today's data separately
    save_data(decoded_json, "latest_newMatches.json")
    #accumulate_data(decoded_json, "newMatches.json")

    return jsonify(message={"state": "succeeded"}, status=204), 204

def decode_data(content):
    payload: bytes = content.get("payload")
    decoded_bytes = base64.b64decode(payload)
    decoded_json = json.loads(decoded_bytes.decode("utf-8"))
    return decoded_json
    
def load_data(filename):
    try:
        with open (filename, "r",encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"JSON Decode error: {e}")
        return
    except FileNotFoundError as e:
        with open (filename, "w") as f: # if not exist, make file
            f.close
            return
    
def save_data (data, filename):
    with open (filename, "w") as f:
        json.dump(data, f)
        return

def format_match(data):     # process newMatches torikumi format
    sch=""
    wr = get_wr()
    for match in data:
        westname = match.get("westShikona")
        eastname = match.get("eastShikona")
        westid = wr.get(match.get("westId"), "n/a")
        eastid = wr.get(match.get("eastId"), "n/a")

        matchString = f"""{(westname+ "("+westid+")").center(10)}  vs  {(eastname+"("+eastid+")").rjust(15)}\n"""
        #        {match.get("westRank").center(25)} {match.get("eastRank").center(25)}
        sch = sch + matchString
    return sch

def get_wr():    # get latest banzuke from https://www.sumo-api.com/api/basho/202511/banzuke/Makuuchi
    wr: dict = {}
    division = ["Makuuchi", "Juryo"]
    ew = ["east", "west"]
    for div in division:
        data = requests.get(url=f"https://www.sumo-api.com/api/basho/202511/banzuke/{div}")
        banzuke = data.json()
        for side in ew:
            for rikishi in banzuke[side]:   # go through east and west parts
                wl= f"{rikishi["wins"]} - {rikishi["losses"]}"
                wr.update({rikishi["rikishiID"]: wl})
    return (wr) #{rikishiid: "win - loss"}

def accumulate_data(new_data, filename):
    # today = datetime.date.today().isoformat()
    # save_data(new_data, f"{today}_newMatches.json")    #save today's data separately

    history = load_data(filename)   #open existing
    for element in new_data:    #for each {} in []
            
        if element["day"] >= history[-1]["day"]:
            history.append(element)
    #history.append(new_data)
    #history.append(["Date: ", today])
    
    save_data(history, filename)
    return

def calc_sig(url: str, body: bytes, secret: str):
    sig = hmac.new(secret.encode("utf-8"), digestmod=hashlib.sha256)
    sig.update(url.encode("utf-8"))
    sig.update(body)
    return (sig.hexdigest())
# try:
#     testrequest = requests.get (url="https://www.sumo-api.com/api/rikishis?limit=10")
#     testrequest.raise_for_status()
#     for record in testrequest.json().get("records"):
#         print(record.get('heya'))


#     print(testrequest.headers.items())
# except requests.RequestException as e:
#     print("Request exception: ", e)

if __name__ == "__main__":

    threading.Thread(target=run_flask).start()
    asyncio.run(smokeyBot())

# def subscribe(hookType: str):

#   body = json.dumps ({
#   "name":"1234444444",
#   "destination":f"http://{host}:{port}/sumo",
#   "secret":secret,
#   "subscriptions":
#   {
#     hookType: True,
#   }
# })
#   try:
#       testrequest = requests.post(url = f"https://www.sumo-api.com/api/webhook/test?type={hookType}",data=body)
#       testrequest.raise_for_status()
#       print (testrequest.status_code)
#       print(testrequest.headers.items())
#   except requests.RequestException as e:
#       print("Request exception: ", e)
#       print(testrequest.headers.items())