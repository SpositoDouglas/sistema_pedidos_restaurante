import json
import boto3
import os

# Configurações do LocalStack
LOCALSTACK_ENDPOINT = 'http://localstack:4566'

# Ajuste para rodar localmente ou no LocalStack
if os.environ.get('AWS_LAMBDA_RUNTIME_API'):
    s3 = boto3.client('s3', endpoint_url=LOCALSTACK_ENDPOINT)
    sns = boto3.client('sns', endpoint_url=LOCALSTACK_ENDPOINT)
    # ADICIONADO: Conexão com DynamoDB
    dynamodb = boto3.resource('dynamodb', endpoint_url=LOCALSTACK_ENDPOINT) 
else:
    s3 = boto3.client('s3')
    sns = boto3.client('sns')
    # ADICIONADO: Conexão com DynamoDB
    dynamodb = boto3.resource('dynamodb')

# Nomes dos recursos (definidos no setup.sh)
BUCKET_NAME = "pedidos-comprovantes"
TOPIC_ARN = "arn:aws:sns:us-east-1:000000000000:PedidosConcluidos"
# ADICIONADO: Tabela do DynamoDB
TABLE_NAME = "Pedidos"
TABLE = dynamodb.Table(TABLE_NAME)

def lambda_handler(event, context):
    
    # A Lambda é acionada por um lote de mensagens SQS
    for record in event.get('Records', []):
        try:
            message_body = json.loads(record.get('body', '{}'))
            order_id = message_body.get('order_id')

            if not order_id:
                print("Mensagem SQS sem order_id. Ignorando.")
                continue

            print(f"Processando pedido: {order_id}")

            # 1. Gerar comprovante em PDF (simulado)
            pdf_content = f"--- COMPROVANTE ---\nPedido ID: {order_id}\nStatus: Processado pela Cozinha"
            pdf_filename = f"comprovante-{order_id}.txt" # Usando .txt para simplificar

            # 2. Salvar o PDF no S3
            s3.put_object(
                Bucket=BUCKET_NAME,
                Key=pdf_filename,
                Body=pdf_content,
                ContentType='text/plain'
            )
            print(f"Comprovante salvo em s3://{BUCKET_NAME}/{pdf_filename}")

            # --- NOVO BLOCO DE CÓDIGO ---
            # 3. Atualizar o status do pedido no DynamoDB
            try:
                TABLE.update_item(
                    Key={'id': order_id},
                    UpdateExpression="SET #status_pedido = :novo_status",
                    ExpressionAttributeNames={'#status_pedido': 'status'},
                    ExpressionAttributeValues={':novo_status': 'CONCLUIDO'}
                )
                print(f"Status do pedido {order_id} atualizado para CONCLUIDO.")
            except Exception as e:
                print(f"Erro ao atualizar DynamoDB: {e}")
            # --- FIM DO NOVO BLOCO ---

            # 4. (Bônus) Enviar notificação para o cliente via SNS
            sns.publish(
                TopicArn=TOPIC_ARN,
                Message=f"Novo pedido concluído: {order_id}",
                Subject="Pedido Pronto!"
            )
            print(f"Notificação SNS enviada para o pedido {order_id}")

        except Exception as e:
            print(f"Erro ao processar mensagem SQS: {e}")
            raise e 

    return {'statusCode': 200, 'body': json.dumps('Processamento concluído.')}