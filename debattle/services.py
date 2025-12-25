from django.db import transaction
from django.db.models import Count

from .models import DebattleEvent, Tour, TourTeam, Team


@transaction.atomic
def add_team_to_tour(event: DebattleEvent, team: Team) -> Tour:
    # Берём открытый тур (самый ранний открытый)
    tour = (
        Tour.objects.select_for_update()
        .filter(event=event, status=Tour.Status.OPEN)
        .annotate(cnt=Count("teams"))
        .order_by("number")
        .first()
    )

    if tour is None:
        last_number = Tour.objects.filter(event=event).aggregate(mx=Count("id"))["mx"] or 0
        # number лучше считать по max(number), но для MVP можно так.
        # Сделаем правильно:
        last = Tour.objects.filter(event=event).order_by("-number").first()
        next_number = (last.number + 1) if last else 1
        tour = Tour.objects.create(event=event, number=next_number, status=Tour.Status.OPEN)

    TourTeam.objects.create(tour=tour, team=team)

    # Если после добавления стало 4 команды — закрываем тур
    teams_count = TourTeam.objects.filter(tour=tour).count()
    if teams_count >= 4:
        tour.status = Tour.Status.CLOSED
        tour.save(update_fields=["status"])

    return tour