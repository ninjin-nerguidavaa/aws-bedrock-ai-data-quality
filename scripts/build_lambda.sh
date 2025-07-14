#!/bin/bash

# Exit on error
set -e

# Set variables
LAMBDA_DIR="../lambda_functions/data_quality_checker"
BUILD_DIR="../build/lambda"
PACKAGE_NAME="data_quality_checker.zip"

# Create build directory
mkdir -p "$BUILD_DIR"

# Create a temporary directory for the package
echo "Creating temporary build directory..."
TEMP_DIR=$(mktemp -d)

# Copy Python files
cp "$LAMBDA_DIR/lambda_function.py" "$TEMP_DIR/"

# Install dependencies
echo "Installing dependencies..."
pip install -r "$LAMBDA_DIR/requirements.txt" -t "$TEMP_DIR" --no-cache-dir

# Create the ZIP file
echo "Creating ZIP package..."
cd "$TEMP_DIR"
zip -r "$PACKAGE_NAME" .

# Move the ZIP file to the build directory
mv "$PACKAGE_NAME" "$BUILD_DIR/"

# Clean up
echo "Cleaning up..."
rm -rf "$TEMP_DIR"

echo "Lambda package created at: $BUILD_DIR/$PACKAGE_NAME"
