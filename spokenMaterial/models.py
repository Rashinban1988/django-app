# models.py
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
import os

class UploadedFile(models.Model):
    file = models.FileField(upload_to='uploads/')
    # その他の必要なフィールド
    def __str__(self):
        return self.file.name

# UploadedFileインスタンスが保存される前に実行されるシグナルを作成
@receiver(pre_save, sender=UploadedFile)
def delete_old_file(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_file = UploadedFile.objects.get(pk=instance.pk).file
        except UploadedFile.DoesNotExist:
            return
        else:
            new_file = instance.file
            if not old_file == new_file:
                if os.path.isfile(old_file.path):
                    os.remove(old_file.path)

class Transcription(models.Model):
    uploaded_file = models.ForeignKey(UploadedFile, on_delete=models.CASCADE)
    start_time = models.IntegerField()  # 開始時間（秒）
    text = models.TextField()  # 文字起こしテキスト
    # その他の必要なフィールド
    def __str__(self):
        return self.text