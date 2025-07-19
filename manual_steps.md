# AWS Data Quality Bots - Manual Deployment Guide

This document provides comprehensive, step-by-step instructions for manually deploying the AWS Data Quality Bots project using the AWS Management Console.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Architecture Overview](#architecture-overview)
3. [Step 1: Set Up S3 Buckets](#step-1-set-up-s3-buckets)
4. [Step 2: Upload Sample Data](#step-2-upload-sample-data)
5. [Step 3: Configure IAM Roles and Policies](#step-3-configure-iam-roles-and-policies)
6. [Step 4: Deploy Lambda Function](#step-4-deploy-lambda-function)
7. [Step 5: Set Up AWS Glue](#step-5-set-up-aws-glue)
8. [Step 6: Configure EventBridge Rule](#step-6-configure-eventbridge-rule)
9. [Step 7: Test the Deployment](#step-7-test-the-deployment)
10. [Step 8: Set Up Monitoring (Optional)](#step-8-set-up-monitoring-optional)
11. [Step 9: Deploy the Dashboard](#step-9-deploy-the-dashboard)
12. [Step 10: Configure CloudFront (Recommended for Production)](#step-10-configure-cloudfront-recommended-for-production)
13. [Troubleshooting](#troubleshooting)
14. [Maintenance and Operations](#maintenance-and-operations)

## Prerequisites

Before you begin, ensure you have the following:

### AWS Account Requirements
- AWS Account with AdministratorAccess or equivalent permissions
- AWS CLI configured with credentials
- Default VPC and subnets in your preferred region
- Access to Amazon Bedrock with Claude 2.1 model enabled
- IAM permissions for Bedrock:InvokeModel and Bedrock:InvokeModelWithResponseStream

### Local Development Environment
- Python 3.8 or later
- pip (Python package manager)
- Git (for cloning the repository)

## Architecture Overview

The AWS Data Quality Bots solution consists of the following components:

1. **S3 Buckets**: Store input data, processed results, and reports
2. **AWS Lambda**: Serverless function that processes data quality checks using Claude 2.1
3. **AWS Glue**: Data catalog and ETL service for data discovery and preparation
4. **Amazon Bedrock**: AI service with Claude 2.1 for intelligent data quality and anomaly analysis
5. **Amazon EventBridge**: Triggers the Lambda function on S3 upload events
6. **Static Website Hosting**: S3 + CloudFront for the interactive dashboard

### Data Flow

1. Data is uploaded to the S3 input bucket
2. EventBridge triggers the Lambda function
3. Lambda processes the data and sends it to Claude 2.1 via Bedrock
4. Analysis results are stored in the output S3 bucket
5. The web dashboard displays the results with interactive visualizations
6. **Amazon SNS**: Sends notifications for data quality issues
7. **Amazon CloudWatch**: Monitors and logs all activities

## Step 1: Set Up S3 Buckets

### Create Main Data Bucket
1. Sign in to the AWS Management Console and open the Amazon S3 console
2. Choose **Create bucket**
3. Under **General configuration**:
   - **Bucket name**: `data-quality-bots-<your-account-id>-<region>` (must be globally unique)
   - **AWS Region**: Select your preferred region (e.g., us-east-1)
4. Under **Object Ownership**:
   - Select **ACLs disabled** (recommended)
5. Under **Block Public Access settings for this bucket**:
   - Keep all options checked
   - Acknowledge the warning about the bucket not being public
6. Under **Bucket Versioning**:
   - Select **Enable**
7. Under **Default encryption**:
   - Select **Enable**
   - Choose **AES-256 (SSE-S3)**
8. Click **Create bucket**

### Create Required Folders
1. In the S3 console, select your newly created bucket
2. Click **Create folder** and create the following structure:
   ```
   ├── input/               # Source data files
   │   └── customers/       # Customer data
   ├── output/             # Processed data
   ├── reports/            # Data quality reports
   └── athena-results/     # Athena query results
   ```
3. Click **Save** after creating each folder

## Step 2: Upload Sample Data

1. In the S3 console, navigate to your bucket
2. Create a folder called `customers/` inside the `input/` folder
3. Upload the sample CSV file:
   ```bash
   aws s3 cp test_data/sample_customers.csv s3://data-quality-bots-<your-account-id>-<region>/input/customers/
   ```

## Step 3: Create IAM Roles and Policies

### Create IAM Role for Lambda

1. Navigate to **IAM** > **Roles** > **Create role**
2. Select **AWS service** > **Lambda** > **Next**
3. Attach the following policies:
   - `AWSLambdaBasicExecutionRole`
   - `AmazonS3FullAccess` (or restrict to your specific bucket)
   - `AWSGlueConsoleFullAccess` (or more restricted permissions)
   - `AmazonAthenaFullAccess` (or more restricted permissions)
   - `AmazonBedrockFullAccess` (or more restricted permissions)
   - `AmazonSNSFullAccess` (if using notifications)
4. Click **Next**
5. Role name: `DataQualityLambdaRole`
6. Click **Create role**

### Update IAM Role for Lambda

1. Navigate to **IAM** > **Roles**
2. Find and select your Lambda execution role
3. Click **Add permissions** > **Create inline policy**
4. Use the JSON tab and add the following policy:
   ```json
   {
       "Version": "2012-10-17",
       "Statement": [
           {
               "Effect": "Allow",
               "Action": [
                   "bedrock:InvokeAgent",
                   "bedrock:RetrieveAndGenerate",
                   "bedrock:Retrieve"
               ],
               "Resource": [
                   "arn:aws:bedrock:*::agent/*",
                   "arn:aws:bedrock:*::knowledge-base/*"
               ]
           },
           {
               "Effect": "Allow",
               "Action": [
                   "bedrock:ListAgentKnowledgeBases",
                   "bedrock:ListAgents",
                   "bedrock:ListAgentAliases"
               ],
               "Resource": "*"
           }
       ]
   }
   ```
5. Click **Review policy** > **Name**: `BedrockAccessPolicy` > **Create policy**

## Step 4: Deploy Lambda Function

### Package the Lambda function
   ```bash
   # Install dependencies
   pip install -r requirements.txt -t ./package
   
   # Create deployment package
   cd package
   zip -r ../lambda_function.zip .
   cd ..
   zip -g lambda_function.zip lambda_function.py
   ```

2. **Create the Lambda function**:
   - Go to AWS Lambda console
   - Click "Create function"
   - Select "Author from scratch"
   - Enter function name: `data-quality-checker`
   - Runtime: Python 3.9
   - Architecture: x86_64
   - Click "Create function"

3. **Upload the deployment package**:
   - In the function configuration, click "Upload from" > ".zip file"
   - Select the `lambda_function.zip` file
   - Click "Save"

4. **Configure environment variables**:
   - In the function configuration, go to "Configuration" > "Environment variables"
   - Add the following variables:
     - `S3_BUCKET`: Your S3 bucket name
     - `GLUE_DATABASE`: Your Glue database name
     - `GLUE_TABLE`: Your Glue table name
     - `AWS_REGION`: Your AWS region
     - `LOG_LEVEL`: "INFO"
     - `BEDROCK_ENABLED`: "true"
     - `BEDROCK_MODEL_ID`: "anthropic.claude-v2:1"
     - `MAX_RETRY_ATTEMPTS`: "3"
     - `CIRCUIT_BREAKER_TIMEOUT`: "300"

## Step 5: Set Up AWS Glue

### 5.1 Create a Glue Database

1. Navigate to **AWS Glue** > **Databases** > **Add database**
   - **Database name**: `data_quality_db`
   - **Description**: Database for data quality check tables
   - Click **Create database**

### 5.2 Set Up Glue Crawler

1. Go to **AWS Glue** > **Crawlers** > **Add crawler**
   - **Crawler name**: `data-quality-crawler`
   - Click **Next**

2. **Choose data sources and classifiers**:
   - Select **S3**
   - **Include path**: `s3://data-quality-bots-<your-account-id>-<region>/input/customers/`
   - Click **Next**

   > **Note**: The crawler will create a table named `customers` based on the last folder in the path. For multiple tables, you would create separate folders (e.g., `customers/`, `orders/`) under the `input/` directory.

3. **Add another data source**:
   - Select **No**
   - Click **Next**

4. **Configure security settings**:
   - **IAM role**: Select an existing IAM role with Glue permissions or create a new one
   - Click **Next**

5. **Set output and scheduling**:
   - **Database**: `data_quality_db`
   - **Table name prefix**: (leave blank)
   - **Crawler schedule**: Select **Run on demand**
   - Click **Next**

6. **Review and create**:
   - Verify all settings
   - Click **Finish**

7. **Run the crawler**:
   - Select the crawler
   - Click **Run crawler**
   - Wait for the status to change to **Ready**

### 5.3 Verify Table Creation

1. Go to **AWS Glue** > **Tables**
2. Verify you see your table (e.g., `customers`)
3. Click on the table to verify schema detection

## Step 6: Configure EventBridge Rule

1. Navigate to **EventBridge** > **Rules** > **Create rule**
   - **Name**: `s3-data-arrival-rule`
   - **Description**: Trigger Lambda when new data arrives in S3
   - **Event bus**: default
   - **Rule type**: Rule with an event pattern
   - Click **Next**

2. **Event pattern**:
   ```json
   {
     "source": ["aws.s3"],
     "detail-type": ["AWS API Call via CloudTrail"],
     "detail": {
       "eventSource": ["s3.amazonaws.com"],
       "eventName": ["PutObject"],
       "requestParameters": {
         "bucketName": ["data-quality-bots-<your-account-id>-<region>"],
         "key": [{"prefix": "input/"}]
       }
     }
   }
   ```
   - Click **Next**

3. **Select targets**:
   - **Target 1**:
     - **Target types**: AWS service
     - **Select a target**: Lambda function
     - **Function**: `data-quality-checker`
   - Click **Next**

4. **Configure tags** (optional) > **Next**
5. **Review and create** > **Create rule**

## Step 7: Test the Deployment

### Test the Titan Agent Directly

1. Navigate to **Amazon Bedrock** > **Agents**
2. Select your `DataQualityAgent`
3. Go to the **Test** tab
4. Enter a test prompt: "Analyze this customer data for quality issues"
5. Verify the agent responds with appropriate analysis

### End-to-End Test

1. Upload a test file to trigger the Lambda function:
   ```bash
   aws s3 cp test_data/sample_customers.csv s3://your-bucket-name/input/customers/
   ```

2. **Monitor Execution**:
   - Check CloudWatch logs for the Lambda function
   - Look for logs related to Bedrock Agent invocation
   - Verify the agent's analysis is included in the output

3. **Verify Output**:
   - Check the S3 reports folder for the analysis output
   - The report should include both data quality metrics and AI-powered insights
   - Look for the `ai_analysis` section in the report JSON

## Step 8: Set Up SNS Notifications (Optional)

1. Navigate to **SNS** > **Topics** > **Create topic**
   - **Type**: Standard
   - **Name**: `data-quality-alerts`
   - Click **Create topic**

2. **Create subscription**:
   - **Protocol**: Email
   - **Endpoint**: your-email@example.com
   - Click **Create subscription**

3. Update your Lambda function to send notifications to this SNS topic

## Step 9: Set Up CloudWatch Dashboard (Optional)

1. Navigate to **CloudWatch** > **Dashboards** > **Create dashboard**
2. Add widgets to monitor:
   - Lambda invocation metrics
   - Error rates
   - Execution duration
   - S3 object counts

## Common Issues and Solutions

### Athena Query Failing
- **Symptom**: Queries fail with permission errors
- **Solution**:
  1. Verify the IAM role has `athena:StartQueryExecution` and `glue:GetTable` permissions
  2. Check the S3 bucket policy allows Athena to write results
  3. Ensure the workgroup's query result location is correctly set

### Glue Crawler Not Detecting Schema
- **Symptom**: Crawler runs but doesn't detect tables
- **Solution**:
  1. Verify the S3 path is correct and accessible
  2. Check if files are in the expected format
  3. Ensure the IAM role has `s3:ListBucket` and `s3:GetObject` permissions

## Troubleshooting

### Common Issues

1. **Titan Agent Connection Issues**:
   - Verify the agent ID and alias ID are correct
   - Check that the agent is in the `PREPARED` or `UPDATING` state
   - Ensure the Lambda's IAM role has `bedrock:InvokeAgent` permission

2. **Lambda Timeout**:
   - Increase the timeout in Lambda configuration (up to 15 minutes)
   - For large datasets, consider processing in smaller batches
   - Enable active tracing in Lambda for better visibility

3. **Permission Issues**:
   - Verify IAM roles have the correct Bedrock permissions
   - Check for resource-based policies on the Bedrock agent
   - Ensure the agent's service role has access to required resources

4. **Agent Response Issues**:
   - Check the agent's CloudWatch logs for errors
   - Verify the input format matches the API schema
   - Test the agent directly in the Bedrock console to isolate issues
4. **Bedrock Access**:
   - Ensure the region supports Bedrock
   - Verify the model ID is correct and accessible

5. **EventBridge Not Triggering**:
   - Check if CloudTrail is enabled in the region
   - Verify the event pattern matches your S3 events
   - Check the EventBridge rule's status (should be enabled)

### Checking Logs

1. **Lambda Logs**:
   - Go to **CloudWatch** > **Log groups** > **/aws/lambda/data-quality-checker**
   - Check the most recent log streams for errors

2. **S3 Access Logs**:
   - If enabled, check the S3 access logs for permission issues

3. **CloudTrail Logs**:
   - Go to **CloudTrail** > **Event history**
   - Filter for the S3 PutObject event to verify it's being captured

### Common Error Messages

- **Access Denied**: Check IAM roles and policies
- **Resource Not Found**: Verify resource names and ARNs
- **Timeout**: Increase Lambda timeout or optimize the function
- **Throttling**: Check service quotas and request rates

## Next Steps

- Implement additional data quality checks
- Set up monitoring and alerting
- Create additional test cases
- Implement error handling and retries

## Cleanup

To avoid unnecessary charges, remember to delete all resources when you're done testing:

1. Delete the S3 bucket and all its contents
2. Delete the Lambda function
3. Delete the IAM roles and policies
4. Delete the Glue database and tables
5. Delete the EventBridge rule
6. Delete any CloudWatch log groups
7. Delete any SNS topics and subscriptions
