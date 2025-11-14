import string
from datetime import timedelta
from functools import partial
from typing import List

from django.db import models
from django.utils import timezone
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils.crypto import get_random_string

from shared.models import Game, generate_code, Player


class DPSGame(Game):
    # TODO: TESTING ONLY - restore MinValueValidator(10) after testing
    photon_number = models.IntegerField(default=10, validators=[
        MaxValueValidator(30),
        MinValueValidator(4)  # Temporarily changed from 10 to 4 for testing
    ])
    eve = models.BooleanField(default=False)
    validation_bits_length = models.IntegerField(default=0)
    eve_percentage = models.FloatField(default=0.5)

    def save(self, *args, **kwargs):
        self.type = 'dps'
        super().save(*args, **kwargs)


class DPSPlayer(Player):
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


class DPSRoom(models.Model):
    game_id = models.ForeignKey(Game,
                                to_field='id',
                                related_name='dps_rooms',
                                on_delete=models.CASCADE)
    player1 = models.ForeignKey(DPSPlayer,
                                related_name='dps_rooms_as_player1',
                                on_delete=models.CASCADE)
    player2 = models.ForeignKey(DPSPlayer,
                                related_name='dps_rooms_as_player2',
                                on_delete=models.CASCADE)


class DPSIteration(models.Model):
    CREATED = 'CREATED'
    FINISHED = 'FINISHED'
    STATUS_CHOICES = [
        (CREATED, 'Created'),
        (FINISHED, 'Finished')
    ]

    room = models.ForeignKey(DPSRoom,
                             related_name='iterations',
                             on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    status = models.CharField(choices=STATUS_CHOICES,
                              default=CREATED,
                              max_length=10)
    eve_present = models.BooleanField(default=False)
    score = models.IntegerField(default=0, validators=[
        MaxValueValidator(100),
        MinValueValidator(0)
    ])
    bob_times_detected = models.CharField(max_length=30, default=None, null=True, blank=True)
    elapsed_time = models.DurationField(null=True, blank=True, default=timedelta)

    def save(self, *args, **kwargs):
        if self.status == self.FINISHED:
            self.elapsed_time = timezone.now() - self.created
        super().save(*args, **kwargs)
