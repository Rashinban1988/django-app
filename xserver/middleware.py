from django.http import HttpResponseForbidden

class RestrictMediaAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # メディアファイルへのリクエストをチェック
        if request.path.startswith('/media/'):
            # 許可するドメイン
            allowed_referer = 'https://nextjs14-hvttlnd0g-rashinban1988s-projects.vercel.app'

            # Referer ヘッダーをチェック
            referer = request.META.get('HTTP_REFERER', '')
            if not referer.startswith(allowed_referer):
                return HttpResponseForbidden("このドメインからのアクセスは許可されていません。")

        response = self.get_response(request)
        return response