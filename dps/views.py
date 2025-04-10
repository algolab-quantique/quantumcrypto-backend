from rest_framework import viewsets
from dps.models import DPSGame, DPSPlayer, DPSRoom
from dps.serializers import (DPSGameSerializer,
                              DPSPlayerSerializer,
                              DPSRoomSerializer)


class DPSGameViewSet(viewsets.ModelViewSet):
    queryset = DPSGame.objects.all()
    serializer_class = DPSGameSerializer


class DPSPlayerViewSet(viewsets.ModelViewSet):
    queryset = DPSPlayer.objects.all()
    serializer_class = DPSPlayerSerializer


class DPSRoomViewSet(viewsets.ModelViewSet):
    queryset = DPSRoom.objects.all()
    serializer_class = DPSRoomSerializer
