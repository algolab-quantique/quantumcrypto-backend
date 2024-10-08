from django.urls import re_path

from bb84.consumers import (PlayingRoomConsumer,
                            WaitingRoomConsumer,
                            ResultsPageConsumer, )

websocket_urlpatterns = [
    re_path(r'^ws/games/bb84/(?P<game_code>\w+)/$',
            WaitingRoomConsumer.as_asgi()),
    re_path(r'^ws/games/bb84/(?P<game_code>\w+)/rooms/(?P<room_id>\w+)/$',
            PlayingRoomConsumer.as_asgi()),
    re_path(r'^ws/games/(?P<game_code>\w+)/results/$',
            ResultsPageConsumer.as_asgi()),

]
