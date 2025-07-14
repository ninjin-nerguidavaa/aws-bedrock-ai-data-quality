# IAM Policy for Lambda to access S3 and other AWS services
resource "aws_iam_policy" "lambda_data_quality_policy" {
  name        = "${local.project_name}-lambda-policy"
  description = "IAM policy for Data Quality Lambda function"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          "${aws_s3_bucket.data_quality.arn}",
          "${aws_s3_bucket.data_quality.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "glue:GetTable",
          "glue:GetTables",
          "glue:GetDatabase",
          "glue:GetDatabases",
          "glue:GetPartitions"
        ]
        Resource = ["*"]
      },
      {
        Effect = "Allow"
        Action = [
          "athena:StartQueryExecution",
          "athena:GetQueryExecution",
          "athena:GetQueryResults"
        ]
        Resource = ["*"]
      },
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = ["*"]
      },
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
resource "aws_lambda_function" "data_quality_checker" {
  function_name = "${local.project_name}-checker"
  role          = aws_iam_role.lambda_execution_role.arn
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.9"
  timeout       = 900  # 15 minutes (increased for Bedrock API calls)
  memory_size   = 1024  # Increased for better performance with Bedrock
  
  # Package the Lambda function code and dependencies
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  
  environment {
    variables = {
      S3_BUCKET             = aws_s3_bucket.data_quality.id
      SNS_TOPIC_ARN         = aws_sns_topic.data_quality_alerts.arn
      DEFAULT_DATABASE      = var.default_database
      BEDROCK_REGION        = var.aws_region
      LOG_LEVEL             = var.log_level
      MAX_RETRY_ATTEMPTS    = "3"
      BEDROCK_MODEL_ID      = "anthropic.claude-3-sonnet-20240229-v1:0"
      ENABLE_AI_ANALYSIS    = var.enable_ai_analysis ? "true" : "false"
    }
  }
  
  # Add a dead-letter queue for failed invocations
  dead_letter_config {
    target_arn = aws_sns_topic.dlq.arn
  }
  
  vpc_config {
    subnet_ids         = var.lambda_subnet_ids
    security_group_ids = [aws_security_group.lambda_sg.id]
  }
  
  tags = local.common_tags
}

# Create a ZIP archive of the Lambda function code and dependencies
data "archive_file" "lambda_zip" {
  type        = "zip"
  output_path = "${path.module}/lambda_functions/data_quality_checker/lambda.zip"
  
  source_dir  = "${path.module}/lambda_functions/data_quality_checker"
  excludes    = ["__pycache__", "*.pyc", "lambda.zip"]
  
  depends_on = [
    null_resource.install_dependencies
  ]
}

# Install Python dependencies
resource "null_resource" "install_dependencies" {
  provisioner "local-exec" {
    command = <<EOT
      cd ${path.module}/lambda_functions/data_quality_checker
      pip install -r requirements.txt -t .
    EOT
  }
  
  triggers = {
    requirements = filemd5("${path.module}/lambda_functions/data_quality_checker/requirements.txt")
  }
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
