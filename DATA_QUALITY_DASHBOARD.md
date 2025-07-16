# AWS Data Quality Dashboard

This document provides an overview of the AWS Data Quality Dashboard setup and configuration.

## Architecture Overview

The dashboard consists of the following components:

1. **Frontend**: Static HTML/JS dashboard hosted on S3
2. **Backend**: AWS Lambda function for data quality checks
3. **Data Storage**: S3 bucket for storing reports and results
4. **Data Catalog**: AWS Glue for metadata management
5. **Query Engine**: Amazon Athena for running data quality queries
6. **Automation**: AWS Glue Crawler for schema discovery

## Setup Instructions

### Prerequisites

1. AWS CLI configured with appropriate credentials
2. Terraform installed
3. Node.js and npm (for local development)

### Deployment Steps

1. **Initialize Terraform**
   ```bash
   terraform init
   ```

2. **Review the execution plan**
   ```bash
   terraform plan
   ```

3. **Apply the configuration**
   ```bash
   terraform apply
   ```

4. **Upload the dashboard files to S3**
   ```bash
   aws s3 sync ./html s3://your-bucket-name/html/ --delete
   ```

### Configuration

#### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `aws_region` | AWS region to deploy resources | `us-east-1` |
| `project_name` | Name of the project | `data-quality-bots` |
| `environment` | Deployment environment | `hackathon` |
| `glue_database_name` | Name of the Glue database | `data_quality_db` |
| `crawler_schedule` | Schedule for Glue crawler | `cron(0 1 * * ? *)` |

#### Athena Workgroup Configuration

The Athena workgroup is configured with the following settings:
- Query result location: `s3://<bucket>/athena_results/`
- Encryption: SSE-S3
- Query results encryption: Enabled
- Metrics: Published to CloudWatch
- Engine version: Athena engine version 3

#### Glue Crawler Configuration

The Glue crawler is configured to:
- Run daily at 1 AM UTC
- Target S3 location: `s3://<bucket>/data/`
- Update the data catalog with schema changes
- Log schema changes without deleting tables

## Usage

### Accessing the Dashboard

1. After deployment, the dashboard will be available at:
   ```
   http://<your-bucket-name>.s3-website-<region>.amazonaws.com
   ```

2. The dashboard will automatically load the latest data quality report from:
   ```
   s3://<bucket>/reports/data_quality_db/customers/20250715_042655/report.json
   ```

### Running Manual Data Quality Checks

1. Navigate to the AWS Lambda console
2. Find the data quality Lambda function
3. Configure a test event with the following format:
   ```json
   {
     "database": "your_database",
     "table": "your_table"
   }
   ```
4. Run the test

## Troubleshooting

### Common Issues

1. **Dashboard not loading data**
   - Verify the S3 bucket policy allows public read access to the report file
   - Check CORS configuration on the S3 bucket
   - Verify the report file exists at the expected location

2. **Athena query failures**
   - Check CloudWatch logs for the Lambda function
   - Verify the Athena workgroup has the correct permissions
   - Ensure the Glue catalog has the latest table definitions

3. **Glue crawler not updating tables**
   - Check the crawler's CloudWatch logs
   - Verify the IAM role has the necessary permissions
   - Check if the crawler has been run recently

## Maintenance

### Updating the Dashboard

1. Make changes to the HTML/JS files in the `html` directory
2. Upload the changes to S3:
   ```bash
   aws s3 sync ./html s3://your-bucket-name/html/ --delete
   ```

### Monitoring

- **CloudWatch Logs**: `/aws/lambda/data-quality-bots`
- **CloudWatch Metrics**: `AWS/Glue` and `AWS/Athena` namespaces
- **S3 Access Logs**: Enabled on the S3 bucket

## Security Considerations

1. **IAM Roles**
   - Use least privilege principles for all IAM roles
   - Regularly review and rotate access keys

2. **Data Encryption**
   - All data at rest is encrypted using S3 server-side encryption
   - Data in transit is encrypted using HTTPS

3. **Access Control**
   - Restrict access to the S3 bucket using bucket policies
   - Use IAM policies to control access to AWS resources

## Cost Optimization

1. **S3 Lifecycle Rules**
   - Configure lifecycle rules to transition old reports to S3 Glacier
   - Set up expiration for temporary files

2. **Athena**
   - Use partitioning to reduce the amount of data scanned
   - Set query result size limits

3. **Glue**
   - Schedule crawlers during off-peak hours
   - Configure the crawler to only scan necessary paths

## Support

For issues and feature requests, please open an issue in the project repository.
