from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('/',include('testapp.urls')),
    # path('api/spokenMaterial/', include('spokenMaterial.urls')),
]