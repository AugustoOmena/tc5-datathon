# API Gateway (V2 para ser mais barato e rápido)
resource "aws_apigatewayv2_api" "lambda_api" {
  name          = "tc5-ml-gateway"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_stage" "lambda_stage" {
  api_id      = aws_apigatewayv2_api.lambda_api.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id           = aws_apigatewayv2_api.lambda_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.api_lambda.invoke_arn
}

# Rota para o path raiz (health, etc.)
resource "aws_apigatewayv2_route" "root" {
  api_id    = aws_apigatewayv2_api.lambda_api.id
  route_key = "ANY /"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

# Proxy: todas as demais rotas (predict, docs, openapi.json, etc.) vão para a Lambda
resource "aws_apigatewayv2_route" "proxy" {
  api_id    = aws_apigatewayv2_api.lambda_api.id
  route_key = "ANY /{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

# Permissão para o Gateway chamar o Lambda
resource "aws_lambda_permission" "api_gw" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.lambda_api.execution_arn}/*/*"
}

output "api_url" {
  value       = aws_apigatewayv2_api.lambda_api.api_endpoint
  description = "URL base da API (ex.: /predict, /docs, /)"
}