from django.contrib import admin
from .models import DebattleEvent, Theme, Team, Participant, Tour, TourTeam, Match, Round
from accounts.models import ScoreCriterion

class ThemeInline(admin.TabularInline):
    model = Theme
    extra = 9


@admin.register(DebattleEvent)
class DebattleEventAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("title",)}
    inlines = [ThemeInline]
    list_display = ("title", "start_at", "state", "themes_revealed", "voting_open")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        # если критериев нет — создаём 5 дефолтных
        if obj.criteria.count() == 0:
            default_titles = [
                "Аргументация",
                "Логика",
                "Подача",
                "Командная работа",
                "Ответы на вопросы",
            ]
            for t in default_titles:
                ScoreCriterion.objects.create(event=obj, title=t, max_value=3)


admin.site.register(Team)
admin.site.register(Participant)
admin.site.register(Tour)
admin.site.register(TourTeam)
admin.site.register(Match)
admin.site.register(Round)