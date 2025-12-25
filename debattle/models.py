from django.db import models
from django.utils import timezone


class DebattleEvent(models.Model):
    class State(models.TextChoices):
        COUNTDOWN = "COUNTDOWN"
        REGISTRATION = "REGISTRATION"
        ROULETTE = "ROULETTE"
        PREVIEW = "PREVIEW"
        ROUND_ACTIVE = "ROUND_ACTIVE"
        VOTING_OPEN = "VOTING_OPEN"
        RESULTS = "RESULTS"
        FINISHED = "FINISHED"

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    start_at = models.DateTimeField()

    state = models.CharField(max_length=32, choices=State.choices, default=State.COUNTDOWN)

    themes_revealed = models.BooleanField(default=False)
    voting_open = models.BooleanField(default=False)
    current_round_number = models.PositiveSmallIntegerField(default=0)

    current_tour = models.ForeignKey("Tour", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    current_match = models.ForeignKey("Match", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    created_at = models.DateTimeField(auto_now_add=True)

    def can_show_themes_button(self) -> bool:
        # За 7 дней до start_at
        return timezone.now() >= (self.start_at - timezone.timedelta(days=7))

    class Meta:
        verbose_name = "ДеБатл"
        verbose_name_plural = "ДеБатл"


class Theme(models.Model):
    event = models.ForeignKey(DebattleEvent, on_delete=models.CASCADE, related_name="themes")
    order = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=255)

    class Meta:
        unique_together = ("event", "order")
        ordering = ["order"]
        verbose_name = "Темы"
        verbose_name_plural = "Темы"


class Team(models.Model):
    event = models.ForeignKey(DebattleEvent, on_delete=models.CASCADE, related_name="teams")
    name = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name

    class Meta:
        verbose_name = "Команды"
        verbose_name_plural = "Команды"


class Participant(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="participants")
    name = models.CharField(max_length=120)
    photo = models.ImageField(upload_to="participants/", blank=True, null=True)
    bio = models.TextField(blank=True)

    def __str__(self) -> str:
        return self.name


class Tour(models.Model):
    class Status(models.TextChoices):
        OPEN = "OPEN"
        CLOSED = "CLOSED"
        RUNNING = "RUNNING"
        FINISHED = "FINISHED"

    event = models.ForeignKey(DebattleEvent, on_delete=models.CASCADE, related_name="tours")
    number = models.PositiveIntegerField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)

    teams = models.ManyToManyField(Team, through="TourTeam", related_name="tours")

    class Meta:
        unique_together = ("event", "number")
        ordering = ["number"]
        verbose_name = "Туры"
        verbose_name_plural = "Туры"


class TourTeam(models.Model):
    tour = models.ForeignKey(Tour, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("tour", "team")


class Match(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING"
        RUNNING = "RUNNING"
        DONE = "DONE"

    tour = models.ForeignKey(Tour, on_delete=models.CASCADE, related_name="matches")
    team_a = models.ForeignKey(Team, on_delete=models.PROTECT, related_name="+")
    team_b = models.ForeignKey(Team, on_delete=models.PROTECT, related_name="+")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    winner = models.ForeignKey(Team, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    created_at = models.DateTimeField(auto_now_add=True)


class Round(models.Model):
    class Status(models.TextChoices):
        READY = "READY"
        ACTIVE = "ACTIVE"
        VOTING = "VOTING"
        LOCKED = "LOCKED"

    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name="rounds")
    number = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.READY)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("match", "number")
        ordering = ["number"]
        verbose_name = "Раунды"
        verbose_name_plural = "Раунды"