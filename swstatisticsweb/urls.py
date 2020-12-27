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
from django.views.generic.base import TemplateView, RedirectView

from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi


schema_view = get_schema_view(
    openapi.Info(
        title="SWStats Public API",
        default_version='v0.1',
        description="Summoners War Statistics Web Public API",
        contact=openapi.Contact(email="quatzo97@gmail.com"),
        license=openapi.License(name="Apache 2.0"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

router = routers.DefaultRouter()
router.register(r'upload', views.UploadViewSet, 'upload')
router.register(r'command', views.CommandViewSet, 'command')

# PUBLIC API
router.register(r'monsters', views.MonsterViewSet, 'monsters')
router.register(r'runes', views.RuneViewSet, 'runes')
router.register(r'artifacts', views.ArtifactViewSet, 'artifacts')

# upload theoritically CONST data only if DEBUG mode is enabled ( i.e. when in need to update whole Database )
if settings.DEBUG:
    router.register(r'monsterfamilyupload',
                    views.MonsterFamilyUploadViewSet, 'monsterfamilyupload')
    router.register(r'monstersourceupload',
                    views.MonsterSourceUploadViewSet, 'monstersourceupload')
    router.register(r'monsterbaseupload',
                    views.MonsterBaseUploadViewSet, 'monsterbaseupload')
    router.register(r'monsterhohupload',
                    views.MonsterHohUploadViewSet, 'monsterhohupload')
    router.register(r'monsterfusionupload',
                    views.MonsterFusionUploadViewSet, 'monsterfusionupload')
    router.register(r'buildingupload',
                    views.BuildingUploadViewSet, 'buildingupload')
    router.register(r'homunculusupload',
                    views.HomunculusUploadViewSet, 'homunculusupload')
    router.register(r'homunculusbuildupload',
                    views.HomunculusBuildUploadViewSet, 'homunculusbuildupload')

urlpatterns = [
    path('admin/', admin.site.urls),
    path("robots.txt", TemplateView.as_view(
        template_name="robots.txt", content_type="text/plain")),
    url(r'^$', RedirectView.as_view(url='https://web.swstats.info/'), name='home'),

    path('api/', include((router.urls, 'router'), namespace="api"), name="api"),

    url(r'^swagger(?P<format>\.json|\.yaml)$',
        schema_view.without_ui(cache_timeout=0), name='schema-json'),
    url(r'^swagger/$', schema_view.with_ui('swagger',
                                           cache_timeout=0), name='schema-swagger-ui'),
    url(r'^redoc/$', schema_view.with_ui('redoc',
                                         cache_timeout=0), name='schema-redoc'),

    # BOT
    path('bot/monsters/<int:monster_id>',
         views.bot_get_monster_report, name='bot_get_monster_report'),
    #########

    # WEB
    path('web/', include('swstats_web.urls')),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),

        # BOT DEBUG
        path('debug/bot/monsters/',
             views.bot_debug_get_all_monster_report, name='bot_debug_get_monster_report'),
        path('debug/bot/monsters/<int:monster_id>',
             views.bot_debug_get_monster_report, name='bot_debug_get_monster_report'),
    ] + urlpatterns
