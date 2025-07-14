# Lambda Layer Management

This document provides detailed information about the Lambda Layer used in the AWS Data Quality Bots project, including how to build, update, and manage it.

## Overview

The Lambda Layer contains all the Python dependencies required by the Lambda function, allowing for better code organization, smaller deployment packages, and easier dependency management.

## Layer Contents

The layer includes the following key dependencies:

- **boto3**: AWS SDK for Python
- **botocore**: Low-level, core functionality of boto3
- **pandas**: Data manipulation and analysis
- **pyathena**: Python DB API 2.0 (PEP 249) client for Amazon Athena
- **awswrangler**: Pandas on AWS

## Building the Layer

### Prerequisites

- Python 3.9
- pip
- AWS CLI configured with appropriate permissions

### Build Process

1. Navigate to the project root directory:
   ```bash
   cd aws-data-quality-bots
   ```

2. Run the build script:
   ```bash
   python3 scripts/build_layer.py
   ```

3. The built layer package will be available at:
   ```
   build/layer/data-quality-deps.zip
   ```

## Deploying the Layer

### AWS Management Console

1. Go to the AWS Lambda Console
2. Navigate to **Layers** in the left sidebar
3. Click **Create layer**
4. Configure the layer:
   - **Name**: `data-quality-deps`
   - **Description**: Dependencies for Data Quality Bots Lambda function
   - **Upload a .zip file**: Select the built `data-quality-deps.zip`
   - **Compatible runtimes**: Python 3.9
   - **Compatible architectures**: x86_64
5. Click **Create**

### AWS CLI

```bash
aws lambda publish-layer-version \
    --layer-name data-quality-deps \
    --description "Dependencies for Data Quality Bots Lambda function" \
    --license-info "MIT" \
    --zip-file fileb://build/layer/data-quality-deps.zip \
    --compatible-runtimes python3.9 \
    --compatible-architectures "x86_64"
```

## Updating the Layer

1. Update the dependencies in `lambda_functions/data_quality_checker/requirements.txt`
2. Rebuild the layer:
   ```bash
   python3 scripts/build_layer.py
   ```
3. Publish a new version following the deployment steps above
4. Update your Lambda function to use the new layer version

## Using the Layer in Lambda

### AWS Management Console

1. Open your Lambda function in the AWS Console
2. Scroll down to the **Layers** section
3. Click **Add a layer**
4. Select **Custom layers**
5. Choose the `data-quality-deps` layer
6. Select the version you want to use
7. Click **Add**

### AWS CLI

```bash
aws lambda update-function-configuration \
    --function-name your-function-name \
    --layers arn:aws:lambda:region:account-id:layer:data-quality-deps:version
```

## Best Practices

1. **Versioning**: Always create a new version when updating the layer instead of modifying existing versions
2. **Testing**: Test new layer versions in a development environment before promoting to production
3. **Documentation**: Keep the `requirements.txt` file updated with all dependencies and their versions
4. **Size Management**: Monitor the layer size (AWS Lambda has a 250MB limit for layers)

## Troubleshooting

### Common Issues

1. **Import Errors**:
   - Ensure the layer is properly attached to your Lambda function
   - Verify the layer version is compatible with your function's runtime

2. **Size Limitations**:
   - The uncompressed layer size must be less than 250MB
   - If the layer is too large, consider splitting it into multiple layers

3. **Permission Issues**:
   - Ensure your Lambda execution role has `lambda:GetLayerVersion` permission
   - Verify the layer is in the same region as your Lambda function

### Debugging

1. Check CloudWatch Logs for import errors
2. Use the Lambda Test feature to verify the layer is loaded correctly
3. Check the Lambda function's configuration in the AWS Console to confirm the layer is attached
