import string
import random
from django.core.files.storage import FileSystemStorage
import os
import hashlib
import datetime
from iapoker.settings import SECRET_KEY, SECRET_KEY_ADMIN
from django.http import FileResponse, Http404
from django.conf import settings
import base64
from core.models import Authorization
from django.core.exceptions import PermissionDenied


def saveFile(folder, format, file, name=None):

    if not name:
        caracteres = 30
        name = ''.join(random.choices(string.ascii_uppercase + string.digits, k=caracteres))

    fss = FileSystemStorage()
    file = fss.save(folder + name + '.' + format, file)
    file_url = fss.url(file)
    return name

def saveFileBase64(folder, format, base64_file, name=None):
    
    if not name:
        caracteres = 30
        name = ''.join(random.choices(string.ascii_uppercase + string.digits, k=caracteres))
    
    if base64_file:
        # Decodifica o Base64
        file_data = base64.b64decode(base64_file)        
        
        # Cria o diretório caso não exista
        os.makedirs(folder, exist_ok=True)

        # Salva o arquivo
        path = os.path.join(settings.BASE_DIR, folder, name + format)
        
        with open(path, "wb") as f:
            f.write(file_data)
    
    return name

def deleteFile(folder, filename, format):
    # Cria o caminho completo do arquivo
    file_path = os.path.join(folder, f"{filename}.{format}")

    # Instância do FileSystemStorage
    fss = FileSystemStorage()

    # Verifica se o arquivo existe
    if fss.exists(file_path):
        # Deleta o arquivo
        fss.delete(file_path)
        return True
    else:
        return False
    
# Api's devem mandar esse hash no cabeçalho
def getHash(secret_key=SECRET_KEY):
    # Obtém a data atual (dia, mês e ano)
    today = datetime.datetime.now()
    dia = today.day
    mes = today.month
    ano = today.year        
    
    # Concatena os valores de data e chave secreta
    data = f'{dia}-{mes}-{ano}-{secret_key}'    # Essa é para os gps antigos
    # data = f'{ano}@{SECRET_KEY}!{dia}${mes}'    
    
    # Gera o hash SHA-256
    hash_value = hashlib.sha256(data.encode()).hexdigest()
    
    return hash_value

def getAccess(request):
    authorization_header = request.headers.get('Authorization', None)     
    
    if authorization_header != getHash():
        raise PermissionDenied("Forbidden! Be careful, we know where you are!")
    
    return True

def getAccessAdmin(request):
    authorization_header = request.headers.get('Authorization', None)     
    
    if authorization_header != getHash(SECRET_KEY_ADMIN):
        raise PermissionDenied("Forbidden! Be careful, we know where you are!")
    
    return True

def downloadFile(folder, filename, format):       
    
     # Caminho completo do arquivo
    file_path = os.path.join(settings.MEDIA_ROOT, folder, f'{filename}.{format}')
     
    # Verifica se o arquivo existe
    if not os.path.exists(file_path):
        raise Http404(fr"File does not exist. The url is:    {file_path}") 

    # Retorna o arquivo como resposta
    response = FileResponse(open(file_path, 'rb'), as_attachment=True)
    response['Content-Disposition'] = f'attachment; filename="{filename}.{format}"'
    return response

def DateSTR2Datetime(str_date):
    try:
        return datetime.datetime.strptime(str_date, "%d/%m/%Y")  # Converte a string para datetime
    except ValueError:
        return False  # Retorna False se a conversão falhar
    
def str_to_datetime(date_time_str):
    try:        
        newDate = datetime.datetime.strptime(date_time_str, "%d/%m/%Y %H:%M")
        return newDate
    except ValueError:
        return False  # Retorna False se a conversão falhar
    
