from django.contrib.postgres.fields import ArrayField
from django.db import models

STATEMENT_TYPES = [
        ('OPENING', 'Opening'),
        ('QUESTIONING', 'Questioning'),
        ('PRESENTING', 'Presenting'),
        ('CLOSING_OUTCOME', 'Closing & Outcome'),
]

CATEGORY_CHOICES = [
        ('OPENING', 'Opening'),
        ('QUESTIONING', 'Questioning'),
        ('PRESENTING', 'Presenting'),
        ('CLOSING_OUTCOME', 'Closing & Outcome'),
    ]
class Transcription(models.Model):
    text = models.TextField()
    segments = ArrayField(
        models.TextField(),  # Define the type of data in the array
        size=None,  # If you do not want to limit the number of segments, keep size=None
        default=list  # Default to an empty list if no segments are provided
    )
    docker_feteched = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.id)

class StatementClassification(models.Model):
    transcription = models.ForeignKey(Transcription, on_delete=models.CASCADE)
    segment_number = models.IntegerField(default=-1, blank=True, null=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    statement = models.TextField()
    levelDone = models.BooleanField(default=False)

    def transcription_id(self):
        return self.transcription.id

    transcription_id.short_description = 'transcription ID'


class StatementClassificationTypePrompt(models.Model):
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, unique=True)
    definition = models.TextField()
    examples = models.TextField()
    invalid_examples = models.TextField()
    active = models.BooleanField(default=True)

class StatementLevelPrompt(models.Model):
    category = models.CharField(max_length=20, choices=STATEMENT_TYPES, unique=True)
    objective = models.TextField()
    evaluation_criteria = models.TextField()
    score_assignment_criteria = models.TextField()
    instruction = models.TextField()
    examples = models.TextField()
    notes = models.TextField()
    active = models.BooleanField(default=True)

class llmModel(models.Model):
    name = models.CharField(max_length=100)
    ibm_name = models.CharField(max_length=100)
    active = models.BooleanField(default=False)


class FinalStatementWithLevel(models.Model):
    transcription = models.ForeignKey(Transcription, on_delete=models.CASCADE)
    category = models.CharField(max_length=20, choices=STATEMENT_TYPES)
    level = models.IntegerField(blank=True, null=True)
    confidence_score = models.TextField(blank=True, null=True)
    reason_for_level = models.TextField(blank=True, null=True)
    statement = models.TextField()
