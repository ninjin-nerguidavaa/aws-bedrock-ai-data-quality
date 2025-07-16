# Lambda Function Execution Flow

This document outlines the step-by-step execution flow of the Data Quality Checker Lambda function, including AI-powered analysis using Amazon Bedrock.

## Table of Contents
1. [Initialization](#initialization)
2. [Handler Execution](#handler-execution)
3. [Event Processing](#event-processing)
4. [Data Quality Check Execution](#data-quality-check-execution)
5. [AI-Powered Analysis](#ai-powered-analysis)
6. [Report Generation](#report-generation)
7. [Error Handling](#error-handling)
8. [Cleanup](#cleanup)

## Initialization

1. **Environment Variables**
   - Loads required environment variables:
     - `S3_BUCKET`: Target S3 bucket for storing reports (required)
     - `SNS_TOPIC_ARN`: ARN for SNS notifications (optional)
     - `GLUE_DATABASE`: Source Glue database name (required)
     - `GLUE_TABLE`: Source Glue table name (required)
     - `BEDROCK_ENABLED`: Flag to enable/disable Bedrock AI analysis ('true' or 'false')
     - `BEDROCK_MODEL_ID`: ID of the Amazon Titan model to use (default: 'amazon.titan-text-express-v1')
     - `AWS_REGION`: AWS region for service clients (default: 'us-east-1')
     - `LOG_LEVEL`: Logging verbosity level (default: 'INFO')

2. **Logging Setup**
   - Configures logging with the specified log level
   - Sets up log format and handlers

## Handler Execution

1. **Synchronous Wrapper**
   - The Lambda handler (`lambda_handler`) serves as a synchronous wrapper
   - Creates and runs an asyncio event loop
   - Delegates to the main async handler (`async_lambda_handler`)
   - Handles any uncaught exceptions
   - Returns standardized response format

2. **Async Handler**
   - Validates required environment variables
   - Initializes AWS service clients
   - Executes the data quality check pipeline
   - Returns results to the synchronous wrapper

## Event Processing

1. **Input Validation**
   - Validates the incoming event object
   - Extracts and validates required parameters:
     - `database`: Source database name (falls back to GLUE_DATABASE env var)
     - `table`: Source table name (falls back to GLUE_TABLE env var)
   - Validates database and table names match Glue catalog
   - Applies default values if parameters are not provided

2. **AWS Service Initialization**
   - Creates boto3 clients with error handling:
     - AWS Glue (for table metadata)
     - Amazon Athena (for data sampling)
     - Amazon S3 (for report storage)
     - Amazon SNS (for notifications)
     - Amazon Bedrock Runtime (if AI analysis enabled)
   - Configures retry policies and timeouts

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

## AI-Powered Analysis

1. **Conditional Execution**
   - Only executes if `BEDROCK_ENABLED` is 'true'
   - Validates Bedrock model ID is an Amazon Titan model
   - Skips if validation fails (with warning)

2. **Data Preparation**
   - Samples data for AI analysis
   - Formats data into a prompt for the model
   - Includes schema and statistical information

3. **Bedrock API Integration**
   - Invokes the specified Amazon Titan model
   - Implements exponential backoff for rate limiting
   - Handles API timeouts and errors gracefully

4. **Insight Processing**
   - Parses model response
   - Extracts structured insights
   - Validates and formats insights for the report
   - Includes model metadata and confidence scores

5. **Error Handling**
   - Continues execution if AI analysis fails
   - Logs detailed error information
   - Includes error details in the final report

## Report Generation

1. **Report Creation**
   - Compiles results of all quality checks
   - Calculates overall data quality score
   - Includes detailed metrics for each check
   - Adds AI-powered insights (if enabled)
   - Includes execution metadata and timing information

2. **Report Structure**
   ```json
   {
     "status": "SUCCESS|FAILED|PARTIAL",
     "database": "database_name",
     "table": "table_name",
     "timestamp": "ISO-8601 timestamp",
     "execution_summary": {
       "total_time_seconds": 0.0,
       "checks_performed": 0,
       "checks_passed": 0,
       "checks_failed": 0,
       "quality_score": 0.0
     },
     "profile": {
       "row_count": 0,
       "column_count": 0,
       "columns": {
         "column_name": {
           "dtype": "data_type",
           "null_percentage": 0.0,
           "unique_percentage": 0.0,
           "sample_values": [],
           "stats": {}
         }
       }
     },
     "ai_analysis": {
       "enabled": true,
       "model_id": "amazon.titan-text-express-v1",
       "insights": "AI-generated insights text",
       "analysis_time_seconds": 0.0
     }
   }
   ```

3. **Report Storage**
   - Creates a timestamped directory in S3 (format: `YYYYMMDD_HHMMSS`)
   - Saves the report in JSON format with pretty-printing
   - Example path: `s3://{bucket}/reports/{database}/{table}/{timestamp}/report.json`
   - Sets appropriate content type and metadata

4. **Notification**
   - If SNS topic is configured:
     - Sends success/failure notification
     - Includes report location and summary
     - Includes execution status and quality score
     - Includes direct S3 pre-signed URL (if configured)

## Error Handling

1. **Input Validation Errors**
   - Validates all required parameters
   - Returns 400 status code with error details
   - Logs validation failures with context

2. **Data Quality Check Failures**
   - Continues execution after check failures
   - Captures detailed error information
   - Includes failure context in the report
   - Updates overall status to 'PARTIAL' for partial failures

3. **AWS Service Errors**
   - Implements retry logic with exponential backoff
   - Handles throttling and service limits
   - Includes service-specific error details in logs

4. **AI Analysis Errors**
   - Gracefully handles Bedrock API failures
   - Continues execution without AI insights
   - Includes error details in the report
   - Logs detailed diagnostic information

5. **Unexpected Errors**
   - Captures and logs stack traces
   - Sends error notification (if SNS is configured)
   - Returns appropriate HTTP status codes
   - Includes error details in the response

## Cleanup

1. **Resource Release**
   - Closes any open database connections
   - Releases AWS resources
   - Cleans up temporary files

2. **Logging**
   - Ensures all log messages are flushed
   - Closes log handlers

## Example Event Payloads

### Direct Invocation
```json
{
  "database": "your_database_name",
  "table": "your_table_name",
  "sample_size": 1000,
  "enable_ai_analysis": true,
  "additional_parameters": {}
}
```

### S3 Event Trigger
```json
{
  "Records": [
    {
      "eventSource": "aws:s3",
      "s3": {
        "bucket": {
          "name": "source-bucket"
        },
        "object": {
          "key": "path/to/table/data.parquet"
        }
      }
    }
  ]
}
```

### Scheduled Event
```json
{
  "source": "aws.events",
  "detail-type": "Scheduled Event",
  "resources": ["arn:aws:events:region:account-id:rule/rule-name"],
  "detail": {}
}
```

## Output Format

### Successful Execution
```json
{
  "statusCode": 200,
  "body": {
    "status": "SUCCESS",
    "report_location": "s3://bucket/reports/db/table/20250101_123456/report.json",
    "execution_summary": {
      "total_checks": 15,
      "passed_checks": 14,
      "failed_checks": 1,
      "quality_score": 93.3,
      "execution_time_seconds": 12.45,
      "ai_analysis": {
        "enabled": true,
        "model_id": "amazon.titan-text-express-v1",
        "analysis_time_seconds": 3.21
      }
    },
    "warnings": [
      "High null percentage (15.2%) in column 'customer_email'"
    ]
  }
}
```

### Error Response
```json
{
  "statusCode": 400,
  "body": {
    "status": "ERROR",
    "error_type": "ValidationError",
    "message": "Missing required parameter: 'table'",
    "details": {
      "required_parameters": ["database", "table"],
      "provided_parameters": {
        "database": "sales_db"
      }
    },
    "timestamp": "2025-01-01T12:34:56Z"
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
