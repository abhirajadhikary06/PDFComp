from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_page, name='login'),
    path('compressor/', views.compressor, name='compressor'),
    path('download/<str:filename>/', views.download_file, name='download'),
]