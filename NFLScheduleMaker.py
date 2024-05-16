from ScheduleGetter import *
import requests

GET_NEW_DATA = True


if GET_NEW_DATA:
    outfile = open("./games.json", "w")
    outfile.write("")
    outfile.close()

    response = requests.get("http://site.api.espn.com/apis/site/v2/sports/football/nfl/teams").json()

    tricodes = [team["team"]["abbreviation"] for team in response["sports"][0]["leagues"][0]["teams"]]

    for tricode in tricodes:
        loadSchedule(NFL, tricode)




outfile = open("./out.adoc", "w")
outfile.write("")
outfile.close()



outfile = open("./out.adoc", "a")

datafile = open("./games.json")
gameData:dict = json.load(datafile)
datafile.close()

for week in range(1,19):
    # collect game ids so we know if there's any duplicates
    ids = []

    thisWeeksGames = []

    byeHavers = []

    for tricode in gameData:
        # check if our team is a bye haver
        if gameData[tricode]["bye"] == week:
            byeHavers.append(tricode)

        for game in gameData[tricode]["games"]:
            id = game["id"]

            # stop right there, if this is a duplicate
            if id in ids:
                continue
            ids.append(id)

            # stop right there, if it's the wrong week
            if game["week"] != week:
                continue

            # otherwise it's the right week and not a duplicate
            thisWeeksGames.append(game)
    
    # sort by the various criteria
    thisWeeksGames = sorted(thisWeeksGames, key=lambda game: (game["home"]["tricode"] != "CHI", game["away"]["tricode"] != "CHI", game["date"][3:], game["time"][-2], game["time"]))

    outfile.write("== Week %d\n\n"%week)
    outfile.write("[%autowidth.stretch]\n")
    outfile.write("|===\n")
    outfile.write("|Date |Time |Game |Network\n\n\n")

    for game in thisWeeksGames:
        gameName = "image:%s[%s,width={imgwidth},height={imgwidth}, pdfwidth={pdfwidth}, height={pdfheight}] *@* image:%s[%s,width={imgwidth},height={imgwidth}, pdfwidth={pdfwidth}, height={pdfheight}] \n" % (game["away"]["logo"], game['away']['tricode'], game["home"]["logo"], game["home"]["tricode"])
        #gameName = "*%s @ %s* \n" % (game["away"]["tricode"].replace("CHC", "CUBS").replace("CHW", "SOX"), game["home"]["tricode"].replace("CHC", "CUBS").replace("CHW", "SOX"))

        outfile.write("|%s |%s |%s |%s\n\n"%(game["date"], game["time"], gameName, ", ".join(game["networks"])))
    
    outfile.write("|===\n\n")



outfile.close()