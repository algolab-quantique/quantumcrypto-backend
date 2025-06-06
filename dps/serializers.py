from rest_framework import serializers
from dps.models import DPSGame, DPSPlayer, DPSRoom, DPSIteration


class DPSGameSerializer(serializers.ModelSerializer):
    class Meta:
        model = DPSGame
        fields = ['id', 'created', 'num_players', 'player_limit', 'status',
                  'code', 'photon_number', 'eve', 'validation_bits_length',
                  'eve_percentage']


class DPSPlayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = DPSPlayer
        fields = ['id', 'name', 'game_id', 'role']


class DPSIterationSerializer(serializers.ModelSerializer):
    class Meta:
        model = DPSIteration
        fields = '__all__'


class DPSRoomSerializer(serializers.ModelSerializer):
    iterations = DPSIterationSerializer(many=True, read_only=True)

    class Meta:
        model = DPSRoom
        fields = '__all__'
