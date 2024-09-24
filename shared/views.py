from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from shared.serializers import PlayerSerializer
from .models import Player, Game


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
