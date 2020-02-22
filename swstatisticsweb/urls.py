"""swstatisticsweb URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from django.conf.urls import url
from website import views
from rest_framework import routers, serializers, viewsets

router = routers.DefaultRouter()
router.register(r'upload', views.UploadViewSet, 'upload')

if settings.DEBUG: # upload theoritically CONST data only if DEBUG mode is enabled ( i.e. when in need to update whole Database )
    router.register(r'monsterfamilyupload', views.MonsterFamilyUploadViewSet, 'monsterfamilyupload')
    router.register(r'monstersourceupload', views.MonsterSourceUploadViewSet, 'monstersourceupload')
    router.register(r'monsterbaseupload', views.MonsterBaseUploadViewSet, 'monsterbaseupload')
    router.register(r'monsterhohupload', views.MonsterHohUploadViewSet, 'monsterhohupload')
    router.register(r'monsterfusionupload', views.MonsterFusionUploadViewSet, 'monsterfusionupload')
    router.register(r'buildingupload', views.BuildingUploadViewSet, 'buildingupload')
    router.register(r'homunculusupload', views.HomunculusUploadViewSet, 'homunculusupload')
    router.register(r'itemupload', views.ItemUploadViewSet, 'itemupload')

urlpatterns = [
    path('admin/', admin.site.urls),
    url(r'^$', views.get_homepage, name='home'),

    path('runes/', views.get_runes, name='runes'),
    path('runes/id/<int:arg_id>/', views.get_rune_by_id, name='rune_by_id'),

    path('monsters/', views.get_monsters, name='monsters'),
    path('monsters/id/<int:arg_id>/', views.get_monster_by_id, name='monster_by_id'),

    path('decks/', views.get_decks, name='decks'),
    path('decks/id/<int:arg_id>/', views.get_deck_by_id, name='deck_by_id'),
    
    path('dungeons/', views.get_dungeons, name='dungeons'),
    path('dungeons/<str:name>/<str:stage>/', views.get_dungeon_by_stage, name='dungeon_by_stage'),
    path('dungeons/<str:name>/', views.get_rift_dungeon_by_stage, name='rift_dungeon_by_stage'),

    path('contribute/', views.get_contribute_info, name='contribute'),
    path('credits/', views.get_credits, name='credits'),

    path('api/', include((router.urls, 'router'), namespace="api"), name="api"),
]
