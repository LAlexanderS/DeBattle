from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from debattle.models import DebattleEvent, Round
from .models import JuryMember, Score, JuryMatchSubmission

@login_required
@require_http_methods(["GET", "POST"])
def jury_view(request, slug: str):
    event = get_object_or_404(DebattleEvent, slug=slug)

    jury = JuryMember.objects.filter(user=request.user, event=event, is_active=True).first()
    if not jury:
        return render(request, "debattle/jury_denied.html", {"event": event}, status=403)

    match = event.current_match
    if not match:
        return render(request, "debattle/jury.html", {"event": event, "jury": jury, "match": None})

    submission, _ = JuryMatchSubmission.objects.get_or_create(match=match, jury=jury)
    criteria = list(event.criteria.all().order_by("id"))

    # ВАЖНО: submit запрещён до старта 3-го раунда
    can_submit = event.current_round_number >= 3

    if request.method == "POST":
        action = request.POST.get("action", "")

        if submission.is_submitted:
            messages.error(request, "Итог уже отправлен. Изменения запрещены.")
            return redirect("debattle_jury", slug=slug)

        if action == "set_score":
            try:
                team_id = int(request.POST["team_id"])
                criterion_id = int(request.POST["criterion_id"])
                value = int(request.POST["value"])
            except Exception:
                messages.error(request, "Некорректные данные.")
                return redirect("debattle_jury", slug=slug)

            if value not in (1, 2, 3):
                messages.error(request, "Оценка может быть только 1, 2 или 3.")
                return redirect("debattle_jury", slug=slug)

            # менять можно всегда (в любой момент матча)
            Score.objects.update_or_create(
                match=match,
                jury=jury,
                team_id=team_id,
                criterion_id=criterion_id,
                defaults={"value": value},
            )
            messages.success(request, "Оценка сохранена.")
            return redirect("debattle_jury", slug=slug)

        if action == "submit_final":
            if not can_submit:
                messages.error(request, "Нельзя отправить итог до старта 3-го раунда.")
                return redirect("debattle_jury", slug=slug)

            submission.submit()
            messages.success(request, "Итог отправлен. Спасибо.")
            return redirect("debattle_jury", slug=slug)

        messages.error(request, "Неизвестное действие.")
        return redirect("debattle_jury", slug=slug)

    # map для вывода текущих оценок: "team_id:criterion_id" -> value
    scores = Score.objects.filter(jury=jury, match=match).select_related("team", "criterion")
    score_map = {f"{s.team_id}:{s.criterion_id}": int(s.value) for s in scores}

    # Получаем текущий раунд и все раунды матча
    from debattle.models import Round
    current_round = None
    all_rounds = []
    if event.current_round_number:
        current_round = Round.objects.filter(match=match, number=event.current_round_number).first()
    all_rounds = Round.objects.filter(match=match).order_by("number")

    return render(
        request,
        "debattle/jury.html",
        {
            "event": event,
            "jury": jury,
            "match": match,
            "criteria": criteria,
            "score_map": score_map,
            "submission": submission,
            "can_submit": can_submit,
            "current_round": current_round,
            "all_rounds": all_rounds,
        },
    )