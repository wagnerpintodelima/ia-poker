from django.urls import path
from core.Controller import ApiPlayerController as api, GameManagerController as gmc

urlpatterns = [
    path('player/new', api.newPlayer, name="ApiPlayerNew"),    
    path('player/find', api.getPlayer, name="ApiPlayerFind"),    
    
    path('table/new', gmc.newTable, name="GameNewTable"),    
    path('table/list', gmc.getTables, name="GameListTable"),    
    
    path('get/hash', api.showHash, name="ApiGetHash"),    
    path('gen/hash', api.genHash, name="ApiGenHash")    
]
