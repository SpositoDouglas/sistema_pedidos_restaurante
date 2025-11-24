import boto3
import json
import os
import sys


ENDPOINT = os.getenv('ENDPOINT_URL', 'http://localstack:4566')
REGION = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
QUEUE_URL = f'{ENDPOINT}/000000000000/FilaDePedidos'

sqs = boto3.client('sqs', endpoint_url=ENDPOINT, region_name=REGION)
lambda_client = boto3.client('lambda', endpoint_url=ENDPOINT, region_name=REGION)

def processar_unico_pedido():
    print(f"📡 Conectando a {ENDPOINT}...")
    print("🔍 Verificando se há pedidos na fila...")
    
    try:
        response = sqs.receive_message(
            QueueUrl=QUEUE_URL,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=2
        )
    except Exception as e:
        print(f"❌ Erro ao conectar no SQS: {e}")
        sys.exit(1)

    messages = response.get('Messages', [])

    if not messages:
        print("📭 A fila está vazia. Nada para processar.")
        sys.exit(0)


    message = messages[0]
    receipt_handle = message['ReceiptHandle']
    body = message['Body']
    
    print(f"⚙️ Processando pedido: {body}")

    lambda_payload = {"Records": [{"body": body}]}

    try:
        invoke_response = lambda_client.invoke(
            FunctionName='processar-pedido',
            InvocationType='RequestResponse',
            Payload=json.dumps(lambda_payload)
        )
        
        if invoke_response['StatusCode'] == 200:
            print("✅ Lambda executada com sucesso!")
            
            sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=receipt_handle)
            print("🗑️ Pedido removido da fila.")
        else:
            print(f"❌ A Lambda retornou erro: {invoke_response}")

    except Exception as e:
        print(f"❌ Falha ao invocar a Lambda: {e}")

if __name__ == "__main__":
    processar_unico_pedido()