import requests
import json
import boto3
import os



ENDPOINT = os.getenv('ENDPOINT_URL', 'http://localstack:4566')
REGION = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')

print(f"📡 Tentando conectar ao LocalStack em: {ENDPOINT}")

def get_api_url():
    try:
        client = boto3.client(
            'apigateway', 
            endpoint_url=ENDPOINT, 
            region_name=REGION
        )
        
        apis = client.get_rest_apis()
        
        if not apis.get('items'):
            return None

        api_id = apis['items'][0]['id']
        
        base_url = ENDPOINT
        return f"{base_url}/restapis/{api_id}/prod/_user_request_/pedidos"
        
    except Exception as e:
        print(f"⚠️ Erro na detecção automática: {e}")
        return None

# Tenta detectar
API_URL = get_api_url()

if not API_URL:
    print("❌ Não foi possível detectar a API automaticamente.")
    print("Dica: Se você está rodando via Docker, a URL deve começar com http://localstack:4566")
    entrada = input("Cole a URL da API Gateway aqui: ").strip()
    API_URL = entrada.replace('\u2060', '').strip() 
else:
    print(f"✅ API Detectada: {API_URL}")

print(f"--- Criando Pedido ---")

cliente = input("Nome do Cliente: ")
mesa = input("Número da Mesa: ")
itens_str = input("Itens (separados por vírgula): ")
itens = [i.strip() for i in itens_str.split(',')]

payload = {
    "cliente": cliente,
    "mesa": int(mesa) if mesa.isdigit() else 0,
    "itens": itens
}

try:
    response = requests.post(API_URL, json=payload)
    
    if response.status_code == 201:
        dados = response.json()
        print(f"\n✅ Sucesso! Pedido Criado.")
        print(f"ID do Pedido: {dados.get('order_id')}")
    else:
        print(f"\n❌ Erro: {response.status_code} - {response.text}")
except Exception as e:
    print(f"\n❌ Erro de conexão: {e}")