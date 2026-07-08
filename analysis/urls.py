from django.urls import path
from .views import ClassificationView, FullSyncProcessView, TranscriptionView, VectorDataView, LevellingDataView, highest_level_statements, \
    FullProcessView, highest_level_statements_docker_results, transcription_status_update

urlpatterns = [
    path('classification/', ClassificationView.as_view(), name='classification'),
    path('transcription/', TranscriptionView.as_view(), name='transcript'),
    path('transcription/<int:transcript_id>/', transcription_status_update, name='transcript_details'),
    path('vectorDb/', VectorDataView.as_view(), name='vectorDb'),
    path('rating/', LevellingDataView.as_view(), name='rating'),
    path('results/<int:transcript_id>/', highest_level_statements, name='highest_level_statements'),
    path('docker-results/<int:transcript_id>/', highest_level_statements_docker_results, name='highest_level_statements_docker'),
    path('process/', FullProcessView.as_view(), name='full_process_single_api'),
    path('sync-process/', FullSyncProcessView.as_view(), name='full_sync_process_single_api'),
]