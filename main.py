import requests
from datetime import datetime as dt, timedelta as td, timezone as tz
import pytz
import threading
import json

URL = "http://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard"
#URL = "http://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard"
#URL = "http://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"

#FIRST_DAY = dt(2024, 3, 28)

FIRST_DAY = dt(2024, 3, 28)
LAST_DAY = dt(2024, 10, 1)

ONE_DAY = td(days=1)

scoreboards = {}

def main():
    global scoreboards
    req_threads = []

    date = FIRST_DAY

    outfile = open("./out.adoc", "w")
    outfile.write("")
    outfile.close()


    while date <= LAST_DAY:
        YYYYMMDD = dt.strftime(date, "%Y%m%d")

        newThread = threading.Thread(target=getScoreboard, args=(YYYYMMDD,))
        newThread.start()

        req_threads.append(newThread)

        date += ONE_DAY
    
    for thread in req_threads:
        thread.join()


    outfile = open("./out.adoc", "a")
    

    date = FIRST_DAY
    while date <= LAST_DAY:
        YYYYMMDD = dt.strftime(date, "%Y%m%d")

        todaysGames = scoreboards[YYYYMMDD]

        outfile.write("//%s\n"%YYYYMMDD)

        for game in todaysGames:
            outfile.write("|%s \n" % game["date"])
            outfile.write("|%s \n" % game["time"])
            #outfile.write("|image:%s[%s,width={imgwidth},height={imgwidth}, pdfwidth={pdfwidth}, height={pdfheight}] @ image:%s[%s,width={imgwidth},height={imgwidth}, pdfwidth={pdfwidth}, height={pdfheight}] \n" % (game["away"]["icon"], game['away']['tricode'], game["home"]["icon"], game["home"]["tricode"]))
            outfile.write("|%s @ %s \n" % (game["away"]["tricode"].replace("CHC", "CUBS").replace("CHW", "SOX"), game["home"]["tricode"].replace("CHC", "CUBS").replace("CHW", "SOX")))
            outfile.write("|%s \n" % ", ".join(game["networks"]))

        outfile.write("\n")

        date += ONE_DAY
    outfile.close()


    theJson = open("./games.json", "w")
    json.dump(obj=scoreboards, fp=theJson)
    theJson.close()

def getScoreboard(YYYYMMDD:str):
    req = requests.get("%s?dates=%s"%(URL,YYYYMMDD))
    req_json = req.json()

    scoreboards[YYYYMMDD] = []

    todaysGamesList = req_json["events"]

    for game in todaysGamesList:
        if game["competitions"][0]["competitors"][0]["team"]["abbreviation"] in ["CHC", "CHW", "CHI"] or game["competitions"][0]["competitors"][1]["team"]["abbreviation"] in ["CHC", "CHW", "CHI"]:
            # then this is a cubs/sox game so we add it
            newGame = {}
            
            newGame["home"] = {}
            newGame["home"]["name"] = game["competitions"][0]["competitors"][0]["team"]["name"]
            newGame["home"]["tricode"] = game["competitions"][0]["competitors"][0]["team"]["abbreviation"]
            newGame["home"]["icon"] = game["competitions"][0]["competitors"][0]["team"]["logo"]

            newGame["away"] = {}
            newGame["away"]["name"] = game["competitions"][0]["competitors"][1]["team"]["name"]
            newGame["away"]["tricode"] = game["competitions"][0]["competitors"][1]["team"]["abbreviation"]
            newGame["away"]["icon"] = game["competitions"][0]["competitors"][1]["team"]["logo"]

            newGame["networks"] = []
            for broadcast in game["competitions"][0]["broadcasts"]:
                # sometimes things are streamed in multiple places
                for bannedNetwork in ["ESPN+", "NESN", "NHLPP|ESPN+"]:
                    if bannedNetwork in broadcast["names"]:
                        broadcast["names"].remove(bannedNetwork)

                newGame["networks"].append(", ".join(broadcast["names"]))

            # in utc, i.e. "2024-03-29T17:40Z"
            startDate = game["competitions"][0]["startDate"]
            year = int(startDate[0:4])
            month = int(startDate[5:7])
            day = int(startDate[8:10])

            hour = int(startDate[11:13])
            min = int(startDate[14:16])

            chicagoTime = pytz.timezone("America/Chicago")

            startDate = dt(year, month, day, hour, min, tzinfo=tz.utc)
            startDate = startDate.astimezone(chicagoTime)
            newGame["date"] = dt.strftime(startDate, "%m/%d")
            newGame["time"] = dt.strftime(startDate, "%I:%M")

            scoreboards[YYYYMMDD].append(newGame)


main()