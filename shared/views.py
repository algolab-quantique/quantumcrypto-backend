from rest_framework import viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from shared.serializers import PlayerSerializer
from .models import Player, Game, GameStatistic


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


@api_view(['POST'])
def record_game_statistic(request):
    data = request.data
    protocol_type = data.get('protocol_type')
    ip_address = request.META.get('REMOTE_ADDR')
    players_count = data.get('players_count', 1)

    GameStatistic.objects.create(
        protocol_type=protocol_type,
        ip_address=ip_address,
        players_count=players_count
    )
    return Response({"status": "success"})

