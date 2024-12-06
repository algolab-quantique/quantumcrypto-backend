from rest_framework import serializers
from bb84.models import BB84Game, BB84Player, BB84Room, BB84Iteration


class BB84GameSerializer(serializers.ModelSerializer):
    class Meta:
        model = BB84Game
        fields = ['id', 'created', 'num_players', 'player_limit', 'status',
                  'code', 'photon_number', 'eve', 'validation_bits_length',
                  'eve_percentage']


class BB84PlayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = BB84Player
        fields = ['id', 'name', 'game_id', 'role']


class BB84IterationSerializer(serializers.ModelSerializer):
    class Meta:
        model = BB84Iteration
        fields = '__all__'


class BB84RoomSerializer(serializers.ModelSerializer):
    iterations = BB84IterationSerializer(many=True, read_only=True)

    class Meta:
        model = BB84Room
        fields = '__all__'
