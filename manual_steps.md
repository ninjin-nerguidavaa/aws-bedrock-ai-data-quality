# AWS Data Quality Bots - Manual Setup Guide

This document provides step-by-step instructions to manually set up the AWS Data Quality Bots project using the AWS Management Console.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Step 1: Create S3 Buckets](#step-1-create-s3-buckets)
3. [Step 2: Upload Sample Data](#step-2-upload-sample-data)
4. [Step 3: Create IAM Roles and Policies](#step-3-create-iam-roles-and-policies)
5. [Step 4: Create Lambda Function](#step-4-create-lambda-function)
6. [Step 5: Create Glue Database and Table](#step-5-create-glue-database-and-table)
7. [Step 6: Set Up EventBridge Rule](#step-6-set-up-eventbridge-rule)
8. [Step 7: Test the Setup](#step-7-test-the-setup)
9. [Step 8: Set Up SNS Notifications (Optional)](#step-8-set-up-sns-notifications-optional)
10. [Step 9: Set Up CloudWatch Dashboard (Optional)](#step-9-set-up-cloudwatch-dashboard-optional)
11. [Troubleshooting](#troubleshooting)

## Prerequisites

- AWS Account with appropriate permissions
- AWS CLI configured with your credentials
- Python 3.8+ installed locally
- Sample test data (in the `test_data/` directory)

## Step 1: Create S3 Buckets

1. **Log in** to the AWS Management Console
2. Navigate to **S3** service
3. Click **Create bucket**
   - **Bucket name**: `data-quality-bots-<your-account-id>-<region>` (must be globally unique)
   - **Region**: Select your preferred region
   - **Block Public Access**: Keep all settings enabled
   - **Bucket Versioning**: Enable
   - **Default encryption**: Enable (SSE-S3 or KMS)
   - Click **Create bucket**

4. Create the following folders in your bucket:
   - `input/` - For source data
   - `output/` - For processed results
   - `reports/` - For data quality reports
   - `scripts/` - For Lambda function code

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

## Step 4: Create Lambda Function

1. Navigate to **Lambda** > **Create function**
2. Select **Author from scratch**
   - **Function name**: `data-quality-checker`
   - **Runtime**: Python 3.9
   - **Architecture**: x86_64
   - **Permissions**: Use an existing role
   - **Existing role**: Select `DataQualityLambdaRole`
   - Click **Create function**

3. In the **Code** tab:
   - Upload your Lambda function code (zip file containing `lambda_function.py` and dependencies)
   - Or use the inline editor to paste the code

4. **Basic Settings**:
   - **Handler**: `lambda_function.lambda_handler`
   - **Memory**: 1024 MB
   - **Timeout**: 5 minutes

5. **Environment Variables**:
   - Add the following:
     - `S3_BUCKET`: `data-quality-bots-<your-account-id>-<region>`
     - `S3_INPUT_PREFIX`: `input/`
     - `S3_OUTPUT_PREFIX`: `output/`
     - `S3_REPORT_PREFIX`: `reports/`
     - `GLUE_DATABASE`: `data_quality_db`
     - `GLUE_TABLE`: `customers`
     - `ATHENA_OUTPUT_LOCATION`: `s3://data-quality-bots-<your-account-id>-<region>/athena-results/`

6. Click **Save**

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
