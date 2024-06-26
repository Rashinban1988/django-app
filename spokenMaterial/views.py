import json
import logging
from openai import OpenAI
import os
import time
import warnings
import wave

import numpy as np
from celery import shared_task
from django.db import transaction
from django.http import JsonResponse
from django.views import View
from dotenv import load_dotenv
from pydub import AudioSegment
from rest_framework import status, viewsets
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from urllib.parse import unquote
from vosk import KaldiRecognizer, Model

from .management.commands.transcribe import Command as TranscribeCommand
from .models import Transcription, UploadedFile
from .serializers import TranscriptionSerializer, UploadedFileSerializer

# 環境変数をロードする
load_dotenv()
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

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
        # ノイズリダクションのパラメータを調整
        reduced_noise_audio = nr.reduce_noise(y=audio.get_array_of_samples(), sr=audio.frame_rate, n_std_thresh=2, prop_decrease=0.95)
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

    # 音声ファイルの読み込みと調整
    try:
        file_path = os.path.join('/code', file_path)
        file_extension = os.path.splitext(file_path)[1].lower()
        if file_extension in [".wav", ".mp3", ".m4a", ".mp4"]:
            # 音声の正規化と増幅（音声のボリュームを均一化）
            audio = AudioSegment.from_file(file_path, format=file_extension.replace(".", ""), frame_rate=16000, sample_width=2)
            audio = audio.normalize()  # 音声の正規化
        else:
            raise ValueError("サポートされていない音声形式です。")
    except Exception as e:
        logger.error(f"ファイルの読み込みに失敗しました: {e}")
        return

    # 音声ファイルを指定秒数ごとに分割して文字起こし
    try:
        split_interval = 15 * 1000  # ミリ秒単位
        all_transcription_text = ""
        for i, start_time in enumerate(range(0, len(audio), split_interval)):
            end_time = min(start_time + split_interval, len(audio))
            split_audio = audio[start_time:end_time]
            temp_file_path = f"temp_{i}.wav"
            try:
                split_audio.export(temp_file_path, format="wav")

                # ----------------------------------voskの音声分析 はじめ----------------------------------
                # with wave.open(temp_file_path, 'rb') as wf:

                    # 分析処理
                    # rec = KaldiRecognizer(model, wf.getframerate())
                    # while True:
                    #     data = wf.readframes(1000)
                    #     if len(data) == 0:
                    #         break
                    #     if rec.AcceptWaveform(data):
                    #         pass
                    # result = json.loads(rec.FinalResult())
                    # transcription_text = result['text'] if 'text' in result else ''
                # ----------------------------------voskの音声分析 おわり----------------------------------

                # ----------------------------------open ai whisper1 音声分析 はじめ-----------------------
                transcription = client.audio.transcriptions.create(
                    model = "whisper-1",
                    file = open(temp_file_path, "rb"),
                )
                transcription_text = transcription.text
                all_transcription_text += transcription_text
                # API呼び出し後に待機時間を追加
                time.sleep(0.7)  # 1分間に100回の制限を考慮して0.7秒待機（85回）
                # ----------------------------------open ai whisper1 音声分析 おわり-----------------------

                # 分析処理終了
                serializer_class = TranscriptionSerializer(data={
                    "start_time": start_time / 1000,
                    "text": transcription_text,
                    "uploaded_file": uploaded_file_id,
                })
                if serializer_class.is_valid():
                    serializer_class.save()
                else:
                    logger.error(f"文字起こし結果の保存に失敗しました: {serializer_class.errors}")
            finally:
                os.remove(temp_file_path)
        summary_result = summarize_and_save(uploaded_file_id, all_transcription_text)
        if not summary_result:
            logger.error("文字起こし結果の要約に失敗しました。")
    except Exception as e:
        logger.error(f"文字起こし処理中にエラーが発生しました: {e}")

def summarize_and_save(uploaded_file_id, all_transcription_text):
    """
    文字起こし結果を要約して保存する。

    Args:
        uploaded_file_id (int): UploadedFileのID

    Returns:
        bool: 成功した場合はTrue、UploadedFileが見つからない場合はFalse
    """
    try:
        uploaded_file = UploadedFile.objects.get(pk=uploaded_file_id)
        summary_text = summarize_text(all_transcription_text)  # この関数は要約アルゴリズムを実装する必要があります。

        with transaction.atomic():
            uploaded_file.summarization = summary_text
            uploaded_file.save()

        return True
    except UploadedFile.DoesNotExist:
        return False

def summarize_text(text):
    """
    テキストを要約する。

    Args:
        text (str): 要約するテキスト

    Returns:
        str: 要約されたテキスト
    """
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "次の文章を要約してください: " + text},
        ]
    )
    return response.choices[0].message.content