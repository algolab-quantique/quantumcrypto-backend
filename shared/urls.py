from django.urls import path, include
from rest_framework.routers import DefaultRouter
from e91 import views
from shared.views import PlayerViewSet, record_game_statistic, record_player_ip, get_protocol_stats

router = DefaultRouter()
router.register(r'', PlayerViewSet)


urlpatterns = [
    path('record_game_statistic/', record_game_statistic, name='record_game_statistic'),
    path('record_player_ip/', record_player_ip, name='record_player_ip'),
    path('get_protocol_stats/', get_protocol_stats, name='get_protocol_stats'),
    path('', include(router.urls))
]