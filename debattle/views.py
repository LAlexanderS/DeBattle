from django.shortcuts import render, get_object_or_404
from .models import DebattleEvent, Round

from django.shortcuts import redirect
from django.forms import modelformset_factory

from .forms import TeamCreateForm, ParticipantForm
from .models import Participant
from .services import add_team_to_tour
from accounts.models import Score
from accounts.services import compute_match_results

from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages

from .game_flow import reveal_themes, set_current_tour, start_roulette, start_next_round, open_voting, close_voting
from accounts.models import JuryMember, JuryMatchSubmission

from django.http import HttpResponse

def screen_view(request, slug: str):
    event = get_object_or_404(DebattleEvent, slug=slug)
    tours = event.tours.prefetch_related("teams").all()

    match = event.current_match
    rnd = None
    results = None
    criteria = list(event.criteria.all().order_by("id"))

    if match and event.current_round_number:
        rnd = Round.objects.filter(match=match, number=event.current_round_number).first()

    if match and event.state == DebattleEvent.State.RESULTS:
        results = compute_match_results(match)

    return render(
        request,
        "debattle/screen.html",
        {
            "event": event,
            "tours": tours,
            "match": match,
            "round": rnd,
            "results": results,
            "criteria": criteria,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def control_view(request, slug: str):
    if not request.user.is_staff:
        return HttpResponse("Доступ запрещён", status=403)

    event = get_object_or_404(DebattleEvent, slug=slug)
    tours = event.tours.prefetch_related("teams").all()

    if request.method == "POST":
        action = request.POST.get("action", "")

        try:
            if action == "reveal_themes":
                reveal_themes(event)
                messages.success(request, "Темы раскрыты.")

            elif action == "set_tour":
                tour_id = int(request.POST["tour_id"])
                set_current_tour(event, tour_id)
                messages.success(request, "Текущий тур выбран.")

            elif action == "start_roulette":
                m = start_roulette(event)
                messages.success(request, f"Рулетка: выбрана пара {m.team_a.name} vs {m.team_b.name}.")

            elif action == "start_round":
                rnd = start_next_round(event)
                messages.success(request, f"Запущен раунд {rnd.number}.")

            elif action == "open_voting":
                open_voting(event)
                messages.success(request, "Голосование открыто.")

            elif action == "close_voting":
                close_voting(event)
                messages.success(request, "Голосование закрыто. Показ результатов.")

            else:
                messages.error(request, "Неизвестное действие.")

        except Exception as e:
            messages.error(request, f"Ошибка: {e}")

        return redirect("debattle_control", slug=slug)

    jury_total = JuryMember.objects.filter(event=event, is_active=True).count()

    submitted = 0
    if event.current_match_id:
        submitted = JuryMatchSubmission.objects.filter(match=event.current_match, is_submitted=True).count()

    scores_count = 0
    expected_scores = 0

    if event.current_match_id:
        match = event.current_match
        rounds_count = match.rounds.count()
        # ожидаем: кол-во судей * раунды * 2 команды * 5 критериев
        expected_scores = jury_total * 2 * 5
        scores_count = Score.objects.filter(match=event.current_match).count()
    else:
        match = None

    # Получаем текущий раунд и все раунды матча
    current_round = None
    all_rounds = []
    if match:
        if event.current_round_number:
            current_round = Round.objects.filter(match=match, number=event.current_round_number).first()
        all_rounds = Round.objects.filter(match=match).order_by("number")

    return render(
        request,
        "debattle/control.html",
        {
            "event": event,
            "tours": tours,
            "jury_total": jury_total,
            "submitted": submitted,
            "scores_count": scores_count,
            "expected_scores": expected_scores,
            "match": match,
            "current_round": current_round,
            "all_rounds": all_rounds,
        },
    )


def register_team_view(request, slug: str):
    event = get_object_or_404(DebattleEvent, slug=slug)

    # после старта регистрацию можно закрыть
    # (позже сделаем флагом/состоянием, пока так)
    # if timezone.now() >= event.start_at:
    #     return HttpResponse("Регистрация закрыта", status=403)

    ParticipantFormSet = modelformset_factory(
        Participant,
        form=ParticipantForm,
        extra=2,
        max_num=2,
        validate_max=True,
        can_delete=False,
    )

    if request.method == "POST":
        team_form = TeamCreateForm(request.POST)
        formset = ParticipantFormSet(request.POST, request.FILES, queryset=Participant.objects.none())

        if team_form.is_valid() and formset.is_valid():
            team = team_form.save(commit=False)
            team.event = event
            team.save()

            participants = formset.save(commit=False)
            # строго 2 участника
            if len(participants) != 2:
                team.delete()
                messages.error(request, "Нужно указать ровно 2 участников.")
                return redirect("debattle_register", slug=slug)

            for p in participants:
                p.team = team
                p.save()

            tour = add_team_to_tour(event, team)

            messages.success(request, f"Команда зарегистрирована и добавлена в тур №{tour.number}.")
            return redirect("debattle_register", slug=slug)

        messages.error(request, "Проверь поля: где-то ошибка.")

    else:
        team_form = TeamCreateForm()
        formset = ParticipantFormSet(queryset=Participant.objects.none())

    return render(
        request,
        "debattle/register.html",
        {"event": event, "team_form": team_form, "formset": formset},
    )

def index_view(request):
    return render(request, "index.html")