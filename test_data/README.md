# Test Data for AWS Data Quality Bots

This directory contains sample data files that can be used to test the data quality checks in the AWS Data Quality Bots project.

## Sample Dataset: Customer Data

File: `sample_customers.csv`

### Dataset Description
This is a synthetic dataset containing customer information with the following fields:

| Column Name       | Data Type | Description                                      | Example Values                     |
|-------------------|-----------|--------------------------------------------------|------------------------------------|
| customer_id       | Integer   | Unique identifier for each customer              | 1001, 1002, 1003                  |
| first_name        | String    | Customer's first name                            | John, Jane, Robert                |
| last_name         | String    | Customer's last name                             | Smith, Doe, Johnson               |
| email             | String    | Customer's email address                         | john.smith@example.com            |
| phone             | String    | Customer's phone number                          | 555-0101, 555-0102                |
| address           | String    | Street address                                   | 123 Main St, 456 Oak Ave          |
| city              | String    | City of residence                                | New York, Los Angeles             |
| state             | String    | State/Province code                              | NY, CA, TX                        |
| postal_code       | String    | Postal/ZIP code                                  | 10001, 90001                      |
| country           | String    | Country code                                     | USA                               |
| date_of_birth     | Date      | Customer's date of birth (YYYY-MM-DD)            | 1985-03-15, 1990-07-22            |
| join_date         | Date      | Date when customer joined (YYYY-MM-DD)           | 2020-01-15, 2020-02-20            |
| last_purchase_date| Date      | Date of most recent purchase (YYYY-MM-DD)        | 2023-07-10, 2023-07-12            |
| total_purchases   | Integer   | Total number of purchases made                   | 45, 32, 78                        |
| avg_order_value   | Decimal   | Average value of customer orders                 | 125.50, 89.99, 210.25             |
| is_active         | Boolean   | Whether the customer is currently active         | True, False                       |
| segment           | String    | Customer segment/category                        | Premium, Standard, Basic, New     |
| preferred_category| String    | Customer's preferred product category            | Electronics, Clothing, Home & Kitchen |
| credit_score      | Integer   | Customer's credit score                          | 750, 680, 820                     |
| account_balance   | Decimal   | Current account balance                          | 1250.75, 875.30, 3420.50          |

### Data Quality Test Cases

This dataset includes various data quality aspects that can be tested:

1. **Completeness Checks**
   - Missing values in required fields
   - Incomplete records

2. **Validity Checks**
   - Email format validation
   - Phone number format
   - Date format and validity
   - State/Country code validation

3. **Consistency Checks**
   - Date consistency (join_date <= last_purchase_date)
   - Age validation based on date_of_birth
   - Numeric range validation (credit_score, account_balance)

4. **Uniqueness Checks**
   - Duplicate customer_ids
   - Duplicate email addresses

5. **Pattern Matching**
   - Name format (no numbers/special characters)
   - Postal code format

6. **Business Rules**
   - Active customers should have account_balance >= 0
   - Premium customers should have credit_score >= 700
   - Last purchase date should not be in the future

### How to Use

1. Upload the CSV file to your S3 bucket:
   ```bash
   aws s3 cp sample_customers.csv s3://your-bucket-name/input/customers/
   ```

2. Configure your data quality job to read from this file:
   ```python
   source_path = "s3://your-bucket-name/input/customers/sample_customers.csv"
   ```

3. Run your data quality checks and verify the results.

### Notes
- This is synthetic data generated for testing purposes only.
- All personal information is fictional and any resemblance to real persons is coincidental.
- The data includes intentional variations and potential issues to test data quality rules.

## Adding More Test Data

To add more test cases, create additional CSV files in this directory following the same structure. Consider including:
- Edge cases
- Erroneous data for negative testing
- Different data formats
- Large datasets for performance testing

## License

This test data is provided under the MIT License.
