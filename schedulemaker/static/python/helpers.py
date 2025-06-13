from threading import Thread, Semaphore, Lock
import json
import requests
from datetime import datetime as dt, timedelta as td
import zulu
from pytz import timezone as tz
from schedulemaker.models import League, Team, Network, Game, Schedule
import uuid
from django.utils import timezone
import os
import pytz

# this lets us use logic when we query the models
from django.db.models import Q

PRESEASON = 1
REG_SEASON = 2
POSTSEASON = 3

networkChangeSemaphore = Semaphore(20)

networkCreateLock = Lock()
gameCreateLock = Lock()
teamCreateLock = Lock()

# start with ur uuid as a key
# then choose "html" or "pdf" as the second key
compilationlocks:dict[str, dict[str, Lock]] = {}

# uuid: the uuid
# format: must be pdf or html!
def compile(theUUID:str, format:str, timeout=-1):
    if theUUID not in compilationlocks.keys():
        compilationlocks[theUUID] = {}
    if format not in compilationlocks[theUUID].keys():
        compilationlocks[theUUID][format] = Lock()
    
    sch = Schedule.objects.get(uuid=theUUID)
    print('pdfReady', sch.pdfReady, 'htmlReady', sch.htmlReady)
    if format == 'pdf' and sch.pdfReady:
        return True
    if format == 'html' and sch.htmlReady:
        return True

    if not compilationlocks[theUUID][format].acquire(timeout=timeout):
        return False
    
    print('locked the compilation thingy for ', theUUID, format)

    try:
        if format == "pdf":
            exitcode = os.system("asciidoctor-pdf -a allow-uri-read ./schedulemaker/out/%s/out.adoc"%theUUID)
            if exitcode == 0:
                sch = Schedule.objects.get(uuid=theUUID)
                sch.pdfReady = True
                sch.save()
        if format == "html":
            exitcode = os.system("asciidoctor ./schedulemaker/out/%s/out.adoc"%theUUID)
            if exitcode == 0:
                sch = Schedule.objects.get(uuid=theUUID)
                sch.htmlReady = True
                sch.save()
    except Exception as e:
        # if it doesn't work then at least we can release the lock
        compilationlocks[theUUID][format].release()
        return False

    compilationlocks[theUUID][format].release()
    return True

def loadTeams(league:League):
    sport = league.sport
    leaguename = league.league
    response:dict
    response = requests.get("http://site.api.espn.com/apis/site/v2/sports/%s/%s/teams"%(sport,leaguename)).json()

    for team in response['sports'][0]['leagues'][0]['teams']:
        team = team['team']
        getOrCreateTeamFromESPNDict(league, team)

# We get or create a team from the information provided generously to us by the ESPN API.
# The dict has several useful keys such as id, location, name, etc.
def getOrCreateTeamFromESPNDict(league:League, team:dict):
    # the logo is kind of in a nebulous place
    logo:str
    try:
        logo = team["logos"][0]["href"]
    except KeyError:
        try:
            logo = team["logo"]
        except KeyError:
            logo = None
    t:Team
    exists:bool
    
    try:
        t = Team.objects.get(league=league, espnid=int(team['id']))
    except Exception as e:
        try:
            teamCreateLock.acquire()
            t, exists = Team.objects.get_or_create(
                espnid = int(team['id']),
                location = team['location'],
                name = team['name'],
                displayName = team['displayName'],
                shortDisplayName = team['shortDisplayName'],
                league=league,
                tricode = team['abbreviation'],
                logo = logo
            )
            teamCreateLock.release()
        except Exception as e:
            t = getOrCreateTeamFromESPNID(league, int(team['id']))
    
    return t

def getOrCreateTeamFromESPNID(league:League, espnid:int):
    sport = league.sport
    leaguename = league.league
    response = requests.get("http://site.api.espn.com/apis/site/v2/sports/%s/%s/teams/%d"%(sport,leaguename, espnid)).json()
    return getOrCreateTeamFromESPNDict(league, response['team'])

def getOrCreateNetworkFromESPNDict(network:dict) -> list[Network]:
    market = network['market']

    try:
        market = market['type']
    except Exception:
        pass

    networks:list[Network] = []
    names:list[str] = []
    if 'names' in network.keys():
        names = network['names']
    if 'name' in network.keys():
        names = [network['name']]
    if 'media' in network.keys():
        names = [network['media']['shortName']]

    for name in names:
        networkCreateLock.acquire()
        n, exists = Network.objects.get_or_create(
            market=market,
            name=name
        )
        networkCreateLock.release()
        networks.append(n)
    
    return networks


def loadScheduleByDate(league:League, date:dt):
    sport = league.sport
    leaguename = league.league
    response:dict
    response = requests.get("http://site.api.espn.com/apis/site/v2/sports/%s/%s/scoreboard?dates=%s"%(sport,leaguename,dt.strftime(date, "%Y%m%d"))).json()

    saveGames(league, response)



def loadScheduleByESPNID(league:League, tricode_or_espnid:str, seasontype:str="2", season:str=""):
    sport = league.sport
    leaguename = league.league
    response:dict
    response = requests.get("http://site.api.espn.com/apis/site/v2/sports/%s/%s/teams/%s/schedule?season=%s&seasontype=%s"%(sport,leaguename,tricode_or_espnid,season,seasontype)).json()

    saveGames(league, response)



def saveGames(league:League, schedule:dict):
    bye:int = -1
    
    if "byeWeek" in schedule.keys():
        bye = schedule["byeWeek"]

    ## add each game, if we haven't already
    threads = []
    for game in schedule["events"]:
        t = Thread(target=saveGame, args=(league, game,))
        t.run()
        threads.append(t)
    
    for t in threads:
        t.join()


def saveGame(league:League, game:dict):
    week = None
    if "week" in game.keys():
        week = game["week"]["number"]

    homeTeam = getOrCreateTeamFromESPNDict(league, game["competitions"][0]["competitors"][0]["team"])
    awayTeam = getOrCreateTeamFromESPNDict(league, game["competitions"][0]["competitors"][1]["team"])

    theTime = dt.fromisoformat(game["date"])


    timeValid:bool

    try:
        timeValid = game["timeValid"]
    except KeyError:
        timeValid = game["competitions"][0]["timeValid"]
    
    espnid = game["id"]

    # add the networks
    network_ids = []
    for networkdata in game["competitions"][0]["broadcasts"]:
        newnets = getOrCreateNetworkFromESPNDict(networkdata)
        for n in newnets:
            network_ids.append(n.id)
    
    # convert to queryset
    networks = Network.objects.filter(id__in=network_ids).all()

    gameCreateLock.acquire()
    newGame, exists = Game.objects.get_or_create(
        espnid=espnid,
        utcstart = theTime,
        timevalid = timeValid,
        awayteam=awayTeam,
        hometeam=homeTeam,
        week=week
    )
    gameCreateLock.release()
    # now we add the networks
    networkChangeSemaphore.acquire()
    newGame.networks.clear()
    for n in networks:
        newGame.networks.add(n)
    newGame.save()
    networkChangeSemaphore.release()

# overloading main
# takes a uuid,
# and a bunch of items from the schedule maker form response
def main_from_form_response(my_uuid, data:dict):
    main(
        data['league'],
        uuid4=my_uuid,
        GET_NEW_DATA=data['getNewData'],
        SEASON=data['season'],
        SEASONTYPE=data['seasontype'],
        PRINT_ENTIRE_LEAGUE=data['allTeams'],
        FAVORITE_TRICODES=[t.tricode for t in data['teams']],
        DAILY_HEADERS = data['dailyHeaders'],
        USE_TEAM_IMAGES = data['useImages'],
        USE_SHORT_NAME = data['useShortName'],
        PAGE_BREAKS = data['dailyPageBreaks'],
        PRINT_BYES = data['printByes'],
        TABLE_HEADER = data['tableHeader'],
        START_DATE = data['startTime'],
        END_DATE= (data['endTime'] if data['endTimeEnabled'] else dt(2100, 1, 1)),
        NETWORK_WHITELIST_MODE = data['whitelistMode'],
        PREFERRED_NETWORKS = data['blacklist'],
        NAME_SUBS = json.loads(data['nameSubs'].replace("'", '"')),
        TIMEZONE = data['timezone'],
        IMGWIDTH=data['imgwidth'],
        PDFWIDTH=data['pdfwidth'],
        MARGINS_IN=[data['horzmargin'], data['vertmargin']],
        PAPERSIZE_IN=[data['paperwidth'], data['paperheight']],
        HEADING_SIZE=data['headingsize'],
        FONT_SIZE=data['fontsize']
    )

def main(league:League,
        uuid4:uuid = uuid.uuid4(),
        GET_NEW_DATA = False,
        SEASON="",
        SEASONTYPE="",
        PRINT_ENTIRE_LEAGUE = False,
        FAVORITE_TRICODES = ["CHI", "CHC"],
        DAILY_HEADERS = True,
        USE_TEAM_IMAGES = False,
        USE_SHORT_NAME = False,
        PAGE_BREAKS = True,
        PRINT_BYES = False,
        TABLE_HEADER = r'%autowidth.stretch',
        START_DATE = dt.now(),
        END_DATE=dt(2100,1,1),
        NETWORK_WHITELIST_MODE = False,
        PREFERRED_NETWORKS = [],
        NAME_SUBS = {},
        TIMEZONE = timezone.get_current_timezone(),
        IMGWIDTH=30,
        PDFWIDTH=30,
        MARGINS_IN=[0,0],
        PAPERSIZE_IN=[8.5,11],
        HEADING_SIZE=16,
        FONT_SIZE=16):
    timezone.activate(TIMEZONE)

    #START_DATE = START_DATE.astimezone(pytz.timezone("America/Chicago"))
    sport = league.sport
    league_name = league.league

    FAVORITE_TEAMS = Team.objects.filter(league=league, tricode__in=FAVORITE_TRICODES)

    # ask the api for the teams
    loadTeams(league)
    if GET_NEW_DATA:

        teams = Team.objects.filter(league=league)

        if not PRINT_ENTIRE_LEAGUE:
            teams = teams.filter(id__in=FAVORITE_TEAMS)

        # ask the api for the games
        for t in teams:
            print(dt.now(), "Getting %s's games:"%t.location)
            loadScheduleByESPNID(league, str(t.espnid), SEASONTYPE, SEASON)


    ADOC_PATH = "./schedulemaker/out/%s"%uuid4
    os.makedirs(ADOC_PATH, exist_ok=True)

    themefile = open(ADOC_PATH+"/theme.yml", 'w')
    themefile.write("""extends: default-for-print

page:
    size: [%fin,%fin]
    margin: [%fin,%fin]
heading:
    h2-font-size: %fpt
base:
    font-size: %fpt

"""%(PAPERSIZE_IN[0], PAPERSIZE_IN[1], MARGINS_IN[0], MARGINS_IN[1],
     HEADING_SIZE, FONT_SIZE))
    themefile.close()



    outfile = open(ADOC_PATH+"/out.adoc", "w")
    outfile.write("")
    outfile.close()

    # first get teams of interest
    teams = Team.objects.filter(league=league).all()
    if not PRINT_ENTIRE_LEAGUE:
        teams = teams.filter(tricode__in=FAVORITE_TRICODES)

    # then use that to get games of interest
    games = Game.objects.filter((Q(hometeam__in=teams) | Q(awayteam__in=teams)) & Q(start__range=(START_DATE, END_DATE))).all()

    outfile = open(ADOC_PATH+"./out.adoc", "a")

    outfile.write(
""":pdf-theme: %s/theme.yml
:imgwidth: %fpt
:pdfwidth: %fpt
:!pagenums:
:nofooter:

"""%(ADOC_PATH, IMGWIDTH, PDFWIDTH))


    # list of week numbers or datetime objects
    dates:list
    if league.weekly_games:
        # then "dates" are actually "weeks"
        dates = list(set([game.week for game in games]))
    else:
        dates = list(set([timezone.localdate(game.start) for game in games]))
        print(sorted(dates))

    dates = sorted(dates)

    if not (DAILY_HEADERS or PAGE_BREAKS):
        outfile.write("[%s]\n"%TABLE_HEADER)
        outfile.write("|===\n")
        outfile.write("|Date |Time |Game |TV\n\n\n")

    for date in dates:
        # if date isn't an int (i.e. week...) then it's an actual date...
        if not isinstance(date, int):
            date = dt(year=date.year, month=date.month, day=date.day, tzinfo=timezone.get_current_timezone())
        currGames = None
        if league.weekly_games:
            currGames = games.filter(week=date)
        else:
            # we either gather one days' worth of games or one week's worth of games
            currGames = None
            if isinstance(date, int):
                currGames = games.filter(week_range=(date,date+1))
            else:
                currGames = games.filter(start__range=(date,date+td(days=1)))
        # sort by the various criteria
        currGames = sorted(currGames, key=lambda game: (game.hometeam.tricode not in FAVORITE_TRICODES and game.awayteam.tricode not in FAVORITE_TRICODES, game.start))
        

        if DAILY_HEADERS:
            if league.weekly_games:
                outfile.write("== Week %s\n\n"%(date))
            else:
                outfile.write("== %s\n\n"%(timestampToDate(date)))

        if PAGE_BREAKS or DAILY_HEADERS:
            outfile.write("[%s]\n"%TABLE_HEADER)
            outfile.write("|===\n")
            outfile.write("|Date |Time |Game |TV\n\n\n")

        # list of all teams in the game data, we will thin the herd as we find teams that actually don't have a bye 
        byeHavers = set(teams)

        for game in currGames:
            date:str
            time:str

            date = timestampToDate(timezone.localtime(game.start))
            if game.timevalid:
                time = timestampToTime(timezone.localtime(game.start))
            else:
                if league.weekly_games:
                    date = ""
                
                time = ""

            try:
                byeHavers.remove(game.hometeam)
            except KeyError as e:
                pass

            try:
                byeHavers.remove(game.awayteam)
            except KeyError as e:
                pass


            gameName = ""

            ## add the away team
            if USE_TEAM_IMAGES and game.awayteam.logo != None:
                gameName += "image:%s[%s,width={imgwidth},height={imgwidth}, pdfwidth={pdfwidth}, height={pdfheight}]" % (game.awayteam.logo, game.awayteam.tricode)
            elif USE_SHORT_NAME:
                gameName += game.awayteam.tricode
            else:
                gameName += game.awayteam.shortDisplayName

            gameName += " @ "

            ## add the home team
            if USE_TEAM_IMAGES and game.hometeam.logo != None:
                gameName += "image:%s[%s,width={imgwidth},height={imgwidth}, pdfwidth={pdfwidth}, height={pdfheight}]" % (game.hometeam.logo, game.hometeam.tricode)
            elif USE_SHORT_NAME:
                gameName += game.hometeam.tricode
            else:
                gameName += game.hometeam.shortDisplayName



            # the actual network list that we'll use in our document
            networksList = game.networks.all()

            if NETWORK_WHITELIST_MODE:
                networksList = networksList.filter(id__in=PREFERRED_NETWORKS)
            else:
                networksList = networksList.exclude(id__in=PREFERRED_NETWORKS)

            # make necessary substitutions in networks list
            for network in networksList:
                if network.name in NAME_SUBS.keys():
                    network.name = NAME_SUBS[network.name]

            # finally, just stringify the networks list
            networksList = [n.name for n in networksList]

            
            # make necessary substitutions for the game name
            for name in NAME_SUBS.keys():
                gameName = gameName.replace(name, NAME_SUBS[name])

            outfile.write("|%s |%s |%s |%s\n\n"%(date, time, gameName, ", ".join(networksList)))

        if DAILY_HEADERS or PAGE_BREAKS:
            outfile.write("|===\n\n")
        
        # print byes
        if PRINT_BYES:
            outfile.write("Byes:")

            for byeHaver in byeHavers:
                if USE_TEAM_IMAGES:
                    outfile.write("image:%s[%s,width={imgwidth},height={imgwidth}, pdfwidth={pdfwidth}, height={pdfheight}]"%(byeHaver.logo,byeHaver.tricode))
                else:
                    outfile.write("%s "%byeHaver.tricode)

            outfile.write("\n\n")

        if PAGE_BREAKS:
            outfile.write("\n\n<<<\n\n")  
                    

    if not (DAILY_HEADERS or PAGE_BREAKS):
        outfile.write("|===\n\n")


    outfile.close()


# helper function
# zulu to nice+readable
def timestampToDate(timestamp:dt) -> str:
    return dt.strftime(timestamp, "%a %m-%d")

# helper function
# zulu to time
def timestampToTime(timestamp:zulu.Zulu) -> str:
    return dt.strftime(timestamp, "%I:%M %p")