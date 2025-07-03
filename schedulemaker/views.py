from django.shortcuts import render
from django.http import HttpRequest, HttpResponseRedirect, JsonResponse, HttpResponse, HttpResponseBadRequest, HttpResponseNotFound, FileResponse
from schedulemaker import forms

from django.contrib.auth.decorators import login_required
from django.contrib import auth

from schedulemaker.static.python import helpers

from schedulemaker.models import Team, Schedule, League, Game, Network

from datetime import datetime as dt

import uuid

import json

from django.core import serializers

from threading import Thread

import os

# Create your views here.
def index(req:HttpRequest):
    return render(req, 'index.html')

# Landing page for making a schedule.
@login_required
def makeschedule(req:HttpRequest):
    my_uuid = uuid.uuid4()
    if req.GET.get('uuid'):
        my_uuid = req.GET.get('uuid')

    form = forms.ScheduleMakingForm()
    context = {}
    context['user'] = req.user
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

            # port over any preferred settings
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

            # generate the preset
            preset = form.createPreset()

            # generate the schedule
            if bool(data['generateSchedule']):
                helpers.main_from_form_response(my_uuid, data)
                
                # ok now we know that the pdf and html are absolutely NOT ready
                # and make a new schedule!
                sch, exists = Schedule.objects.get_or_create(
                    uuid = my_uuid,
                )
                sch.preset = preset=json.dumps(preset)
                sch.pdfReady = False
                sch.htmlReady = False
                sch.save()

                # now that we have the asciidoc file we can compile it
                for format in 'html', 'pdf':
                    Thread(target=helpers.compile, args=(my_uuid, format)).start()

                return HttpResponseRedirect("../viewschedule?uuid=%s"%my_uuid)

    return render(req, 'schedulemaker/makeschedule.html', context)

def logout(req:HttpRequest):
    auth.logout(req)

    return HttpResponseRedirect('/')

def viewschedule(req:HttpRequest):
    uuid = req.GET.get('uuid')
    schedule = None
    
    try:
        schedule = Schedule.objects.get(uuid=uuid)
    except Exception:
        pass

    if req.method == "GET":
        form = forms.ScheduleRenameForm()
    if req.method == "POST":
        form = forms.ScheduleRenameForm(req.POST)
        if form.is_valid():
            data = form.cleaned_data
            schedule.name = data['name']
            schedule.save()
    
    if schedule != None:
        form.fields['name'].initial = schedule.name

    context = {
        "schedule": schedule,
        "form": form
    }
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

            # create a new schedule for this!!
            schedule, exists = Schedule.objects.get_or_create(
                uuid=uuid.uuid4()
            )
            schedule.preset = preset
            schedule.save()

            return HttpResponseRedirect("../makeschedule?uuid=%s"%schedule.uuid)

    context = {
        "form": form
    }

    return render(req, './schedulemaker/loadpreset.html', context)

def preset(req:HttpRequest):
    theUUID = req.GET.get('uuid')
    schedule = Schedule.objects.get(uuid=theUUID)

    print(json.loads(schedule.preset))

    response = HttpResponse(schedule.preset, content_type='file/json')
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

def nuke_schedule_cache(req:HttpRequest):
    # delete all files
    OUTFOLDER = "./schedulemaker/out/"
    for dir in os.listdir(OUTFOLDER):
        os.system("rm -r "+OUTFOLDER+dir)

    # and reset pdf/html ready flags
    for s in Schedule.objects.all():
        s.pdfReady = False
        s.htmlReady = False
        s.save()

    return HttpResponseRedirect("../schedules")

# format must be webpage or pdf
def showschedule(theUUID:str, format:str):
    if format not in ['html', 'pdf']:
        return HttpResponseBadRequest('must be html or pdf you are asking for something else')
    
    # first check the cache
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

    # then try to make it on ur own
    try:
        if helpers.compile(theUUID, format, 0):
            infile = open("./schedulemaker/out/%s/out.%s"%(theUUID, format), 'rb')
            if format == 'html':
                return HttpResponse(payload)
            if format == 'pdf':
                return FileResponse(infile, content_type='application/pdf')
        else:
            return HttpResponseNotFound('still workin on it')
    except Exception as e:
        # at this point, the adoc file probably doesn't exist
        return HttpResponseRedirect("../makeschedule?uuid="+theUUID)
