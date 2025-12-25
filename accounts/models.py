from django.db import models
from django.contrib.auth.models import User
from debattle.models import DebattleEvent, Team, Round
from django.utils import timezone
from debattle.models import Match

class JuryMember(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    event = models.ForeignKey(DebattleEvent, on_delete=models.CASCADE, related_name="jury")
    display_name = models.CharField(max_length=120, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.display_name or self.user.username

    class Meta:
        verbose_name = "Жюри"
        verbose_name_plural = "Жюри"


class ScoreCriterion(models.Model):
    event = models.ForeignKey(DebattleEvent, on_delete=models.CASCADE, related_name="criteria")
    title = models.CharField(max_length=64)
    max_value = models.PositiveSmallIntegerField(default=10)

    def __str__(self) -> str:
        return self.title

    class Meta:
        verbose_name = "Критерии оценок"
        verbose_name_plural = "Критерии оценок"


class Score(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name="scores")
    jury = models.ForeignKey(JuryMember, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    criterion = models.ForeignKey(ScoreCriterion, on_delete=models.CASCADE)
    value = models.PositiveSmallIntegerField()  # 1..3

    class Meta:
        unique_together = ("match", "jury", "team", "criterion")
        verbose_name = "Оценка"
        verbose_name_plural = "Оценки"


class JuryMatchSubmission(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name="jury_submissions")
    jury = models.ForeignKey(JuryMember, on_delete=models.CASCADE, related_name="match_submissions")
    is_submitted = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("match", "jury")

    def submit(self):
        self.is_submitted = True
        self.submitted_at = timezone.now()
        self.save(update_fields=["is_submitted", "submitted_at"])