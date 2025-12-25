from collections import defaultdict
from decimal import Decimal

from debattle.models import Match
from .models import Score, JuryMatchSubmission


def compute_match_results(match: Match) -> dict:
    submitted_jury_ids = list(
        JuryMatchSubmission.objects.filter(match=match, is_submitted=True)
        .values_list("jury_id", flat=True)
    )

    if not submitted_jury_ids:
        return {"team_totals": {}, "team_by_criterion": {}, "submitted_jury_count": 0}

    qs = Score.objects.filter(match=match, jury_id__in=submitted_jury_ids).select_related("team", "criterion")

    team_totals = defaultdict(Decimal)
    team_by_criterion = defaultdict(lambda: defaultdict(Decimal))

    for s in qs:
        team_totals[s.team_id] += Decimal(s.value)
        team_by_criterion[s.team_id][s.criterion_id] += Decimal(s.value)

    return {
        "team_totals": dict(team_totals),
        "team_by_criterion": {k: dict(v) for k, v in team_by_criterion.items()},
        "submitted_jury_count": len(submitted_jury_ids),
    }