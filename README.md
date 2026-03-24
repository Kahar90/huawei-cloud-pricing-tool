# Huawei Cloud Pricing Tool

A Streamlit-based application for mapping VM and database specifications to Huawei Cloud ECS flavors and calculating costs.

## Features

- **Excel Template Loading**: Upload standardized Excel files with VM and database specifications
- **Flavor Mapping**: Automatically map vCPUs and RAM requirements to the best matching Huawei Cloud flavors
- **Pricing Models**: Support for Hourly (Pay-per-use), Monthly, and Yearly pricing
- **Database Support**: RDS for MySQL and RDS for PostgreSQL with Single/HA deployment options
- **Storage Cost Calculation**: Separate storage cost calculation for SSD, HighIO, and UltraHighIO
- **Summary Reports**: Cost summaries by resource type, flavor family, and deployment mode
- **Export Results**: Download enriched Excel files with mapping results and costs

## Current Region

**AP-Jakarta** (`ap-southeast-3`) - Region selection is disabled in this version.

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Install Dependencies

```bash
pip install -r requirements.txt
```

## Running the Application

### Local Development

```bash
streamlit run app/huawei_pricing_app.py
```

The application will open in your web browser at `http://localhost:8501`

## Building Executable

To create a standalone Windows executable:

```bash
build_exe.bat
```

The executable will be created in the `dist/` folder.

## Usage

### 1. Download Template

Click the "Download Template" button in the sidebar to get the standardized Excel template.

### 2. Fill in Specifications

Complete the template with your VM and database specifications:

| Column | Description | Required | Values |
|--------|-------------|----------|--------|
| Resource Type | Type of resource | Yes | ECS, Database |
| vCPUs | Number of virtual CPUs | Yes | Integer (e.g., 2, 4, 8) |
| RAM (GB) | Memory in gigabytes | Yes | Integer (e.g., 8, 16, 32) |
| Storage (GB) | Storage size in gigabytes | Yes | Integer (e.g., 100, 200) |
| Storage Type | Type of storage | Yes | SSD, HighIO, UltraHighIO |
| Quantity | Number of instances | Yes | Integer (default: 1) |
| Desired Tier | Preferred flavor family (ECS only) | No | general, compute, memory |
| DB Type | Database type (Database only) | No | mysql, postgresql |
| Deployment | Deployment mode (Database only) | No | single, ha |

### 3. Upload and Process

1. Upload the completed Excel file
2. Select the pricing model (Hourly, Monthly, or Yearly)
3. Set default database type and deployment mode (for rows without these values)
4. Click "Run Calculation"

### 4. Review Results

- **Cost Summary**: Total monthly and yearly costs, total instances, resources needing review
- **Detailed Results**: Full mapping results with compute and storage costs
- **Download**: Export results as Excel file with multiple sheets

## Data Files

All pricing and flavor data is stored in JSON files under `app/data/`:

| File | Purpose |
|------|---------|
| ecs_pricing.json | ECS flavors with combined pricing |
| db_pricing.json | Database flavors with Single/HA pricing |
| storage_pricing.json | Storage pricing per GB |

### ECS Pricing Format (`ecs_pricing.json`)

```json
{
  "region": "ap-southeast-3",
  "region_name": "AP-Jakarta",
  "flavors": [
    {
      "name": "s6.large.2",
      "family": "general",
      "vcpus": 2,
      "ram_gb": 8,
      "hourly": 0.042,
      "monthly": 28.00,
      "yearly": 302.40
    }
  ]
}
```

### Database Pricing Format (`db_pricing.json`)

```json
{
  "region": "ap-southeast-3",
  "region_name": "AP-Jakarta",
  "databases": {
    "mysql": [
      {
        "name": "rds.mysql.c6.large.4",
        "vcpus": 2,
        "ram_gb": 8,
        "pricing": {
          "single": {"hourly": 0.06, "monthly": 40.00, "yearly": 432.00},
          "ha": {"hourly": 0.12, "monthly": 80.00, "yearly": 864.00}
        }
      }
    ],
    "postgresql": [
      // similar structure
    ]
  }
}
```

### Storage Pricing Format (`storage_pricing.json`)

```json
{
  "region": "ap-southeast-3",
  "region_name": "AP-Jakarta",
  "types": [
    {"name": "SSD", "price_per_gb": 0.10},
    {"name": "HighIO", "price_per_gb": 0.15},
    {"name": "UltraHighIO", "price_per_gb": 0.20}
  ]
}
```

## Mapping Logic

### ECS Flavor Mapping

1. If `Desired Tier` is specified, filter flavors by family
2. Find exact match for vCPUs and RAM
3. If no exact match, find next larger vCPU with sufficient RAM
4. If no match found, mark as "Needs Review"

### Database Flavor Mapping

1. Select database type (MySQL or PostgreSQL)
2. Select deployment mode (Single or HA)
3. Find exact match for vCPUs and RAM
4. If no exact match, find next larger configuration
5. If no match found, mark as "Needs Review"

## Project Structure

```
vm-database-mapper-HWC/
├── app/
│   ├── huawei_pricing_app.py    # Main Streamlit application
│   ├── mapping_engine.py        # Flavor mapping logic
│   ├── pricing_calculator.py    # Cost calculation functions
│   └── data/
│       ├── ecs_pricing.json     # ECS flavors + pricing
│       ├── db_pricing.json      # Database flavors + pricing
│       └── storage_pricing.json # Storage pricing
├── templates/                   # (Generated by app)
├── requirements.txt
├── build_exe.bat
└── README.md
```

## Troubleshooting

### Common Issues

1. **Missing columns error**: Ensure your Excel file has all required columns
2. **Invalid Storage Type**: Use only SSD, HighIO, or UltraHighIO
3. **Invalid Resource Type**: Use only ECS or Database
4. **Database not mapping**: Add DB Type column with value "mysql" or "postgresql"

### Getting Help

For issues or feature requests, please contact the development team.

## License

Internal tool for Huawei Cloud pricing automation.