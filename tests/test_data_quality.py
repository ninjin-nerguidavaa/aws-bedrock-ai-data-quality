import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
import json
import os

# Mock the Lambda context
class MockContext:
    def __init__(self):
        self.function_name = "test-function"
        self.memory_limit_in_mb = 128
        self.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test-function"
        self.aws_request_id = "test-request-id"

# Mock boto3 clients
@pytest.fixture
def mock_aws_clients():
    with patch('boto3.client') as mock_client:
        mock_s3 = MagicMock()
        mock_sns = MagicMock()
        
        mock_client.side_effect = lambda service, **kwargs: {
            's3': mock_s3,
            'sns': mock_sns
        }[service]
        
        yield {
            's3': mock_s3,
            'sns': mock_sns
        }

# Mock environment variables
@pytest.fixture(autouse=True)
def mock_env_vars():
    with patch.dict(os.environ, {
        'S3_BUCKET': 'test-bucket',
        'SNS_TOPIC_ARN': 'arn:aws:sns:us-east-1:123456789012:test-topic'
    }):
        yield

def test_check_data_quality_success():
    """Test successful data quality check"""
    # Import here to apply the mock environment variables
    from lambda_functions.data_quality_checker.lambda_function import check_data_quality
    
    # Mock awswrangler to return a test DataFrame
    with patch('awswrangler.athena.read_sql_table') as mock_read_sql:
        # Create a test DataFrame
        test_df = pd.DataFrame({
            'id': [1, 2, 3],
            'name': ['Alice', 'Bob', None],
            'email': ['alice@test.com', 'bob@test.com', 'charlie@test.com']
        })
        mock_read_sql.return_value = test_df
        
        # Call the function
        result = check_data_quality('test_db', 'test_table')
        
        # Assert the results
        assert result['table'] == 'test_db.test_table'
        assert result['row_count'] == 3
        assert any(check['check'] == 'row_count' for check in result['checks'])
        assert any('null_check_name' in check['check'] for check in result['checks'])
        assert any('unique_values_id' in check['check'] for check in result['checks'])

def test_lambda_handler_success(mock_aws_clients):
    """Test Lambda handler with successful execution"""
    # Import here to apply the mock environment variables
    from lambda_functions.data_quality_checker.lambda_function import lambda_handler
    
    # Mock awswrangler
    with patch('awswrangler.athena.read_sql_table') as mock_read_sql:
        # Setup test data
        test_df = pd.DataFrame({'col1': [1, 2, 3]})
        mock_read_sql.return_value = test_df
        
        # Setup S3 mock
        mock_aws_clients['s3'].put_object.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Call the handler
        event = {
            'database': 'test_db',
            'table': 'test_table'
        }
        context = MockContext()
        
        response = lambda_handler(event, context)
        
        # Verify the response
        assert response['statusCode'] == 200
        assert 's3://' in json.loads(response['body'])['s3_location']
        
        # Verify S3 put_object was called
        mock_aws_clients['s3'].put_object.assert_called_once()
        
        # Verify SNS was not called (no failures)
        mock_aws_clients['sns'].publish.assert_not_called()

def test_lambda_handler_with_failures(mock_aws_clients):
    """Test Lambda handler with data quality failures"""
    # Import here to apply the mock environment variables
    from lambda_functions.data_quality_checker.lambda_function import lambda_handler
    
    # Mock awswrangler to return a DataFrame with issues
    with patch('awswrangler.athena.read_sql_table') as mock_read_sql:
        # Setup test data with issues (all nulls in a column)
        test_df = pd.DataFrame({
            'id': [1, 2, 3],
            'name': [None, None, None],  # All nulls should trigger a warning
            'email': ['a@test.com', 'b@test.com', 'c@test.com']
        })
        mock_read_sql.return_value = test_df
        
        # Setup S3 mock
        mock_aws_clients['s3'].put_object.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Call the handler
        event = {
            'database': 'test_db',
            'table': 'test_table'
        }
        context = MockContext()
        
        response = lambda_handler(event, context)
        
        # Verify the response
        assert response['statusCode'] == 200
        
        # Verify SNS was called due to data quality issues
        mock_aws_clients['sns'].publish.assert_called_once()
        
        # Check that the message contains our table name
        call_args = mock_aws_clients['sns'].publish.call_args[1]
        assert 'test_db.test_table' in call_args['Subject']
        assert 'Data quality check failed' in call_args['Subject']
