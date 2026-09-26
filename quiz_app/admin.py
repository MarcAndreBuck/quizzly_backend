from django.contrib import admin

from .models import Quiz, Question


class QuestionInline(admin.TabularInline):
    """Allow editing questions directly within a quiz."""

    model = Question
    extra = 0


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    """Configure quiz management in Django admin."""

    list_display = ('id', 'title', 'user', 'created_at')
    search_fields = ('title', 'user__username')
    inlines = [QuestionInline]


admin.site.register(Question)
