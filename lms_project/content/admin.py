from django.contrib import admin
"""
from .models import Theme, VideoLesson, VideoProgress, Notebook

@admin.register(Theme)
class ThemeAdmin(admin.ModelAdmin):
    list_display  = ('id','name','section','complexity','priority')
    list_filter   = ('section','complexity')
    search_fields = ('name',)

@admin.register(VideoLesson)
class VideoLessonAdmin(admin.ModelAdmin):
    list_display  = ('id','title','theme','uploaded_at')
    list_filter   = ('theme',)
    search_fields = ('title',)

@admin.register(VideoProgress)
class VideoProgressAdmin(admin.ModelAdmin):
    list_display  = ('student','video','watched_percent','last_watched_at')
    list_filter   = ('video',)

@admin.register(Notebook)
class NotebookAdmin(admin.ModelAdmin):
    list_display  = ('id','title','theme','uploaded_at')
    list_filter   = ('theme',)
    search_fields = ('title',)
"""