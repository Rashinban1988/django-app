from django.shortcuts import HttpResponse
from django.core.cache import cache
import logging

def index(request):
    cache.set('test', 'value', timeout=30)  # Redis にデータを書き込むテスト
    print(cache.get('test'))  # 書き込んだデータを読み出すテスト\
    logger = logging.getLogger(__name__)
    logger.debug("ファイルアップロードがリクエストされました。")
    logger.debug(cache.get('test'))  # 書き込んだデータを読み出すテスト
    return HttpResponse('Hello world!')
