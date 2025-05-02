from django.urls import path
from core.Controller import ApiPlayerController as api, GameManagerController as gmc

urlpatterns = [
    path('player/new', api.newPlayer, name="ApiPlayerNew"),      # Admin
    path('player/find', api.getPlayer, name="ApiPlayerFind"),    # System
    path('player/list', api.getPlayers, name="ApiPlayerList"),    # Admin
    
    path('table/new', gmc.newTable, name="GameNewTable"),        # Admin
    path('table/list', gmc.getTables, name="GameListTable"),     # System
    path('table/join', gmc.joinTable, name="GameJoinTable"),     # System
    
    path('get/hash', api.showHash, name="ApiGetHash"),           # PUBLIC - Oh My GOD
    path('gen/hash', api.genHash, name="ApiGenHash"),             # Admin
]
