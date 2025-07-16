# Lambda Function Execution Flow

This document outlines the step-by-step execution flow of the Data Quality Checker Lambda function.

## Table of Contents
1. [Initialization](#initialization)
2. [Event Processing](#event-processing)
3. [Data Quality Check Execution](#data-quality-check-execution)
4. [Report Generation](#report-generation)
5. [Error Handling](#error-handling)
6. [Cleanup](#cleanup)

## Initialization

1. **Environment Variables**
   - Loads required environment variables:
     - `S3_BUCKET`: Target S3 bucket for storing reports
     - `SNS_TOPIC_ARN`: ARN for SNS notifications (optional)
     - `DEFAULT_DATABASE`: Default Glue database name
     - `BEDROCK_MODEL_ID`: ID of the Bedrock model to use
     - `LOG_LEVEL`: Logging verbosity level
     - `ENABLE_AI_ANALYSIS`: Flag to enable/disable AI analysis

2. **Logging Setup**
   - Configures logging with the specified log level
   - Sets up log format and handlers

## Event Processing

1. **Input Validation**
   - Validates the incoming event object
   - Extracts and validates required parameters:
     - `database`: Source database name
     - `table`: Source table name
   - Applies default values if parameters are not provided

2. **AWS Session Initialization**
   - Creates a boto3 session with the specified region
   - Initializes AWS service clients (S3, Glue, Athena, SNS, Bedrock)

## Data Quality Check Execution

1. **Table Metadata Retrieval**
   - Fetches table metadata from AWS Glue Data Catalog
   - Retrieves column definitions and table properties

2. **Data Sampling**
   - Executes Athena query to sample data from the table
   - Applies sampling logic if configured

3. **Quality Checks**
   Performs the following data quality checks:
   - **Schema Validation**
     - Verifies column data types
     - Checks for required columns
   - **Data Completeness**
     - Identifies NULL values
     - Checks for empty strings
   - **Data Validity**
     - Validates data against expected patterns
     - Checks for out-of-range values
   - **Uniqueness**
     - Identifies duplicate records
   - **Referential Integrity**
     - Validates foreign key relationships (if configured)
   - **Custom Rules**
     - Applies any user-defined validation rules

4. **AI-Powered Analysis** (if enabled)
   - Sends data samples to Amazon Bedrock for analysis
   - Processes AI-generated insights about data quality
   - Identifies potential data anomalies

## Report Generation

1. **Report Creation**
   - Compiles results of all quality checks
   - Calculates overall data quality score
   - Generates detailed metrics for each check

2. **Report Storage**
   - Creates a timestamped directory in S3
   - Saves the report in JSON format
   - Example path: `s3://{bucket}/reports/{database}/{table}/{timestamp}/report.json`

3. **Notification**
   - If SNS topic is configured:
     - Sends success/failure notification
     - Includes report location and summary

## Error Handling

1. **Input Validation Errors**
   - Logs detailed error messages
   - Returns 400 status code with error details

2. **Data Quality Check Failures**
   - Captures and logs all validation errors
   - Continues execution to complete all checks
   - Includes all failures in the final report

3. **Unexpected Errors**
   - Logs stack trace for debugging
   - Sends error notification (if SNS is configured)
   - Returns 500 status code with error details

## Cleanup

1. **Resource Release**
   - Closes any open database connections
   - Releases AWS resources
   - Cleans up temporary files

2. **Logging**
   - Ensures all log messages are flushed
   - Closes log handlers

## Example Event Payload

```json
{
  "database": "your_database_name",
  "table": "your_table_name",
  "sample_size": 1000,
  "enable_ai_analysis": true
}
```

## Output Format

```json
{
  "statusCode": 200,
  "body": {
    "status": "success",
    "report_location": "s3://bucket/reports/db/table/timestamp/report.json",
    "execution_summary": {
      "total_checks": 10,
      "passed_checks": 8,
      "failed_checks": 2,
      "quality_score": 80.0
    }
  }
}
```

## Monitoring

- **CloudWatch Metrics**
  - Execution duration
  - Error rates
  - Data quality scores

- **CloudWatch Logs**
  - Detailed execution logs
  - Error traces
  - Performance metrics

## Security Considerations

- Uses IAM roles for AWS service access
- Encrypts sensitive data in transit and at rest
- Follows principle of least privilege for IAM policies
- Logs all significant operations for audit purposes
