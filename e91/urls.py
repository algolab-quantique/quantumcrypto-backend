from django.urls import path, include
from rest_framework.routers import DefaultRouter
from e91 import views
from cryptoweb import views as v

router = DefaultRouter()
#router.register(r'', v.PlayerViewSet)
router.register(r'games/e91', views.E91GameViewSet, basename='e91game')
router.register(r'players/e91', views.E91PlayerViewSet,
                basename='e91player')
router.register(r'rooms/e91', views.E91RoomViewSet, basename='e91room')

urlpatterns = [
    path('', include(router.urls))
]
