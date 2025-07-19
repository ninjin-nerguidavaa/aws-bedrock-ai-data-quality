import os
import boto3
import json
import logging
import os
import time
import traceback
import uuid
import asyncio
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import awswrangler as wr
import pandas as pd
from botocore.exceptions import ClientError
from botocore.config import Config
import asyncio
from enum import Enum

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_bedrock_agent_client():
    """Initialize and return a Bedrock Agent Runtime client"""
    config = Config(
        region_name=os.environ.get('AWS_REGION', 'us-east-1'),
        retries={
            'max_attempts': 5,
            'mode': 'standard'
        }
    )
    return boto3.client('bedrock-agent-runtime', config=config)

class AnalysisType(Enum):
    DATA_QUALITY = "data_quality"
    ANOMALY_DETECTION = "anomaly_detection"
    DATA_DRIFT = "data_drift"
    SCHEMA_VALIDATION = "schema_validation"

async def analyze_with_titan_agent(profile: Dict[str, Any], df: pd.DataFrame, 
                                 analysis_type: AnalysisType = AnalysisType.DATA_QUALITY) -> Dict[str, Any]:
    """
    Analyze data using Claude 2.1 model.
    
    Args:
        profile: Data profile dictionary
        df: Input DataFrame
        analysis_type: Type of analysis to perform
        
    Returns:
        Dictionary containing analysis results
    """
    try:
        # Initialize Bedrock client for Claude 2.1
        bedrock_runtime = boto3.client('bedrock-runtime')
        
        # Prepare the prompt for Claude 2.1
        prompt = f"""
        <task>
        Perform {analysis_type.value.upper()} analysis on this dataset.
        
        <context>
        Data Profile:
        - Rows: {profile.get('row_count', 0):,}
        - Columns: {profile.get('column_count', 0):,}
        - Column Names: {', '.join(profile.get('columns', {}).keys())}
        
        Sample Data (first 5 rows):
        {json.dumps(df.head(5).to_dict(orient='records') if not df.empty else [], indent=2)}
        
        Analysis Focus:
        {"Data Quality: Check for missing values, outliers, inconsistencies, and data type issues" 
         if analysis_type == AnalysisType.DATA_QUALITY 
         else "Anomaly Detection: Identify unusual patterns, outliers, and potential data quality issues"}
        </context>
        
        <output_format>
        # {analysis_type.value.replace('_', ' ').title()} Analysis Report
        
        ## 1. Key Findings
        - [Summary of main findings]
        
        ## 2. Issues Detected
        - [List of specific issues found]
        
        ## 3. Impact Assessment
        - [Impact of each issue on data quality]
        
        ## 4. Recommendations
        - [Actionable recommendations]
        
        ## 5. Confidence Score
        - Overall confidence: [0-1]
        </output_format>
        
        Please provide a detailed analysis following the output format above.
        """
        
        logger.info(f"Prepared prompt for {analysis_type.value} analysis")
        
        # Calculate basic statistics for numeric columns
        stats = {}
        for col in df.select_dtypes(include=['number']).columns:
            stats[col] = {
                'mean': float(df[col].mean()),
                'std': float(df[col].std()),
                'min': float(df[col].min()),
                'max': float(df[col].max()),
                'null_count': int(df[col].isnull().sum())
            }
        
        # Prepare context for the agent
        context = {
            'analysis_type': analysis_type.value,
            'profile_summary': {
                'row_count': profile.get('row_count', 0),
                'column_count': profile.get('column_count', 0),
                'columns': list(profile.get('columns', {}).keys()),
                'column_statistics': stats
            },
            'sample_data': df.head(5).to_dict(orient='records') if not df.empty else []
        }
        
        # Invoke Claude 2.1 model
        try:
            response = bedrock_runtime.invoke_model(
                modelId='anthropic.claude-v2:1',
                contentType='application/json',
                accept='application/json',
                body=json.dumps({
                    'prompt': f"\n\nHuman: {prompt.strip()}\n\nAssistant:",
                    'max_tokens_to_sample': 4000,
                    'temperature': 0.2,
                    'top_p': 0.9,
                    'stop_sequences': ['\n\nHuman:']
                })
            )
            
            # Parse the response
            response_body = json.loads(response['body'].read().decode('utf-8'))
            completion = response_body['completion']
            
            logger.info("Successfully received response from Claude 2.1")
            
            return {
                'status': 'success',
                'analysis_type': analysis_type.value,
                'insights': completion.strip(),
                'statistics': stats,  # Include calculated statistics in the response
                'generated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
            }
            
        except Exception as e:
            error_msg = f"Error invoking Claude 2.1: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'status': 'error',
                'analysis_type': analysis_type.value,
                'error': error_msg,
                'generated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
            }
            
    except Exception as e:
        error_msg = f"Error in analyze_with_titan_agent: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'status': 'error',
            'analysis_type': analysis_type.value,
            'error': error_msg,
            'stack_trace': traceback.format_exc(),
            'generated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        }

class BedrockAgent:
    # Class-level circuit breaker state
    _circuit_open = False
    _circuit_reset_time = 0
    CIRCUIT_RESET_TIMEOUT = 300  # 5 minutes in seconds
    
    def __init__(self, agent_id: str, agent_alias_id: Optional[str] = None):
        """
        Initialize the Bedrock Agent client with circuit breaker pattern
        
        Args:
            agent_id: The ID of the Bedrock agent
            agent_alias_id: Optional alias ID. If not provided, will use the default alias
        """
        self.client = get_bedrock_agent_client()
        self.agent_id = agent_id
        self.agent_alias_id = agent_alias_id or 'TSTALIASID'  # Default alias ID
        self.session_id = str(uuid.uuid4())  # Generate a unique session ID for each agent instance
        self.last_call_time = 0
        self.min_call_interval = 2.0  # Minimum seconds between calls
    
    def _check_circuit_breaker(self) -> None:
        """Check if circuit breaker is open and raise exception if it is"""
        current_time = time.time()
        if self._circuit_open:
            if current_time - self._circuit_reset_time < self.CIRCUIT_RESET_TIMEOUT:
                raise Exception("Circuit breaker is open. Too many failures. Try again later.")
            self._circuit_open = False
            logger.warning("Circuit breaker reset after timeout")
    
    def _trip_circuit_breaker(self) -> None:
        """Trip the circuit breaker to prevent further calls"""
        self._circuit_open = True
        self._circuit_reset_time = time.time()
        logger.error(f"Circuit breaker tripped. Will reset after {self.CIRCUIT_RESET_TIMEOUT} seconds")
    
    async def _enforce_rate_limit(self):
        """Enforce minimum time between API calls"""
        current_time = time.time()
        time_since_last_call = current_time - self.last_call_time
        if time_since_last_call < self.min_call_interval:
            sleep_time = self.min_call_interval - time_since_last_call
            logger.info(f"Rate limiting: Waiting {sleep_time:.2f}s before next call")
            await asyncio.sleep(sleep_time)
        self.last_call_time = time.time()
    
    async def invoke_agent(self, prompt: str, max_retries: int = 5, initial_delay: float = 2.0) -> Dict[str, Any]:
        """
        Invoke the Bedrock agent with the given prompt with exponential backoff and circuit breaker.
        
        Args:
            prompt: The input text prompt for the agent
            max_retries: Maximum number of retry attempts (increased from 3 to 5)
            initial_delay: Initial delay between retries in seconds (increased from 1.0 to 2.0)
            
        Returns:
            Dictionary containing the response or error information
        """
        # Check circuit breaker first
        self._check_circuit_breaker()
        
        # Enforce rate limiting
        await self._enforce_rate_limit()
        
        retry_count = 0
        delay = initial_delay
        
        while retry_count < max_retries:
            try:
                # Prepare the request parameters
                params = {
                    'agentId': self.agent_id,
                    'sessionId': self.session_id,
                    'inputText': prompt,
                    'enableTrace': True
                }
                
                # Add alias ID if provided
                if self.agent_alias_id:
                    params['agentAliasId'] = self.agent_alias_id
                
                logger.info(f"Invoking Bedrock agent (attempt {retry_count + 1}/{max_retries}) with ID: {self.agent_id}" + 
                          (f" and alias: {self.agent_alias_id}" if self.agent_alias_id else ""))
                
                # Make the API call
                response = self.client.invoke_agent(**params)
                
                # Process the streaming response
                completion = ""
                for event in response.get('completion', []):
                    chunk = event.get('chunk', {})
                    if 'bytes' in chunk:
                        completion += chunk['bytes'].decode('utf-8')
                
                return {
                    'status': 'success',
                    'response': completion.strip()
                }
                
            except Exception as e:
                error_msg = str(e)
                if 'throttlingException' in error_msg and retry_count < max_retries - 1:
                    # Calculate exponential backoff with jitter
                    sleep_time = min(delay * (2 ** retry_count) + (random.uniform(0, 0.1) * retry_count), 10)
                    logger.warning(f"Rate limited. Retrying in {sleep_time:.2f} seconds...")
                    await asyncio.sleep(sleep_time)
                    retry_count += 1
                    continue
                    
                # If we get here, either it's not a retriable error or we've hit max retries
                logger.error(f"Error invoking Bedrock agent (attempt {retry_count + 1}/{max_retries}): {error_msg}", exc_info=True)
                
                # Trip circuit breaker if we've hit max retries
                if retry_count >= max_retries - 1:
                    self._trip_circuit_breaker()
                
                return {
                    'status': 'error',
                    'error': f"Error invoking Bedrock agent: {error_msg}",
                    'details': str(e),
                    'retry_attempts': retry_count + 1,
                    'suggestion': 'Please wait before retrying or check your Bedrock service quotas.'
                }
        
        # Should never reach here due to the while loop logic
        return {
            'status': 'error',
            'error': 'Max retries exceeded',
            'details': 'Failed to invoke Bedrock agent after maximum retry attempts'
        }

def get_data_profile(df: pd.DataFrame) -> Dict[str, Any]:
    """Generate a data profile for the given DataFrame."""
    profile = {
        'column_count': len(df.columns),
        'row_count': len(df),
        'columns': {}
    }
    
    for column in df.columns:
        try:
            col_data = df[column]
            col_type = str(col_data.dtype)
            
            # Basic stats
            stats = {
                'dtype': col_type,
                'unique_count': int(col_data.nunique()),
                'null_count': int(col_data.isnull().sum()),
                'null_percentage': float(col_data.isnull().mean() * 100) if len(col_data) > 0 else 0.0,
                'unique_percentage': float(col_data.nunique() / len(col_data) * 100) if len(col_data) > 0 else 0.0
            }
            
            # Add sample values (non-null)
            sample_values = col_data.dropna().head(5).tolist()
            if sample_values:
                stats['sample_values'] = [str(v) for v in sample_values]
            
            # Handle boolean columns first to avoid numeric operations
            if pd.api.types.is_bool_dtype(col_data):
                stats.update({
                    'true_count': int(col_data.sum()),
                    'false_count': int((~col_data).sum()),
                    'true_percentage': float(col_data.mean() * 100) if len(col_data) > 0 else 0.0
                })
            # Handle numeric columns (int, float)
            elif pd.api.types.is_numeric_dtype(col_data):
                stats.update({
                    'mean': float(col_data.mean()),
                    'std': float(col_data.std()) if len(col_data) > 1 else 0.0,
                    'min': float(col_data.min()) if len(col_data) > 0 else None,
                    'max': float(col_data.max()) if len(col_data) > 0 else None,
                    'median': float(col_data.median()) if len(col_data) > 0 else None,
                    'zeros': int((col_data == 0).sum())
                })
            # Handle datetime columns
            elif pd.api.types.is_datetime64_any_dtype(col_data):
                stats.update({
                    'min': str(col_data.min()) if not col_data.empty and not col_data.isnull().all() else None,
                    'max': str(col_data.max()) if not col_data.empty and not col_data.isnull().all() else None
                })
            # Handle string/object columns
            elif pd.api.types.is_string_dtype(col_data):
                str_lengths = col_data.astype(str).str.len()
                stats.update({
                    'max_length': int(str_lengths.max()) if not str_lengths.empty else 0,
                    'min_length': int(str_lengths.min()) if not str_lengths.empty else 0,
                    'avg_length': float(str_lengths.mean()) if not str_lengths.empty else 0.0,
                    'empty_strings': int((col_data == '').sum())
                })
            
            profile['columns'][column] = stats
            
        except Exception as e:
            logger.error(f"Error profiling column '{column}': {str(e)}")
            profile['columns'][column] = {
                'dtype': str(df[column].dtype),
                'error': f"Profiling failed: {str(e)}"
            }
    
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
    
    # Add error information if present
    if 'error' in result:
        report.append("## Error Details")
        report.append(f"An error occurred during processing: `{result['error']}`")
        report.append("")
        
        # Add stack trace if available
        if 'stack_trace' in result:
            report.append("### Stack Trace")
            report.append(f"```\n{result['stack_trace']}\n```")
        report.append("")
    
    # Add execution summary
    exec_summary = result.get('execution_summary', {})
    if exec_summary:
        report.append("## Execution Summary")
        report.append(f"- **Total Time:** {exec_summary.get('total_time_seconds', 0):.2f} seconds")
        
        # Only show rows processed if no error
        if 'error' not in result:
            report.append(f"- **Total Rows Processed:** {exec_summary.get('rows_processed', 0):,}")
        
        # Show error from execution summary if present
        if 'error' in exec_summary:
            report.append(f"- **Error:** {exec_summary['error']}")
        report.append("")
    
    # Add AI analysis if available
    if 'ai_analysis' in result:
        if 'insights' in result['ai_analysis'] and result['ai_analysis'].get('status') == 'success':
            report.append("## AI-Powered Analysis")
            report.append(result['ai_analysis']['insights'])
        elif 'error' in result['ai_analysis']:
            report.append("## AI Analysis Failed")
            report.append(f"Error: {result['ai_analysis'].get('error', 'Unknown error')}")
        report.append("")
    
    # Add data profile summary if available and not empty
    profile = result.get('profile', {})
    if profile and isinstance(profile, dict) and profile.get('columns'):
        report.append("## Data Profile")
        report.append(f"- **Total Rows:** {profile.get('row_count', 0):,}")
        report.append(f"- **Total Columns:** {profile.get('column_count', 0)}")
        report.append("")
        
        # Add column statistics
        report.append("### Column Statistics")
        for col, stats in profile.get('columns', {}).items():
            if not isinstance(stats, dict):
                continue
                
            report.append(f"#### {col}")
            report.append(f"- **Type:** {stats.get('dtype', 'N/A')}")
            
            # Safely handle null values
            if 'null_count' in stats and 'null_percentage' in stats:
                report.append(f"- **Null Values:** {stats['null_count']:,} ({stats['null_percentage']:.1f}%)")
            
            # Safely handle unique values
            if 'unique_count' in stats and 'unique_percentage' in stats:
                report.append(f"- **Unique Values:** {stats['unique_count']:,} ({stats['unique_percentage']:.1f}%)")
            
            # Add numeric stats if available
            if 'stats' in stats and isinstance(stats['stats'], dict):
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
        
        # AI-Powered Analysis with Titan Text G1 - Premier Agent
        if os.environ.get('BEDROCK_AGENT_ENABLED', 'true').lower() == 'true':
            logger.info("Running AI-powered analysis with Titan Text G1 - Premier Agent")
            try:
                analyses = {}
                
                # Always run data quality analysis
                quality_analysis = await analyze_with_titan_agent(
                    profile=profile,
                    df=df,
                    analysis_type=AnalysisType.DATA_QUALITY
                )
                analyses['data_quality'] = quality_analysis
                
                # Conditionally run anomaly detection if enabled
                if os.environ.get('ENABLE_ANOMALY_DETECTION', 'true').lower() == 'true':
                    # Add a small delay to avoid rate limiting
                    await asyncio.sleep(2)  # 2 second delay between agent calls
                    logger.info("Running anomaly detection analysis")
                    try:
                        anomaly_analysis = await analyze_with_titan_agent(
                            profile=profile,
                            df=df,
                            analysis_type=AnalysisType.ANOMALY_DETECTION
                        )
                        analyses['anomaly_detection'] = anomaly_analysis
                    except Exception as e:
                        logger.error(f"Anomaly detection failed but continuing: {str(e)}")
                        analyses['anomaly_detection'] = {
                            'status': 'error',
                            'error': str(e),
                            'message': 'Anomaly detection failed due to rate limiting or other error'
                        }
                
                result['ai_analysis'] = analyses
                logger.info("Successfully completed AI analysis")
                
            except Exception as e:
                error_msg = f"AI analysis with Titan Agent failed: {str(e)}"
                logger.error(error_msg, exc_info=True)
                result['ai_analysis'] = {
                    'status': 'error',
                    'error': error_msg,
                    'stack_trace': traceback.format_exc(),
                    'generated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
                }
        
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
