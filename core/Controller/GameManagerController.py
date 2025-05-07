import ast
import requests
import json
import threading
import time
from datetime import datetime
from django.shortcuts import get_object_or_404
import pytz
from treys import Deck, Card, Evaluator
import random
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
from core.models import Player, Table, TablePlayer, GameLog, PlayerTurnToken, ActionState
from django.db.models import Q
import datetime
from django.db import transaction


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

@csrf_exempt
@require_http_methods(["GET"])        
def treys_tour(request):
    
    deck = Deck()
    evaluator = Evaluator()

    hand1 = [deck.draw(1)[0], deck.draw(1)[0]]
    hand2 = [deck.draw(1)[0], deck.draw(1)[0]]
    board = [deck.draw(1)[0] for _ in range(5)]

    score1 = evaluator.evaluate(board, hand1)
    score2 = evaluator.evaluate(board, hand2)

    winner = "draw"
    if score1 < score2:
        winner = "hand1"
    elif score2 < score1:
        winner = "hand2"

    # 🎨 Print bonito no console
    print("\n=== 🃏 IA Poker | Simulação com treys ===")
    print("Mão 1:")
    Card.print_pretty_cards(hand1)
    print("Mão 2:")
    Card.print_pretty_cards(hand2)
    print("Board:")
    Card.print_pretty_cards(board)

    print(f"\nAvaliação:")
    print(f"🧠 Hand 1: {score1} | {evaluator.class_to_string(evaluator.get_rank_class(score1))}")
    print(f"🧠 Hand 2: {score2} | {evaluator.class_to_string(evaluator.get_rank_class(score2))}")
    print(f"\n🏆 Vencedor: {'Empate' if winner == 'draw' else winner.upper()}")

    # 🧾 JSON de retorno (sem ANSI)
    result = {
        "hand1": {
            "cards": [Card.int_to_str(c) for c in hand1],
            "score": score1,
            "rank": evaluator.class_to_string(evaluator.get_rank_class(score1))
        },
        "hand2": {
            "cards": [Card.int_to_str(c) for c in hand2],
            "score": score2,
            "rank": evaluator.class_to_string(evaluator.get_rank_class(score2))
        },
        "board": [Card.int_to_str(c) for c in board],
        "winner": winner
    }

    return JsonResponse(result)

###############ROTINA START#####################
    
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
                    'description': fr'A mesa #{table_id} não está disponível!'
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
                'players_in_table': fr'{TablePlayer.objects.filter(table=table).count()}/{table.max_players}',
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
    
    # dispara processo em segundo plano após a transação
    threading.Thread(
        target=delayed_setup_hand,
        args=(table.id, 2)
    ).start()

def delayed_setup_hand(table_id, delay=5):
    from core.models import Table  # importa aqui para evitar loop
    time.sleep(delay)
    table = Table.objects.get(id=table_id)
    setup_hand(table)  # essa função você vai criar depois

def setup_hand(table):
    with transaction.atomic():
        deck = Deck()

        # Valida as posições na mesa
        assign_positions(table)
        
        # Reinicia os estados de ação para o preflop
        reset_action_state_for_stage(table, stage='preflop')
        
        jogadores = list(
            TablePlayer.objects.filter(table=table, is_active=True).order_by('seat_number')
        )

        # Reinicia o board
        table.flop1 = None
        table.flop2 = None
        table.flop3 = None
        table.turn = None
        table.river = None
        table.current_pot = 0
        table.save()

        # Distribui cartas e salva no banco
        for jogador in jogadores:
            c1 = deck.draw(1)[0]
            c2 = deck.draw(1)[0]
            jogador.card1 = Card.int_to_str(c1)
            jogador.card2 = Card.int_to_str(c2)
            jogador.save()
        
        # Salva o deck no banco
        table.deck = [Card.int_to_str(c) for c in deck.cards]  # salva o baralho restante como strings
        table.save()
        
        # Aplica as blinds
        apply_blinds(table, jogadores)

        # Encontra o jogador da vez
        ordem = jogadores
        if len(ordem) == 2:
            # Heads-up: o botão (BTN) age primeiro no pré-flop
            jogador_da_vez = next((j for j in ordem if j.position == 'btn'), ordem[0])
        else:
            # Mesas com 3+ jogadores: primeiro a agir é o da esquerda do BB
            idx_bb = next((i for i, j in enumerate(ordem) if j.position == 'bb'), 0)
            idx_primeiro = (idx_bb + 1) % len(ordem)
            jogador_da_vez = ordem[idx_primeiro]

        # Cria o token e envia pro jogador da vez
        token = PlayerTurnToken.objects.create(
            table=table,
            player=jogador_da_vez.player,
            hands_played=table.hands_played,
            round_stage='preflop'
        )

        # Envia requests
        send_turn_to_player(token, [jogador_da_vez.card1, jogador_da_vez.card2])
        send_broadcast_state(table)
                
def send_turn_to_player(token_obj, cartas_privadas):
    
    data = {
        'token': token_obj.token,
        'table_id': token_obj.table.id,
        'player_id': token_obj.player.id,
        'round_stage': token_obj.round_stage,
        'hands_played': token_obj.hands_played,
        'your_cards': cartas_privadas
    }

    print("\n=== [SIMULAÇÃO DE ENVIO PARA CALLBACK] ===")
    print(f"URL: {token_obj.player.callback_url}")
    print("Payload:")
    for key, value in data.items():
        print(f"  {key}: {value}")
    print("==========================================")

    # Descomentar para ativar envio real
    """
    try:
        response = requests.post(
            token_obj.player.callback_url,
            json=data,
            timeout=5
        )
        return response.status_code == 200
    except Exception as e:
        print(f"[Erro] Envio para {token_obj.player.callback_url}: {e}")
        return False
    """
    return True

def send_broadcast_state(table):
    jogadores = TablePlayer.objects.filter(table=table, is_active=True).order_by('seat_number')

    broadcast_data = {
        'table_id': table.id,
        'hands_played': table.hands_played,
        'current_pot': table.current_pot,
        'players': [],
        'stage': 'preflop'
    }

    for j in jogadores:
        broadcast_data['players'].append({
            'name': j.player.name,
            'seat_number': j.seat_number,
            'position': j.position,
            'chips': j.chips,
            'is_bot': j.player.is_bot
        })

    for j in jogadores:
        data = {
            'type': 'broadcast',
            'your_cards': [j.card1, j.card2],
            'btn_seat': next((p.seat_number for p in jogadores if p.position == 'btn'), None),
            **broadcast_data
        }

        print(f"\n🎙️ Enviando broadcast para {j.player.name} ({j.player.callback_url})")
        print(data)

        # Descomente abaixo se quiser ativar envio real
        """
        try:
            requests.post(j.player.callback_url, json=data, timeout=5)
        except Exception as e:
            print(f"[Erro] Broadcast para {j.player.name}: {e}")
        """ 

def assign_positions(table):
    jogadores = list(
        TablePlayer.objects.filter(table=table, is_active=True).order_by('seat_number')
    )

    total = len(jogadores)

    # Limpa todas as posições primeiro
    for j in jogadores:
        j.position = '-'
        j.save()

    if total == 2:
        # Heads-up: jogador 0 é BTN (que também age como SB implicitamente), jogador 1 é BB
        jogadores[0].position = 'btn'
        jogadores[0].save()

        jogadores[1].position = 'bb'
        jogadores[1].save()

    elif total >= 3:
        # Define posições padrão em mesa cheia (até 9 players)
        POSITIONS = ['sb', 'bb', 'utg', 'utg+1', 'utg+2', 'lj', 'hj', 'co', 'btn']
        ativos = jogadores[:len(POSITIONS)]  # Corta o excesso, se houver

        for i, jogador in enumerate(ativos):
            jogador.position = POSITIONS[i]
            jogador.save()

    return jogadores

def apply_blinds(table, jogadores):
    """
    Aplica os blinds aos jogadores ativos com base nas posições.
    Funciona tanto para mesas normais quanto heads-up.
    """
    sb_player = next((j for j in jogadores if j.position == 'sb'), None)

    # Se não houver SB, assume que BTN é o SB (caso heads-up)
    if not sb_player:
        sb_player = next((j for j in jogadores if j.position == 'btn'), None)

    bb_player = next((j for j in jogadores if j.position == 'bb'), None)

    if sb_player:
        sb_player.chips -= table.small_blind
        sb_player.save()
        table.current_pot += table.small_blind
        print(f"[BLIND] {sb_player.player.name} pagou SB ({table.small_blind})")
        
        ActionState.objects.filter(table=table, player=sb_player.player, stage='preflop')\
            .update(amount_invested=table.small_blind)

    if bb_player:
        bb_player.chips -= table.big_blind
        bb_player.save()
        table.current_pot += table.big_blind
        print(f"[BLIND] {bb_player.player.name} pagou BB ({table.big_blind})")
        
        ActionState.objects.filter(table=table, player=bb_player.player, stage='preflop')\
            .update(amount_invested=table.big_blind)
    
    table.save()                            

    
    reset_betting_state(table)    
    
def reset_betting_state(table):
    table.current_bet = table.big_blind
    table.last_raise_amount = table.big_blind
    table.save()
    
################################################

@csrf_exempt
@require_http_methods(["POST"])
def receive_action(request):
    try:
        getAccess(request)
        dados = json.loads(request.body.decode('utf-8'))
        checkRequiredFields(dados, ['token', 'action', 'amount'])

        token_str = dados.get('token')
        action = dados.get('action')
        amount = dados.get('amount', 0)

        token_obj = PlayerTurnToken.objects.filter(token=token_str, is_used=False).first()
        if not token_obj:
            return JsonResponse({'status': 400, 'description': 'Token inválido ou expirado'})

        if action == 'raise' and amount <= 0:
            return JsonResponse({'status': 400, 'description': 'Amount obrigatório para raise'})

        if action in ['fold', 'check', 'call', 'all-in']:
            amount = 0

        table = token_obj.table
        player = token_obj.player
        stage = token_obj.round_stage

        valid_actions = ['fold', 'check', 'call', 'raise', 'all-in']
        if action not in valid_actions:
            return JsonResponse({'status': 400, 'description': 'Ação inválida'})
        
        with transaction.atomic():
            
            to_call = get_to_call(player, table, stage)
            state = ActionState.objects.filter(player=player, table=table, stage=stage).first()
            table_player = TablePlayer.objects.get(table=table, player=player)            

            if action == 'fold':                
                table_player.is_in_hand = False
                # Atualiza a Action State                
                state.needs_to_act = False
                
                table_player.save()
                state.save()

            elif action == 'check':
                if to_call > 0:
                    return JsonResponse({'status': 400, 'description': 'Não é possível dar CHECK com aposta pendente.'})
                
                # Atualiza a Action State                
                state.needs_to_act = False
                state.save()

            elif action == 'call':
                
                if table_player.chips < to_call:
                    return JsonResponse({'status': 400, 'description': 'Fichas insuficientes para call'})                
                                
                # Pego as chips do player e add no pote
                table.current_pot += to_call
                table_player.chips -= to_call
                
                state.needs_to_act = False
                state.amount_invested += to_call

                table.save()
                state.save()
                table_player.save()
            elif action == 'raise':
                
                min_raise = table.current_bet + table.last_raise_amount

                if amount < min_raise:
                    return JsonResponse({'status': 400, 'description': f'O mínimo para raise é {min_raise}'})
                if table_player.chips < amount:
                    return JsonResponse({'status': 400, 'description': 'Fichas insuficientes para raise'})

                # Atualizo a table
                diff = amount - to_call
                table.last_raise_amount = diff
                table.current_bet = amount                

                # Atualiza pot
                table.current_pot += diff
                table_player.chips -= diff
                
                state.needs_to_act = False
                state.amount_invested += diff
                
                table.save()
                state.save()
                table_player.save()
                
                mark_all_need_to_act_except(player, table, stage)

            elif action == 'all-in':

                investido = state.amount_invested if state else 0
                allin_amount = table_player.chips + investido                
                diff = allin_amount - to_call

                if diff > 0:
                    table.last_raise_amount = diff
                    table.current_bet = allin_amount
                    table.save()
                    mark_all_need_to_act_except(player, table, stage)                

                # Atualiza pot
                table.current_pot += diff
                table_player.chips -= diff
                table_player.is_all_in = True

                state.needs_to_act = False
                state.amount_invested += diff
                state.save()                
                table_player.save()
                table.save()

            token_obj.is_used = True
            token_obj.save()            

            GameLog.objects.create(
                table=table,
                player=player,
                log_type='action',
                round_stage=stage,
                hands_played=token_obj.hands_played,
                message=f"{player.name} fez {action.upper()} ({amount})",
                json_data=dados
            )

            verifica_proximo_turno(table, stage)

            return JsonResponse({
                'status': 200,
                'description': f"Ação '{action}' registrada com sucesso",
                'pot': table.current_pot,
                'player_chips': table_player.chips
            })

    except Exception as e:
        return JsonResponse({'status': 500, 'description': str(e)})

def get_to_call(player, table, stage):
    state = ActionState.objects.filter(player=player, table=table, stage=stage).first()
    if not state:
        return 0
    return max(table.current_bet - state.amount_invested, 0)

def reset_action_state_for_stage(table, stage):
    ActionState.objects.filter(table=table, stage=stage).delete()
    ativos = TablePlayer.objects.filter(table=table, is_active=True, is_in_hand=True)
    ActionState.objects.bulk_create([
        ActionState(table=table, player=tp.player, stage=stage, needs_to_act=True, amount_invested=0)
        for tp in ativos
    ])

def mark_all_need_to_act_except(raiser, table, stage):
    ActionState.objects.filter(table=table, stage=stage).exclude(player=raiser).update(needs_to_act=True)
    
def verifica_proximo_turno(table, stage):
    try:
        state = ActionState.objects.filter(table=table, stage=stage, needs_to_act=True).first()
        
        if not state:
            print(fr"🏁 ({stage}) Rodada de apostas encerrada.")
            resolve_end_of_round(table, stage)

        jogador = TablePlayer.objects.filter(table=table, player=state.player).first()
        if not jogador or not jogador.is_active or not jogador.is_in_hand:
            state.needs_to_act = False
            state.save()
            return verifica_proximo_turno(table, stage)

        token = PlayerTurnToken.objects.create(
            table=table,
            player=jogador.player,
            hands_played=table.hands_played,
            round_stage=stage
        )

        send_turn_to_player(token, [jogador.card1, jogador.card2])
    except Exception as e:
        print(f"Erro ao gerar próximo turno: {e}")    
        
def resolve_end_of_round(table, stage):
    """Verifica o estágio atual e avança para o próximo."""     
    if stage == 'preflop':
        deal_flop(table)
    elif stage == 'flop':        
        deal_turn(table)
    elif stage == 'turn':
        deal_river(table)        
    elif stage == 'river':            
        # Showdown
        showdown(table)
        
        GameLog.objects.create(
            table=table,
            player=None,
            log_type='round',
            round_stage='river',
            hands_played=table.hands_played,
            message='🏁 Rodada de apostas encerrada (pré-showdown)',
            json_data={}
        )        

def deal_flop(table):
    """Distribui o flop (3 cartas) e atualiza o deck na tabela."""
    deck_list = ast.literal_eval(table.deck) if isinstance(table.deck, str) else table.deck or []
    deck = Deck()
    deck.cards = [Card.new(s) for s in deck_list if isinstance(s, str) and len(s) == 2]

    if len(deck.cards) < 3:
        raise ValueError("Deck não contém cartas suficientes para o flop.")

    table.flop1 = Card.int_to_str(deck.draw(1)[0])
    table.flop2 = Card.int_to_str(deck.draw(1)[0])
    table.flop3 = Card.int_to_str(deck.draw(1)[0])
    table.round_stage = 'flop'
    
    # Zera a aposta atual
    table.current_bet = 0
    table.deck = [Card.int_to_str(c) for c in deck.cards]
    table.save()

    GameLog.objects.create(
        table=table,
        player=None,
        log_type='round',
        round_stage='flop',
        hands_played=table.hands_played,
        message='🟩 Flop distribuído',
        json_data={'flop': [table.flop1, table.flop2, table.flop3]}
    )

    ActionState.objects.filter(table=table).delete()

    for jogador in TablePlayer.objects.filter(table=table, is_active=True, is_in_hand=True):
        ActionState.objects.create(
            table=table,
            player=jogador.player,
            stage='flop',
            amount_invested=0,
            needs_to_act=True
        )

    verifica_proximo_turno(table, 'flop')    
            
def deal_turn(table):
    """Distribui o turn (1 carta) e atualiza o deck na tabela."""
    deck_list = ast.literal_eval(table.deck) if isinstance(table.deck, str) else table.deck or []
    deck = Deck()
    deck.cards = [Card.new(s) for s in deck_list if isinstance(s, str) and len(s) == 2]

    if len(deck.cards) < 1:
        raise ValueError("Deck não contém cartas suficientes para o turn.")

    table.turn = Card.int_to_str(deck.draw(1)[0])    
    table.round_stage = 'turn'
    
    # Zera a aposta atual
    table.current_bet = 0
    table.deck = [Card.int_to_str(c) for c in deck.cards]
    table.save()

    GameLog.objects.create(
        table=table,
        player=None,
        log_type='round',
        round_stage='turn',
        hands_played=table.hands_played,
        message='🟧 Turn distribuído',
        json_data={'turn': table.turn}
    )

    ActionState.objects.filter(table=table).delete()

    for jogador in TablePlayer.objects.filter(table=table, is_active=True, is_in_hand=True):
        ActionState.objects.create(
            table=table,
            player=jogador.player,
            stage='turn',
            amount_invested=0,
            needs_to_act=True
        )

    verifica_proximo_turno(table, 'turn')         
    
def deal_river(table):
    """Distribui o turn (1 carta) e atualiza o deck na tabela."""
    deck_list = ast.literal_eval(table.deck) if isinstance(table.deck, str) else table.deck or []
    deck = Deck()
    deck.cards = [Card.new(s) for s in deck_list if isinstance(s, str) and len(s) == 2]

    if len(deck.cards) < 1:
        raise ValueError("Deck não contém cartas suficientes para o turn.")

    table.river = Card.int_to_str(deck.draw(1)[0])    
    table.round_stage = 'river'
    
    # Zera a aposta atual
    table.current_bet = 0
    table.deck = [Card.int_to_str(c) for c in deck.cards]
    table.save()

    GameLog.objects.create(
        table=table,
        player=None,
        log_type='round',
        round_stage='river',
        hands_played=table.hands_played,
        message='🟧 River distribuído',
        json_data={'river': table.river}
    )

    ActionState.objects.filter(table=table).delete()

    for jogador in TablePlayer.objects.filter(table=table, is_active=True, is_in_hand=True):
        ActionState.objects.create(
            table=table,
            player=jogador.player,
            stage='river',
            amount_invested=0,
            needs_to_act=True
        )

    verifica_proximo_turno(table, 'river')  

def showdown(table):

    evaluator = Evaluator()

    board = [
        Card.new(table.flop1),
        Card.new(table.flop2),
        Card.new(table.flop3),
        Card.new(table.turn),
        Card.new(table.river)
    ]

    ativos = TablePlayer.objects.filter(table=table, is_active=True, is_in_hand=True)

    resultados = []

    for jogador in ativos:
        mao = [Card.new(jogador.card1), Card.new(jogador.card2)]
        score = evaluator.evaluate(board, mao)
        descricao = evaluator.class_to_string(evaluator.get_rank_class(score))
        resultados.append({
            'jogador': jogador,
            'score': score,
            'descricao': descricao,
            'mao': mao
        })

    if not resultados:
        return  # Nenhum jogador elegível

    menor_score = min(r['score'] for r in resultados)
    vencedores = [r for r in resultados if r['score'] == menor_score]
    premio = table.current_pot // len(vencedores)

    for vencedor in vencedores:
        vencedor['jogador'].chips += premio
        vencedor['jogador'].save()

        GameLog.objects.create(
            table=table,
            player=vencedor['jogador'].player,
            log_type='win',
            round_stage='showdown',
            hands_played=table.hands_played,
            message=f"🏆 {vencedor['jogador'].player.name} venceu com {vencedor['descricao']}",
            json_data={
                'board': [table.flop1, table.flop2, table.flop3, table.turn, table.river],
                'hand': [vencedor['jogador'].card1, vencedor['jogador'].card2],
                'score': vencedor['score'],
                'mao_descricao': vencedor['descricao']
            }
        )    

    # Aqui pode resetar mesa ou preparar nova mão
    reset_for_new_hand(table)    
    
def reset_for_new_hand(table):    
    
    table.hands_played += 1
    table.current_bet = 0
    table.last_raise_amount = 0
    table.current_pot = 0
    table.flop1 = None
    table.flop2 = None
    table.flop3 = None
    table.turn = None
    table.river = None
    table.save()

    # Atualizar jogadores na mesa
    for player in TablePlayer.objects.filter(table=table, is_eliminated=False):
        if player.chips > 0:
            player.is_in_hand = True            
        else:
            player.is_in_hand = False
            player.is_eliminated = True
            print(fr'❌ Jogador {player.id} foi eliminado.')
        
        player.is_all_in = False
        player.card1 = None
        player.card2 = None
        player.save()    
        
    ActionState.objects.filter(table=table).delete()

    # TODO: Avaliar se as blinds devem aumentar com base em algum critério

      