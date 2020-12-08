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

    path('siege/', views.SiegeView.as_view(), name='web_siege'),
    path('siege/table/', views.SiegeTableView.as_view(),
         name='web_siege_table'),

    path('cairos/', views.CairosView.as_view(), name='web_cairos'),
    path('cairos-detail/', views.CairosDetailView.as_view(),
         name='web_cairos-detail'),

    path('rifts/', views.RiftView.as_view(), name='web_rifts'),
    path('rifts-detail/', views.RiftDetailView.as_view(),
         name='web_rifts-detail'),

    path('dimhole/', views.DimholeView.as_view(), name='web_dimhole'),
    path('dimhole-detail/', views.DimholeDetailView.as_view(),
         name='web_dimhole-detail'),

    path('artifacts/', views.ArtifactsView.as_view(), name='web_artifacts'),
    path('artifacts/table/', views.ArtifactsTableView.as_view(),
         name='web_artifacts_table'),

    path('monster/<int:mon_id>/', views.MonsterView.as_view(), name='web_monster'),

    path('status/<str:task_id>/', views.StatusView.as_view(), name='web_status'),
]
