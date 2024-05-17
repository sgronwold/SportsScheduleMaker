from ScheduleGetter import *
import requests

GET_NEW_DATA = False
DAILY_HEADINGS = True
USE_TEAM_IMAGES = True
PAGE_BREAKS = True
league = NFL
NETWORK_COLUMN_WIDTH = "~"

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

    if DAILY_HEADINGS:
        for tricode in tricodes:
            print(tricode)
            loadSchedule(league, tricode)
    else:
        loadSchedule(league, "CHI")




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
    pass
else:
    dates = list(set([game["date"] for tricode in gameData for game in gameData[tricode]["games"]]))
    dates = sorted(dates, key=lambda date : date[4:])

if not DAILY_HEADINGS:
    outfile.write("[columns=\"~,~,~,%s\"]\n"%NETWORK_COLUMN_WIDTH)
    outfile.write("|===\n")
    outfile.write("|Date |Time |Game |Network\n\n\n")

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

    if DAILY_HEADINGS:
        if PAGE_BREAKS:
            outfile.write("\n\n<<<\n\n")

        if league == NFL:
            outfile.write("== Week %s\n\n"%(date))
        else:
            outfile.write("== %s\n\n"%(date))
        outfile.write("[columns=\"~,~,~,%s\"]\n"%NETWORK_COLUMN_WIDTH)
        outfile.write("|===\n")
        outfile.write("|Date |Time |Game |Network\n\n\n")

    for game in games:
        if USE_TEAM_IMAGES:
            gameName = "image:%s[%s,width={imgwidth},height={imgwidth}, pdfwidth={pdfwidth}, height={pdfheight}] *@* image:%s[%s,width={imgwidth},height={imgwidth}, pdfwidth={pdfwidth}, height={pdfheight}] \n" % (game["away"]["logo"], game['away']['tricode'], game["home"]["logo"], game["home"]["tricode"])
        else:
            gameName = "*%s @ %s* \n" % (game["away"]["tricode"].replace("CHC", "CUBS"), game["home"]["tricode"].replace("CHC", "CUBS"))

        outfile.write("|%s |%s |%s |%s\n\n"%(game["date"], game["time"], gameName, ", ".join(game["networks"])))

    if DAILY_HEADINGS:
        outfile.write("|===\n\n")
    
    # print byes
    if league == NFL:
        
        pass

if not DAILY_HEADINGS:
    outfile.write("|===\n\n")


outfile.close()