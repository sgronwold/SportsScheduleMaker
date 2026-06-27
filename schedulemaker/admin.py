from django.contrib import admin
from django.contrib.auth.models import User

from schedulemaker import models

# Register your models here.
@admin.register(models.League)
class LeagueAdmin(admin.ModelAdmin):
    list_display = ['id', 'sport', 'league', 'weekly_games']

@admin.register(models.Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ['location', 'name']

@admin.register(models.Network)
class NetworkAdmin(admin.ModelAdmin):
    list_display = ['market', 'name']

@admin.register(models.Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ['awayteam', 'hometeam', 'start', 'timevalid']

@admin.register(models.Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ['name', 'uuid', 'preset', 'htmlReady', 'pdfReady']
