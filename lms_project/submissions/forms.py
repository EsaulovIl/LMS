from django import forms
from .models import Submission, SubmissionFile


class SubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['status']  # статус выставляет ментор/авто; для студента можно не показывать


class SubmissionFileForm(forms.ModelForm):
    class Meta:
        model = SubmissionFile
        fields = ['file_path']
        widgets = {
            'file_path': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
        }
