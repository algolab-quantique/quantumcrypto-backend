from rest_framework import serializers
from e91.models import E91Game, E91Player, E91Room, E91Iteration


class E91GameSerializer(serializers.ModelSerializer):
    class Meta:
        model = E91Game
        fields = ['id', 'created', 'num_players', 'player_limit', 'status',
                  'code', 'photon_number', 'eve', 'validation_bits_length',
                  'eve_percentage']


class E91PlayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = E91Player
        fields = ['id', 'name', 'game_id', 'role']


class E91IterationSerializer(serializers.ModelSerializer):
    class Meta:
        model = E91Iteration
        fields = '__all__'


class E91RoomSerializer(serializers.ModelSerializer):
    iterations = E91IterationSerializer(many=True, read_only=True)

    class Meta:
        model = E91Room
        fields = '__all__'
