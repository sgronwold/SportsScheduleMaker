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
    print('sport is', sport, 'league is', league)

    c = Calendar()
    c.add('prodid', '-//My Company//My Calendar//EN')
    c.add('version', '2.0')

    # Add subcomponents
    l:League = None
    l = League.objects.get(sport__iexact=sport, league=league)
    league = l

    if league != None:
        # team abbr's
        teams = req.GET.get("teams")
        if teams == None:
            # then get all the teams
            teams = ",".join([t.tricode for t in Team.objects.filter(league=league).all()])
        teams = teams.split(",")

        for t in teams:
            team = Team.objects.get(tricode__iexact=t, league=league)

            # default date radius is one year in the past, one year in the future
            # TODO make this customizable
            DATE_RADIUS = 365#days
            START = dt.now(tz=pytz.utc) - td(days=DATE_RADIUS)
            END = dt.now(tz=pytz.utc) + td(days=DATE_RADIUS)

            # update the database
            if league not in nextUpdate.keys():
                nextUpdate[league] = Lock()
            if nextUpdate[league].acquire(timeout=0):
                helpers.loadScheduleByDateRange(league, START, END)

                # release the lock after a minute i.e. 60 seconds
                Thread(target=release_thread_after_delay, args=(nextUpdate[league], 60))

            for game in Game.objects.filter(Q(start__range=(START,END)) & (Q(hometeam=team)|Q(awayteam=team))):
                event = Event()
                event.add('summary', '%s @ %s'%(game.awayteam.name, game.hometeam.name))
                event.add('description', 'Watch on: %s'%(", ".join([n.name for n in game.networks.all()])))
                event.add('dtstart', game.start)
                event.add('dtend', game.start + td(hours=3))
                event.add('UID', uuid.uuid4().__str__())

                event.add('DTSTAMP', dt.now())

                c.add_component(event)

        buffer = io.BytesIO()
        buffer.write(c.to_ical())
        buffer.seek(0)
        

        return FileResponse(buffer, content_type='text/calendar')

def release_thread_after_delay(lock:Lock, delay_sec:int):
    sleep(delay_sec)
    lock.release()
