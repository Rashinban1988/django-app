from django.urls import path, include
from .views import UploadedFileViewSet, TranscriptionViewSet

urlpatterns = [
    # UploadedFileの一覧を取得するためのパス
    path('uploaded-files/', UploadedFileViewSet.as_view({
        'get': 'list',
    }), name='uploaded-files-list'),

    path('uploaded-files/<int:pk>/', UploadedFileViewSet.as_view({
        'get': 'retrieve'
    }), name='uploaded-file-detail'),

    # UploadedFileのIDに紐づいたTranscriptionの一覧を取得するための新しいパス
    path('transcriptions/uploaded-file/<int:uploadedfile_id>/', TranscriptionViewSet.as_view({
        'get': 'list'
    }), name='transcriptions-by-uploadedfile'),
]