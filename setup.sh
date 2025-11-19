set -e
ENDPOINT_URL="${ENDPOINT_URL:-http://localhost:4566}"

echo "Usando endpoint: $ENDPOINT_URL"

# Ajustamos o alias para usar a variável
alias awslocal="aws --endpoint-url=$ENDPOINT_URL --region us-east-1"

echo "=== 1. Criando Recursos Básicos (Dynamo, SQS, S3, SNS) ==="

awslocal dynamodb create-table \
    --table-name Pedidos \
    --attribute-definitions AttributeName=id,AttributeType=S \
    --key-schema AttributeName=id,KeyType=HASH \
    --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5


awslocal sqs create-queue --queue-name FilaDePedidos


awslocal s3 mb s3://pedidos-comprovantes

 
awslocal sns create-topic --name PedidosConcluidos

echo "=== 2. Empacotando e Criando Lambdas ==="


zip -j lambda_criar_pedido.zip lambda_criar_pedido/app.py


zip -j lambda_processar_pedido.zip lambda_processar_pedido/app.py


awslocal lambda create-function \
    --function-name criar-pedido \
    --runtime python3.9 \
    --handler app.lambda_handler \
    --role arn:aws:iam::000000000000:role/lambda-role \
    --zip-file fileb://lambda_criar_pedido.zip


awslocal lambda create-function \
    --function-name processar-pedido \
    --runtime python3.9 \
    --handler app.lambda_handler \
    --role arn:aws:iam::000000000000:role/lambda-role \
    --zip-file fileb://lambda_processar_pedido.zip


echo "=== 3. Conectando Serviços ==="


QUEUE_ARN=$(awslocal sqs get-queue-attributes --queue-url http://localhost:4566/000000000000/FilaDePedidos --attribute-names QueueArn --query 'Attributes.QueueArn' --output text)


awslocal lambda create-event-source-mapping \
    --function-name processar-pedido \
    --event-source-arn $QUEUE_ARN \
    --batch-size 1


API_ID=$(awslocal apigateway create-rest-api --name "API Pedidos Restaurante" --query 'id' --output text)

ROOT_RESOURCE_ID=$(awslocal apigateway get-resources --rest-api-id $API_ID --query 'items[0].id' --output text)


PEDIDOS_RESOURCE_ID=$(awslocal apigateway create-resource \
    --rest-api-id $API_ID \
    --parent-id $ROOT_RESOURCE_ID \
    --path-part "pedidos" \
    --query 'id' --output text)

awslocal apigateway put-method \
    --rest-api-id $API_ID \
    --resource-id $PEDIDOS_RESOURCE_ID \
    --http-method POST \
    --authorization-type "NONE"


LAMBDA_ARN=$(awslocal lambda get-function --function-name criar-pedido --query 'Configuration.FunctionArn' --output text)

awslocal apigateway put-integration \
    --rest-api-id $API_ID \
    --resource-id $PEDIDOS_RESOURCE_ID \
    --http-method POST \
    --type AWS_PROXY \
    --integration-http-method POST \
    --uri arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/$LAMBDA_ARN/invocations

awslocal apigateway create-deployment \
    --rest-api-id $API_ID \
    --stage-name "prod"

echo "=== Setup Concluído! ==="
echo "URL da API Gateway:"
echo "http://localhost:4566/restapis/$API_ID/prod/_user_request_/pedidos"