from django.contrib import admin

from .aiService.weaviateDb import storeData
from .models import Transcription, StatementClassification, StatementClassificationTypePrompt, llmModel, StatementLevelPrompt, FinalStatementWithLevel


@admin.action(description="correct statement push to db")
def push_to_right_classification(modeladmin, request, queryset):
    classified_objects = {}
    classified_objects['QUESTIONING_CORRECT_EXAMPLE'] = queryset.filter(category="QUESTIONING").all()
    classified_objects['OPENING_CORRECT_EXAMPLE'] = queryset.filter(category="OPENING").all()
    classified_objects['PRESENTING_CORRECT_EXAMPLE'] = queryset.filter(category="PRESENTING").all()
    for name in classified_objects.keys():
        if len(classified_objects[name]) > 0:
            print(name, classified_objects[name].values_list('statement', flat=True))
            storeData(name, classified_objects[name].values_list('statement', flat=True))
@admin.action(description="incorrect statement push to db")
def push_to_wrong_classification(modeladmin, request, queryset):
    classified_objects = {}
    classified_objects['QUESTIONING_INCORRECT_EXAMPLE'] = queryset.filter(category="QUESTIONING").all()
    classified_objects['OPENING_INCORRECT_EXAMPLE'] = queryset.filter(category="OPENING").all()
    classified_objects['PRESENTING_INCORRECT_EXAMPLE'] = queryset.filter(category="PRESENTING").all()
    for name in classified_objects.keys():
        if len(classified_objects[name]) > 0:
            print(name, classified_objects[name].values_list('statement', flat=True))
            storeData(name, classified_objects[name].values_list('statement', flat=True))
    # print(objects[0].category)
    # print(request)

@admin.register(Transcription)
class TranscriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'text', 'created_at')
    search_fields = ('id', 'text')

@admin.register(StatementClassification)
class ClassificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'transcription_id', 'segment_number', 'category', 'statement', 'levelDone')
    list_filter = ('category', 'segment_number')
    search_fields = ('category', 'transcription__id')
    actions = [push_to_right_classification, push_to_wrong_classification]


@admin.register(StatementClassificationTypePrompt)
class StatementTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'category', 'definition', 'active')
    search_fields = ('id', 'category')


@admin.register(FinalStatementWithLevel)
class FinalStatementWithLevel(admin.ModelAdmin):
    list_display = ('id', 'category', 'transcription_id', 'statement', 'level', 'reason_for_level', 'confidence_score')
    search_fields = ('transcription__id', 'category')
    list_filter = ('category',)


@admin.register(StatementLevelPrompt)
class StatementLevelPromptAdmin(admin.ModelAdmin):
    list_display = ('id', 'category', 'objective', 'evaluation_criteria', 'instruction', 'active')
    search_fields = ('id', 'category')
