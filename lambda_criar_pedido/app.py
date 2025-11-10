import json
import boto3
import uuid
import os

# Estamos no LocalStack, então apontamos o boto3 para ele
# A porta 4566 é a porta interna do container do LocalStack
LOCALSTACK_ENDPOINT = 'http://localstack:4566'

# Ajuste para rodar localmente ou no LocalStack
if os.environ.get('AWS_LAMBDA_RUNTIME_API'):
    # Estamos dentro da Lambda (LocalStack)
    dynamodb = boto3.resource('dynamodb', endpoint_url=LOCALSTACK_ENDPOINT)
    sqs = boto3.client('sqs', endpoint_url=LOCALSTACK_ENDPOINT)
else:
    # Estamos rodando local (ex: testes)
    dynamodb = boto3.resource('dynamodb')
    sqs = boto3.client('sqs')

# Nomes dos recursos (definidos no setup.sh)
TABLE_NAME = "Pedidos"
QUEUE_URL = f"{LOCALSTACK_ENDPOINT}/000000000000/FilaDePedidos"
TABLE = dynamodb.Table(TABLE_NAME)

def lambda_handler(event, context):
    try:
        # 1. Receber e validar o pedido da API Gateway [cite: 4, 12]
        body = json.loads(event.get('body', '{}'))

        cliente = body.get('cliente')
        itens = body.get('itens')
        mesa = body.get('mesa')

        if not cliente or not itens or not mesa:
            return {'statusCode': 400, 'body': json.dumps('Erro: Faltando cliente, itens ou mesa.')}

        # 2. Preparar o item para o DynamoDB
        order_id = str(uuid.uuid4())
        item = {
            'id': order_id,
            'cliente': cliente,
            'itens': itens,
            'mesa': mesa,
            'status': 'PENDENTE'
        } # [cite: 26]

        # 3. Salvar no DynamoDB 
        TABLE.put_item(Item=item)

        # 4. Enviar o ID para a fila SQS 
        sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps({'order_id': order_id})
        )

        # 5. Retornar sucesso para a API Gateway
        return {
            'statusCode': 201,
            'body': json.dumps({'message': 'Pedido criado com sucesso!', 'order_id': order_id})
        }

    except Exception as e:
        print(f"Erro: {e}")
        return {'statusCode': 500, 'body': json.dumps('Erro interno no servidor.')}