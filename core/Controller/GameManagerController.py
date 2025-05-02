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
from core.Controller.BaseController import getHash, getAccess, getAccessAdmin, checkRequiredFields
from core.models import Player, Table, TablePlayer, GameLog
from django.db.models import Q
import datetime
from django.db import transaction



POSITIONS_ORDERED = [
    'sb', 'bb', 'utg', 'utg+1', 'utg+2', 'lj', 'hj', 'co', 'btn'
]

@staticmethod
def get_positions_for_player_count(player_count: int):
    """
    Retorna a lista de posições de acordo com a quantidade de jogadores ativos.
    """
    max_players = min(player_count, len(POSITIONS_ORDERED))
    return POSITIONS_ORDERED[:max_players]


@staticmethod
def start_game(table):
    with transaction.atomic():
        # Atualiza status da mesa
        table.status = 'active'
        table.hands_played += 1    
        table.save()
        hands_played = table.hands_played

        # Busca jogadores ordenados por seat_number
        jogadores = TablePlayer.objects.filter(table=table).order_by('seat_number')
        posicoes = get_positions_for_player_count(jogadores.count())

        for i, jogador in enumerate(jogadores):
            jogador.position = posicoes[i]
            jogador.is_in_hand = True
            jogador.is_eliminated = False
            jogador.is_all_in = False
            jogador.save()

            # Cria log de posição
            GameLog.objects.create(
                table = table,
                player = jogador.player,
                log_type = 'position',
                round_stage = '-',
                hands_played = hands_played,
                message = f"{jogador.player.name} recebeu a posição {jogador.get_position_display()}.",
                json_data = {
                    'seat_number': jogador.seat_number,
                    'position': jogador.position
                }
            )

        # Cria log de início da partida
        GameLog.objects.create(
            table = table,
            player = None,
            log_type = 'start',
            round_stage = '-',
            hands_played = hands_played,
            message = "A partida foi iniciada automaticamente.",
            json_data = {
                'players': [jogador.player.name for jogador in jogadores],
                'total_players': jogadores.count(),
                'start_time': datetime.datetime.now().strftime('%d/%m/%Y %H:%M')
            }
        )

@csrf_exempt
@require_http_methods(["POST"])
def joinTable(request):
    
    try:
        with transaction.atomic():
            getAccess(request)

            dados = json.loads(request.body.decode('utf-8'))
        
            checkRequiredFields(dados, ['table_id', 'secret_key'])

            table_id = dados.get('table_id', None)
            secret_key = dados.get('secret_key', None)
            
            table = Table.objects.filter(id=table_id, status='waiting').first()
            player = Player.objects.filter(secret_key=secret_key).first()
            
            # Mesa não disponível
            if not table:
                return JsonResponse({
                    'status': 400,
                    'description': fr'A mesa {table.id} não está disponível!'
                })
                
            # Player Não existe            
            if not player:
                return JsonResponse({
                    'status': 400,
                    'description': fr'player não encontrado'
                })     
                
            # Player Já está na mesa
            tablePlayer = TablePlayer.objects.filter(table=table, player=player).first()        
            if tablePlayer:
                return JsonResponse({
                    'status': 400,
                    'description': fr'O Jogador {player.name} já está na mesa {table.id}!'
                })
            
            # Vê se tem vaga na mesa
            ocupados = TablePlayer.objects.filter(table=table).count()
            if ocupados >= table.max_players:
                return JsonResponse({
                    'status': 400,
                    'description': fr'A mesa {table.id} está completa. Não foi possível add mais um player nela!'
                })
                
            seat_number = ocupados + 1

            TablePlayer.objects.create(
                table = table,
                player = player,
                seat_number = seat_number,
                chips = table.initial_chips,
                is_active = True,
                is_in_hand = True,
                position='-'
            )

            log_event(table, player, 'join', f"{player.name} entrou na mesa.", data={
                'seat_number': seat_number,
                'chips': table.initial_chips
            })
            
            # Se juntou todo mundo que os comecem os jogos...
            if seat_number == table.max_players:
                start_game(table)


            return JsonResponse({
                'status': 200,
                'description': f'Jogador {player.name} entrou na mesa com sucesso.',
                'player': {
                    'name': player.name,
                    'seat_number': seat_number,
                    'chips': table.initial_chips,
                    'position': '-',
                    'table_id': table.id
                }
            })

    except Exception as e:
        context = {
            'status': 500,
            'description': str(e)
        }

    return HttpResponse(json.dumps(context, ensure_ascii=False), content_type="application/json")

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

def log_event(table, player, log_type, message, stage='-', hands=0, data=None):
    GameLog.objects.create(
        table=table,
        player=player,
        log_type=log_type,
        round_stage=stage,
        hands_played=hands,
        message=message,
        json_data=data or {}
    )

