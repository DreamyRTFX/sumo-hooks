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
        {
          "name": "Left side",
          "value": "",
          "inline": "true"
        },
        {
          "name": "Right side",
          "value": "",
          "inline": "true"
        },
        {
          "name": "",
          "value": ""
        }
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
    #accumulate_data(decoded_json, "matchResults.json")
    print("matchresults hit")
    post_webhook(format_match(torikumi()))

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

    today = datetime.today().date()
    save_data(decoded_json, f"{today}_newMatches.json")    #save today's data separately
    save_data(decoded_json, "latest_newMatches.json")
    #accumulate_data(decoded_json, "newMatches.json")
    print("newmatches hit")


    return jsonify(message={"state": "succeeded"}, status=204), 204

def post_webhook(json):
    
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
    
def torikumi():
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
                data = requests.get(url=f"https://www.sumo-api.com/api/basho/202511/torikumi/Makuuchi/{diff}")
            
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

if __name__ == "__main__":

    app.run(host=host, port=port)
