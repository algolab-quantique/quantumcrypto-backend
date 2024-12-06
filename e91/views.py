from rest_framework import viewsets
from e91.models import E91Game, E91Player, E91Room, Player, Game
from e91.serializers import (E91GameSerializer,
                             E91PlayerSerializer,
                             E91RoomSerializer)


class E91GameViewSet(viewsets.ModelViewSet):
    queryset = E91Game.objects.all()
    serializer_class = E91GameSerializer


class E91PlayerViewSet(viewsets.ModelViewSet):
    queryset = E91Player.objects.all()
    serializer_class = E91PlayerSerializer


class E91RoomViewSet(viewsets.ModelViewSet):
    queryset = E91Room.objects.all()
    serializer_class = E91RoomSerializer
