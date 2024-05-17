from threading import Thread
import json
import requests
from datetime import datetime as dt
import zulu
from pytz import timezone as tz

# basically enums
NHL = 0
NFL = 1
MLB = 2
NBA = 3

PRESEASON = 1
REG_SEASON = 2
POSTSEASON = 3

THIS_YEAR = dt.now().year

def loadSchedule(league:int, tricode:str, seasontype:str="2", season:str=""):
    response:dict
    bye:int = -1
    games = []

    if league == NHL:
        response = requests.get("http://site.api.espn.com/apis/site/v2/sports/hockey/nhl/teams/%s/schedule?season=%s&seasontype=%s"%(tricode,season,seasontype)).json()
    if league == NFL:
        response = requests.get("http://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/%s/schedule?season=%s&seasontype=%s"%(tricode,season,seasontype)).json()
    if league == MLB:
        response = requests.get("http://site.api.espn.com/apis/site/v2/sports/baseball/mlb/teams/%s/schedule?season=%s&seasontype=%s"%(tricode,season,seasontype)).json()
    if league == NBA:
        response = requests.get("http://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/%s/schedule?season=%s&seasontype=%s"%(tricode,season,seasontype)).json()

    if "byeWeek" in response.keys():
        bye = response["byeWeek"]

    for game in response["events"]:
        newGame = {}
        
        if "week" in game.keys():
            newGame["week"] = game["week"]["number"]
        
        newGame["home"] = {
            "tricode": game["competitions"][0]["competitors"][0]["team"]["abbreviation"],
            "logo": game["competitions"][0]["competitors"][0]["team"]["logos"][0]["href"]
        }

        newGame["away"] = {
            "tricode": game["competitions"][0]["competitors"][1]["team"]["abbreviation"],
            "logo": game["competitions"][0]["competitors"][1]["team"]["logos"][0]["href"]
        }

        theTime = zulu.parse(game["date"])

        if(game["timeValid"]):
            theTime = theTime.astimezone(tz = tz("America/Chicago"))
            newGame["date"] = dt.strftime(theTime, "%a %m-%d")
            newGame["time"] = dt.strftime(theTime, "%I:%M %p")
        else:
            newGame["date"] = dt.strftime(theTime, "%a %m-%d")
            newGame["time"] = "TBD"
        
        newGame["id"] = game["id"]

        newGame["zulu"] = game["date"]

        newGame["networks"] = [network["media"]["shortName"].replace("|", ", ") for network in game["competitions"][0]["broadcasts"]]

        games.append(newGame)
    
    jsonSchedule = {}

    try:
        infile = open("./games.json", "r")
        jsonSchedule = json.loads(infile.read())
        infile.close()
    except json.decoder.JSONDecodeError:
        pass
    except FileNotFoundError:
        pass

    jsonSchedule[tricode] = {
        "bye": bye,
        "games": games
    }

    outfile = open("./games.json", "w")
    json.dump(jsonSchedule, outfile)
    outfile.close()