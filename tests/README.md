# Test Files for Huawei Cloud Pricing Tool

## Overview

This directory contains test files and generators for the Huawei Cloud Pricing Tool.

## Files

### `generate_comprehensive_test.py`
A Python script that generates comprehensive test Excel files with various configurations:

- **ECS entries (20)**: Various flavors, storage types, and quantities
- **Database entries (20)**: MySQL and PostgreSQL with single and HA deployments
- **OSS entries (10)**: Different storage classes, AZ types, and access patterns

### Generated Test Files
Test files are named with timestamps: `comprehensive_test_YYYYMMDD_HHMMSS.xlsx`

## Usage

### Generate a New Test File

```bash
python tests/generate_comprehensive_test.py
```

This will create a new Excel file in the `tests/` directory with randomized test data.

### Using Test Files

1. Run the Streamlit app:
   ```bash
   streamlit run app/huawei_pricing_app.py
   ```

2. Upload the generated test file through the web interface

3. Select your pricing model (Hourly, Monthly, or Yearly)

4. Click "Run Calculation" to see the results

## Test Coverage

### ECS Test Cases
- Minimum resources (1 vCPU, 2 GB RAM)
- Standard configurations (2-32 vCPUs, 4-128 GB RAM)
- Large instances (32 vCPUs, 128 GB RAM)
- All storage types (SSD, HighIO, UltraHighIO, GeneralSSDv2, ExtremeSSD)
- Various quantities (1-50 instances)
- Different flavor families (general-computing-plus, memory-optimized, etc.)

### Database Test Cases
- MySQL and PostgreSQL
- Single and HA deployments
- Various sizes (2-16 vCPUs, 4-64 GB RAM)
- Different storage configurations

### OSS Test Cases
- Storage classes: Standard, InfrequentAccess, Archive, DeepArchive
- AZ types: single-az, multi-az
- Various request patterns (reads, writes, deletes)
- Data retrieval scenarios (for Archive/DeepArchive)
- Internet outbound traffic

## Edge Cases Covered

- Empty values
- Zero quantities
- Maximum values
- Mixed resource types
- Invalid/unmappable configurations (for testing "Needs Review" status)
