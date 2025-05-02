from iapoker.settings import SECRET_KEY, SECRET_KEY_ADMIN
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
from core.models import Player
from django.db.models import Q
from django.db import transaction



@csrf_exempt
@require_http_methods(["GET"])
def getPlayer(request):

    try:
        dados = json.loads(request.body.decode('utf-8'))
        getAccess(request)        
        
        checkRequiredFields(dados, ['secret_key', 'email'])
        
        secret_key = dados.get('secret_key', None)
        email = dados.get('email', None)
        
        if not secret_key and not email:
            return JsonResponse({
                'status': 500,
                'description': f"Campos obrigatórios ausentes ou vazios: {', '.join(missing_fields)}"
            })
            
        
        player = Player.objects.filter(
            Q(email=email) | Q(secret_key=secret_key)
        ).first()

        if player:
            return JsonResponse({
                'status': 200,
                'description': 'Foi encontrado um player com para esse filtro',
                'name': player.name,
                'email': player.email,
                'callback_url': player.callback_url,
                'secret_key': player.secret_key,
                'avatar_url': player.avatar_url,
                'is_bot': player.is_bot,
                'is_active': player.is_active,
                'created_at': player.created_at.strftime('%d/%m/%Y %H:%M'),
                'updated_at': player.updated_at.strftime('%d/%m/%Y %H:%M')
            })
        else:                
            return JsonResponse({
                'status': 200,
                'description': 'Não há ninguém com esses dados'
            })

    except Exception as e:
        context = {
            'status': 500,
            'description': str(e)
        }


    return HttpResponse(json.dumps(context, ensure_ascii=False), content_type="application/json")

@csrf_exempt
@require_http_methods(["POST"])
def newPlayer(request):

    try:
        dados = json.loads(request.body.decode('utf-8'))
        getAccessAdmin(request)
        
        checkRequiredFields(dados, ['name', 'email', 'callback_url', 'avatar_url'])
        
        # Acessando um valor específico | {"deviceNumber":"cf916da6509da698be4854f789b26c01","version": "v4.3.2"}
        name = dados.get('name', None)
        email = dados.get('email', None)
        callback_url = dados.get('callback_url', None)
        avatar_url = dados.get('avatar_url', None)
        
        item = Player()
        item.name = name
        item.email = email
        item.callback_url = callback_url
        item.avatar_url = avatar_url
        item.save()

        # Fazer algo com o valor
        return JsonResponse({
            'status': 200,
            'description': 'Player add com sucesso!',
            'secret_key': item.secret_key
        })

    except Exception as e:
        context = {
            'status': 500,
            'description': str(e)
        }


    return HttpResponse(json.dumps(context, ensure_ascii=False), content_type="application/json")

@csrf_exempt
@require_http_methods(["GET"])
def showHash(request):

    try:        
        return JsonResponse({
            'status': 200,
            'hash_system': getHash(),
            'hash_admin': getHash(SECRET_KEY_ADMIN)
        })

    except Exception as e:
        context = {
            'status': 500,
            'description': str(e)
        }


    return HttpResponse(json.dumps(context, ensure_ascii=False), content_type="application/json")

@csrf_exempt
@require_http_methods(["GET"])
def genHash(request):

    try:
        dados = json.loads(request.body.decode('utf-8'))
        
        getAccessAdmin(request)

        # Acessando um valor específico | {"deviceNumber":"cf916da6509da698be4854f789b26c01","version": "v4.3.2"}
        secret_key = dados.get('secret_key', None)        

        # Fazer algo com o valor
        return JsonResponse({
            'status': 200,
            'description': fr'Secret Key Received: {secret_key}',
            'secret_key': getHash(secret_key)
        })

    except Exception as e:
        context = {
            'status': 500,
            'description': str(e)
        }


    return HttpResponse(json.dumps(context, ensure_ascii=False), content_type="application/json")

@csrf_exempt
@require_http_methods(["GET"])
def getPlayers(request):

    try:
        
        getAccessAdmin(request)
        
        players = Player.objects.filter(is_active=True).values(
            'id', 'name', 'email', 'callback_url',
            'secret_key', 'is_bot', 'is_active',
            'avatar_url', 'created_at', 'updated_at'
        )

        if players:
            return JsonResponse({
                'status': 200,
                'description': fr'Foi encontrado {len(players)} players ativo.',
                'players': list(players)
            })
        else:                
            return JsonResponse({
                'status': 200,
                'description': 'Não há players ativo'
            })

    except Exception as e:
        context = {
            'status': 500,
            'description': str(e)
        }


    return HttpResponse(json.dumps(context, ensure_ascii=False), content_type="application/json")
