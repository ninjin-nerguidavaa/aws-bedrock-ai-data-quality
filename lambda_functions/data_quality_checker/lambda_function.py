import json
import boto3
import pandas as pd
import awswrangler as wr
import time
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum

# Initialize AWS clients
s3 = boto3.client('s3')
sns = boto3.client('sns')
bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1')

# Constants
BEDROCK_MODEL_ID = 'anthropic.claude-3-sonnet-20240229-v1:0'
MAX_RETRIES = 3

class AgentType(Enum):
    DATA_PROFILER = "data_profiler"
    RULE_ENGINE = "rule_engine"
    ANOMALY_DETECTOR = "anomaly_detector"
    ROOT_CAUSE_ANALYZER = "root_cause_analyzer"
    REMEDIATION_ADVISOR = "remediation_advisor"

class DataQualityAgent:
    """Base class for all data quality agents"""
    
    def __init__(self, agent_type: AgentType):
        self.agent_type = agent_type
    
    def analyze(self, data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Base analyze method to be implemented by subclasses"""
        raise NotImplementedError

class BedrockAgent(DataQualityAgent):
    """Agent that uses Amazon Bedrock for analysis"""
    
    def __init__(self, agent_type: AgentType, model_id: str = BEDROCK_MODEL_ID):
        super().__init__(agent_type)
        self.model_id = model_id
        
    def _invoke_bedrock(self, prompt: str, system_prompt: str = None, max_tokens: int = 2000) -> str:
        """Invoke Bedrock model with retry logic"""
        messages = [{"role": "user", "content": prompt}]
        if system_prompt:
            messages.insert(0, {"role": "system", "content": system_prompt})
            
        body = {
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.5,
            "top_p": 0.9,
        }
        
        for attempt in range(MAX_RETRIES):
            try:
                response = bedrock_runtime.invoke_model(
                    modelId=self.model_id,
                    body=json.dumps(body)
                )
                result = json.loads(response['body'].read().decode())
                return result['content'][0]['text']
            except Exception as e:
                if attempt == MAX_RETRIES - 1:
                    raise
                time.sleep(2 ** attempt)  # Exponential backoff
                
    def analyze(self, data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        system_prompt = self._get_system_prompt()
        user_prompt = self._format_prompt(data, context or {})
        
        try:
            response = self._invoke_bedrock(user_prompt, system_prompt)
            return self._parse_response(response, data)
        except Exception as e:
            return {
                "status": "ERROR",
                "message": f"Error in {self.agent_type.value}: {str(e)}",
                "details": str(e)
            }
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for the specific agent type"""
        if self.agent_type == AgentType.DATA_PROFILER:
            return """You are a data quality expert analyzing data profiles. 
            Provide a concise summary of the data characteristics and potential data quality issues."""
        elif self.agent_type == AgentType.RULE_ENGINE:
            return """You are a data quality rule engine. 
            Analyze the data and suggest appropriate data quality rules based on the data characteristics."""
        elif self.agent_type == AgentType.ANOMALY_DETECTOR:
            return """You are an anomaly detection system. 
            Identify any anomalies or outliers in the provided data."""
        elif self.agent_type == AgentType.ROOT_CAUSE_ANALYZER:
            return """You are a root cause analyzer. 
            Analyze the data quality issues and identify potential root causes."""
        elif self.agent_type == AgentType.REMEDIATION_ADVISOR:
            return """You are a remediation advisor. 
            Suggest specific actions to fix the identified data quality issues."""
    
    def _format_prompt(self, data: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Format the prompt for the specific agent type"""
        if self.agent_type == AgentType.DATA_PROFILER:
            return f"""Analyze the following data profile and provide insights:
            
            Data Profile:
            {json.dumps(data, indent=2)}
            
            Provide a summary of data characteristics and potential issues."""
            
        elif self.agent_type == AgentType.RULE_ENGINE:
            return f"""Based on the following data profile, suggest data quality rules:
            
            Data Profile:
            {json.dumps(data, indent=2)}
            
            Context:
            {json.dumps(context, indent=2)}
            
            Suggest rules in JSON format with name, description, and severity."""
            
        # Add other agent types as needed
        return json.dumps(data, indent=2)
    
    def _parse_response(self, response: str, original_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse the response from Bedrock"""
        try:
            # Try to parse as JSON first
            return json.loads(response)
        except json.JSONDecodeError:
            # If not JSON, return as text
            return {
                "status": "SUCCESS",
                "analysis": response,
                "agent_type": self.agent_type.value
            }

def get_data_profile(df: pd.DataFrame) -> Dict[str, Any]:
    """Generate a data profile summary for the DataFrame"""
    profile = {
        'row_count': len(df),
        'columns': {},
        'basic_stats': {}
    }
    
    for column in df.columns:
        col_data = df[column]
        null_count = col_data.isnull().sum()
        null_pct = (null_count / len(df)) * 100 if len(df) > 0 else 0
        unique_count = col_data.nunique()
        
        profile['columns'][column] = {
            'dtype': str(col_data.dtype),
            'null_count': int(null_count),
            'null_percentage': float(null_pct),
            'unique_count': int(unique_count),
            'sample_values': col_data.dropna().head(5).tolist() if not col_data.empty else []
        }
        
        # Add basic statistics for numeric columns
        if pd.api.types.is_numeric_dtype(col_data):
            profile['basic_stats'][column] = {
                'min': float(col_data.min()) if not col_data.empty else None,
                'max': float(col_data.max()) if not col_data.empty else None,
                'mean': float(col_data.mean()) if not col_data.empty else None,
                'std': float(col_data.std()) if not col_data.empty else None,
                'percentiles': {
                    '25%': float(col_data.quantile(0.25)) if not col_data.empty else None,
                    '50%': float(col_data.quantile(0.5)) if not col_data.empty else None,
                    '75%': float(col_data.quantile(0.75)) if not col_data.empty else None
                }
            }
    
    return profile

def run_agent_analysis(profile: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Run analysis using multiple specialized agents"""
    context = context or {}
    results = {}
    
    # Initialize agents
    agents = [
        BedrockAgent(AgentType.DATA_PROFILER),
        BedrockAgent(AgentType.RULE_ENGINE),
        BedrockAgent(AgentType.ANOMALY_DETECTOR),
        BedrockAgent(AgentType.ROOT_CAUSE_ANALYZER),
        BedrockAgent(AgentType.REMEDIATION_ADVISOR)
    ]
    
    # Run each agent's analysis
    for agent in agents:
        try:
            agent_result = agent.analyze(profile, context)
            results[agent.agent_type.value] = agent_result
        except Exception as e:
            results[agent.agent_type.value] = {
                'status': 'ERROR',
                'message': str(e)
            }
    
    return results

def check_data_quality(database: str, table: str) -> Dict[str, Any]:
    """
    Perform comprehensive data quality checks on a Glue table using multi-agent system
    """
    results = {
        'table': f"{database}.{table}",
        'checks': [],
        'agents': {},
        'profile': {},
        'execution_summary': {}
    }
    
    start_time = time.time()
    
    try:
        # Step 1: Read and profile the data
        read_start = time.time()
        df = wr.athena.read_sql_table(
            table=table,
            database=database,
            ctas_approach=False,
            s3_output=f"s3://{s3_bucket}/athena-results/"
        )
        read_time = time.time() - read_start
        
        # Step 2: Generate data profile
        profile_start = time.time()
        profile = get_data_profile(df)
        profile_time = time.time() - profile_start
        results['profile'] = profile
        
        # Step 3: Run basic checks
        basic_checks_start = time.time()
        results['row_count'] = profile['row_count']
        
        # Add basic data quality checks
        for col, stats in profile['columns'].items():
            # Null value check
            null_check = {
                'check': f'null_check_{col}',
                'column': col,
                'null_count': stats['null_count'],
                'null_percentage': stats['null_percentage'],
                'status': 'WARNING' if stats['null_percentage'] > 5 else 'PASS',
                'message': f'Column {col} has {stats["null_count"]} null values ({stats["null_percentage"]:.2f}%)'
            }
            results['checks'].append(null_check)
            
            # Uniqueness check
            unique_check = {
                'check': f'uniqueness_check_{col}',
                'column': col,
                'unique_count': stats['unique_count'],
                'unique_percentage': (stats['unique_count'] / profile['row_count']) * 100 if profile['row_count'] > 0 else 0,
                'status': 'PASS',
                'message': f'Column {col} has {stats["unique_count"]} unique values'
            }
            results['checks'].append(unique_check)
        
        basic_checks_time = time.time() - basic_checks_start
        
        # Step 4: Run AI-powered analysis
        ai_analysis_start = time.time()
        context = {
            'database': database,
            'table': table,
            'basic_checks': [c for c in results['checks'] if c['status'] != 'PASS']
        }
        
        agent_results = run_agent_analysis(profile, context)
        results['agents'] = agent_results
        ai_analysis_time = time.time() - ai_analysis_start
        
        # Step 5: Compile execution metrics
        total_time = time.time() - start_time
        results['execution_summary'] = {
            'total_time_seconds': total_time,
            'time_breakdown': {
                'data_loading': read_time,
                'profiling': profile_time,
                'basic_checks': basic_checks_time,
                'ai_analysis': ai_analysis_time
            },
            'status': 'COMPLETED'
        }
        
        return results
        
    except Exception as e:
        error_time = time.time() - start_time
        return {
            'table': f"{database}.{table}",
            'error': str(e),
            'checks': [],
            'execution_summary': {
                'total_time_seconds': error_time,
                'status': 'FAILED',
                'error': str(e)
            }
        }

def generate_quality_report(result: Dict[str, Any]) -> str:
    """Generate a human-readable quality report from the results"""
    report = []
    
    # Basic info
    report.append(f"# Data Quality Report for {result.get('table', 'unknown')}")
    report.append(f"- **Status**: {result.get('execution_summary', {}).get('status', 'UNKNOWN')}")
    report.append(f"- **Total Rows**: {result.get('row_count', 0):,}")
    
    # Summary of issues
    failed_checks = [c for c in result.get('checks', []) if c.get('status') in ['FAIL', 'WARNING']]
    if failed_checks:
        report.append("\n## Issues Found")
        for check in failed_checks:
            status_emoji = "❌" if check['status'] == 'FAIL' else "⚠️"
            report.append(f"{status_emoji} **{check['check']}**: {check['message']}")
    
    # Agent insights
    if 'agents' in result and result['agents']:
        report.append("\n## AI-Powered Insights")
        for agent_name, analysis in result['agents'].items():
            if isinstance(analysis, dict) and 'status' in analysis and analysis['status'] == 'SUCCESS':
                report.append(f"\n### {agent_name.replace('_', ' ').title()}")
                if 'analysis' in analysis:
                    report.append(analysis['analysis'])
                elif isinstance(analysis, str):
                    report.append(analysis)
    
    # Execution summary
    exec_summary = result.get('execution_summary', {})
    if exec_summary:
        report.append("\n## Execution Summary")
        report.append(f"- **Total Time**: {exec_summary.get('total_time_seconds', 0):.2f} seconds")
        if 'time_breakdown' in exec_summary:
            report.append("\n### Time Breakdown")
            for step, time_taken in exec_summary['time_breakdown'].items():
                report.append(f"- {step.replace('_', ' ').title()}: {time_taken:.2f}s")
    
    return "\n".join(report)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for data quality checks with multi-agent analysis
    """
    global s3_bucket
    
    try:
        # Get configuration from environment variables
        s3_bucket = os.environ.get('S3_BUCKET')
        if not s3_bucket:
            raise ValueError("S3_BUCKET environment variable is required")
            
        sns_topic_arn = os.environ.get('SNS_TOPIC_ARN', '')
        
        # Get database and table from event
        database = event.get('database', os.environ.get('DEFAULT_DATABASE', 'default'))
        table = event.get('table', '')
        
        if not table:
            raise ValueError("Table name is required in the event")
        
        print(f"Starting data quality check for {database}.{table}")
        
        # Run data quality checks with multi-agent analysis
        result = check_data_quality(database, table)
        
        # Generate timestamps and paths
        timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
        date_prefix = pd.Timestamp.now().strftime('%Y/%m/%d')
        s3_key = f"quality-checks/{database}/{table}/{date_prefix}/{timestamp}.json"
        report_key = f"quality-reports/{database}/{table}/{date_prefix}/{timestamp}.md"
        
        # Save detailed results to S3
        s3.put_object(
            Bucket=s3_bucket,
            Key=s3_key,
            Body=json.dumps(result, indent=2, default=str).encode('utf-8'),
            ContentType='application/json'
        )
        print(f"Saved detailed results to s3://{s3_bucket}/{s3_key}")
        
        # Generate and save human-readable report
        report = generate_quality_report(result)
        s3.put_object(
            Bucket=s3_bucket,
            Key=report_key,
            Body=report.encode('utf-8'),
            ContentType='text/markdown'
        )
        print(f"Saved quality report to s3://{s3_bucket}/{report_key}")
        
        # Send notification if SNS topic is configured and there are issues
        if sns_topic_arn:
            failed_checks = [c for c in result.get('checks', []) if c.get('status') in ['FAIL', 'WARNING']]
            
            if failed_checks:
                message = f"Data quality check completed for {database}.{table}\n\n"
                message += f"Issues found: {len([c for c in failed_checks if c['status'] == 'FAIL'])} critical, "
                message += f"{len([c for c in failed_checks if c['status'] == 'WARNING'])} warnings\n\n"
                
                # Add a summary of critical issues
                critical_issues = [c for c in failed_checks if c['status'] == 'FAIL']
                if critical_issues:
                    message += "Critical Issues:\n"
                    for issue in critical_issues[:5]:  # Limit to top 5 critical issues
                        message += f"- {issue['message']}\n"
                    if len(critical_issues) > 5:
                        message += f"... and {len(critical_issues) - 5} more\n"
                
                # Add links to the full report
                message += f"\nView full report: s3://{s3_bucket}/{report_key}"
                message += f"\nRaw results: s3://{s3_bucket}/{s3_key}"
                
                sns.publish(
                    TopicArn=sns_topic_arn,
                    Subject=f"Data Quality Alert: {database}.{table} - {len(critical_issues)} critical issues found",
                    Message=message
                )
                print("Sent SNS notification")
        
        # Return success response
        response = {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Data quality check completed',
                's3_location': f"s3://{s3_bucket}/{s3_key}",
                'report_location': f"s3://{s3_bucket}/{report_key}",
                'status': result.get('execution_summary', {}).get('status', 'UNKNOWN'),
                'issue_count': len([c for c in result.get('checks', []) if c.get('status') in ['FAIL', 'WARNING']])
            })
        }
        
        return response
        
    except Exception as e:
        error_msg = f"Error in lambda_handler: {str(e)}"
        print(error_msg)
        
        # Try to send error notification if SNS is configured
        if 'sns_topic_arn' in locals() and sns_topic_arn:
            try:
                sns.publish(
                    TopicArn=sns_topic_arn,
                    Subject="Data Quality Check Failed",
                    Message=f"Error processing data quality check: {str(e)}\n\nEvent: {json.dumps(event)}"
                )
            except Exception as sns_error:
                print(f"Failed to send SNS notification: {str(sns_error)}")
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Failed to process data quality check',
                'details': str(e)
            })
        }
