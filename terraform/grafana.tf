variable "enable_grafana" {
  description = "Enable Amazon Managed Grafana provisioning"
  type        = bool
  default     = true
}

variable "grafana_workspace_name" {
  description = "Name for the Amazon Managed Grafana workspace"
  type        = string
  default     = "tc5-api-monitoring"
}

resource "aws_iam_role" "grafana_workspace" {
  count = var.enable_grafana ? 1 : 0
  name  = "tc5_grafana_workspace_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "grafana.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "grafana_cloudwatch_read" {
  count = var.enable_grafana ? 1 : 0
  name  = "tc5_grafana_cloudwatch_read"
  role  = aws_iam_role.grafana_workspace[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:DescribeAlarms",
          "cloudwatch:DescribeAlarmHistory",
          "cloudwatch:DescribeAlarmsForMetric",
          "cloudwatch:GetMetricData",
          "cloudwatch:GetMetricStatistics",
          "cloudwatch:ListMetrics",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams",
          "logs:GetLogEvents",
          "logs:StartQuery",
          "logs:StopQuery",
          "logs:GetQueryResults",
          "logs:GetLogGroupFields",
          "xray:BatchGetTraces",
          "xray:GetTraceSummaries",
          "xray:GetServiceGraph",
          "tag:GetResources"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_grafana_workspace" "monitoring" {
  count = var.enable_grafana ? 1 : 0

  name                     = var.grafana_workspace_name
  description              = "Monitoring workspace for tc5 API and ML services"
  account_access_type      = "CURRENT_ACCOUNT"
  authentication_providers = ["AWS_SSO"]
  permission_type          = "CUSTOMER_MANAGED"
  role_arn                 = aws_iam_role.grafana_workspace[0].arn
  data_sources             = ["CLOUDWATCH"]
}

resource "aws_cloudwatch_dashboard" "api_observability" {
  dashboard_name = "tc5-api-observability"
  dashboard_body = <<DASH
{
  "widgets": [
    {
      "type": "metric",
      "x": 0,
      "y": 0,
      "width": 12,
      "height": 6,
      "properties": {
        "view": "timeSeries",
        "region": "${var.aws_region}",
        "period": 300,
        "title": "API Gateway - Requests / 4XX / 5XX",
        "metrics": [
          ["AWS/ApiGateway", "Count", "ApiId", "${aws_apigatewayv2_api.lambda_api.id}", {"stat": "Sum"}],
          ["AWS/ApiGateway", "4xx", "ApiId", "${aws_apigatewayv2_api.lambda_api.id}", {"stat": "Sum"}],
          ["AWS/ApiGateway", "5xx", "ApiId", "${aws_apigatewayv2_api.lambda_api.id}", {"stat": "Sum"}]
        ]
      }
    },
    {
      "type": "metric",
      "x": 12,
      "y": 0,
      "width": 12,
      "height": 6,
      "properties": {
        "view": "timeSeries",
        "region": "${var.aws_region}",
        "period": 300,
        "title": "API Gateway - Latency",
        "metrics": [
          ["AWS/ApiGateway", "Latency", "ApiId", "${aws_apigatewayv2_api.lambda_api.id}", {"stat": "Average"}],
          ["AWS/ApiGateway", "IntegrationLatency", "ApiId", "${aws_apigatewayv2_api.lambda_api.id}", {"stat": "Average"}]
        ]
      }
    },
    {
      "type": "metric",
      "x": 0,
      "y": 6,
      "width": 12,
      "height": 6,
      "properties": {
        "view": "timeSeries",
        "region": "${var.aws_region}",
        "period": 300,
        "title": "Lambda - Invocations / Errors / Throttles",
        "metrics": [
          ["AWS/Lambda", "Invocations", "FunctionName", "${aws_lambda_function.api_lambda.function_name}", {"stat": "Sum"}],
          ["AWS/Lambda", "Errors", "FunctionName", "${aws_lambda_function.api_lambda.function_name}", {"stat": "Sum"}],
          ["AWS/Lambda", "Throttles", "FunctionName", "${aws_lambda_function.api_lambda.function_name}", {"stat": "Sum"}]
        ]
      }
    },
    {
      "type": "metric",
      "x": 12,
      "y": 6,
      "width": 12,
      "height": 6,
      "properties": {
        "view": "timeSeries",
        "region": "${var.aws_region}",
        "period": 300,
        "title": "Lambda - Duration",
        "metrics": [
          ["AWS/Lambda", "Duration", "FunctionName", "${aws_lambda_function.api_lambda.function_name}", {"stat": "Average"}]
        ]
      }
    }
  ]
}
DASH
}

resource "aws_cloudwatch_metric_alarm" "api_5xx_alarm" {
  alarm_name          = "tc5-api-gateway-5xx"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "5xx"
  namespace           = "AWS/ApiGateway"
  period              = 300
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "API Gateway returning 5xx errors"
  treat_missing_data  = "notBreaching"

  dimensions = {
    ApiId = aws_apigatewayv2_api.lambda_api.id
  }
}

resource "aws_cloudwatch_metric_alarm" "lambda_error_alarm" {
  alarm_name          = "tc5-lambda-errors"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 1
  alarm_description   = "Lambda prediction API is returning errors"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.api_lambda.function_name
  }
}

output "grafana_workspace_url" {
  description = "Amazon Managed Grafana endpoint URL"
  value       = var.enable_grafana ? "https://${aws_grafana_workspace.monitoring[0].endpoint}" : ""
}

output "api_observability_dashboard_name" {
  description = "CloudWatch dashboard name for API observability"
  value       = aws_cloudwatch_dashboard.api_observability.dashboard_name
}
