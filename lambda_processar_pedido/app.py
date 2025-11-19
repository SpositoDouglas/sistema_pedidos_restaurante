import json
import boto3
import os

LOCALSTACK_ENDPOINT = 'http://localstack:4566'

if os.environ.get('AWS_LAMBDA_RUNTIME_API'):
    s3 = boto3.client('s3', endpoint_url=LOCALSTACK_ENDPOINT)
    sns = boto3.client('sns', endpoint_url=LOCALSTACK_ENDPOINT)
    dynamodb = boto3.resource('dynamodb', endpoint_url=LOCALSTACK_ENDPOINT) 
else:
    s3 = boto3.client('s3')
    sns = boto3.client('sns')
    dynamodb = boto3.resource('dynamodb')

BUCKET_NAME = "pedidos-comprovantes"
TOPIC_ARN = "arn:aws:sns:us-east-1:000000000000:PedidosConcluidos"
TABLE_NAME = "Pedidos"
TABLE = dynamodb.Table(TABLE_NAME)

def lambda_handler(event, context):
    
    for record in event.get('Records', []):
        try:

            message_body = json.loads(record.get('body', '{}'))
            order_id = message_body.get('order_id')

            if not order_id:
                continue


            response = TABLE.get_item(Key={'id': order_id})
            item = response.get('Item')

            if not item:
                print(f"Erro: Pedido {order_id} não encontrado no banco.")
                continue
            

            cliente = item.get('cliente', 'Desconhecido')
            mesa = item.get('mesa', 'N/A')
            lista_itens = ", ".join(item.get('itens', [])) 
            
            print_do_pedido = (
                f"=== PEDIDO PRONTO ===\n"
                f"ID: {order_id}\n"
                f"Cliente: {cliente}\n"
                f"Mesa: {mesa}\n"
                f"Itens: {lista_itens}\n"
                f"====================="
            )


            s3.put_object(
                Bucket=BUCKET_NAME,
                Key=f"comprovante-{order_id}.txt",
                Body=print_do_pedido,
                ContentType='text/plain'
            )


            TABLE.update_item(
                Key={'id': order_id},
                UpdateExpression="SET #status_pedido = :novo_status",
                ExpressionAttributeNames={'#status_pedido': 'status'},
                ExpressionAttributeValues={':novo_status': 'CONCLUIDO'}
            )


            sns.publish(
                TopicArn=TOPIC_ARN,
                Message=print_do_pedido,
                Subject="Pedido Pronto para Retirada!"
            )

 
            print("\n" + "#"*40)
            print("      [SNS] NOTIFICAÇÃO ENVIADA      ")
            print("#"*40)
            print(print_do_pedido)
            print("#"*40 + "\n")

        except Exception as e:
            print(f"Erro ao processar mensagem: {e}")
            raise e 

    return {'statusCode': 200, 'body': json.dumps('Processamento concluído.')}