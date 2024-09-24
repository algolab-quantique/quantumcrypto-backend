from django.urls import path, include
from rest_framework.routers import DefaultRouter
from e91 import views
from shared.views import PlayerViewSet

router = DefaultRouter()
router.register(r'', PlayerViewSet)


urlpatterns = [
    path('', include(router.urls))
]