from django import forms

from schedulemaker import models

from datetime import datetime as dt, timedelta as td

import pytz
from django.utils import timezone

import json

from schedulemaker.models import Network, Team, Game

class ScheduleMakingForm(forms.Form):
    league = forms.ModelChoiceField(
        models.League.objects.all(), initial=[], required=True)

    getNewData = forms.BooleanField(
        label='get data from espn instead of cache?',
        required=False
    )
    season = forms.CharField(label="if you're getting espn data and you don't want the current season, " \
    "specify which season you want here", required=False)

    seasontype = forms.IntegerField(label="preseason, regseason, postseason, offseason", required=False)

    allTeams = forms.BooleanField(
        label='all teams\' schedule?', initial=False, required=False)
    
    teams = forms.ModelMultipleChoiceField(
        models.Team.objects.all(), initial=[], required=False, label='preferred teams:')

    dailyHeaders = forms.BooleanField(
        label='daily/weekly headers?',
        required=False
    )

    useImages = forms.BooleanField(
        label='use the teams\' logos?',
        required=False
    )

    useShortName = forms.BooleanField(
        label='use team abbreviations?',
        required=False,
        initial=True
    )

    dailyPageBreaks = forms.BooleanField(
        label='page breaks for each day (or week, for football etc.) of action?',
        required=False
    )

    printByes = forms.BooleanField(
        label='print every day/week\'s byes?',
        required=False
    )

    tableHeader = forms.CharField(
        label='what should the asciidoc table header be? if u don\'t know what this is don\'t mess with it',
        required=False,
        initial=r'%autowidth.stretch'
    )

    startTime = forms.DateTimeField(initial=dt.now().replace(second=0), widget=forms.widgets.DateTimeInput(attrs={
        'type': 'datetime-local'
    }))

    endTimeEnabled = forms.BooleanField(
        label='YES, I would like to use the below end time: ',
        required=False
    )

    endTime = forms.DateTimeField(initial=dt.now().replace(second=0)+td(days=365),
                                  widget=forms.widgets.DateTimeInput(attrs={
                                      'type': 'datetime-local'
                                    }))

    whitelistMode = forms.BooleanField(
        label='Check to make the next item a whitelist instead of blacklist',
        required=False
    )

    blacklist = forms.ModelMultipleChoiceField(
        queryset = models.Network.objects.all(),
        label='Select networks to blacklist (or whitelist)',
        required=False,
    )

    nameSubs = forms.JSONField(
        label='If you want to substitute network names, then write some json here (single quote preferred). For example' \
        'this replaces NBC Sports Network with NBCSN.',
        initial="{'NBC Sports Network': 'NBCSN'}"
    )

    timezone = forms.ChoiceField(
        choices = [(tz, tz) for tz in pytz.common_timezones],
        initial=timezone.get_current_timezone_name()
    )

    imgwidth = forms.IntegerField(
        label='Width of images in the webpage',
        initial=30
    )

    pdfwidth = forms.IntegerField(
        label='Width of images in the pdf',
        initial=30
    )

    paperwidth = forms.FloatField(
        label='Width of the paper in inches',
        initial=8.5
    )

    paperheight = forms.FloatField(
        label='Height of the paper in inches',
        initial=11
    )

    horzmargin = forms.FloatField(
        label="Horizontal margin in inches",
        initial=0.5
    )

    vertmargin = forms.FloatField(
        label="Vertical margin in inches",
        initial=0.5
    )

    headingsize = forms.FloatField(
        label="Size of the header (pt)",
        initial=16
    )

    fontsize = forms.FloatField(
        label="Size of the reg. text (pt)",
        initial=16 
    )

    generateSchedule = forms.BooleanField(
        label="When you are ready to create the schedule, check this box. NOTE it may take a long time!",
        required=False
    )

    # returns json formatted string to use as preset
    def createPreset(self) -> dict:
        if self.is_valid():
            preset = self.cleaned_data.copy()

            preset['league'] = preset['league'].id
            preset['teams'] = [t.id for t in preset['teams']]
            preset['startTime'] = preset['startTime'].isoformat()
            preset['endTime'] = preset['endTime'].isoformat()
            preset['blacklist'] = [n.id for n in preset['blacklist']]

            return preset
        
        return None
            

    def applyPreset(self, preset:dict):
        preset['startTime'] = dt.fromisoformat(preset['startTime'])
        preset['endTime'] = dt.fromisoformat(preset['endTime'])

        for key in preset.keys():
            try:
                self.initial[key] = preset[key]#League.objects.get(id=preset['league'])
            except KeyError as e:
                print("ERROR APPLYING THE " + key + " PRESET")
                pass
        
        self.populateQuerySets()

    # populates the network blacklist and the teams list
    def populateQuerySets(self):
        if self.is_valid():
            data = self.cleaned_data

            # first populate the network blacklist
            network_ids = set()
            for team in data['league'].teams.all():
                for game in team.gamesashome.all():
                    for network in game.networks.all():
                        network_ids.add(network.id)
            self.fields['blacklist'].queryset = Network.objects.filter(id__in=network_ids)
            
            # then populate the team list
            self.fields['teams'].queryset = Team.objects.filter(league=data['league'])

        else:
            print(dt.now(), "ERROR: Invalid form")
            print(self.errors)
            print(self.non_field_errors)
            print(self.initial)

class PresetFileUploadForm(forms.Form):
    file = forms.FileField()

class ScheduleRenameForm(forms.Form):
    name = forms.CharField(label="Rename this schedule if you so desire")