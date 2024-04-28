# views.py
from rest_framework import viewsets
from .models import Transcription
from .serializers import TranscriptionSerializer

class TranscriptionViewSet(viewsets.ModelViewSet):
    queryset = Transcription.objects.all()
    serializer_class = TranscriptionSerializer

    def get_queryset(self):
        """
        uploadedfileのIDに基づいてtranscriptionのクエリセットをフィルタリングする。
        """
        queryset = super().get_queryset()
        # URLからuploadedfileのIDを取得するためのキーを修正する
        uploadedfile_id = self.kwargs.get('uploadedfile_id')  # 修正が必要
        if uploadedfile_id is not None:
            queryset = queryset.filter(uploaded_file__id=uploadedfile_id)
        return queryset
