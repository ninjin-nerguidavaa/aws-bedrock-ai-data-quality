# Terraform Configuration for AWS Data Quality Bots

This directory contains the Terraform configuration for deploying the AWS Data Quality Bots infrastructure.

## Directory Structure

- `main.tf` - Main configuration file
- `variables.tf` - Input variables
- `outputs.tf` - Output values
- `iam.tf` - IAM roles and policies
- `providers.tf` - Provider configuration
- `versions.tf` - Version constraints
- `backend.tf` - Backend configuration for Terraform state

## Usage

### Prerequisites

- Terraform >= 1.0.0
- AWS CLI configured with appropriate credentials

### Initialization

```bash
terraform init
```

### Planning

```bash
terraform plan
```

### Applying Changes

```bash
terraform apply
```

## Variables

See `variables.tf` for all available variables and their descriptions.

## Outputs

- `athena_workgroup_name` - Name of the Athena workgroup
- `glue_crawler_name` - Name of the Glue crawler

## Notes

- The root `main.tf` file is a wrapper that includes this module for backward compatibility.
- All new development should reference this directory directly.
