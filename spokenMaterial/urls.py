from django.urls import path, include
from .views import UploadedFileViewSet, TranscriptionViewSet

urlpatterns = [

    path('uploaded-files/', UploadedFileViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='uploaded-files-list'),

    path('uploaded-files/<int:pk>/', UploadedFileViewSet.as_view({
        'get': 'retrieve'
    }), name='uploaded-file-detail'),

    path('transcriptions/', TranscriptionViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='transcriptions-list'),

    # UploadedFileのIDに紐づいたTranscriptionの一覧を取得するための新しいパス
    path('transcriptions/uploaded-file/<int:uploadedfile_id>/', TranscriptionViewSet.as_view({
        'get': 'list'
    }), name='transcriptions-by-uploadedfile'),
]