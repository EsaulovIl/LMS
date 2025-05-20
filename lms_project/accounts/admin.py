from django.contrib import admin

from .models import StudentGroup

@admin.register(StudentGroup)
class StudentGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'mentor')
    filter_horizontal = ('students',)