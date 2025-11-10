#!/bin/bash
set -e # Para o script se qualquer comando falhar

alias awslocal="aws --endpoint-url=http://localhost:4566 --region us-east-1"

echo "=== 1. Criando Recursos Básicos (Dynamo, SQS, S3, SNS) ==="

awslocal dynamodb create-table \
    --table-name Pedidos \
    --attribute-definitions AttributeName=id,AttributeType=S \
    --key-schema AttributeName=id,KeyType=HASH \
    --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5

# Criar Fila SQS [cite: 28]
awslocal sqs create-queue --queue-name FilaDePedidos

# Criar Bucket S3 [cite: 7]
awslocal s3 mb s3://pedidos-comprovantes

# Criar Tópico SNS (Bônus) 
awslocal sns create-topic --name PedidosConcluidos

echo "=== 2. Empacotando e Criando Lambdas ==="

# Empacotar Lambda 1
zip -j lambda_criar_pedido.zip lambda_criar_pedido/app.py

# Empacotar Lambda 2
zip -j lambda_processar_pedido.zip lambda_processar_pedido/app.py

# Criar Lambda 1: Criar Pedido 
# Usamos a pasta /etc/localstack/init/.. que montamos no docker-compose
awslocal lambda create-function \
    --function-name criar-pedido \
    --runtime python3.9 \
    --handler app.lambda_handler \
    --role arn:aws:iam::000000000000:role/lambda-role \
    --zip-file fileb://lambda_criar_pedido.zip

# Criar Lambda 2: Processar Pedido 
awslocal lambda create-function \
    --function-name processar-pedido \
    --runtime python3.9 \
    --handler app.lambda_handler \
    --role arn:aws:iam::000000000000:role/lambda-role \
    --zip-file fileb://lambda_processar_pedido.zip


echo "=== 3. Conectando Serviços ==="

# Conectar SQS à Lambda 'processar-pedido'
# Pega o ARN da Fila
QUEUE_ARN=$(awslocal sqs get-queue-attributes --queue-url http://localhost:4566/000000000000/FilaDePedidos --attribute-names QueueArn --query 'Attributes.QueueArn' --output text)

# Criar o mapeamento
awslocal lambda create-event-source-mapping \
    --function-name processar-pedido \
    --event-source-arn $QUEUE_ARN \
    --batch-size 1

# Criar API Gateway [cite: 10]
# 1. Criar a API
API_ID=$(awslocal apigateway create-rest-api --name "API Pedidos Restaurante" --query 'id' --output text)

# 2. Obter o ID do Recurso Raiz (/)
ROOT_RESOURCE_ID=$(awslocal apigateway get-resources --rest-api-id $API_ID --query 'items[0].id' --output text)

# 3. Criar o recurso /pedidos [cite: 11]
PEDIDOS_RESOURCE_ID=$(awslocal apigateway create-resource \
    --rest-api-id $API_ID \
    --parent-id $ROOT_RESOURCE_ID \
    --path-part "pedidos" \
    --query 'id' --output text)

# 4. Criar o método POST em /pedidos [cite: 11]
awslocal apigateway put-method \
    --rest-api-id $API_ID \
    --resource-id $PEDIDOS_RESOURCE_ID \
    --http-method POST \
    --authorization-type "NONE"

# 5. Conectar o método POST à Lambda 'criar-pedido'
# Pega o ARN da Lambda
LAMBDA_ARN=$(awslocal lambda get-function --function-name criar-pedido --query 'Configuration.FunctionArn' --output text)

awslocal apigateway put-integration \
    --rest-api-id $API_ID \
    --resource-id $PEDIDOS_RESOURCE_ID \
    --http-method POST \
    --type AWS_PROXY \
    --integration-http-method POST \
    --uri arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/$LAMBDA_ARN/invocations

# 6. Fazer o deploy da API
awslocal apigateway create-deployment \
    --rest-api-id $API_ID \
    --stage-name "prod"

echo "=== Setup Concluído! ==="
echo "URL da API Gateway:"
echo "http://localhost:4566/restapis/$API_ID/prod/_user_request_/pedidos"