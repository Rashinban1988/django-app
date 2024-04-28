from django.urls import path, include
from .views import TranscriptionViewSet

urlpatterns = [
    # UploadedFileのIDに紐づいたTranscriptionの一覧を取得するための新しいパス
    path('transcriptions/uploaded-file/<int:uploadedfile_id>/', TranscriptionViewSet.as_view({
        'get': 'list'
    }), name='transcriptions-by-uploadedfile'),
]