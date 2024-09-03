from datetime import timedelta
from typing import List

from django.db import models
from django.utils import timezone
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils.crypto import get_random_string
import string
from functools import partial


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


class BB84Game(Game):
    photon_number = models.IntegerField(default=10, validators=[
        MaxValueValidator(30),
        MinValueValidator(10)
    ])
    eve = models.BooleanField(default=False)
    validation_bits_length = models.IntegerField(default=0)
    eve_percentage = models.FloatField(default=0.5)

    def save(self, *args, **kwargs):
        self.type = 'bb84'
        super().save(*args, **kwargs)


class Player(models.Model):
    game_id = models.ForeignKey(Game, to_field="id", on_delete=models.CASCADE)
    name = models.CharField(max_length=10)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['name', 'game_id'],
                                    name='unique_game_name'),
        ]


class BB84Player(Player):
    NONE = 'N'
    BOB = 'B'
    ALICE = 'A'
    SOLO = 'S'
    ROLE_CHOICES = [
        (NONE, 'None'),
        (BOB, 'Bob'),
        (ALICE, 'Alice'),
        (SOLO, 'Solo')
    ]
    role = models.CharField(default=NONE, choices=ROLE_CHOICES, max_length=1)


class BB84Room(models.Model):
    game_id = models.ForeignKey(Game,
                                to_field='id',
                                related_name='rooms',
                                on_delete=models.CASCADE)
    player1 = models.ForeignKey(BB84Player,
                                related_name='rooms_as_player1',
                                on_delete=models.CASCADE)
    player2 = models.ForeignKey(BB84Player,
                                related_name='rooms_as_player2',
                                on_delete=models.CASCADE)


class BB84Iteration(models.Model):
    CREATED = 'CREATED'
    FINISHED = 'FINISHED'
    STATUS_CHOICES = [
        (CREATED, 'Created'),
        (FINISHED, 'Finished')
    ]

    room = models.ForeignKey(BB84Room,
                             related_name='iterations',
                             on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    status = models.CharField(choices=STATUS_CHOICES,
                              default=CREATED,
                              max_length=10)
    eve_present = models.BooleanField(default=False)
    elapsed_time = models.DurationField(null=True, blank=True, default=timedelta)

    def save(self, *args, **kwargs):
        if self.status == self.FINISHED:
            self.elapsed_time = timezone.now() - self.created
        super().save(*args, **kwargs)
