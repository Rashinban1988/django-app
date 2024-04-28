# ベースイメージとしてPythonの公式イメージを使用
FROM python:3.9

# 環境変数を設定
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 作業ディレクトリを設定
WORKDIR /code

# 依存関係のインストール
COPY requirements.txt /code/
RUN pip install --upgrade pip && pip install -r requirements.txt

# プロジェクトのファイルをコンテナにコピー
COPY . /code/

# アプリケーションを起動するコマンド
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]