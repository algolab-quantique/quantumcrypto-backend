from django.urls import path, include
from rest_framework.routers import DefaultRouter
from e91 import views
from shared.views import PlayerViewSet, record_game_statistic, record_player_ip

router = DefaultRouter()
router.register(r'', PlayerViewSet)


urlpatterns = [
    path('record_game_statistic/', record_game_statistic, name='record_game_statistic'),
    path('record_player_ip/', record_player_ip, name='record_player_ip'),
    path('', include(router.urls))
]