from flask import Flask, request, jsonify
from dotenv import load_dotenv
import os
import requests
import json
from datetime import datetime, timezone
import hmac
import hashlib
import base64
import random
from dataclasses import dataclass

load_dotenv()
_secret = os.getenv('SECRET')
host = os.getenv('MYIP')
port = os.getenv('PORT')
endpoints = os.getenv('endpoints').split(",")
barnsumo = os.getenv('barnsumo')
failsumo = os.getenv('failsumo')

_request = {
  "username": "Sumo-hooks",
  "avatar_url": "",
  "content": "Sumo update!",
  "embeds": [
    {
      "author": {
        "name": "",
        "url": "https://www.sumo-api.com/",
        "icon_url": ""
      },
      "title": "Title",
      "url": "https://www.sumo-api.com/",
      "description": "Makuuchi division matches for the day",
      "color": 15258703,
      "fields": [
      ],
      "thumbnail": {
        "url": ""
      },
      "image": {
        "url": ""
      },
      "footer": {
        "text": "*It's just a phase, it'll pass* -- Phasedozer",
        "icon_url": ""
      }
    }
  ]
}
matchups: list = []
winloss: dict = {}
tjson: dict = {}

@dataclass
class Matchup:
  east_id: int
  east_shikona: str
  east_rank: str
  east_wins: int
  east_losses: int

  west_id: int
  west_shikona: str
  west_rank: str
  west_wins: int
  west_losses: int

  date: int
  day: int

@dataclass
class Field:

   name: str
   value: str
   inline: str = "true"

   def to_dict(self):
     return self.__dict__
   
app = Flask(__name__)
def run_flask():
    app.run(host=host, port=port)

@app.route("/matchresults", methods=["POST"])
def matchresults():
    
    content = request.json
    payload: bytes = content.get("payload")
    decoded_bytes = base64.b64decode(payload)
    decoded_json = json.loads(decoded_bytes.decode("utf-8"))
    sig = request.headers.get("X-Webhook-Signature")
    print(sig)
    print(calc_sig(request.base_url, decoded_bytes, _secret))
    print(decoded_json)
    today = datetime.today().date()

    save_data(decoded_json, f"{today}_matchResults.json")    #save today's data separately
    save_data(decoded_json, "latest_matchResults.json")
    print("matchresults hit")
    #post_webhook(format_match(torikumi()))

    return jsonify(message={"state": "succeeded"}, status=204), 204

@app.route("/newmatches", methods=["POST"])
def newmatches():
    
    content = request.json
    payload: bytes = content.get("payload")
    decoded_bytes = base64.b64decode(payload)
    decoded_json = json.loads(decoded_bytes.decode("utf-8"))
    sig = request.headers.get("X-Webhook-Signature")
    print(sig)
    print(calc_sig(request.base_url, decoded_bytes, _secret))
    print(decoded_json)

    bashoid = decoded_json[0].get("bashoId")
    day = decoded_json[0].get("day")
    post_webhook(format_request(collectData(bashoid, day)))

    today = datetime.today().date()
    save_data(decoded_json, f"{today}_newMatches.json")    #save today's data separately
    save_data(decoded_json, "latest_newMatches.json")
    print("newmatches hit")

    return jsonify(message={"state": "succeeded"}, status=204), 204

def post_webhook(json):
    #for ep in endpoints:
        
    try:
        post=requests.post(url=barnsumo,json=json)
        post.raise_for_status()

    except Exception as e:
        print(e)
    return

def decode_data(content):
    payload: bytes = content.get("payload")
    decoded_bytes = base64.b64decode(payload)
    decoded_json = json.loads(decoded_bytes.decode("utf-8"))
    return decoded_json
    
def collectData(date, day) -> list:  #pass YYYYMM to get that basho, day

  tdata = requests.get(url=f"https://www.sumo-api.com/api/basho/{date}/torikumi/Makuuchi/{day}")
  tjson = tdata.json()
  _request["content"] = f"Grand Sumo {date} update! Full makuuchi results so far [here](https://www.sumo-api.com/dashboard/hoshitori/{date}/Makuuchi)"
  _request["embeds"][0]["title"] = f"Day {day} schedule"
  _request["embeds"][0]["url"] = f"https://www.sumo-api.com/dashboard/torikumi/{date}/Makuuchi/{day} "
  _request["embeds"][0]["color"] = random.randint(1,16777210)

  for div in ["Makuuchi", "Juryo"]:
    bdata = requests.get(url=f"https://www.sumo-api.com/api/basho/{date}/banzuke/{div}")
    bjson = bdata.json()
    for ew in ["east", "west"]:
       for rikishi in bjson.get(ew):
        winloss.update({
           rikishi.get("rikishiID") : [rikishi.get("wins"), rikishi.get("losses") + rikishi.get("absences")]
           })

  for mu in tjson.get("torikumi"):
      matchup = Matchup(
          mu.get("eastId"),
          mu.get("eastShikona"),
          mu.get("eastRank"),
          winloss.get(mu.get("eastId"))[0],
          winloss.get(mu.get("eastId"))[1],
          mu.get("westId"),
          mu.get("westShikona"),
          mu.get("westRank"),
          winloss.get(mu.get("westId"))[0],
          winloss.get(mu.get("westId"))[1],
          date,
          day
      )
      matchups.append(matchup)
  return matchups

def r_populate(left, vs, right):
        
  field_l = Field("Left (East)", left)
  field_m = Field("Vs", vs)
  field_r = Field("Right (West)", right)
  _request["embeds"][0]["fields"].append(field_l.to_dict())
  _request["embeds"][0]["fields"].append(field_m.to_dict())
  _request["embeds"][0]["fields"].append(field_r.to_dict())
  return

def format_request(data: list) -> dict:
  left="" 
  right=""
  vs=""

  for match in data:
      westid = winloss.get(match.west_id)
      eastid = winloss.get(match.east_id)
      left = left + f"""**[{match.east_shikona}](https://www.sumo-api.com/dashboard/rikishi/{match.east_id})** {eastid}\n*{match.east_rank}*\n""" 
      vs = vs + f"""**[vs](https://www.sumo-api.com/dashboard/matchups/{match.east_id}/{match.west_id})**\n\n"""
      right = right + f"""**[{match.west_shikona}](https://www.sumo-api.com/dashboard/rikishi/{match.west_id})** {westid}\n*{match.west_rank}*\n"""
      if len(left)>850: # accumulate until 900+ then dump and flush
        r_populate(left, vs, right)
        left="" 
        right=""
        vs=""
  r_populate(left, vs, right) # dump the remainder
  return _request

def load_data(filename) -> any:
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
    
def torikumi() -> None:
    data = requests.get(url=f"https://www.sumo-api.com/api/basho/202511/torikumi/Makuuchi/1")
    tk = data.json()
    startDate = tk.get("startDate", False)
    endDate = tk.get("endDate", False)
    to = tk.get("torikumi", False)
    yu = tk.get("yusho", False)

    if startDate:
        start_date = datetime.strptime(startDate, "%Y-%m-%dT%H:%M:%SZ").date()
        today = datetime.now(timezone.utc).date()
        diff = (today-start_date).days + 2

        if diff <= 15:
            while True:
                data = requests.get(url=f"https://www.sumo-api.com/api/basho/202511/torikumi/Makuuchi/{diff}")
                to = data.json().get("torikumi", False)
                if tk:
                    break
                diff -=1
            return to
        if diff > 15:
            if yu:
                data = requests.get(url=f"https://www.sumo-api.com/api/basho/202511/torikumi/Makuuchi/14")
                to = data.json().get("torikumi", False)

                diff -=1
            return to
            
def format_match(data):
    sch=""
    left="" 
    right=""
    wr = get_wr()
    day = data[0]["day"]
    for match in data:
        westname = match.get("westShikona")
        eastname = match.get("eastShikona")
        westrank = match.get("westRank")
        eastrank = match.get("eastRank")
        westid = wr.get(match.get("westId", False), "n/a")
        eastid = wr.get(match.get("eastId", False), "n/a")
        left = left + f"""**{eastname}** ({eastid})\n*{eastrank}*\n""" 
        right = right + f"""**{westname}** ({westid})\n*{westrank}*\n"""
        # matchString = f"""{(westname+ "("+westid+")").center(30)}  vs  {(eastname+"("+eastid+")").center(30)}
        # {match.get("westRank").center(25)} {match.get("eastRank").center(25)}
        # {"====".center(70)}\n"""
        # sch = sch + matchString
    _request["embeds"][0]["fields"][0]["value"] = left
    _request["embeds"][0]["fields"][1]["value"] = right
    _request["embeds"][0]["title"] = f"Day {day}"
    return _request

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

def calc_sig(url: str, body: bytes, secret: str):
    sig = hmac.new(secret.encode("utf-8"), digestmod=hashlib.sha256)
    sig.update(url.encode("utf-8"))
    sig.update(body)
    return (sig.hexdigest())

if __name__ == "__main__":

    app.run(host=host, port=port)
