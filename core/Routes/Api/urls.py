from django.urls import path
from core.Controller import ApiPlayerController as api, GameManagerController as gmc

urlpatterns = [
#                           URL                                          # Level Token    
    path('player/new', api.newPlayer, name="ApiPlayerNew"),                 # Admin
    path('player/find', api.getPlayer, name="ApiPlayerFind"),               # System
    path('player/list', api.getPlayers, name="ApiPlayerList"),              # Admin

    path('table/new', gmc.newTable, name="GameNewTable"),                   # Admin
    path('table/list', gmc.getTables, name="GameListTable"),                # System
    path('table/join', gmc.joinTable, name="GameJoinTable"),                # System

    path('get/hash', api.showHash, name="ApiGetHash"),                      # PUBLIC - Oh My GOD
    path('gen/hash', api.genHash, name="ApiGenHash"),                       # Admin

    path('treys/tour', gmc.treys_tour, name="TreysTour"),                   # Public

    path('receive/action', gmc.receive_action, name="ReceiveAction"),       # System + Token User
]
