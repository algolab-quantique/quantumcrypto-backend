from datetime import timedelta

from django.db import models
from django.utils import timezone
from django.core.validators import MaxValueValidator, MinValueValidator

from cryptoweb.models import Game, Player


class E91Game(Game):
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


class E91Player(Player):
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


class E91Room(models.Model):
    game_id = models.ForeignKey(Game,
                                to_field='id',
                                related_name='rooms',
                                on_delete=models.CASCADE)
    player1 = models.ForeignKey(E91Player,
                                related_name='rooms_as_player1',
                                on_delete=models.CASCADE)
    player2 = models.ForeignKey(E91Player,
                                related_name='rooms_as_player2',
                                on_delete=models.CASCADE)


class E91Iteration(models.Model):
    CREATED = 'CREATED'
    FINISHED = 'FINISHED'
    STATUS_CHOICES = [
        (CREATED, 'Created'),
        (FINISHED, 'Finished')
    ]

    room = models.ForeignKey(E91Room,
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
