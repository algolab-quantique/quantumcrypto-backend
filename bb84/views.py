from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from bb84.models import BB84Game, BB84Player, BB84Room, Player, Game
from bb84.serializers import (BB84GameSerializer,
                              BB84PlayerSerializer,
                              BB84RoomSerializer, PlayerSerializer)


class BB84GameViewSet(viewsets.ModelViewSet):
    queryset = BB84Game.objects.all()
    serializer_class = BB84GameSerializer


class PlayerViewSet(viewsets.ModelViewSet):
    queryset = Player.objects.all()
    serializer_class = PlayerSerializer

    @action(detail=False, methods=['get'])
    def players(self, request):
        game_code = request.query_params.get('game_code')
        game = Game.objects.get(code=game_code)
        players = Player.objects.filter(game_id=game.id)
        serializer = self.get_serializer(players, many=True)

        return Response(serializer.data)


class BB84PlayerViewSet(viewsets.ModelViewSet):
    queryset = BB84Player.objects.all()
    serializer_class = BB84PlayerSerializer


class BB84RoomViewSet(viewsets.ModelViewSet):
    queryset = BB84Room.objects.all()
    serializer_class = BB84RoomSerializer
