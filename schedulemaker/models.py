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

    def __str__(self):
        return "(%s) %s %s"%(self.league.league, self.location, self.name)

class Network(models.Model):
    market = models.TextField(max_length=30)
    name = models.TextField(max_length=50)

    def __str__(self):
        return "(%s) %s"%(self.market,self.name)
    
    class Meta:
        ordering = ['-market']

class Game(models.Model):
    espnid = models.BigIntegerField(unique=True)
    start = models.DateTimeField()
    timevalid = models.BooleanField(default=True)
    awayteam = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='gamesasaway')
    hometeam = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='gamesashome')

    awayscore = models.SmallIntegerField()
    homescore = models.SmallIntegerField()
    gameover = models.BooleanField()

    # 1 preseason 2 regseason 3 postseason (and 4 offseason but this should never happen)
    seasontype = models.SmallIntegerField()

    networks = models.ManyToManyField(Network, related_name='games')
    week = models.SmallIntegerField(null=True)

class Schedule(models.Model):
    uuid = models.UUIDField()
    preset = models.JSONField(default=dict)
    adocReady = models.BooleanField(default=False)
    htmlReady = models.BooleanField(default=False)
    pdfReady = models.BooleanField(default=False)
    name = models.TextField(default="Untitled")