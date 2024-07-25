from ScheduleGetter import *
import requests
import pytz
from datetime import datetime as dt


GET_NEW_DATA = True
PRINT_ENTIRE_LEAGUE = False
DAILY_HEADERS = False
USE_TEAM_IMAGES = False
PAGE_BREAKS = False
league = MLB
PRINT_BYES = False
TABLE_HEADER = r'%autowidth.stretch'
START_DATE = dt(2024,7,14)
NETWORK_BLACKLIST = []
NETWORK_WHITELIST = ["ESPN", "FOX", "Apple TV+"]


START_DATE = START_DATE.astimezone(pytz.timezone("America/Chicago"))

if league == NFL:
    sport = 'football'
    league_name = 'nfl'
if league == MLB:
    sport = 'baseball'
    league_name = 'mlb'
if league == NHL:
    sport = 'hockey'
    league_name = 'nhl'

if GET_NEW_DATA:
    outfile = open("./games.json", "w")
    outfile.write("")
    outfile.close()

    response = requests.get("http://site.api.espn.com/apis/site/v2/sports/%s/%s/teams"%(sport,league_name)).json()

    tricodes = [team["team"]["abbreviation"] for team in response["sports"][0]["leagues"][0]["teams"]]

    if PRINT_ENTIRE_LEAGUE:
        for tricode in tricodes:
            print(tricode)
            loadSchedule(league, tricode)
    else:
        loadSchedule(league, "CHC")
        #loadSchedule(league, "CHW")




outfile = open("./out.adoc", "w")
outfile.write("")
outfile.close()



outfile = open("./out.adoc", "a")

datafile = open("./games.json")
gameData:dict = json.load(datafile)
datafile.close()

if league == NFL:
    # then "dates" are actually "weeks"
    dates = list(set([game["week"] for tricode in gameData for game in gameData[tricode]["games"]]))
    dates = sorted(dates)
else:
    dates = list(set([game["zulu"] for tricode in gameData for game in gameData[tricode]["games"]]))
    dates = sorted(dates)

    # parse the zulu as a date
    i = 0
    while i < len(dates):
        zuluAsLocalTime = zulu.parse(dates[i]).astimezone(pytz.timezone("America/Chicago"))

        if zuluAsLocalTime >= START_DATE:
            dates[i] = zuluToDate(zuluAsLocalTime)
            i += 1
        else:
            dates.pop(i)

    # remove duplicate dates
    i = 1
    while i < len(dates):
        if dates[i] == dates[i-1]:
            dates.pop(i)
        else:
            i+=1
    

if not DAILY_HEADERS:
    outfile.write("[%s]\n"%TABLE_HEADER)
    outfile.write("|===\n")
    outfile.write("|Date |Time |Game |TV\n\n\n")

print(dates)
for date in dates:
    # collect game ids so we know if there's any duplicates
    ids = []
    games = []
    for tricode in gameData:
        for game in gameData[tricode]["games"]:
            id = game["id"]

            # stop right there, if this is a duplicate
            if id in ids:
                continue
            ids.append(id)

            if league == NFL:
                # stop right there, if this is the incorrect date
                if date != game["week"]:
                    continue

            else:
                # stop right there, if this is the incorrect date
                if date != game["date"]:
                    continue

            # otherwise it's the right day and not a duplicate
            games.append(game)

    # sort by the various criteria
    games = sorted(games, key=lambda game: (game["home"]["tricode"] not in ["CHI", "CHC"], game["away"]["tricode"] not in ["CHI", "CHC"], game["zulu"]))

    if DAILY_HEADERS:
        if PAGE_BREAKS:
            outfile.write("\n\n<<<\n\n")

        if league == NFL:
            outfile.write("== Week %s\n\n"%(date))
        else:
            outfile.write("== %s\n\n"%(date))
        outfile.write("[%s]\n"%TABLE_HEADER)
        outfile.write("|===\n")
        outfile.write("|Date |Time |Game |TV\n\n\n")

    byeHavers = set([tricode for tricode in gameData])
    for game in games:
        try:
            byeHavers.remove(game["home"]["tricode"])
        except KeyError:
            pass
        try:
            byeHavers.remove(game["away"]["tricode"])
        except KeyError:
            pass

        if USE_TEAM_IMAGES:
            gameName = "image:%s[%s,width={imgwidth},height={imgwidth}, pdfwidth={pdfwidth}, height={pdfheight}] *@* image:%s[%s,width={imgwidth},height={imgwidth}, pdfwidth={pdfwidth}, height={pdfheight}] \n" % (game["away"]["logo"], game['away']['tricode'], game["home"]["logo"], game["home"]["tricode"])
        else:
            gameName = "%s @ %s \n" % (game["away"]["tricode"].replace("CHC", "CUBS").replace("CHW", "SOX"), game["home"]["tricode"].replace("CHC", "CUBS").replace("CHW", "SOX"))

        # filter the networks
        # if there's a whitelist
        if len(NETWORK_BLACKLIST) == 0 and len(NETWORK_WHITELIST) != 0:
            # old school for loop
            i = 0
            while i < len(game["networks"]):
                if game["networks"][i] not in NETWORK_WHITELIST:
                    game["networks"].remove(game["networks"][i])
                    i-=1
                i+=1
        # if there's a blacklist
        elif len(NETWORK_BLACKLIST) != 0 and len(NETWORK_WHITELIST) == 0:
            print("blacklist mode")
            for network in NETWORK_BLACKLIST:
                while network in game["networks"]:
                    game["networks"].remove(network)
        # otherwise throw an error
        else:
            raise ValueError("ERROR: Whitelist and blacklist are both nonempty.\nEither the whitelist or blacklist must be empty.")

        outfile.write("|%s |%s |%s |%s\n\n"%(game["date"], game["time"], gameName, ", ".join(game["networks"])))

    if DAILY_HEADERS:
        outfile.write("|===\n\n")
    
    # print byes
    if PRINT_BYES:
        outfile.write("Byes: ")

        for tricode in byeHavers:
            if USE_TEAM_IMAGES:
                outfile.write("image:%s[%s,width={imgwidth},height={imgwidth}, pdfwidth={pdfwidth}, height={pdfheight}]"%(gameData[tricode]["logo"],tricode))
            else:
                outfile.write("%s "%tricode)

        outfile.write("\n\n")
                

if not DAILY_HEADERS:
    outfile.write("|===\n\n")


outfile.close()