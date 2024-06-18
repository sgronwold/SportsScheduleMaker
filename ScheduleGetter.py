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
NCAAF = 4
NCAAMBB = 5
NCAAWBB = 6

PRESEASON = 1
REG_SEASON = 2
POSTSEASON = 3

THIS_YEAR = dt.now().year

def loadScheduleByDate(league, date:dt):
    response:dict

    if league == NHL:
        response = requests.get("http://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard?dates=%s"%(dt.strftime(date, "%Y%m%d"))).json()
    if league == NFL:
        response = requests.get("http://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates=%s"%(dt.strftime(date, "%Y%m%d"))).json()
    if league == MLB:
        response = requests.get("http://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard?dates=%s"%(dt.strftime(date, "%Y%m%d"))).json()
    if league == NBA:
        response = requests.get("http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates=%s"%(dt.strftime(date, "%Y%m%d"))).json()
    if league == NCAAF:
        response = requests.get("http://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?dates=%s"%(dt.strftime(date, "%Y%m%d"))).json()
    if league == NCAAMBB:
        response = requests.get("http://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard?dates=%s"%(dt.strftime(date, "%Y%m%d"))).json()
    if league == NCAAWBB:
        response = requests.get("http://site.api.espn.com/apis/site/v2/sports/basketball/womens-college-basketball/scoreboard?dates=%s"%(dt.strftime(date, "%Y%m%d"))).json()

    exportGamesToJson(response)



def loadScheduleByTricode(league:int, tricode:str, seasontype:str="2", season:str=""):
    response:dict

    if league == NHL:
        response = requests.get("http://site.api.espn.com/apis/site/v2/sports/hockey/nhl/teams/%s/schedule?season=%s&seasontype=%s"%(tricode,season,seasontype)).json()
    if league == NFL:
        response = requests.get("http://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/%s/schedule?season=%s&seasontype=%s"%(tricode,season,seasontype)).json()
    if league == MLB:
        response = requests.get("http://site.api.espn.com/apis/site/v2/sports/baseball/mlb/teams/%s/schedule?season=%s&seasontype=%s"%(tricode,season,seasontype)).json()
    if league == NBA:
        response = requests.get("http://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/%s/schedule?season=%s&seasontype=%s"%(tricode,season,seasontype)).json()
    if league == NCAAF:
        response = requests.get("http://site.api.espn.com/apis/site/v2/sports/football/college-football/teams/%s/schedule?season=%s&seasontype=%s"%(tricode,season,seasontype)).json()
    if league == NCAAMBB:
        response = requests.get("http://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/teams/%s/schedule?season=%s&seasontype=%s"%(tricode,season,seasontype)).json()
    if league == NCAAWBB:
        response = requests.get("http://site.api.espn.com/apis/site/v2/sports/basketball/womens-college-basketball/teams/%s/schedule?season=%s&seasontype=%s"%(tricode,season,seasontype)).json()

    exportGamesToJson(response)



def exportGamesToJson(response:dict):

    ## read the schedule
    jsonSchedule = {}
    try:
        infile = open("./games.json", "r")
        jsonSchedule = json.loads(infile.read())
        infile.close()
    except json.decoder.JSONDecodeError:
        pass
    except FileNotFoundError:
        pass

    bye:int = -1
    
    if "byeWeek" in response.keys():
        bye = response["byeWeek"]

    ## add each game to the json directory of games
    for game in response["events"]:
        newGame = {}
        
        if "week" in game.keys():
            newGame["week"] = game["week"]["number"]
        

        newGame["home"] = {
            "tricode": game["competitions"][0]["competitors"][0]["team"]["abbreviation"],
            "shortDisplayName": game["competitions"][0]["competitors"][0]["team"]["shortDisplayName"]
        }
        try:
            newGame["home"]["logo"] = game["competitions"][0]["competitors"][0]["team"]["logos"][0]["href"]
        except KeyError:
            try:
                newGame["home"]["logo"] = game["competitions"][0]["competitors"][0]["team"]["logo"]
            except KeyError:
                newGame["home"]["logo"] = None

            
        newGame["away"] = {
            "tricode": game["competitions"][0]["competitors"][1]["team"]["abbreviation"],
            "shortDisplayName": game["competitions"][0]["competitors"][1]["team"]["shortDisplayName"]
        }
        try:
            newGame["away"]["logo"] = game["competitions"][0]["competitors"][1]["team"]["logos"][0]["href"]
        except KeyError:
            try:
                newGame["away"]["logo"] = game["competitions"][0]["competitors"][1]["team"]["logo"]
            except KeyError:
                newGame["away"]["logo"] = None

        theTime = zulu.parse(game["date"])



        timeValid:bool

        try:
            timeValid = game["timeValid"]
        except KeyError:
            timeValid = game["competitions"][0]["timeValid"]

        newGame["timeValid"] = timeValid

        if(timeValid):
            theTime = theTime.astimezone(tz = tz("America/Chicago"))
            newGame["date"] = zuluToDate(theTime)
            newGame["time"] = zuluToTime(theTime)
        else:
            newGame["date"] = zuluToDate(theTime)
            newGame["time"] = ""
        
        newGame["id"] = game["id"]

        newGame["zulu"] = game["date"]

        try:
            newGame["networks"] = [network["media"]["shortName"].replace("|", ", ") for network in game["competitions"][0]["broadcasts"]]
        except KeyError:
            newGame["networks"] = [network["names"][0].replace("|", ", ") for network in game["competitions"][0]["broadcasts"]]
            


        tricode = newGame["home"]["tricode"]
        if tricode not in jsonSchedule.keys():
            jsonSchedule[newGame["home"]["tricode"]] = {}

        jsonSchedule[tricode]["bye"] = bye
        jsonSchedule[tricode]["logo"] = newGame["home"]["logo"]

        if "games" not in jsonSchedule[tricode].keys():
            jsonSchedule[tricode]["games"] = []

        jsonSchedule[tricode]["games"].append(newGame)


        tricode = newGame["away"]["tricode"]
        if tricode not in jsonSchedule.keys():
            jsonSchedule[newGame["away"]["tricode"]] = {}

        jsonSchedule[tricode]["bye"] = bye
        jsonSchedule[tricode]["logo"] = newGame["away"]["logo"]

        if "games" not in jsonSchedule[tricode].keys():
            jsonSchedule[tricode]["games"] = []

        jsonSchedule[tricode]["games"].append(newGame)

    ## write new schedule
    outfile = open("./games.json", "w")
    json.dump(jsonSchedule, outfile)
    outfile.close()



# helper function
# zulu to nice+readable
def zuluToDate(theZulu:zulu.Zulu) -> str:
    return dt.strftime(theZulu, "%a %m-%d")

# helper function
# zulu to time
def zuluToTime(theZulu:zulu.Zulu) -> str:
    return dt.strftime(theZulu, "%I:%M %p")