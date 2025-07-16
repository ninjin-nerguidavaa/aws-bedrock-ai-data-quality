import os
import json
import time
import logging
import boto3
import pandas as pd
import awswrangler as wr
from typing import Dict, Any, List, Optional
from datetime import datetime
from botocore.config import Config
import asyncio

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_bedrock_client():
    """Initialize and return a Bedrock runtime client"""
    config = Config(
        region_name=os.environ.get('AWS_REGION', 'us-east-1'),
        retries={
            'max_attempts': 5,
            'mode': 'standard'
        }
    )
    return boto3.client('bedrock-runtime', config=config)

def validate_bedrock_model_id(model_id: str) -> bool:
    """Validate that only Amazon Titan models are used"""
    return model_id.startswith('amazon.titan-')

async def analyze_with_bedrock(data_profile: dict, sample_data: pd.DataFrame) -> dict:
    """Analyze data profile using Amazon Bedrock's Titan model"""
    try:
        bedrock = get_bedrock_client()
        
        # Convert sample data to a readable format
        sample_str = sample_data.head(10).to_string()
        
        # Prepare the prompt for Amazon Titan
        prompt = f"""You are a data quality analyst. Analyze this data profile and provide insights:

Data Profile:
{json.dumps(data_profile, indent=2)}

Sample Data:
{sample_str}

Provide a structured analysis with these sections:
1. Data Quality Summary
2. Key Findings
3. Recommendations for Improvement
4. Potential Data Issues
"""
        
        # Prepare the request for Amazon Titan
        body = {
            "inputText": prompt,
            "textGenerationConfig": {
                "maxTokenCount": 1024,
                "temperature": 0.2,
                "topP": 0.9
            }
        }
        
        model_id = os.environ.get('BEDROCK_MODEL_ID', 'amazon.titan-text-express-v1')
        if not validate_bedrock_model_id(model_id):
            raise ValueError("Only Amazon Titan models are supported")
        
        # Call Bedrock with Amazon Titan model
        response = bedrock.invoke_model(
            modelId=model_id,
            body=json.dumps(body)
        )
        
        # Parse the response
        response_body = json.loads(response['body'].read().decode('utf-8'))
        insights = response_body.get('results', [{}])[0].get('outputText', 'No insights generated')
        
        return {
            'insights': insights,
            'model_used': model_id,
            'model_provider': 'Amazon Titan'
        }
        
    except Exception as e:
        logger.error(f"Error in Bedrock analysis: {str(e)}")
        return {'error': str(e)}

def send_notification(sns_topic_arn: str, message: str, subject: str = "Data Quality Check Results") -> None:
    """Send notification via SNS"""
    if not sns_topic_arn:
        return
        
    try:
        sns = boto3.client('sns')
        sns.publish(
            TopicArn=sns_topic_arn,
            Message=message,
            Subject=subject
        )
        logger.info("Notification sent successfully")
    except Exception as e:
        logger.error(f"Failed to send notification: {str(e)}")

def get_data_profile(df: pd.DataFrame) -> Dict[str, Any]:
    """Generate a data profile for the DataFrame"""
    profile = {
        'row_count': len(df),
        'column_count': len(df.columns),
        'columns': {}
    }
    
    for col in df.columns:
        col_data = df[col]
        null_count = col_data.isnull().sum()
        unique_count = col_data.nunique()
        
        col_profile = {
            'dtype': str(col_data.dtype),
            'null_count': int(null_count),
            'null_percentage': float(null_count / len(df) * 100) if len(df) > 0 else 0,
            'unique_count': int(unique_count),
            'unique_percentage': float(unique_count / len(df) * 100) if len(df) > 0 else 0,
        }
        
        # Add statistics for numeric columns
        if pd.api.types.is_numeric_dtype(col_data):
            col_profile['stats'] = {
                'min': float(col_data.min()) if not col_data.empty else None,
                'max': float(col_data.max()) if not col_data.empty else None,
                'mean': float(col_data.mean()) if not col_data.empty else None,
                'std': float(col_data.std()) if not col_data.empty else None
            }
            
        profile['columns'][col] = col_profile
    
    return profile

def run_data_quality_checks(df: pd.DataFrame, profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Run data quality checks on the DataFrame"""
    checks = []
    
    # Check for null values
    for col, col_profile in profile['columns'].items():
        if col_profile['null_count'] > 0:
            checks.append({
                'check_name': 'null_values_check',
                'column': col,
                'status': 'WARNING' if col_profile['null_percentage'] < 20 else 'ERROR',
                'message': f"Found {col_profile['null_count']} null values ({col_profile['null_percentage']:.1f}%)",
                'threshold': '0%'
            })
    
    # Add more checks as needed
    
    return checks

def generate_report(result: Dict[str, Any]) -> str:
    """Generate a human-readable report from the results"""
    report = [
        f"# Data Quality Report",
        f"**Database:** {result.get('database', 'N/A')}",
        f"**Table:** {result.get('table', 'N/A')}",
        f"**Status:** {result.get('status', 'UNKNOWN')}",
        f"**Timestamp:** {result.get('timestamp', 'N/A')}",
        ""
    ]
    
    # Add execution summary
    exec_summary = result.get('execution_summary', {})
    if exec_summary:
        report.append("## Execution Summary")
        report.append(f"- **Total Rows Processed:** {exec_summary.get('rows_processed', 0):,}")
        report.append(f"- **Total Time:** {exec_summary.get('total_time_seconds', 0):.2f} seconds")
        report.append("")
    
    # Add AI analysis if available
    if 'ai_analysis' in result and 'insights' in result['ai_analysis']:
        report.append("## AI-Powered Analysis")
        report.append(result['ai_analysis']['insights'])
        report.append("")
    
    # Add data profile summary
    if 'profile' in result:
        report.append("## Data Profile")
        report.append(f"- **Total Rows:** {result['profile'].get('row_count', 0):,}")
        report.append(f"- **Total Columns:** {result['profile'].get('column_count', 0)}")
        report.append("")
        
        # Add column statistics
        report.append("### Column Statistics")
        for col, stats in result['profile'].get('columns', {}).items():
            report.append(f"#### {col}")
            report.append(f"- **Type:** {stats.get('dtype', 'N/A')}")
            report.append(f"- **Null Values:** {stats.get('null_count', 0):,} ({stats.get('null_percentage', 0):.1f}%)")
            report.append(f"- **Unique Values:** {stats.get('unique_count', 0):,} ({stats.get('unique_percentage', 0):.1f}%)")
            
            # Add numeric stats if available
            if 'stats' in stats:
                num_stats = stats['stats']
                report.append("- **Statistics:**")
                for stat, val in num_stats.items():
                    if val is not None:
                        report.append(f"  - {stat.title()}: {val:.2f}")
    
    # Add data quality issues
    checks = result.get('checks', [])
    if checks:
        report.append("\n## Data Quality Issues")
        for check in checks:
            status_emoji = "❌" if check.get('status') == 'ERROR' else "⚠️"
            report.append(
                f"{status_emoji} **{check.get('check_name', 'Unknown Check')}** - "
                f"{check.get('message', 'No details available')}"
            )
    
    return "\n".join(report)

async def check_data_quality(database: str, table: str, s3_bucket: str) -> Dict[str, Any]:
    """Perform data quality checks on the specified table"""
    result = {
        'status': 'SUCCESS',
        'timestamp': datetime.utcnow().isoformat(),
        'database': database,
        'table': table,
        'checks': [],
        'profile': {},
        'execution_summary': {}
    }
    
    start_time = time.time()
    
    try:
        # Step 1: Verify table exists
        if not wr.catalog.does_table_exist(database=database, table=table):
            raise ValueError(f"Table {database}.{table} does not exist")
        
        # Step 2: Sample data from the table
        logger.info(f"Sampling data from {database}.{table}")
        df = wr.athena.read_sql_query(
            f"SELECT * FROM {database}.{table} LIMIT 1000",
            database=database,
            ctas_approach=False
        )
        
        if df.empty:
            raise ValueError("No data found in the table")
        
        # Step 3: Generate data profile
        logger.info("Generating data profile")
        profile = get_data_profile(df)
        result['profile'] = profile
        
        # Step 4: Run data quality checks
        logger.info("Running data quality checks")
        checks = run_data_quality_checks(df, profile)
        result['checks'] = checks
        
        # Step 5: Run AI analysis if enabled
        if os.environ.get('BEDROCK_ENABLED', '').lower() == 'true':
            logger.info("Running AI-powered analysis")
            try:
                bedrock_analysis = await analyze_with_bedrock(profile, df)
                result['ai_analysis'] = bedrock_analysis
            except Exception as e:
                logger.error(f"AI analysis failed: {str(e)}")
                result['ai_analysis'] = {'error': str(e)}
        
        # Update execution summary
        result['execution_summary'] = {
            'rows_processed': len(df),
            'total_time_seconds': time.time() - start_time,
            'checks_performed': len(checks),
            'checks_failed': len([c for c in checks if c.get('status') == 'ERROR']),
            'checks_warning': len([c for c in checks if c.get('status') == 'WARNING'])
        }
        
        # Update status based on checks
        if any(check.get('status') == 'ERROR' for check in checks):
            result['status'] = 'FAILED'
        elif any(check.get('status') == 'WARNING' for check in checks):
            result['status'] = 'WARNING'
        
        return result
        
    except Exception as e:
        logger.error(f"Error in check_data_quality: {str(e)}")
        result.update({
            'status': 'FAILED',
            'error': str(e),
            'execution_summary': {
                'total_time_seconds': time.time() - start_time,
                'error': str(e)
            }
        })
        return result

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Synchronous Lambda handler that wraps the async handler"""
    return asyncio.get_event_loop().run_until_complete(async_lambda_handler(event, context))

async def async_lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Async Lambda handler for data quality checks"""
    try:
        # Get configuration from environment variables
        s3_bucket = os.environ.get('S3_BUCKET')
        if not s3_bucket:
            raise ValueError("S3_BUCKET environment variable is required")
            
        sns_topic_arn = os.environ.get('SNS_TOPIC_ARN', '')
        database = event.get('database', os.environ.get('GLUE_DATABASE'))
        table = event.get('table', os.environ.get('GLUE_TABLE'))
        
        if not database or not table:
            raise ValueError("Both database and table must be provided either in the event or as environment variables")
        
        # Run data quality checks
        result = await check_data_quality(database, table, s3_bucket)
        
        # Generate report
        report = generate_report(result)
        
        # Upload report to S3
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        report_key = f"reports/{database}/{table}/{timestamp}/report.json"
        
        # Create a temporary file to store the JSON
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.json') as temp_file:
            # Write the result as JSON to the temp file
            json.dump(result, temp_file, default=str)
            temp_file.flush()
            
            # Upload the file to S3
            wr.s3.upload(
                local_file=temp_file.name,
                path=f"s3://{s3_bucket}/{report_key}"
            )
        
        # Send notification if SNS topic is configured
        if sns_topic_arn:
            send_notification(
                sns_topic_arn,
                f"Data quality check completed for {database}.{table}\nStatus: {result['status']}\n"
                f"Report: s3://{s3_bucket}/{report_key}"
            )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'status': 'success',
                'report_location': f"s3://{s3_bucket}/{report_key}",
                'execution_summary': result.get('execution_summary', {})
            })
        }
        
    except Exception as e:
        error_msg = f"Error in lambda_handler: {str(e)}"
        logger.error(error_msg)
        
        # Send error notification if SNS topic is configured
        if sns_topic_arn:
            send_notification(
                sns_topic_arn,
                f"Data quality check failed: {str(e)}",
                "Data Quality Check Failed"
            )
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Failed to process data quality check',
                'details': str(e)
            })
        }
