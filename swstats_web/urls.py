from django.urls import path, include
from . import views

urlpatterns = [
    path('homepage/', views.Homepage.as_view(), name='Web Homepage'),
]