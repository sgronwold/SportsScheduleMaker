from django.shortcuts import render
from django.http import HttpRequest, FileResponse

from django.db.models import Q

from icalendar import Calendar, Event
from datetime import datetime as dt, timedelta as td
import pytz
import uuid

import io

from schedulemaker.models import League, Team, Game, Network

from django.utils import timezone

from static.python import helpers
from threading import Lock, Thread

from time import sleep

nextUpdate:dict[League, Lock] = {}

# Create your views here.
def index(req:HttpRequest):
    return render(req, 'calendarmaker/index.html')

def ical(req:HttpRequest, sport:str, league:str):
    teamnames = req.GET.get("names") # options are tricode, location, name, full. default is name
    if teamnames not in ['tricode', 'location', 'name', 'full']:
        teamnames = 'name'

    print('sport is', sport, 'league is', league)

    c = Calendar()
    c.add('prodid', '-//My Company//My Calendar//EN')
    c.add('version', '2.0')

    # Add subcomponents
    l:League = None
    l = League.objects.get(sport__iexact=sport, league=league)
    league = l

    # default date radius is one year in the past, one year in the future
    # TODO make this customizable
    DATE_RADIUS = 365#days
    START = dt.now(tz=pytz.utc) - td(days=DATE_RADIUS)
    END = dt.now(tz=pytz.utc) + td(days=DATE_RADIUS)
    # update the database
    Thread(target=update_db, args=(league,START,END)).start()

    # games to add to the calendar
    gamelist = []
    if league != None:
        # team abbr's
        teams = req.GET.get("teams")
        if teams != None:
            teams = teams.split(",")
        
            for t in teams:
                team = Team.objects.get(tricode__iexact=t, league=league)

                for game in Game.objects.filter(Q(start__range=(START,END)) & (Q(hometeam=team)|Q(awayteam=team))):
                    gamelist.append(game)
        else:
            # get all teams' games, if not specified
            # valid teams for these games
            teams = Team.objects.filter(league=league).all()
            for game in Game.objects.filter(start__range=(START,END), hometeam__in=teams, timevalid=True).all():
                gamelist.append(game)

    for game in gamelist:
        event = Event()
        if teamnames == "tricode":
            event.add('summary', '%s @ %s'%(game.awayteam.tricode, game.hometeam.tricode))
        if teamnames == "location":
            event.add('summary', '%s @ %s'%(game.awayteam.location, game.hometeam.location))
        if teamnames == "name":
            event.add('summary', '%s @ %s'%(game.awayteam.name, game.hometeam.name))
        if teamnames == "full":
            event.add('summary', '%s %s @ %s %s'%(game.awayteam.location, game.awayteam.name, game.hometeam.location, game.hometeam.name))

        event.add('description', 'Watch on: %s'%(",".join([n.name for n in game.networks.all()])))
        event.add('dtstart', game.start)
        event.add('dtend', game.start + td(hours=3))
        event.add('UID', uuid.uuid4().__str__())

        event.add('DTSTAMP', dt.now())

        c.add_component(event)

    buffer = io.BytesIO()
    buffer.write(c.to_ical())
    buffer.seek(0)
    

    return FileResponse(buffer, content_type='text/calendar')
    
def update_db(league:League, START:dt, END:dt):
    if league not in nextUpdate.keys():
        nextUpdate[league] = Lock()
    if nextUpdate[league].acquire(timeout=0):
        helpers.loadScheduleByDateRange(league, START, END)

        # release the lock after a minute i.e. 60 seconds
        Thread(target=release_lock_after_delay, args=(nextUpdate[league], 60))

def release_lock_after_delay(lock:Lock, delay_sec:int):
    sleep(delay_sec)
    lock.release()
