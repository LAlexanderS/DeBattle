from django.contrib import admin
from .models import JuryMember, ScoreCriterion, Score

admin.site.register(JuryMember)
admin.site.register(ScoreCriterion)
admin.site.register(Score)