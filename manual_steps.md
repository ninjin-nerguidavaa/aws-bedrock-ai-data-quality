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
11. [Troubleshooting](#troubleshooting)
12. [Maintenance and Operations](#maintenance-and-operations)

## Prerequisites

Before you begin, ensure you have the following:

### AWS Account Requirements
- AWS Account with AdministratorAccess or equivalent permissions
- AWS CLI configured with credentials
- Default VPC and subnets in your preferred region

### Local Development Environment
- Python 3.8 or later
- pip (Python package manager)
- Git (for cloning the repository)
- AWS CLI v2

### Project Files
- Clone the repository:
  ```bash
  git clone https://github.com/your-org/aws-data-quality-bots.git
  cd aws-data-quality-bots
  ```
- Sample test data is available in the `test_data/` directory

## Architecture Overview

The AWS Data Quality Bots solution consists of the following components:

1. **S3 Buckets**: Store input data, processed results, and reports
2. **AWS Lambda**: Serverless function that processes data quality checks
3. **AWS Glue**: Data catalog and ETL service for data discovery and preparation
4. **Amazon Bedrock**: AI service for intelligent data quality analysis
5. **Amazon EventBridge**: Triggers the Lambda function on S3 upload events
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
4. Click **Next**
5. Role name: `DataQualityLambdaRole`
6. Click **Create role**

### Create IAM Policy for Bedrock Access

1. In IAM, go to **Policies** > **Create policy**
2. Select the **JSON** tab and paste:
   ```json
   {
       "Version": "2012-10-17",
       "Statement": [
           {
               "Effect": "Allow",
               "Action": [
                   "bedrock:InvokeModel",
                   "bedrock:InvokeModelWithResponseStream",
                   "bedrock:ListFoundationModels"
               ],
               "Resource": "*"
           }
       ]
   }
   ```
3. Click **Next: Tags** > **Next: Review**
4. Name: `BedrockAccessPolicy`
5. Click **Create policy**
6. Attach this policy to your `DataQualityLambdaRole`

## Step 4: Deploy Lambda Function

### Create Lambda Layer

1. **Build the Layer Package**:
   ```bash
   cd aws-data-quality-bots
   python3 scripts/build_layer.py
   ```
   This will create the layer package at `build/layer/data-quality-deps.zip`

2. **Upload to AWS**:
   - Go to AWS Lambda Console → Layers → Create Layer
   - Configure the layer:
     - Name: `data-quality-deps`
     - Upload the ZIP file: `build/layer/data-quality-deps.zip`
     - Select Python 3.9 as the compatible runtime
     - Add Python 3.9 as a compatible architecture (x86_64)
   - Click **Create** and note the Layer ARN

### Create Lambda Function

1. Navigate to **Lambda** > **Create function**
2. Select **Author from scratch**
3. Configure basic settings:
   - **Function name**: `data-quality-processor`
   - **Runtime**: Python 3.9
   - **Architecture**: x86_64
   - **Permissions**: Use an existing role (select the role created in Step 3)

### Add Layer to Lambda Function

1. In your Lambda function, go to the **Layers** section
2. Click **Add a layer**
3. Select **Custom layers**
4. Choose the `data-quality-deps` layer you created
5. Select the latest version
6. Click **Add**

3. **Upload Lambda Code**:
   - In the **Code** tab, click **Upload from** and select **.zip file**
   - Upload a zip file containing only your Lambda function code (without dependencies):
     ```bash
     cd aws-data-quality-bots/lambda_functions/data_quality_checker
     zip -r ../../../lambda_code.zip . -x "*__pycache__*"
     ```
   - Or use the inline editor to paste the code from `lambda_function.py`

4. **Configure Basic Settings**:
   - **Handler**: `lambda_function.lambda_handler`
   - **Runtime**: Python 3.9
   - **Architecture**: x86_64
   - **Memory**: 1024 MB
   - **Timeout**: 5 minutes
   - **Execution role**: Choose the IAM role created earlier

5. **Add Environment Variables**:
   - `S3_BUCKET`: `data-quality-bots-<your-account-id>-<region>`
   - `S3_INPUT_PREFIX`: `input/`
   - `S3_OUTPUT_PREFIX`: `output/`
   - `S3_REPORT_PREFIX`: `reports/`
   - `GLUE_DATABASE`: `data_quality_db`
   - `GLUE_TABLE`: `customers`
   - `ATHENA_OUTPUT_LOCATION`: `s3://data-quality-bots-<your-account-id>-<region>/athena-results/`

6. **Add the Lambda Layer**:
   - In the Lambda function page, scroll down to the **Layers** section
   - Click **Add a layer**
   - Select **Custom layers**
   - Choose the `data-quality-deps` layer you created
   - Select the latest version
   - Click **Add**

7. Click **Deploy** to save your changes

## Step 5: Create Glue Database and Table

1. Navigate to **AWS Glue** > **Databases** > **Add database**
   - **Database name**: `data_quality_db`
   - Click **Create database**

2. Go to **Tables** > **Add table**
   - **Table name**: `customers`
   - **Database**: `data_quality_db`
   - Click **Next**
   - **Data store**: S3
   - **Location of dataset**: `s3://data-quality-bots-<your-account-id>-<region>/input/customers/`
   - **Data format**: CSV
   - **Has column headers**: Yes
   - **Delimiter**: Comma (,)
   - Click **Next**
   - Click **Next** (skip classification)
   - Review schema and click **Finish**

## Step 6: Set Up EventBridge Rule

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

## Step 7: Test the Setup

1. Upload a test file to trigger the Lambda:
   ```bash
   aws s3 cp test_data/sample_customers.csv s3://data-quality-bots-<your-account-id>-<region>/input/customers/sample_test.csv
   ```

2. Monitor the Lambda function:
   - Go to **Lambda** > **Functions** > **data-quality-checker** > **Monitor** > **Logs**

3. Check the output in S3:
   - Reports: `s3://data-quality-bots-<your-account-id>-<region>/reports/`
   - Processed data: `s3://data-quality-bots-<your-account-id>-<region>/output/`

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

## Troubleshooting

### Common Issues and Solutions

1. **Lambda Permissions**:
   - Verify the execution role has all necessary permissions
   - Check CloudWatch Logs for errors

2. **S3 Permissions**:
   - Ensure the bucket policy allows the Lambda role to read/write
   - Check for any S3 bucket encryption issues

3. **Glue/Athena**:
   - Verify the Glue table schema matches your CSV
   - Check Athena query results for data quality issues

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
