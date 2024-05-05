from django.core.management.base import BaseCommand
from spokenMaterial.models import UploadedFile

class Command(BaseCommand):
    help = '音声ファイルを文字起こしする'

    def handle(self, *args, **options):
        from spokenMaterial.views import transcribe_and_save
        # transcriptionを持っていないuploaded_fileを取得
        uploaded_files = UploadedFile.objects.filter(transcription__isnull=True, status=0)

        if not uploaded_files.exists():
            self.stdout.write(self.style.SUCCESS('文字起こしするファイルがありません。'))
            return

        # uploaded_filesをループして文字起こしを実行
        for uploaded_file in uploaded_files:
            try:
                uploaded_file.status = 1
                uploaded_file.save()
            except Exception as e:
                uploaded_file.status = 0
                uploaded_file.save()
                self.stdout.write(self.style.ERROR(f'文字起こしでエラーが発生しました: {e}'))
        for uploaded_file in uploaded_files:
            file_path = uploaded_file.file.path
            uploaded_file_id = uploaded_file.id
            try:
                transcribe_and_save(file_path, uploaded_file_id)
                uploaded_file.status = 2
                uploaded_file.save()
                self.stdout.write(self.style.SUCCESS('正常に文字起こしが完了しました。'))
            except Exception as e:
                uploaded_file.status = 0
                uploaded_file.save()
                self.stdout.write(self.style.ERROR(f'文字起こしでエラーが発生しました: {e}'))
        self.stdout.write(self.style.SUCCESS('文字起こし処理が完了しました。'))
