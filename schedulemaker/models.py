from django.db import models

# Create your models here.
class League(models.Model):
    sport = models.CharField(max_length=100)
    league = models.CharField(max_length=100)
    weekly_games = models.BooleanField()

    def __str__(self):
        return self.sport + " " + self.league

class Team(models.Model):
    espnid = models.IntegerField()
    location = models.CharField(max_length=100)
    name = models.CharField(max_length=100)
    displayName = models.CharField(max_length=100)
    shortDisplayName = models.CharField(max_length=100)
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name='teams')
    tricode = models.CharField(max_length=10)
    logo = models.URLField(null=True)

    can_have_bye = models.BooleanField(default=False)

    def __str__(self):
        return "(%s) %s %s"%(self.league.league, self.location, self.name)
    
    # the espnid's won't *necessarily* be unique, since each league has its own id system
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['espnid', 'league'], name='team_espnid_league_unique')
        ]

class Network(models.Model):
    market = models.CharField(max_length=30)
    name = models.CharField(max_length=50)

    def __str__(self):
        return "(%s) %s"%(self.market,self.name)
    
    class Meta:
        ordering = ['-market']
        constraints = [
            models.UniqueConstraint(fields=['market', 'name'], name='network_market_name_unique')
        ]

class Game(models.Model):
    espnid = models.BigIntegerField(unique=True)
    start = models.DateTimeField()
    timevalid = models.BooleanField(default=True)
    awayteam = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='gamesasaway')
    hometeam = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='gamesashome')

    awayscore = models.SmallIntegerField()
    homescore = models.SmallIntegerField()
    gameover = models.BooleanField()

    # latest year of the season
    # for example the 2024-2025 season would be 2025
    season = models.SmallIntegerField()

    # 1 preseason 2 regseason 3 postseason (and 4 offseason but this should never happen)
    seasontype = models.SmallIntegerField()

    networks = models.ManyToManyField(Network, related_name='games')
    week = models.SmallIntegerField(null=True)

    class Meta:
        ordering = ['start']

class Schedule(models.Model):
    uuid = models.UUIDField()
    preset = models.JSONField(default=dict)
    adocReady = models.BooleanField(default=False)
    htmlReady = models.BooleanField(default=False)
    pdfReady = models.BooleanField(default=False)
    name = models.TextField(default="Untitled")