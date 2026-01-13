import random
from django.db import transaction
from django.utils import timezone

from .models import DebattleEvent, Tour, Match, Round


def _pick_current_tour(event: DebattleEvent) -> Tour | None:
    # Берём тур:
    # 1) если уже выбран current_tour — используем его
    # 2) иначе первый CLOSED тур (полностью набран) который ещё не FINISHED
    # 3) иначе None
    if event.current_tour_id:
        return event.current_tour

    tour = (
        Tour.objects.filter(event=event, status__in=[Tour.Status.CLOSED, Tour.Status.RUNNING])
        .order_by("number")
        .first()
    )
    return tour


@transaction.atomic
def reveal_themes(event: DebattleEvent) -> None:
    event.themes_revealed = True
    if event.state == DebattleEvent.State.COUNTDOWN:
        event.state = DebattleEvent.State.REGISTRATION
    event.save(update_fields=["themes_revealed", "state"])


@transaction.atomic
def set_current_tour(event: DebattleEvent, tour_id: int) -> None:
    tour = Tour.objects.select_for_update().get(id=tour_id, event=event)
    event.current_tour = tour
    event.save(update_fields=["current_tour"])


@transaction.atomic
def start_roulette(event: DebattleEvent) -> Match:
    tour = _pick_current_tour(event)
    if tour is None:
        raise ValueError("Нет доступного тура для рулетки. Нужен тур со статусом CLOSED/RUNNING.")

    teams = list(tour.teams.all())
    if len(teams) < 2:
        raise ValueError("В туре меньше 2 команд.")

    if len(teams) > 4:
        # На всякий случай, чтобы не было сюрпризов
        teams = teams[:4]

    # Проверяем, есть ли уже матчи в этом туре
    existing_matches = Match.objects.filter(tour=tour)
    used_teams = set()
    for match in existing_matches:
        used_teams.add(match.team_a_id)
        used_teams.add(match.team_b_id)
    
    # Если уже есть матч, выбираем оставшиеся команды
    if existing_matches.exists():
        remaining_teams = [t for t in teams if t.id not in used_teams]
        if len(remaining_teams) < 2:
            raise ValueError("Недостаточно оставшихся команд для второго матча.")
        team_a, team_b = remaining_teams[0], remaining_teams[1]
    else:
        # Первый раз - случайный выбор
        team_a, team_b = random.sample(teams, 2)

    match = Match.objects.create(tour=tour, team_a=team_a, team_b=team_b, status=Match.Status.PENDING)

    # Обновляем состояние ивента
    event.current_tour = tour
    event.current_match = match
    event.current_round_number = 0
    event.voting_open = False
    event.state = DebattleEvent.State.PREVIEW
    event.save(update_fields=[
        "current_tour", "current_match", "current_round_number", "voting_open", "state"
    ])

    # Тур можно перевести в RUNNING
    if tour.status != Tour.Status.RUNNING:
        tour.status = Tour.Status.RUNNING
        tour.save(update_fields=["status"])

    return match


@transaction.atomic
def start_next_round(event: DebattleEvent) -> Round:
    if not event.current_match_id:
        raise ValueError("Нет текущего матча. Сначала запусти рулетку.")

    if event.current_round_number >= 3:
        raise ValueError("Всего предусмотрено 3 раунда. Больше запускать нельзя.")
    
    match = event.current_match

    next_number = event.current_round_number + 1

    rnd, _created = Round.objects.get_or_create(
        match=match,
        number=next_number,
        defaults={"status": Round.Status.ACTIVE, "started_at": timezone.now()},
    )

    # если раунд существовал — активируем
    rnd.status = Round.Status.ACTIVE
    rnd.started_at = rnd.started_at or timezone.now()
    
    # Если тема еще не выбрана для матча, выбираем её при первом раунде
    if not match.theme_id:
        # Получаем все темы события
        all_themes = list(event.themes.all())
        
        # Получаем уже использованные темы в других матчах этого тура
        used_themes = set(
            Match.objects.filter(tour=match.tour)
            .exclude(id=match.id)
            .exclude(theme__isnull=True)
            .values_list("theme_id", flat=True)
        )
        
        # Выбираем из оставшихся тем
        available_themes = [t for t in all_themes if t.id not in used_themes]
        
        if not available_themes:
            raise ValueError("Все темы уже использованы в этом туре.")
        
        # Случайный выбор темы для матча
        selected_theme = random.choice(available_themes)
        match.theme = selected_theme
        match.save(update_fields=["theme"])
    
    # Позиции выбираются один раз при первом раунде и фиксируются для всего матча
    if not match.team_a_position or not match.team_b_position:
        # Случайный выбор позиций (за/против) для всего матча
        positions = [Match.Position.FOR, Match.Position.AGAINST]
        random.shuffle(positions)
        match.team_a_position = positions[0]
        match.team_b_position = positions[1]
        match.save(update_fields=["team_a_position", "team_b_position"])
    
    rnd.save(update_fields=["status", "started_at"])

    event.current_round_number = next_number
    event.voting_open = False
    event.state = DebattleEvent.State.ROUND_ACTIVE
    event.save(update_fields=["current_round_number", "voting_open", "state"])

    return rnd


@transaction.atomic
def open_voting(event: DebattleEvent) -> None:
    if not event.current_match_id or event.current_round_number == 0:
        raise ValueError("Нет активного раунда. Сначала запусти раунд.")

    rnd = Round.objects.select_for_update().get(match=event.current_match, number=event.current_round_number)
    rnd.status = Round.Status.VOTING
    rnd.save(update_fields=["status"])

    event.voting_open = True
    event.state = DebattleEvent.State.VOTING_OPEN
    event.save(update_fields=["voting_open", "state"])


@transaction.atomic
def close_voting(event: DebattleEvent) -> None:
    if not event.current_match_id or event.current_round_number == 0:
        raise ValueError("Нет активного раунда.")

    rnd = Round.objects.select_for_update().get(match=event.current_match, number=event.current_round_number)
    rnd.status = Round.Status.LOCKED
    rnd.ended_at = timezone.now()
    rnd.save(update_fields=["status", "ended_at"])

    event.voting_open = False
    event.state = DebattleEvent.State.RESULTS
    event.save(update_fields=["voting_open", "state"])