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
router.register(r'desktopupload', views.DesktopUploadViewSet, 'desktopupload')
router.register(r'reportgenerator',
                views.ReportGeneratorViewSet, 'reportgenerator')

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
    url(r'^$', views.get_homepage, name='home'),
    path('homepage/<str:task_id>/', views.get_homepage_ajax, name='homepage_ajax'),

    path('upload/', views.handle_www_profile, name='upload'),
    path('upload/profile/', views.handle_www_profile_upload, name='upload_profile'),
    path('upload/profile/<str:task_id>/',
         views.handle_www_profile_upload_ajax, name='upload_profile_ajax'),

    path('runes/', views.get_runes, name='runes'),
    path('runes/<str:task_id>/', views.get_runes_ajax, name='runes_ajax'),
    path('runes/id/<int:arg_id>/', views.get_rune_by_id, name='rune_by_id'),
    path('runes/id/<int:arg_id>/<str:task_id>/',
         views.get_rune_by_id_ajax, name='rune_by_id_ajax'),

    path('artifacts/', views.get_artifacts, name='artifacts'),
    path('artifacts/<str:task_id>/',
         views.get_artifacts_ajax, name='artifacts_ajax'),
    path('artifacts/id/<int:arg_id>/',
         views.get_artifact_by_id, name='artifact_by_id'),
    path('artifacts/id/<int:arg_id>/<str:task_id>/',
         views.get_artifact_by_id_ajax, name='artifact_by_id_ajax'),

    path('monsters/', views.get_monsters, name='monsters'),
    path('monsters/<str:task_id>/', views.get_monsters_ajax, name='monsters_ajax'),
    path('monsters/id/<int:arg_id>/',
         views.get_monster_by_id, name='monster_by_id'),
    path('monsters/id/<int:arg_id>/<str:task_id>',
         views.get_monster_by_id_ajax, name='monster_by_id_ajax'),

    path('dungeons/', views.get_dungeons, name='dungeons'),
    path('dungeons/<str:name>/', views.get_rift_dungeon_by_stage,
         name='rift_dungeon_by_stage'),
    path('dungeons/<str:name>/<int:stage>/',
         views.get_dungeon_by_stage, name='dungeon_by_stage'),
    path('dungeons/<str:name>/<str:task_id>/',
         views.get_rift_dungeon_by_stage_ajax, name='rift_dungeon_by_stage_ajax'),
    path('dungeons/<str:name>/<int:stage>/<str:task_id>/',
         views.get_dungeon_by_stage_ajax, name='dungeon_by_stage_ajax'),

    path('dimhole/', views.get_dimension_hole, name='dimhole'),
    path('dimhole/<str:task_id>/',
         views.get_dimension_hole_ajax, name='dimhole_ajax'),

    path('siege/', views.get_siege_records, name='siege'),
    path('siege/<str:task_id>/', views.get_siege_records_ajax, name='siege_ajax'),

    path('contribute/', views.get_contribute_info, name='contribute'),
    path('credits/', views.get_credits, name='credits'),

    path('desktop/', views.get_desktop, name='desktop'),
    path('building/', views.get_buildings_calculator, name='building'),
    path('dimholecalc/', views.get_dimhole_calculator, name='dimholecalc'),

    path('api/', include((router.urls, 'router'), namespace="api"), name="api"),
    path('object/<str:obj_type>/<int:obj_id>',
         views.get_object_for_card, name='object_card'),

    path('reports/', views.get_report_menu, name='reports'),
    path('reports/generate/', views.get_report, name='reports_generate'),
    path('oldreports/', RedirectView.as_view(url='/reports/old'),
         name='old_reports'),  # old link, before Generate Report Update
    path('reports/old/', views.get_old_reports, name='reports_old'),

    url(r'^swagger(?P<format>\.json|\.yaml)$',
        schema_view.without_ui(cache_timeout=0), name='schema-json'),
    url(r'^swagger/$', schema_view.with_ui('swagger',
                                           cache_timeout=0), name='schema-swagger-ui'),
    url(r'^redoc/$', schema_view.with_ui('redoc',
                                         cache_timeout=0), name='schema-redoc'),

    # NOT IN SIDEBAR MENU, NO DARK MODE, OLD THEME
    # path('homunculus/', views.get_homunculus, name='homunculus'),
    # path('homunculus/<int:base>/', views.get_homunculus_base, name='homunculus_by_base'),
    # path('homunculus/<int:base>/<str:task_id>/', views.get_homunculus_base_ajax, name='homunculus_by_base_ajax'),
    # path('decks/', views.get_decks, name='decks'),
    # path('decks/<str:task_id>/', views.get_decks_ajax, name='decks_ajax'),
    # path('decks/id/<int:arg_id>/', views.get_deck_by_id, name='deck_by_id'),
    # path('decks/id/<int:arg_id>/<str:task_id>/', views.get_deck_by_id_ajax, name='deck_by_id_ajax'),
    #########

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
