from django.urls import path, include
from rest_framework.routers import DefaultRouter
from e91 import views
from shared.views import PlayerViewSet, record_game_statistic

router = DefaultRouter()
router.register(r'', PlayerViewSet)


urlpatterns = [
    path('record_game_statistic/', record_game_statistic, name='record_game_statistic'),
    path('', include(router.urls))
]