from rest_framework import viewsets
from bb84.models import BB84Game, BB84Player, BB84Room
from bb84.serializers import (BB84GameSerializer,
                              BB84PlayerSerializer,
                              BB84RoomSerializer)


class BB84GameViewSet(viewsets.ModelViewSet):
    queryset = BB84Game.objects.all()
    serializer_class = BB84GameSerializer


class BB84PlayerViewSet(viewsets.ModelViewSet):
    queryset = BB84Player.objects.all()
    serializer_class = BB84PlayerSerializer


class BB84RoomViewSet(viewsets.ModelViewSet):
    queryset = BB84Room.objects.all()
    serializer_class = BB84RoomSerializer
