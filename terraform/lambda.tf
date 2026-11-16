data "archive_file" "stats_lambda" {
  type        = "zip"
  source_file = "${path.module}/../lambda/stats_handler.py"
  output_path = "${path.module}/.terraform/stats_handler.zip"
}

resource "aws_iam_role" "stats_lambda" {
  name = "${local.name}-stats-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "stats_lambda_logs" {
  role       = aws_iam_role.stats_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_cloudwatch_log_group" "stats_lambda" {
  name              = "/aws/lambda/${local.name}-stats"
  retention_in_days = 7
}

resource "aws_lambda_function" "stats" {
  function_name    = "${local.name}-stats"
  filename         = data.archive_file.stats_lambda.output_path
  source_code_hash = data.archive_file.stats_lambda.output_base64sha256
  role             = aws_iam_role.stats_lambda.arn
  handler          = "stats_handler.handler"
  runtime          = "python3.11"
  timeout          = 10
  memory_size      = 128

  depends_on = [aws_iam_role_policy_attachment.stats_lambda_logs]
}

resource "aws_apigatewayv2_api" "stats" {
  name          = "${local.name}-stats-api"
  protocol_type = "HTTP"
  description   = "CloudTask task statistics API"
}

resource "aws_apigatewayv2_integration" "stats" {
  api_id                 = aws_apigatewayv2_api.stats.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.stats.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "stats" {
  api_id    = aws_apigatewayv2_api.stats.id
  route_key = "POST /stats"
  target    = "integrations/${aws_apigatewayv2_integration.stats.id}"
}

resource "aws_apigatewayv2_stage" "stats" {
  api_id      = aws_apigatewayv2_api.stats.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "stats_api" {
  statement_id  = "AllowStatsApiInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.stats.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.stats.execution_arn}/*/*"
}

resource "aws_cloudwatch_metric_alarm" "stats_lambda_errors" {
  alarm_name          = "${local.name}-stats-lambda-errors"
  alarm_description   = "CloudTask statistics Lambda returned errors."
  namespace           = "AWS/Lambda"
  metric_name         = "Errors"
  dimensions          = { FunctionName = aws_lambda_function.stats.function_name }
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
}

output "stats_api_url" {
  description = "POST endpoint for CloudTask task statistics."
  value       = "${aws_apigatewayv2_api.stats.api_endpoint}/stats"
}
