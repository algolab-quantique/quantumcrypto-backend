from django.urls import path, include
from rest_framework.routers import DefaultRouter
from dps import views

router = DefaultRouter()
router.register(r'games/dps', views.DPSGameViewSet, basename='dpsgame')
router.register(r'players/dps', views.DPSPlayerViewSet,
                basename='dpsplayer')
router.register(r'rooms/dps', views.DPSRoomViewSet, basename='dpsroom')

urlpatterns = [
    path('', include(router.urls))
]
