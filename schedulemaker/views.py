from django.shortcuts import render
from django.http import HttpRequest, HttpResponseRedirect, JsonResponse, HttpResponse, HttpResponseBadRequest, HttpResponseNotFound, FileResponse
from schedulemaker import forms

from schedulemaker.static.python import helpers

from schedulemaker.models import Team, Schedule, League, Game, Network

from datetime import datetime as dt

import uuid

import json

from django.core import serializers

from threading import Thread

# Create your views here.
def index(req:HttpRequest):
    return render(req, 'index.html')

def makeschedule(req:HttpRequest):
    my_uuid = uuid.uuid4()
    if req.GET.get('uuid'):
        my_uuid = uuid.UUID(req.GET.get(uuid))

    form = forms.ScheduleMakingForm()
    context = {}
    preset:dict = None
    sch:Schedule = None
    if req.method == "GET":
        context['form'] = form

        # if we're editing a pre-existing schedule...
        if req.GET.get('uuid'):
            # then we need to load that particular preset
            sch = Schedule.objects.get(uuid=my_uuid)

            # so that the json is copy/pastable. otherwise all the "" will be escaped with \
            sch.preset = json.loads(sch.preset)

            # also why not apply the preset?
            form.applyPreset(sch.preset)
        
            context['schedule'] = sch
            
    
    if req.method == "POST":
        form = forms.ScheduleMakingForm(req.POST)

        context['form'] = form

        if form.is_valid():
            data = form.cleaned_data

            helpers.loadTeams(data['league'])

            #this replaces all the below
            form.populateQuerySets()


            ## populate the correct teams
            #form.fields['teams'].queryset = Team.objects.filter(league=data['league']).all()

            ## populate the correct networks
            #networks = set()

            #for team in Team.objects.filter(league=data['league']):
            #    for game in Game.objects.filter(hometeam=team):
            #        networks = networks.union(set(game.networks.all()))

            #network_ids = [n.id for n in networks]

            #form.fields["blacklist"].queryset = Network.objects.filter(id__in=network_ids)
            #context['form'] = form

            # generate the preset
            preset = form.createPreset()
            if "save and quit" in req.POST:
                response = HttpResponse(preset, content_type='file/json')
                response['Content-Disposition'] = "attachment; filename=\"preset.json\""
                return response

            # generate the schedule
            if bool(data['generateSchedule']):
                helpers.main(
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

                # now that we have the asciidoc file we can compile it
                for format in 'html', 'pdf':
                    Thread(target=helpers.compile, args=(my_uuid, format)).start()
                
                # and make a new schedule!
                sch, exists = Schedule.objects.get_or_create(
                    uuid = my_uuid,
                    preset=json.dumps(preset)
                )

                return HttpResponseRedirect("?uuid=%s"%my_uuid)

    return render(req, 'schedulemaker/makeschedule.html', context)

def viewschedule(req:HttpRequest):
    

    context = {}
    return render(req, "./schedulemaker/viewschedule.html", context)

def schedules(req:HttpRequest):
    schedules = Schedule.objects.all()
    context = {
        "schedules": schedules
    }
    return render(req, "./schedulemaker/schedules.html", context)

def loadpreset(req:HttpRequest):
    form = forms.PresetFileUploadForm()

    if req.method == "POST":
        # we should DEFINITELY be below 10 kB
        if req.FILES['file'].size < 10e3:
            preset = json.dumps(json.loads(req.FILES['file'].read()))

            return HttpResponseRedirect("../makeschedule?preset=%s"%preset)
            
            

    context = {
        "form": form
    }

    return render(req, './schedulemaker/loadpreset.html', context)

def preset(req:HttpRequest):
    theUUID = req.GET.get('uuid')
    schedule = Schedule.objects.get(uuid=theUUID)

    print(json.loads(schedule.preset))

    response = HttpResponse(json.loads(schedule.preset), content_type='file/json')
    response['Content-Disposition'] = "attachment; filename=\"preset.json\""
    return response

def webpage(req:HttpRequest):
    theUUID = req.GET.get('uuid')
    if theUUID == None:
        return HttpResponse('Couldnt get a uuid from you')

    return showschedule(theUUID, 'html')

def pdf(req:HttpRequest):
    theUUID = req.GET.get('uuid')
    if theUUID == None:
        return HttpResponse('Couldnt get a uuid from you')

    return showschedule(theUUID, 'pdf')

# format must be webpage or pdf
def showschedule(theUUID:str, format:str):
    if format not in ['html', 'pdf']:
        return HttpResponseBadRequest('must be html or pdf you are asking for something else')
    
    try:
        infile = open("./schedulemaker/out/%s/out.%s"%(theUUID, format))
        payload = infile.read()
        infile.close()
        if format == 'html':
            return HttpResponse(payload)
        if format == 'pdf':
            return FileResponse(payload)
    except Exception as e:
        pass

    if helpers.compile(theUUID, format, 0):
        infile = open("./schedulemaker/out/%s/out.%s"%(theUUID, format), 'rb')
        if format == 'html':
            return HttpResponse(payload)
        if format == 'pdf':
            return FileResponse(infile, content_type='application/pdf')
    else:
        return HttpResponseNotFound('still workin on it')