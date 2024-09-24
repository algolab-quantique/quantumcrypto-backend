from datetime import timedelta
from typing import List

from django.db import models
from django.utils import timezone
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils.crypto import get_random_string
import string
from functools import partial

from bb84.models import BB84Game
from e91.models import E91Game


def generate_code(game: str = None):
    """Utility function to generate a random code for a game"""
    if game is None:
        raise ValueError('No game provided')
    max_iter = 1000
    i = 0
    code = get_random_string(5, string.ascii_uppercase + string.digits)
    if game == 'bb84':
        while i < max_iter:
            try:
                BB84Game.objects.get(code=code)
                i += 1
            except BB84Game.DoesNotExist:
                return code
        raise RuntimeError('Could not generate a unique code')
    elif game == 'e91':
        while i < max_iter:
            try:
                E91Game.objects.get(code=code)
                i += 1
            except E91Game.DoesNotExist:
                return code
        raise RuntimeError('Could not generate a unique code')
    # Add logic for other game types


class Game(models.Model):
    ACTIVE: str = 'ACTIVE'
    ENDED: str = 'ENDED'
    STARTED: str = 'STARTED'
    STATUS_CHOICES: List[str] = [
        (ACTIVE, 'active'),
        (STARTED, 'started'),
        (ENDED, 'ended')
    ]
    created = models.DateTimeField(auto_now_add=True, blank=True)
    code = models.CharField(default=partial(generate_code, 'bb84'),
                            editable=False, max_length=5)
    num_players = models.IntegerField(default=0)
    player_limit = models.IntegerField(null=True)
    status = models.CharField(default=ACTIVE,
                              choices=STATUS_CHOICES,
                              max_length=7)
    type = models.CharField(max_length=100)

    class Meta:
        ordering = ['created']


class Player(models.Model):
    game_id = models.ForeignKey(Game, to_field="id", on_delete=models.CASCADE)
    name = models.CharField(max_length=10)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['name', 'game_id'],
                                    name='unique_game_name'),
        ]
