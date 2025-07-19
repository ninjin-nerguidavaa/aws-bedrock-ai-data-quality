# IAM Policy for Lambda to access S3 and other AWS services
resource "aws_iam_policy" "lambda_data_quality_policy" {
  name        = "${local.project_name}-lambda-policy"
  description = "IAM policy for Data Quality Lambda function"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # S3 Access
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:ListBucket",
          "s3:GetBucketLocation",
          "s3:GetObjectVersion"
        ]
        Resource = [
          "${aws_s3_bucket.data_quality.arn}",
          "${aws_s3_bucket.data_quality.arn}/*"
        ]
      },
      # Glue Access
      {
        Effect = "Allow"
        Action = [
          "glue:GetTable",
          "glue:GetTables",
          "glue:GetDatabase",
          "glue:GetDatabases",
          "glue:GetPartitions",
          "glue:GetTableVersion",
          "glue:GetTableVersions"
        ]
        Resource = ["*"]
      },
      # Athena Access
      {
        Effect = "Allow"
        Action = [
          "athena:StartQueryExecution",
          "athena:GetQueryExecution",
          "athena:GetQueryResults",
          "athena:GetQueryExecution",
          "athena:StopQueryExecution"
        ]
        Resource = ["*"]
      },
      # SNS Access
      {
        Effect = "Allow"
        Action = [
          "sns:Publish",
          "sns:Subscribe"
        ]
        Resource = ["arn:aws:sns:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:*"]
      },
      # Bedrock Access
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = [
          "arn:aws:bedrock:${data.aws_region.current.name}::foundation-model/anthropic.claude-v2:1",
          "arn:aws:bedrock:${data.aws_region.current.name}::foundation-model/anthropic.claude-v2"
        ]
      },
      # CloudWatch Logs
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
        ]
        Resource = ["arn:aws:logs:*:*:*"]
      },
      # X-Ray Access
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = [
          "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0",
          "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-v2"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:ListFoundationModels",
          "bedrock:GetFoundationModel",
          "bedrock:ListTagsForResource"
        ]
        Resource = "*"
      }
    ]
  })
}

# Attach the policy to the Lambda execution role
resource "aws_iam_role_policy_attachment" "lambda_data_quality" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = aws_iam_policy.lambda_data_quality_policy.arn
}

# Lambda function for data quality checks with Bedrock integration
data "aws_lambda_layer_version" "awssdkpandas" {
  layer_name = "AWSSDKPandas-Python39"
  compatible_runtimes = ["python3.9"]
  compatible_architectures = ["x86_64"]
}

resource "aws_lambda_function" "data_quality" {
  function_name = "${local.project_name}-data-quality"
  role          = aws_iam_role.lambda_execution_role.arn
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.9"
  architectures = ["x86_64"]
  timeout       = 900  # 15 minutes
  memory_size   = 2048  # Increased for Bedrock operations
  
  # Enable active tracing with X-Ray
  tracing_config {
    mode = "Active"
  }
  
  # Set environment variables
  environment {
    variables = {
      ENVIRONMENT          = var.environment
      LOG_LEVEL            = var.log_level
      S3_BUCKET           = aws_s3_bucket.data_quality.id
      GLUE_DATABASE       = aws_glue_catalog_database.this.name
      GLUE_TABLE          = var.glue_table_name
      BEDROCK_ENABLED     = "true"
      BEDROCK_MODEL_ID    = "anthropic.claude-v2:1"
      MAX_RETRY_ATTEMPTS  = "3"
      CIRCUIT_BREAKER_TIMEOUT = "300"
      POWERTOOLS_SERVICE_NAME = "data-quality-bots"
      POWERTOOLS_METRICS_NAMESPACE = "DataQuality"
    }
  }
  
  # Add Lambda layers for dependencies
  layers = [
    "arn:aws:lambda:${data.aws_region.current.name}:580247275435:layer:LambdaInsightsExtension:21",
    aws_lambda_layer_version.data_quality_deps.arn
  ]
  
  # Enable enhanced monitoring
  tracing_config {
    mode = "Active"
  }
  
  # VPC configuration (if needed)
  dynamic "vpc_config" {
    for_each = var.vpc_config != null ? [var.vpc_config] : []
    content {
      subnet_ids         = vpc_config.value.subnet_ids
      security_group_ids = vpc_config.value.security_group_ids
    }
  }
  
  # Dead Letter Queue configuration
  dead_letter_config {
    target_arn = aws_sns_topic.dlq.arn
  }
  
  # Enable async event configuration
  event_source_config {
    maximum_event_age_in_seconds = 3600  # 1 hour
    maximum_retry_attempts      = 2
  }
  
  # Enable provisioned concurrency for consistent performance
  provisioned_concurrent_executions = var.enable_provisioned_concurrency ? 1 : 0
  
  # Add tags
  tags = merge(
    local.common_tags,
    {
      "lambda-insights-extension" = "enabled"
      "environment"              = var.environment
      "managed-by"               = "terraform"
    }
  )
  
  vpc_config {
    subnet_ids         = var.lambda_subnet_ids
    security_group_ids = [aws_security_group.lambda_sg.id]
  }
}

# Create a ZIP archive of the Lambda function code
data "archive_file" "lambda_zip" {
  source_dir  = "${path.module}/lambda_functions/data_quality_checker"
  output_path = "${path.module}/lambda_functions/data_quality_checker.zip"
  type        = "zip"
  
  # Include only the Python files (dependencies are in the layer)
  source {
    content  = file("${path.module}/lambda_functions/data_quality_checker/lambda_function.py")
    filename = "lambda_function.py"
  }
  
  # No need to install requirements as they're in the layer
  
  # Use the hash of the source file to detect changes
  source_code_hash = filemd5("${path.module}/lambda_functions/data_quality_checker/lambda_function.py")
}

# Security group for Lambda function
resource "aws_security_group" "lambda_sg" {
  name        = "${local.project_name}-lambda-sg"
  description = "Security group for Data Quality Lambda function"
  vpc_id      = var.vpc_id
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = merge(local.common_tags, {
    Name = "${local.project_name}-lambda-sg"
  })
}

# SNS Topic for dead-letter queue
resource "aws_sns_topic" "dlq" {
  name = "${local.project_name}-dlq"
  
  tags = local.common_tags
}

# SNS Topic for data quality alerts
resource "aws_sns_topic" "data_quality_alerts" {
  name = "${local.project_name}-alerts"
  
  tags = local.common_tags
}

# SNS Subscription for email notifications
resource "aws_sns_topic_subscription" "email_subscription" {
  count     = length(var.notification_emails)
  topic_arn = aws_sns_topic.data_quality_alerts.arn
  protocol  = "email"
  endpoint  = var.notification_emails[count.index]
}

# CloudWatch Event Rule to trigger Lambda on a schedule
resource "aws_cloudwatch_event_rule" "daily_quality_check" {
  name                = "${local.project_name}-daily-check"
  description         = "Trigger data quality checks daily"
  schedule_expression = var.schedule_expression
  
  tags = local.common_tags
}

# CloudWatch Event Target
resource "aws_cloudwatch_event_target" "trigger_lambda" {
  rule = aws_cloudwatch_event_rule.daily_quality_check.name
  arn  = aws_lambda_function.data_quality_checker.arn
  
  input = jsonencode({
    database = var.default_database
    table    = var.default_table
  })
}

# Allow CloudWatch to invoke Lambda
resource "aws_lambda_permission" "allow_cloudwatch" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.data_quality_checker.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_quality_check.arn
}

# CloudWatch Log Group for Lambda function
resource "aws_cloudwatch_log_group" "lambda_log_group" {
  name              = "/aws/lambda/${aws_lambda_function.data_quality_checker.function_name}"
  retention_in_days = var.log_retention_days
  
  tags = local.common_tags
}
