import json
import threading
import time
from datetime import datetime
from django.shortcuts import get_object_or_404
import pytz
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.utils import timezone
from core.Controller.BaseController import getHash, getAccess, getAccessAdmin
from core.models import Player, Table, TablePlayer
from django.db.models import Q


class GameManagerController:
    POSITIONS_ORDERED = [
        'sb', 'bb', 'utg', 'utg+1', 'utg+2', 'lj', 'hj', 'co', 'btn'
    ]

@staticmethod
def get_positions_for_player_count(player_count: int):
    """
    Retorna a lista de posições de acordo com a quantidade de jogadores ativos.
    """
    max_players = min(player_count, len(GameManagerController.POSITIONS_ORDERED))
    return GameManagerController.POSITIONS_ORDERED[:max_players]

@csrf_exempt
@require_http_methods(["POST"])
def newTable(request):

    try:
        dados = json.loads(request.body.decode('utf-8'))
        getAccessAdmin(request)

        required_fields = ['name', 'max_players', 'initial_chips', 'small_blind', 'big_blind', 'blind_strategy', 'blind_interval', 'status']
        missing_fields = [field for field in required_fields if not dados.get(field)]

        if missing_fields:
            return JsonResponse({
                'status': 400,
                'description': f"Campos obrigatórios ausentes ou vazios: {', '.join(missing_fields)}"
            })

        # Acessando um valor específico | {"deviceNumber":"cf916da6509da698be4854f789b26c01","version": "v4.3.2"}
        name = dados.get('name', None)
        max_players = dados.get('max_players', None)
        initial_chips = dados.get('initial_chips', None)
        small_blind = dados.get('small_blind', None)
        big_blind = dados.get('big_blind', None)
        blind_strategy = dados.get('blind_strategy', None)
        blind_interval = dados.get('blind_interval', None)
        status = dados.get('status', None)
        
        item = Table()
        item.name = name
        item.max_players = max_players
        item.initial_chips = initial_chips
        item.small_blind = small_blind
        item.big_blind = big_blind
        item.blind_strategy = blind_strategy
        item.blind_interval = blind_interval
        item.status = status
        item.save()
        
        return JsonResponse({
            'status': 200,
            'description': 'Mesa criado com sucesso com sucesso!',
            'mesa': item.id
        })

    except Exception as e:
        context = {
            'status': 500,
            'description': str(e)
        }


    return HttpResponse(json.dumps(context, ensure_ascii=False), content_type="application/json")

@csrf_exempt
@require_http_methods(["GET"])
def getTables(request):

    try:
        
        getAccess(request)

        tables = Table.objects.filter(status='waiting').values(
            'id', 'name', 'max_players', 'initial_chips',
            'small_blind', 'big_blind', 'blind_strategy',
            'blind_interval', 'status', 'created_at'
        )
        
        return JsonResponse({
            'status': 200,
            'description': 'Mesas ativas no momento!',
            'mesas': list(tables)
        })

    except Exception as e:
        context = {
            'status': 500,
            'description': str(e)
        }


    return HttpResponse(json.dumps(context, ensure_ascii=False), content_type="application/json")

