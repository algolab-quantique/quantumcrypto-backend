from django.urls import path, include
from rest_framework.routers import DefaultRouter
from bb84 import views

router = DefaultRouter()
router.register(r'', views.PlayerViewSet)
router.register(r'games/bb84', views.BB84GameViewSet, basename='bb84game')
router.register(r'players/bb84', views.BB84PlayerViewSet,
                basename='bb84player')
router.register(r'rooms/bb84', views.BB84RoomViewSet, basename='bb84room')

urlpatterns = [
    path('', include(router.urls))
]
