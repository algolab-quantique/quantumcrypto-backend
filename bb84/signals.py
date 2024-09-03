from django.db.models.signals import post_save
from django.dispatch import receiver

from .controller import Controller
from .models import BB84Game


# @receiver(post_save, sender=Game)
# def save_game_is_starting_to_channel(sender, instance, created, **kwargs):
#     if not created and instance.is_starting:
#         Controller.on_play_game(instance.game_id)
#
#
# @receiver(post_save, sender=Game)
# def save_game_is_ending_to_channel(sender, instance, created, **kwargs):
#     if not created and instance.is_ending:
#         Controller.on_end_game(instance.game_id)
