import json
import logging
import os
import warnings
import wave

import numpy as np
from celery import shared_task
from django.http import JsonResponse
from django.views import View
from pydub import AudioSegment
from rest_framework import status, viewsets
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from urllib.parse import unquote
from vosk import KaldiRecognizer, Model

from .management.commands.transcribe import Command as TranscribeCommand
from .models import Transcription, UploadedFile
from .serializers import TranscriptionSerializer, UploadedFileSerializer

class UploadedFileViewSet(viewsets.ModelViewSet):
    queryset = UploadedFile.objects.all()
    serializer_class = UploadedFileSerializer
    parser_classes = (MultiPartParser, FormParser,)  # ファイルアップロードを許可するパーサーを追加

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        # レスポンスデータ内のファイル名をデコード
        for item in response.data:
            if 'file' in item and isinstance(item['file'], str):
                item['file'] = unquote(item['file'])
        response['Content-Type'] = 'application/json; charset=utf-8'
        return response

    def create(self, request, *args, **kwargs):
        # ロガーを取得
        logger = logging.getLogger(__name__)
        logger.debug("ファイルアップロードがリクエストされました。")

        # リクエストデータのファイル名をデコード
        if 'file' in request.data:
            request.data['file'] = unquote(request.data['file'])

        file_serializer = UploadedFileSerializer(data=request.data)
        if file_serializer.is_valid():
            uploaded_file = file_serializer.save() # UploadedFileモデルにファイル情報を保存

            # 文字起こし処理を非同期で実行 Celeryを使う場合
            # transcribe_and_save_async.delay(temp_file_path, uploaded_file.id)

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

class TranscribeView(View):
    def get(self, request, *args, **kwargs):
        command = TranscribeCommand()
        command.handle()
        return JsonResponse({'status': 'transcription started'})

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

# @shared_task # Celeryを使う場合コメントアウトを外す
# def transcribe_and_save_async(file_path, uploaded_file_id):
def transcribe_and_save(file_path, uploaded_file_id):
    logger = logging.getLogger(__name__)

    try:
        import noisereduce as nr
        logger.debug("noisereduce imported successfully.")
    except Exception as e:
        logger.error(f"Failed to import noisereduce: {e}")

    logger.debug("文字起こし処理がリクエストされました。")
    logger.debug(f"ファイルパス: {file_path}")

    # モデルのロード
    try:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        model_path = os.path.join(base_path, 'models/vosk-model-ja-0.22')
        model = Model(model_path)
    except Exception as e:
        logger.error(f"モデルのロードに失敗しました: {e}")
        return

    # 音声ファイルの読み込み
    try:
        file_path = os.path.join('/code', file_path)
        file_extension = os.path.splitext(file_path)[1].lower()
        if file_extension in [".wav", ".mp3", ".m4a", ".mp4"]:
            # 音声の正規化と増幅（音声のボリュームを均一化）
            audio = AudioSegment.from_file(file_path, format=file_extension.replace(".", ""))
            audio = audio.normalize()  # ここで normalize メソッドを使用
            audio = audio + 20
            # # ノイズリダクション（音声のノイズを減らす）
            # audio_np = np.array(audio.get_array_of_samples())
            # reduced_noise_audio_np = nr.reduce_noise(y=audio_np, sr=audio.frame_rate)
            # # 音声の感度を調整
            # audio = AudioSegment(
            #     reduced_noise_audio_np.tobytes(), # バイト列に変換
            #     frame_rate=audio.frame_rate,      # サンプリング周波数
            #     sample_width=audio.sample_width,  # サンプル幅
            #     channels=audio.channels           # チャンネル数
            # )
        else:
            raise ValueError("サポートされていない音声形式です。")
    except Exception as e:
        logger.error(f"ファイルの読み込みに失敗しました: {e}")
        return

    try:
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
    except Exception as e:
        logger.error(f"文字起こし処理中にエラーが発生しました: {e}")