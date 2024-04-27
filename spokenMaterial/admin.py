from django.contrib import admin
from .models import UploadedFile, Transcription

# Register your models here.
admin.site.register(UploadedFile)
admin.site.register(Transcription)