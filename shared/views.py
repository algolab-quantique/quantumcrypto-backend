from django.db.models import Count
from django.http import JsonResponse
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
    debug_headers(request)
    data = request.data
    protocol_type = data.get('protocol_type')
    ip_address = get_client_ip(request)
    players_count = data.get('players_count', 1)

    game_stat = GameStatistic.objects.create(
        protocol_type=protocol_type,
        ip_address=ip_address,
        players_count=players_count
    )
    return Response({"status": "success",
                     "game_id": game_stat.id})


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def debug_headers(request):
    for key, value in request.META.items():
        print(f"{key}: {value}")
    return Response({"status": "debug complete"})


@api_view(['POST'])
def record_player_ip(request):
    debug_headers(request)
    data = request.data
    game_id = data.get('game_id')
    ip_address = get_client_ip(request)

    try:
        game_stat = GameStatistic.objects.get(id=game_id)

        if ip_address not in game_stat.players_ip_addresses:
            game_stat.players_ip_addresses.append(ip_address)
            game_stat.save()

        return Response({
            "status": "success"
        })
    except GameStatistic.DoesNotExist:
        return Response({"status": "error", "message": "Game not found"}, status=404)


@api_view(['GET'])
def get_protocol_stats(request):
    stats = GameStatistic.objects.values('protocol_type').annotate(total_games=Count('protocol_type'))
    return JsonResponse({'protocols': list(stats)})


