from functools import partial
from typing import List

from django.db import models

from django.utils.crypto import get_random_string
import string


def generate_code():
    """Utility function to generate a random code for a game"""
    max_iter = 1000
    i = 0
    code = get_random_string(5, string.ascii_uppercase + string.digits)
    while i < max_iter:
        try:
            Game.objects.get(code=code)
            i += 1
        except Game.DoesNotExist:
            return code
    raise RuntimeError('Could not generate a unique code')
    # Add logic for other game types


class Game(models.Model):
    code = models.CharField(default=partial(generate_code),
                            editable=False, max_length=5)
    ACTIVE: str = 'ACTIVE'
    ENDED: str = 'ENDED'
    STARTED: str = 'STARTED'
    STATUS_CHOICES: List[str] = [
        (ACTIVE, 'active'),
        (STARTED, 'started'),
        (ENDED, 'ended')
    ]
    created = models.DateTimeField(auto_now_add=True, blank=True)
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
from django.db import models

# Create your models here.
