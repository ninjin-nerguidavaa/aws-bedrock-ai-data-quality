# Test Data for AWS Data Quality Bots

This directory contains sample data files and documentation for testing the AWS Data Quality Bots project. The test data is designed to validate various data quality rules and edge cases.

## Sample Dataset: Customer Data

File: `sample_customers.csv`

### Schema Definition

The dataset contains synthetic customer information with the following schema:

| Column Name       | Data Type | Nullable | Description                                      | Example Values                     |
|-------------------|-----------|----------|--------------------------------------------------|------------------------------------|
| customer_id       | BIGINT    | No       | Unique identifier for each customer              | 1001, 1002, 1003                  |
| first_name        | STRING    | No       | Customer's first name                            | John, Jane, Robert                |
| last_name         | STRING    | No       | Customer's last name                             | Smith, Doe, Johnson               |
| email             | STRING    | No       | Customer's email address                         | john.smith@example.com            |
| phone             | STRING    | Yes      | Customer's phone number                          | 555-0101, 555-0102                |
| address           | STRING    | Yes      | Street address                                   | 123 Main St, 456 Oak Ave          |
| city              | STRING    | Yes      | City of residence                                | New York, Los Angeles             |
| state             | STRING    | Yes      | State/Province code (2-letter)                   | NY, CA, TX                        |
| postal_code       | STRING    | Yes      | Postal/ZIP code                                  | 10001, 90001                      |
| country           | STRING    | No       | Country code (ISO 2-letter)                      | US, CA, UK                        |
| date_of_birth     | DATE      | No       | Customer's date of birth                         | 1985-03-15, 1990-07-22            |
| join_date         | TIMESTAMP | No       | Date when customer joined                        | 2020-01-15 10:30:00               |
| last_purchase_date| TIMESTAMP | Yes      | Date of most recent purchase                     | 2023-07-10 14:22:00               |
| total_purchases   | INT       | No       | Total number of purchases made                   | 45, 32, 78                        |
| avg_order_value   | DECIMAL(10,2) | No    | Average value of customer orders                 | 125.50, 89.99, 210.25             |
| is_active         | BOOLEAN   | No       | Whether the customer is currently active         | true, false                       |
| segment           | STRING    | No       | Customer segment/category                        | PREMIUM, STANDARD, BASIC, NEW     |
| preferred_category| STRING    | Yes      | Customer's preferred product category            | ELECTRONICS, CLOTHING, HOME_GOODS |
| credit_score      | INT       | Yes      | Customer's credit score (300-850)                | 750, 680, 820                     |
| account_balance   | DECIMAL(12,2) | Yes   | Current account balance (USD)                    | 1250.75, 875.30, 3420.50          |

### Data Quality Rules

The dataset includes the following data quality validations:

#### 1. Completeness Rules
- **CUSTOMER_ID_NOT_NULL**: Customer ID must be provided
- **NAME_NOT_NULL**: First and last names are required
- **EMAIL_NOT_NULL**: Email address is required
- **DOB_NOT_NULL**: Date of birth is required
- **JOIN_DATE_NOT_NULL**: Join date is required

#### 2. Validity Rules
- **VALID_EMAIL_FORMAT**: Email must match standard email pattern
- **VALID_PHONE_FORMAT**: Phone must match (XXX) XXX-XXXX or XXX-XXX-XXXX
- **VALID_STATE_CODE**: State must be a valid 2-letter US state code
- **VALID_COUNTRY_CODE**: Country must be a valid 2-letter ISO code
- **VALID_CREDIT_SCORE**: Credit score must be between 300 and 850
- **POSITIVE_ACCOUNT_BALANCE**: Account balance cannot be negative

#### 3. Consistency Rules
- **JOIN_DATE_BEFORE_TODAY**: Join date must be in the past
- **LAST_PURCHASE_AFTER_JOIN**: Last purchase date must be after join date
- **VALID_AGE_RANGE**: Customer must be between 18 and 120 years old
- **ACTIVE_CUSTOMER_RECORDS**: Active customers must have made at least one purchase

#### 4. Business Rules
- **PREMIUM_SEGMENT_RULE**: Premium customers must have credit score ≥ 700
- **ACTIVE_ACCOUNT_BALANCE**: Active accounts must have balance ≥ 0
- **PURCHASE_HISTORY_CONSISTENCY**: Total purchases should be consistent with order history

### Sample Data Generation

To generate additional test data with variations for testing:

```python
import pandas as pd
import numpy as np
from faker import Faker
from datetime import datetime, timedelta
import random

fake = Faker()

def generate_customers(num_records=100):
    customers = []
    segments = ['PREMIUM', 'STANDARD', 'BASIC', 'NEW']
    categories = ['ELECTRONICS', 'CLOTHING', 'HOME_GOODS', 'BEAUTY', None]
    
    for i in range(1, num_records + 1):
        join_date = fake.date_time_between(start_date='-5y', end_date='now')
        last_purchase = fake.date_time_between(start_date=join_date) if random.random() > 0.1 else None
        total_purchases = random.randint(0, 100) if last_purchase else 0
        
        customer = {
            'customer_id': 1000 + i,
            'first_name': fake.first_name(),
            'last_name': fake.last_name(),
            'email': fake.email(),
            'phone': f"({random.randint(100, 999)}) {random.randint(100, 999)}-{random.randint(1000, 9999)}",
            'address': fake.street_address(),
            'city': fake.city(),
            'state': fake.state_abbr(),
            'postal_code': fake.zipcode(),
            'country': 'US',
            'date_of_birth': fake.date_of_birth(minimum_age=18, maximum_age=90).strftime('%Y-%m-%d'),
            'join_date': join_date.strftime('%Y-%m-%d %H:%M:%S'),
            'last_purchase_date': last_purchase.strftime('%Y-%m-%d %H:%M:%S') if last_purchase else None,
            'total_purchases': total_purchases,
            'avg_order_value': round(random.uniform(10.0, 500.0), 2),
            'is_active': random.choice([True, False]),
            'segment': random.choice(segments),
            'preferred_category': random.choice(categories),
            'credit_score': random.randint(300, 850) if random.random() > 0.1 else None,
            'account_balance': round(random.uniform(-100.0, 10000.0), 2)
        }
        customers.append(customer)
    
    return pd.DataFrame(customers)

# Generate and save sample data
df = generate_customers(1000)
df.to_csv('sample_customers_large.csv', index=False)
```

### Testing Guidelines

1. **Unit Testing**:
   - Test individual validation rules in isolation
   - Verify edge cases (null values, boundary conditions)
   - Test with both valid and invalid data

2. **Integration Testing**:
   - Test the complete data quality pipeline
   - Verify error handling and logging
   - Test with different file formats and sizes

3. **Performance Testing**:
   - Test with large datasets (>1M records)
   - Monitor execution time and resource usage
   - Test concurrent data processing
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
