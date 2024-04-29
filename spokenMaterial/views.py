# views.py
from rest_framework import viewsets, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from .models import UploadedFile, Transcription
from .serializers import UploadedFileSerializer, TranscriptionSerializer
from pydub import AudioSegment
from celery import shared_task
import warnings, os, logging, wave, numpy as np, json
from vosk import Model, KaldiRecognizer

class UploadedFileViewSet(viewsets.ModelViewSet):
    queryset = UploadedFile.objects.all()
    serializer_class = UploadedFileSerializer
    parser_classes = (MultiPartParser, FormParser,)  # ファイルアップロードを許可するパーサーを追加

    def create(self, request, *args, **kwargs):
        # ロガーを取得
        logger = logging.getLogger(__name__)
        logger.debug("ファイルアップロードがリクエストされました。")
        file_serializer = UploadedFileSerializer(data=request.data)
        if file_serializer.is_valid():
            uploaded_file = file_serializer.save() # UploadedFileモデルにファイル情報を保存
            # 一時ファイルとして保存
            file_obj = request.FILES['file']
            # 'temp' ディレクトリとアップロードされたファイルの名前を結合してパスを作成
            temp_file_path = os.path.join('uploads', file_obj.name)
            with open(temp_file_path, 'wb+') as destination:
                for chunk in file_obj.chunks():
                    destination.write(chunk)

            logger.debug(f"一時ファイルを保存しました: {uploaded_file.file.name}")

            # 文字起こし処理を非同期で実行
            transcribe_and_save_async.delay(temp_file_path, uploaded_file.id)

            return Response(file_serializer.data, status=status.HTTP_202_ACCEPTED)
        else:
            return Response(file_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

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

# FP16に関するワーニングを無視
warnings.filterwarnings("ignore", message="FP16 is not supported on CPU; using FP32 instead")

def file_upload_view(request):
    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            # ファイルの処理
            handle_uploaded_file(request.FILES['file'])
            return render(request, 'transcription/success.html')  # 成功時のテンプレート
    else:
        form = FileUploadForm()
    return render(request, 'transcription/upload.html', {'form': form})

def handle_uploaded_file(f):
    # 一時ファイルとして保存
    with open('temp_file', 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)

@shared_task
def transcribe_and_save_async(file_path, uploaded_file_id):
    logger = logging.getLogger(__name__)
    model_path = 'models/vosk-model-small-ja-0.22'
    model = Model(model_path)

    logger.debug("文字起こし処理がリクエストされました。")
    logger.debug(f"ファイルパス: {file_path}")

    file_path = os.path.join('/code', file_path)
    file_extension = os.path.splitext(file_path)[1].lower()
    if file_extension in [".wav", ".mp3", ".m4a", ".mp4"]:
        audio = AudioSegment.from_file(file_path, format=file_extension.replace(".", ""))
    else:
        raise ValueError("サポートされていない音声形式です。")

    split_interval = 15 * 1000  # ミリ秒単位

    for i, start_time in enumerate(range(0, len(audio), split_interval)):
        end_time = min(start_time + split_interval, len(audio))
        split_audio = audio[start_time:end_time]
        temp_file_path = f"temp_{i}.wav"
        split_audio.export(temp_file_path, format="wav")

        with wave.open(temp_file_path, 'rb') as wf:
            rec = KaldiRecognizer(model, wf.getframerate())
            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                if rec.AcceptWaveform(data):
                    pass

            result = json.loads(rec.FinalResult())
            transcription_text = result['text'] if 'text' in result else ''

        serializer_class = TranscriptionSerializer(data={
            "start_time": start_time / 1000,  # 秒単位に変換
            "text": transcription_text,
            "uploaded_file": uploaded_file_id,
        })
        if serializer_class.is_valid():
            serializer_class.save()
        else:
            logger.error(f"文字起こし結果の保存に失敗しました: {serializer_class.errors}")

        os.remove(temp_file_path)