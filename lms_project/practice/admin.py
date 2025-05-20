from django.contrib import admin

"""
from .models import PracticeAssignment, PracticeAssignmentExercise

class PracticeAssignmentExerciseInline(admin.TabularInline):
    model = PracticeAssignmentExercise
    extra = 0
    fields = ('exercise', 'grade')

@admin.register(PracticeAssignment)
class PracticeAssignmentAdmin(admin.ModelAdmin):
    list_display  = (
        'id',
        'student',
        'theme',
        'assigned_at',
        'deadline',
        'total_score'
    )
    list_filter   = ('theme','deadline','assigned_at')
    search_fields = ('student__username','theme__name')
    inlines       = [PracticeAssignmentExerciseInline]
"""
