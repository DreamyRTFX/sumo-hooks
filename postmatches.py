from dotenv import load_dotenv
import os
import random
import json
import requests
from dataclasses import dataclass

load_dotenv()
endpoints = os.getenv('endpoints').split(",")
barnsumo = "https://discord.com/api/webhooks/1440084933648580698/LAeb8huuV_3qGAMlByAi6TR1fjs89go9sFRk4EPtwunjX-jTnBuoF9OSvBrxmhIKPl5F"

_request = {
  "username": "Sumo-hooks",
  "avatar_url": "",
  "content": "Sumo update!",
  "embeds": [
    {
      "author": {
        "name": "",
        "url": "https://www.sumo-api.com/",
        "icon_url": "https://i.imgur.com/9ZoPrlu.jpeg"
      },
      "title": "Title",
      "url": "https://www.sumo-api.com/",
      "description": "Makuuchi division matches for the day:",
      "color": 15258703,
      "fields": [ 
         {
          "name": "Left (East)",
          "value": " ",
          "inline": "true"
        },
        {
          "name": "VS",
          "value": " ",
          "inline": "true"
        },
        {
          "name": "Right (West)",
          "value": " ",
          "inline": "true"
        },
      ],
      "thumbnail": {
        "url": ""
      },
      "image": {
        "url": "https://preview.redd.it/4jgvhc11vdjf1.gif"
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

def collectData(date, day) -> list:  #pass YYYYMM to get that basho, day

  tdata = requests.get(url=f"https://www.sumo-api.com/api/basho/{date}/torikumi/Makuuchi/{day}")
  tjson = tdata.json()
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
        
  field_l = Field(" ", left)
  field_m = Field(" ", vs)
  field_r = Field(" ", right)
  _request["embeds"][0]["fields"].append(field_l.to_dict())
  _request["embeds"][0]["fields"].append(field_m.to_dict())
  _request["embeds"][0]["fields"].append(field_r.to_dict())
  return

def format_request(data: list) -> dict:
  left="" 
  right=""
  vs=""
  _request["content"] = f"Grand Sumo {data[0].date} update! Full makuuchi results so far [here](https://www.sumo-api.com/dashboard/hoshitori/{data[0].date}/Makuuchi)"
  _request["embeds"][0]["title"] = f"Day {data[0].day} schedule"
  _request["embeds"][0]["url"] = f"https://www.sumo-api.com/dashboard/torikumi/{data[0].date}/Makuuchi/{data[0].day} "
  _request["embeds"][0]["color"] = random.randint(1,16777000)
  for match in data:
      westwl = winloss.get(match.west_id)
      eastwl = winloss.get(match.east_id)
      left = left + f"""**[{match.east_shikona}](https://www.sumo-api.com/dashboard/rikishi/{match.east_id})** {eastwl}\n*{match.east_rank}*\n""" 
      vs = vs + f"""**[vs](https://www.sumo-api.com/dashboard/matchups/{match.east_id}/{match.west_id})**\n\n"""
      right = right + f"""**[{match.west_shikona}](https://www.sumo-api.com/dashboard/rikishi/{match.west_id})** {westwl}\n*{match.west_rank}*\n"""
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

def post_webhook(json): 
    for ep in endpoints:   
      try:
          post=requests.post(url=ep,json=json)
          post.raise_for_status()
          print(post.json)
      except Exception as e:
          print(e)
    return

latestfile = load_data("/home/bleakill/sumo-hooks/latest_newMatches.json")
lastbasho = latestfile[0].get("bashoId")
lastday = latestfile[0].get("day")
post_webhook(format_request(collectData(lastbasho, lastday)))