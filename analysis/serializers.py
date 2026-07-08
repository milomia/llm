from rest_framework import serializers
from .models import Transcription, StatementClassification


class ClassificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatementClassification
        fields = '__all__'


class TranscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transcription
        fields = ['id', 'text']