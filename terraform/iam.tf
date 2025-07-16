# IAM role for Lambda function
resource "aws_iam_role" "data_quality_lambda" {
  name = "data-quality-bots-lambda-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
  
  tags = merge(
    var.tags,
    {
      Name = "data-quality-bots-lambda-role"
    }
  )
}

# Attach basic Lambda execution policy
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.data_quality_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# S3 access policy
resource "aws_iam_policy" "s3_access" {
  name        = "data-quality-bots-s3-access"
  description = "Policy for S3 access by Data Quality Bots"
  
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
          "arn:aws:s3:::${var.s3_bucket_name}",
          "arn:aws:s3:::${var.s3_bucket_name}/*"
        ]
      }
    ]
  })
  
  tags = var.tags
}

# Attach S3 policy to Lambda role
resource "aws_iam_role_policy_attachment" "s3_access" {
  role       = aws_iam_role.data_quality_lambda.name
  policy_arn = aws_iam_policy.s3_access.arn
}

# Bedrock access policy
resource "aws_iam_policy" "bedrock_access" {
  name        = "data-quality-bots-bedrock-access"
  description = "Policy for Bedrock access by Data Quality Bots"
  
  policy = file("${path.module}/iam_policy_bedrock.json")
  
  tags = var.tags
}

# Attach Bedrock policy to Lambda role
resource "aws_iam_role_policy_attachment" "bedrock_access" {
  role       = aws_iam_role.data_quality_lambda.name
  policy_arn = aws_iam_policy.bedrock_access.arn
}

# Glue and Athena access policy
resource "aws_iam_policy" "data_access" {
  name        = "data-quality-bots-data-access"
  description = "Policy for Glue and Athena access by Data Quality Bots"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "glue:GetTable",
          "glue:GetTables",
          "glue:GetDatabase",
          "glue:GetDatabases",
          "glue:GetPartitions",
          "glue:CreateCrawler",
          "glue:GetCrawler",
          "glue:StartCrawler",
          "glue:StopCrawler",
          "glue:UpdateCrawler",
          "glue:DeleteCrawler",
          "glue:ListCrawlers",
          "glue:GetCrawlerMetrics",
          "glue:GetCrawls"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "athena:StartQueryExecution",
          "athena:GetQueryExecution",
          "athena:GetQueryResults",
          "athena:GetWorkGroup",
          "athena:CreateWorkGroup",
          "athena:UpdateWorkGroup",
          "athena:DeleteWorkGroup",
          "athena:ListWorkGroups",
          "athena:ListQueryExecutions",
          "athena:StopQueryExecution"
        ]
        Resource = "*"
      }
    ]
  })
  
  tags = var.tags
}

# Attach data access policy to Lambda role
resource "aws_iam_role_policy_attachment" "data_access" {
  role       = aws_iam_role.data_quality_lambda.name
  policy_arn = aws_iam_policy.data_access.arn
}

# SNS publish policy
resource "aws_iam_policy" "sns_publish" {
  name        = "data-quality-bots-sns-publish"
  description = "Policy for SNS publish by Data Quality Bots"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = "sns:Publish"
        Resource = "*"
      }
    ]
  })
  
  tags = var.tags
}

# Attach SNS publish policy to Lambda role
resource "aws_iam_role_policy_attachment" "sns_publish" {
  role       = aws_iam_role.data_quality_lambda.name
  policy_arn = aws_iam_policy.sns_publish.arn
}
