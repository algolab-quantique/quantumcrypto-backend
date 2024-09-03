import random

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.exceptions import ValidationError

from .models import BB84Game, BB84Player


class Controller:

    @staticmethod
    def on_play_game(game_id):
        game = BB84Game.objects.get(game_id=game_id)
        players = list(BB84Player.objects.filter(game__game_id=game.game_id).values())

        random.shuffle(players)
        message = {}
        try:
            for i in range(0, len(players), 2):
                message[players[i]['pseudo']] = {'room': f'room_{i//2}',
                                                 'role': 'A'}
                message[players[i + 1]['pseudo']] = {'room': f'room_{i//2}',
                                                     'role': 'B'}
        except IndexError:
            message[players[i]['pseudo']] = {'error': 'odd_number_players'}

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(f'game_{game.game_id}',
                                                {
                                                    'type': 'send_message',
                                                    'message': message,
                                                    'event': 'PLAYBALL'
                                                })

    @staticmethod
    def on_end_game(game_id):
        game = BB84Game.objects.get(game_id=game_id)
        players = list(BB84Player.objects.filter(game__game_id=game.game_id).values())

        channel_layer = get_channel_layer()
        for i in range(len(players)//2):
            async_to_sync(channel_layer.group_send)(f'game_{game.game_id}_{i}',
                                                    {
                                                        'type': 'send_message',
                                                        'message': {},
                                                        'event': 'END'
                                                    })

    @staticmethod
    def on_index(pseudo, email, game):
        if not game.is_starting:
            p = BB84Player(pseudo=pseudo, email=email, game=game)
            p.save()
        else:
            # Should be enforced by django's validation module but will do for now.
            raise ValidationError('')

