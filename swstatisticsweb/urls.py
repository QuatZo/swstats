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

urlpatterns = [
    path('admin/', admin.site.urls),
    # path('runes/', views.RuneView), # - not working for all runes
    url(r'^$', views.get_homepage),
    path('runes/<int:rune_id>/', views.specific_rune),
    path('api/', include((router.urls, 'router'), namespace="api"), name="api"),
]
