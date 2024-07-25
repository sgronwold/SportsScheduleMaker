from ScheduleGetter import *
import requests
import pytz
from datetime import datetime as dt, timedelta as td


GET_NEW_DATA = True
PRINT_ENTIRE_LEAGUE = False
DAILY_HEADERS = False
USE_TEAM_IMAGES = False
USE_SHORT_NAME = False
PAGE_BREAKS = False
league = NCAAF
PRINT_BYES = False
TABLE_HEADER = r'%autowidth.stretch'
START_DATE = dt(2000,1,1)
NETWORK_BLACKLIST = []
NETWORK_WHITELIST = ["CTESPN"]
FAVORITE_TEAMS = ["CHI", "CHC"]



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
if league == NCAAF:
    sport = 'football'
    league_name = 'college-football'
if league == NCAAMBB:
    sport = 'basketball'
    league_name = 'mens-college-basketball'
if league == NCAAWBB:
    sport = 'basketball'
    league_name = 'womens-college-basketball'

if GET_NEW_DATA:
    outfile = open("./games.json", "w")
    outfile.write("")
    outfile.close()

    response = requests.get("http://site.api.espn.com/apis/site/v2/sports/%s/%s/teams"%(sport,league_name)).json()

    tricodes = [team["team"]["abbreviation"] for team in response["sports"][0]["leagues"][0]["teams"]]

    if PRINT_ENTIRE_LEAGUE:
        for tricode in tricodes:
            print(tricode)
            loadScheduleByTricode(league, tricode)
    else:
        # valpo
        loadScheduleByTricode(league, "2674")

        # isu
        loadScheduleByTricode(league, "2287")




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
    dates = []
    for tricode in gameData:
        for game in gameData[tricode]["games"]:
            if game["timeValid"]:
                dates.append(zulu.parse(game["zulu"]).astimezone(tz=tz("America/Chicago")))
            else:
                dates.append(zulu.parse(game["zulu"]))
    dates = sorted(dates)

    # parse the zulu as a date
    i = 0
    while i < len(dates):
        if dates[i] >= START_DATE:
            dates[i] = zuluToDate(dates[i])
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
                # stop right there, if this is the incorrect week
                if date != game["week"]:
                    continue

            else:
                # stop right there, if this is the incorrect date
                if date != game["date"]:
                    continue

            # otherwise it's the right day and not a duplicate
            games.append(game)

    # sort by the various criteria
    games = sorted(games, key=lambda game: (game["home"]["tricode"] not in FAVORITE_TEAMS, game["away"]["tricode"] not in FAVORITE_TEAMS, game["zulu"]))

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

    # list of all teams in the game data, we will thin the herd as we find teams that actually don't have a bye 
    byeHavers = set([tricode for tricode in gameData])

    for game in games:
        date:str
        time:str

        if game["timeValid"]:
            date = game["date"]
            time = game["time"]
        else:
            if league in [NFL, NCAAF]:
                date = ""
            else:
                date = game["date"]
            
            time = ""

        try:
            # remove teams that actually have a game today
            byeHavers.remove(game["home"]["tricode"])
        except KeyError:
            pass
        try:
            # remove teams that actually have a game today
            byeHavers.remove(game["away"]["tricode"])
        except KeyError:
            pass


        gameName = ""

        ## add the away team
        if USE_TEAM_IMAGES and game["away"]["logo"] != None:
            gameName += "image:%s[%s,width={imgwidth},height={imgwidth}, pdfwidth={pdfwidth}, height={pdfheight}]" % (game["away"]["logo"], game['away']['tricode'])
        elif USE_SHORT_NAME:
            gameName += game["away"]["tricode"]
        else:
            gameName += game["away"]["shortDisplayName"]

        gameName += " @ "

        ## add the home team
        if USE_TEAM_IMAGES and game["home"]["logo"] != None:
            gameName += "image:%s[%s,width={imgwidth},height={imgwidth}, pdfwidth={pdfwidth}, height={pdfheight}]" % (game["home"]["logo"], game['home']['tricode'])
        elif USE_SHORT_NAME:
            gameName += game["home"]["tricode"]
        else:
            gameName += game["home"]["shortDisplayName"]

        if len(NETWORK_BLACKLIST) != 0 and len(NETWORK_WHITELIST) == 0:
            # remove banned networks
            for network in NETWORK_BLACKLIST:
                while network in game["networks"]:
                    game["networks"].remove(network)
        elif len(NETWORK_BLACKLIST) == 0 and len(NETWORK_WHITELIST) != 0:
            # remove all but allowed networks
            # old fashioned for loop
            i=0
            while i < len(game["networks"]):
                network = game["networks"][i]
                if network not in NETWORK_WHITELIST:
                    game["networks"].remove(network)
                    i-=1
                i+=1
        else:
            raise ValueError("ERROR: Either the NETWORK_BLACKLIST or NETWORK_WHITELIST must be empty.")

        outfile.write("|%s |%s |%s |%s\n\n"%(date, time, gameName, ", ".join(game["networks"])))

    if DAILY_HEADERS:
        outfile.write("|===\n\n")
    
    # print byes
    if PRINT_BYES:
        outfile.write("Byes:")

        for tricode in byeHavers:
            if USE_TEAM_IMAGES:
                outfile.write("image:%s[%s,width={imgwidth},height={imgwidth}, pdfwidth={pdfwidth}, height={pdfheight}]"%(gameData[tricode]["logo"],tricode))
            else:
                outfile.write("%s "%tricode)

        outfile.write("\n\n")
                

if not DAILY_HEADERS:
    outfile.write("|===\n\n")


outfile.close()