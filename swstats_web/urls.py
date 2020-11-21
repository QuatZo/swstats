from django.urls import path, include
from . import views

urlpatterns = [
    path('homepage/', views.Homepage.as_view(), name='web_homepage'),

    path('scoring/', views.Scoring.as_view(), name='web_scoring_system'),
    path('upload/', views.Upload.as_view(), name='web_upload'),
    
    path('status/<str:task_id>/', views.Status.as_view(), name='web_status'),
]
