from django.contrib import admin

"""
from .models import Homework, HomeworkExercise

class HomeworkExerciseInline(admin.TabularInline):
    model = HomeworkExercise
    extra = 0
    fields = ('exercise','grade')

@admin.register(Homework)
class HomeworkAdmin(admin.ModelAdmin):
    list_display  = ('id','theme','assigned_at','deadline','total_score','max_score')
    list_filter   = ('theme','deadline')
    inlines       = [HomeworkExerciseInline]
    search_fields = ('theme__name',)

@admin.register(HomeworkExercise)
class HomeworkExerciseAdmin(admin.ModelAdmin):
    list_display  = ('homework','exercise','grade')
    list_filter   = ('homework',)
    search_fields = ('exercise__description',)
"""
