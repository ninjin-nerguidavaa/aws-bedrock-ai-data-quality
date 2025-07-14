# Lambda Deployment Scripts

This directory contains scripts to build, package, and deploy the AWS Lambda functions for the Data Quality Bots project.

## Available Scripts

### 1. `build_lambda.py` (Recommended)
A robust Python-based build script that creates a deployment package for AWS Lambda with the following features:

**Key Features:**
- 🖥️ Cross-platform compatibility (Windows, macOS, Linux)
- 📦 Clean dependency installation in isolated environment
- 📝 Detailed logging for debugging
- 🧹 Automatic cleanup of temporary files
- ✅ Dependency validation
- 🔍 File integrity verification
- 🚀 Optimized packaging for AWS Lambda

**Usage:**
```bash
# Make the script executable (Unix-like systems)
chmod +x build_lambda.py

# Basic usage
./build_lambda.py

# Advanced options
./build_lambda.py \
    --source-dir ../lambda_functions/data_quality_checker \
    --output-dir ../build/lambda \
    --requirements requirements.txt \
    --exclude "*.pyc" "__pycache__" ".pytest_cache"

# Show help
./build_lambda.py --help
```

### 2. `build_lambda.sh`
A shell script alternative for Unix-like systems with basic functionality.

**Usage:**
```bash
# Make the script executable
chmod +x build_lambda.sh

# Run the script with default parameters
./build_lambda.sh

# Run with custom parameters
./build_lambda.sh /path/to/source /path/to/output
```

## Build Process

1. **Source Preparation**
   - Validates source directory and requirements
   - Creates temporary build directory
   - Copies Python files while maintaining directory structure

2. **Dependency Installation**
   - Creates a virtual environment
   - Installs dependencies from requirements.txt
   - Strips unnecessary files to reduce package size
   - Handles platform-specific dependencies

3. **Package Creation**
   - Creates a ZIP archive of the deployment package
   - Validates the package structure
   - Generates a checksum for verification
   - Cleans up temporary files

## Output Structure

The build process creates the following structure:
```
/build/
  └── lambda/
      ├── data_quality_checker.zip  # Deployment package
      └── checksum.sha256          # Package checksum for verification
```

## Prerequisites

- Python 3.8 or later
- pip (Python package manager)
- Virtual environment (venv) module
- AWS CLI (for deployment)
- Required system libraries (if any native dependencies)

## Environment Variables

You can customize the build process using these environment variables:

```bash
# Source and output directories
LAMBDA_SOURCE_DIR=../lambda_functions/data_quality_checker
LAMBDA_OUTPUT_DIR=../build/lambda

# Build options
CLEAN_BUILD=true
VALIDATE_REQUIREMENTS=true
VERBOSE_LOGGING=true

# AWS specific
AWS_REGION=us-east-1
AWS_PROFILE=default
```

## Best Practices

1. **Dependency Management**
   - Always pin package versions in requirements.txt
   - Test with the same Python version as your Lambda runtime
   - Minimize package size by excluding unnecessary files

2. **Build Process**
   - Run builds in a clean environment
   - Verify the package contents before deployment
   - Test the package locally using AWS SAM CLI

3. **Deployment**
   - Use infrastructure as code (Terraform/CloudFormation)
   - Implement blue/green deployments for zero-downtime updates
   - Monitor Lambda function metrics after deployment

## Troubleshooting

### Common Issues

1. **Package Too Large**
   - Check for unnecessary files in the package
   - Use `--exclude` to exclude test files and documentation
   - Consider using Lambda Layers for large dependencies

2. **Import Errors**
   - Verify all dependencies are included in the package
   - Check for platform-specific dependencies
   - Test with the same Python version as the Lambda runtime

3. **Permission Issues**
   - Ensure the build script has execute permissions
   - Verify write permissions in the output directory
   - Check AWS credentials for deployment

## CI/CD Integration

Example GitHub Actions workflow:

```yaml
name: Build and Deploy Lambda

on:
  push:
    branches: [ main ]
    paths:
      - 'lambda_functions/**'
      - 'scripts/**'
      - 'requirements.txt'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements-dev.txt
    
    - name: Build Lambda package
      run: |
        chmod +x ./scripts/build_lambda.py
        ./scripts/build_lambda.py
    
    - name: Deploy to AWS Lambda
      env:
        AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
        AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
      run: |
        aws lambda update-function-code \
          --function-name data-quality-checker \
          --zip-file fileb://build/lambda/data_quality_checker.zip
```

## Adding to Version Control

The `build/` directory is typically excluded from version control. You can add the built packages to your `.gitignore` file.
