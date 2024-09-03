import json
import logging
from typing import Union
from django.db import IntegrityError, models
from django.forms.models import model_to_dict
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from bb84.models import BB84Game, BB84Player, Game, BB84Room, BB84Iteration
import random

logger = logging.getLogger(__name__)


class WaitingRoomConsumer(AsyncJsonWebsocketConsumer):

    async def connect(self):
        game_code = self.scope['url_route']['kwargs']['game_code']
        params = self.scope['query_string'].decode('utf-8').split('?')
        player_name = params[0].split('=')[1]
        is_admin = params[1].split('=')[1]

        self.game_group_name = f'game_{game_code}'
        await self.channel_layer.group_add(
            self.game_group_name,
            self.channel_name
        )

        await self.accept()

        # Get the game instance or close the connection if it doesn't exist
        try:
            game = await self.get_game(game_code)
        except BB84Game.DoesNotExist:
            await self.send_message({
                "message": "Invalid game code",
                "event": "INVALID_CODE"
            })
            await self.close()
            return

        if game.status == 'STARTED':
            await self.send_message({
                "message": "Game has already started",
                "event": "GAME_STARTED"
            })
            await self.close()
            return

        if is_admin == '0':
            # Create a new player associated with the game
            try:
                player = await self.create_player(player_name, game)
                # Update the num_players property of the game
                game.num_players += 1
                await self.save_game(game)

                await self.save_player(player)
                return await self.acceptance_message({
                    "player": {
                        "id": player.id
                    },
                    "game": {
                        "photon_number": game.photon_number,
                        "validation_bits_length": game.validation_bits_length
                    }
                })
            except IntegrityError:
                await self.send_message({
                    "message": "Invalid player name",
                    "event": "TAKEN_NAME"
                })
                await self.close()
                return
        return await self.acceptance_message()

    async def disconnect(self, close_code):
        print(close_code)
        game_code = self.game_group_name[5:]
        game = await self.get_game(game_code)
        if game.num_players > 0:
            game.num_players -= 1
        await self.save_game(game)
        await self.channel_layer.group_send(self.game_group_name, {
            'type': 'send_message',
            'message': {'count': game.num_players},
            "event": "PLAYER_COUNT"
        })
        await self.channel_layer.group_discard(self.game_group_name,
                                               self.channel_name)

    async def receive(self, text_data):
        payload = json.loads(text_data)
        event = payload.get("event", None)
        message = payload.get("message", None)
        if event == 'JOIN':
            game_code = message['game_code']
            player_name = message['player_name']
            try:
                game = await self.get_game(game_code)
            except BB84Game.DoesNotExist:
                logger.error(f"Player {player_name} not found for game "
                             f"{game_code}.")
                await self.close()
                return
            await self.channel_layer.group_send(self.game_group_name, {
                'type': 'send_message',
                'message': {'count': game.num_players},
                "event": "PLAYER_COUNT"
            })
            await self.channel_layer.group_send(self.game_group_name, {
                'type': 'send_message',
                'message': {
                    "player": {
                        "name": player_name
                    },
                },
                'event': 'PLAYER_JOIN'
            })

        elif event == 'END_ADMIN':
            game_code = message['game_code']
            game = await self.get_game(game_code)
            await self.delete_game(game)
            await self.channel_layer.group_send(self.game_group_name, {
                'type': 'send_message',
                'message': message,
                'event': "END"
            })

        elif event == 'END_PLAYER':
            game_code = message['game_code']
            player_name = message['player_name']
            game = await self.get_game(game_code)
            game.num_players -= 1
            await self.save_game(game)
            player = await self.get_player(game, player_name)
            if player:
                await self.delete_player(player)
            await self.channel_layer.group_send(self.game_group_name, {
                'type': 'send_message',
                'message': {'count': game.num_players},
                'event': "PLAYER_COUNT"
            })

        elif event == 'START':
            game_code = message['game_code']
            try:
                game = await self.get_game(game_code)
            except BB84Game.DoesNotExist:
                raise ValueError("Invalid game code")
            players = await self.get_players(game)
            game.status = 'STARTED'
            await self.save_game(game)
            if players:
                random.shuffle(players)
                message = {}
                even = len(players) % 2 == 0
                limit = len(players) if even else len(
                    players) - 1
                message['game_has_eve'] = game.eve
                for i in range(0, limit, 2):
                    eve_present = False
                    if game.eve:
                        eve_percentage = game.eve_percentage
                        eve_present = random.choices([True, False], weights=[
                            round(eve_percentage, 1), round(1 -
                                                            eve_percentage, 1
                                                            )])[0]
                    player1 = players[i]
                    player2 = players[i + 1]
                    message[str(player1['id'])] = {
                        'room': f'room_{i // 2}',
                        'partner': player2['name'],
                        'role': 'A',
                        'eve_present': eve_present,
                    }
                    message[str(player2['id'])] = {
                        'room': f'room_{i // 2}',
                        'partner': player1['name'],
                        'role': 'B',
                        'eve_present': eve_present,
                    }
                    player1_instance = await self.get_player(game, player1[
                        'name'])
                    player2_instance = await self.get_player(game, player2[
                        'name'])
                    await self.create_room(game, player1_instance,
                                           player2_instance, eve_present)
                if not even:
                    message[str(players[limit]['id'])] = {
                        'role': 'S'
                    }
                await self.channel_layer.group_send(self.game_group_name,
                                                    {
                                                        'type': 'send_message',
                                                        'message': message,
                                                        'event': 'ROLES'
                                                    })

    @database_sync_to_async
    def get_game(self, game_code: str):
        return BB84Game.objects.get(code=game_code)

    @database_sync_to_async
    def delete_game(self, game: BB84Game):
        return game.delete()

    @database_sync_to_async
    def get_player(self, game: BB84Game, player_name: str):
        return BB84Player.objects.get(game_id=game, name=player_name)

    @database_sync_to_async
    def get_players(self, game: BB84Game):
        players = list(BB84Player.objects.filter(game_id=game).values())
        return players

    @database_sync_to_async
    def delete_player(self, player: BB84Player):
        return player.delete()

    @database_sync_to_async
    def create_player(self, player_name: str, game: BB84Game):
        try:
            player = BB84Player.objects.create(name=player_name, game_id=game)
        except Exception as e:
            print(f'Error creating player: {e}')
            raise
        return player

    @database_sync_to_async
    def create_room(self, game, player1: BB84Player, player2: BB84Player,
                    eve_present: bool):
        try:
            room = BB84Room.objects.create(game_id=game, player1=player1,
                                           player2=player2)
            iteration = BB84Iteration.objects.create(room=room,
                                                     eve_present=eve_present)
            room.save()
            iteration.save()
        except Exception as e:
            print(f'Error creating room: {e}')
            raise

    @database_sync_to_async
    def save_game(self, game: BB84Game):
        try:
            game.save()
        except Exception as e:
            print(f'Error saving game: {e}')
            raise

    @database_sync_to_async
    def save_player(self, player: BB84Player):
        try:
            player.save()
        except Exception as e:
            print(f'Error saving player: {e}')
            raise

    async def acceptance_message(self, message: Union[dict, int, str] =
    "Connected") -> None:
        await self.send_message({
            "message": message,
            "event": "CONNECTED"
        })

    async def send_message(self, res):
        await self.send(text_data=json.dumps({
            "payload": res,
        }))


class PlayingRoomConsumer(AsyncJsonWebsocketConsumer):

    async def connect(self):
        game_code = self.scope['url_route']['kwargs']['game_code']
        room_id = self.scope['url_route']['kwargs']['room_id']
        self.game_group_name = f'game_{game_code}_{room_id}'

        await self.channel_layer.group_add(
            self.game_group_name,  # group corresponding to the game_id
            self.channel_name  # channel to access all players for that group
        )

        await self.accept()
        return await self.acceptance_message()

    async def receive(self, text_data):
        response = json.loads(text_data)
        event = response.get("event", None)
        message = response.get("message", None)
        if event in ['A_PHOTONS', 'A_BASES', 'B_BASES', 'A_CIPHER',
                     'NEW_GAME', 'B_KEY', 'RESTART_WITHOUT_EVE',
                     'HANDSHAKE']:
            await self.channel_layer.group_send(self.game_group_name, {
                'type': 'send_message',
                'message': message,
                "event": event
            })

        elif event == 'B_SUCCESS':
            await self.update_iterations_status_to_finished(message[
                                                                'player_name'],
                                                            message[
                                                                'game_code'])
            await self.channel_layer.group_send(self.game_group_name, {
                'type': 'send_message',
                'message': message,
                "event": event
            })

        elif event == 'A_KEY':
            validation_indices = random.sample(range(
                message['key_length']),
                message['validation_bits_length'])
            await self.channel_layer.group_send(self.game_group_name, {
                'type': 'send_message',
                'message': {
                    'key': message['key'],
                    'validation_indices': validation_indices
                },
                "event": event
            })
        elif event in ['A_VALIDATED', 'B_VALIDATED']:
            await self.channel_layer.group_send(self.game_group_name, {
                'type': 'send_message',
                'message': {
                    'valid': message['valid']
                },
                'event': event
            })

    @database_sync_to_async
    def update_iterations_status_to_finished(self, player_name, game_code):

        # Get the game
        game = Game.objects.get(code=game_code)
        player = BB84Player.objects.get(name=player_name, game_id=game)

        # Get the room
        room = BB84Room.objects.get(models.Q(player1=player) | models.Q(
            player2=player),
                                    game_id=game, )

        # Get the created iterations for the room
        created_iterations = BB84Iteration.objects.filter(room=room,
                                                          status='CREATED')

        # Update status to 'FINISHED' and save
        for iteration in created_iterations:
            iteration.status = 'FINISHED'
            iteration.save()

    async def acceptance_message(self, message: Union[dict, int, str] =
    "Connected") -> None:
        await self.send_message({
            "message": message,
            "event": "CONNECTED"
        })

    async def send_message(self, res):
        await self.send(text_data=json.dumps({
            "payload": res,
        }))


class ResultsPageConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        game_code = self.scope['url_route']['kwargs']['game_code']
        self.game_group_name = f'game_results_{game_code}'

        await self.channel_layer.group_add(
            self.game_group_name,  # group corresponding to the game_id
            self.channel_name  # channel to access all players for that group
        )

        await self.accept()

        abstract_game = await self.get_game(game_code)
        game = await self.get_specific_game(game_code, abstract_game.type)
        if game:
            rooms = await self.get_rooms_with_iterations(game)
            message = json.dumps({
                'game_type': game.type,
                'rooms': rooms
            })
            print(message)
            return await self.channel_layer.group_send(self.game_group_name, {
                'type': 'send_message',
                'message': message,
                'event': 'GAME_RESULTS'
            })
        return await self.acceptance_message()

    async def acceptance_message(self, message: Union[dict, int, str] =
    "Connected") -> None:
        await self.send_message({
            "message": message,
            "event": "CONNECTED"
        })

    async def send_message(self, res):
        await self.send(text_data=json.dumps({
            "payload": res,
        }))

    @database_sync_to_async
    def get_game(self, game_code: str):
        return Game.objects.get(code=game_code)

    @database_sync_to_async
    def get_specific_game(self, game_code: str, game_type: str):
        if game_type == 'bb84':
            return BB84Game.objects.get(code=game_code)
        return None

    @database_sync_to_async
    def get_rooms_with_iterations(self, game):
        rooms_queryset = BB84Room.objects.filter(
            game_id=game).prefetch_related(
            'iterations')

        rooms_data = []
        for room in rooms_queryset:
            room_data = model_to_dict(room)
            # print(room_data)
            iterations_data = []
            for iteration in room.iterations.all():
                iteration_data = model_to_dict(iteration)
                elapsed_time_seconds = iteration_data.pop(
                    'elapsed_time').total_seconds()
                iteration_data['elapsed_time'] = elapsed_time_seconds
                iterations_data.append(iteration_data)
            room_data['iterations'] = iterations_data
            rooms_data.append(room_data)

        return rooms_data
