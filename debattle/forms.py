from django import forms
from .models import Team, Participant


class TeamCreateForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ["name"]


class ParticipantForm(forms.ModelForm):
    class Meta:
        model = Participant
        fields = ["name", "photo", "bio"]
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 3}),
        }