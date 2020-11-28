from django.urls import path, include
from . import views

urlpatterns = [
    path('homepage/', views.HomepageView.as_view(), name='web_homepage'),

    path('scoring/', views.ScoringView.as_view(), name='web_scoring_system'),
    path('upload/', views.UploadView.as_view(), name='web_upload'),

    path('runes/', views.RunesView.as_view(), name='web_runes'),
    path('runes/table/', views.RunesTableView.as_view(), name='web_runes_table'),

    path('monsters/', views.MonstersView.as_view(), name='web_monsters'),
    path('monsters/table/', views.MonstersTableView.as_view(),
         name='web_monsters_table'),

    path('monster/<int:mon_id>/', views.MonsterView.as_view(), name='web_monster'),

    path('status/<str:task_id>/', views.StatusView.as_view(), name='web_status'),
]
