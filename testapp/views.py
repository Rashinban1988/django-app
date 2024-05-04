from django.shortcuts import HttpResponse
from django.core.cache import cache
import logging

def index(request):
    cache.set('test', 'value', timeout=30)  # Redis にデータを書き込むテスト
    logger = logging.getLogger(__name__)
    logger.debug("キャッシュに 'test' をセットしました: 'value'")

    cached_value = cache.get('test')  # 書き込んだデータを読み出すテスト
    if cached_value:
        logger.debug(f"キャッシュから 'test' を取得しました: {cached_value}")
    else:
        logger.error("キャッシュから 'test' を取得できませんでした。")

    logger.debug("ファイルアップロードがリクエストされました。")
    return HttpResponse('Hello world!')