# Huawei Cloud Pricing Tool

A Streamlit-based desktop application for mapping VM and database specifications to Huawei Cloud ECS flavors and calculating comprehensive costs.

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/streamlit-1.28+-red.svg)](https://streamlit.io/)
[![License](https://img.shields.io/badge/license-Internal-green.svg)]()

---

![Screenshot Placeholder](docs/screenshot.png)
*Main interface showing the pricing calculation results*

---

## Quick Start

### For Windows Users (Executable)

1. **Download** the latest `HuaweiCloudPricingTool.exe` from the releases page
2. **Double-click** to run the application
3. **Download the template** from the sidebar
4. **Fill in** your resource specifications
5. **Upload** and click "Run Calculation"

### For Developers (Python Source)

```bash
# Clone the repository
git clone <repository-url>
cd vm-database-mapper-HWC

# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run app/huawei_pricing_app.py
```

The application will open in your browser at `http://localhost:8501`

---

## Features

| Feature | Description |
|---------|-------------|
| **Excel Template Loading** | Upload standardized Excel files with VM, database, and storage specifications |
| **Automatic Flavor Mapping** | Maps vCPUs and RAM requirements to the best matching Huawei Cloud ECS and RDS flavors |
| **Multi-Resource Support** | Handles ECS (VMs), RDS (MySQL/PostgreSQL), and OBS (Object Storage) |
| **Flexible Pricing Models** | Calculate costs for Hourly (Pay-per-use), Monthly, or Yearly billing |
| **Database Deployment Options** | Supports both Single and High Availability (HA) deployment modes |
| **Storage Cost Calculation** | Calculates costs for SSD, HighIO, UltraHighIO, and GeneralSSDv2 storage types |
| **OBS Cost Modeling** | Full Object Storage cost calculation including storage, requests, retrieval, and traffic |
| **Summary Reports** | Cost breakdowns by resource type, flavor family, and deployment mode |
| **Excel Export** | Download enriched results with multiple sheets for analysis |
| **"Needs Review" Flagging** | Automatically flags resources that require manual review |

---

## Installation

### Windows (Recommended)

1. Download `HuaweiCloudPricingTool.exe` from the latest release
2. Place it in your desired folder (e.g., `C:\Tools\HuaweiCloudPricing\`)
3. Create a shortcut on your desktop for easy access
4. Double-click to launch

No installation required. The executable is self-contained.

### From Source

**Prerequisites:**
- Python 3.8 or higher
- pip package manager

**Steps:**

```bash
# 1. Clone or download the repository
git clone <repository-url>
cd vm-database-mapper-HWC

# 2. Create a virtual environment (recommended)
python -m venv venv

# 3. Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run the application
streamlit run app/huawei_pricing_app.py
```

---

## Usage Guide

### Step 1: Launch the Application

- **Windows Executable:** Double-click `HuaweiCloudPricingTool.exe`
- **Python Source:** Run `streamlit run app/huawei_pricing_app.py`

### Step 2: Download the Template

1. Look for the "Download Template" button in the left sidebar
2. Click it to get a pre-formatted Excel file
3. Save it to your computer

### Step 3: Fill in Your Specifications

Open the template in Excel or Google Sheets and fill in your resource requirements. See the [Excel Template Documentation](#excel-template-documentation) section for detailed column descriptions.

### Step 4: Upload and Configure

1. Click "Browse files" in the sidebar to upload your completed Excel file
2. Select your preferred **Pricing Model**:
   - Hourly (Pay-per-use): Best for variable workloads
   - Monthly: Fixed monthly rate
   - Yearly: Annual commitment with best rates
3. If using Hourly pricing, adjust "Hours per Month" if needed (default: 730)
4. Set **Database Defaults** if your file has database resources without specified types

### Step 5: Run Calculation

Click the **"Run Calculation"** button. The app will:
- Map your specifications to Huawei Cloud flavors
- Calculate compute and storage costs
- Generate summary statistics

### Step 6: Review Results

The results page shows:
- **Cost Summary Cards:** Total monthly/yearly costs, instance counts, items needing review
- **Detailed Results Table:** Row-by-row breakdown with mapped flavors and costs
- **Download Button:** Export results as a multi-sheet Excel file

### Step 7: Download Results

Click "Download Enriched Excel" to save your results. The exported file includes:
- **Results sheet:** Complete mapping and cost data
- **Summary sheet:** High-level cost breakdown by service
- **ECS sheet:** ECS-specific results with flavor family breakdown
- **Database sheet:** Database results with type and deployment summaries
- **OBS sheet:** Object Storage results with cost component breakdown
- **Unmapped Resources sheet:** Items flagged for review

---

## Excel Template Documentation

### Column Reference Table

| Column | Required | Description | Valid Values | Example |
|--------|----------|-------------|--------------|---------|
| **Resource Type** | Yes | Type of cloud resource | `ECS`, `Database`, `OBS` | `ECS` |
| **vCPUs** | Yes* | Number of virtual CPUs | Integer (0 for OBS) | `4` |
| **RAM (GB)** | Yes* | Memory in gigabytes | Integer (0 for OBS) | `16` |
| **Storage (GB)** | Yes | Storage size in gigabytes | Integer | `200` |
| **Storage Type** | Yes | Storage type or class | See below | `SSD` |
| **Region** | No | Huawei Cloud region | `ap-southeast-3` (default) | `ap-southeast-3` |
| **Quantity** | No | Number of instances | Integer (default: 1) | `2` |
| **Desired Tier** | No | Preferred ECS flavor family | See ECS tiers below | `general-computing-plus` |
| **DB Type** | No** | Database engine type | `mysql`, `postgresql` | `mysql` |
| **Deployment** | No** | Database deployment mode | `single`, `ha` | `ha` |
| **Availability Zone** | No*** | OBS availability zone type | `single-az`, `multi-az` | `single-az` |
| **Requests Read** | No*** | Number of read requests | Integer | `10000` |
| **Requests Write** | No*** | Number of write requests | Integer | `5000` |
| **Requests Delete** | No*** | Number of delete requests | Integer | `1000` |
| **Data Retrieval GB** | No*** | Data retrieval volume in GB | Integer or Decimal | `100` |
| **Retrieval Type** | No*** | Archive retrieval type | `Standard`, `Urgent`, `DirectReading` | `Standard` |
| **Internet Outbound GB** | No*** | Internet outbound traffic in GB | Integer or Decimal | `500` |

\* Not required for OBS resources (set to 0)
\** Required for Database resources if not using defaults
\*** Required for OBS resources only

### Storage Types by Resource

**ECS and Database (Block Storage):**
- `SSD` - Standard SSD storage
- `HighIO` - High I/O performance
- `UltraHighIO` - Ultra-high I/O performance
- `GeneralSSDv2` - General purpose SSD v2
- `ExtremeSSD` - Extreme performance SSD

**OBS (Object Storage Classes):**
- `Standard` - Frequently accessed data
- `InfrequentAccess` - Infrequently accessed data
- `Archive` - Long-term archive storage
- `DeepArchive` - Deep archive for rarely accessed data

### ECS Flavor Families (Desired Tier)

| Tier | Description | Use Case |
|------|-------------|----------|
| `general-computing-plus` | Balanced compute and memory | General purpose workloads |
| `general-computing-basic` | Entry-level balanced compute | Basic applications |
| `memory-optimized` | High memory-to-CPU ratio | Databases, caching |
| `disk-intensive` | High disk I/O performance | Big data, analytics |
| `large-memory` | Very high memory capacity | Large databases, SAP |

### Example Rows

**ECS Example:**
```
Resource Type: ECS
vCPUs: 4
RAM (GB): 16
Storage (GB): 200
Storage Type: SSD
Quantity: 2
Desired Tier: general-computing-plus
```

**Database Example:**
```
Resource Type: Database
vCPUs: 8
RAM (GB): 32
Storage (GB): 500
Storage Type: UltraHighIO
Quantity: 1
DB Type: postgresql
Deployment: ha
```

**OBS Example:**
```
Resource Type: OBS
vCPUs: 0
RAM (GB): 0
Storage (GB): 10000
Storage Type: Standard
Quantity: 1
Availability Zone: single-az
Requests Read: 100000
Requests Write: 50000
Internet Outbound GB: 1000
```

---

## Pricing Models Explained

### Hourly (Pay-per-use)

- **Best for:** Variable workloads, development environments, temporary resources
- **How it works:** You pay only for the hours you use
- **Calculation:** Hourly rate x Hours per month
- **Default hours:** 730 hours/month (full month)
- **Flexibility:** You can adjust hours per month in the sidebar (1-744 hours)

### Monthly

- **Best for:** Stable, predictable workloads
- **How it works:** Fixed monthly rate regardless of usage hours
- **Benefits:** Simpler billing, often lower cost than hourly for full-time usage
- **Commitment:** Month-to-month, no long-term contract

### Yearly

- **Best for:** Production workloads with long-term stability
- **How it works:** Annual commitment with upfront or monthly payment
- **Benefits:** Lowest per-month cost, significant savings over monthly pricing
- **Displayed as:** Monthly equivalent (yearly cost / 12) for comparison

### Cost Comparison Example

For an ECS `s6.large.2` instance (2 vCPUs, 8 GB RAM):

| Pricing Model | Cost Calculation | Monthly Cost |
|---------------|------------------|--------------|
| Hourly (730h) | $0.042 x 730 | $30.66 |
| Monthly | Fixed rate | $28.00 |
| Yearly (monthly equiv.) | $302.40 / 12 | $25.20 |

---

## Mapping Logic

### How ECS Flavors Are Matched

The application uses a tiered matching approach:

1. **Filter by Desired Tier** (if specified)
   - If you specify a `Desired Tier` (e.g., `memory-optimized`), only flavors from that family are considered
   - If no tier is specified or "any" is used, all flavors are considered

2. **Exact Match Search**
   - Looks for flavors with the exact vCPU count and sufficient RAM
   - AMD processors are preferred over Intel when multiple matches exist

3. **Upgrade Match (if no exact match)**
   - Finds the next larger vCPU count with sufficient RAM
   - Marks status as "Upgraded"

4. **Partial Match (last resort)**
   - Finds any flavor with sufficient RAM, even if vCPUs differ significantly
   - Marks status as "Needs Review - Partial Match"

5. **No Match**
   - If no suitable flavor is found, marks as "Needs Review"

### How Database Flavors Are Matched

1. **Select Database Type**
   - Uses the `DB Type` column value (MySQL or PostgreSQL)
   - Falls back to the default DB type from sidebar if not specified

2. **Select Deployment Mode**
   - Uses the `Deployment` column value (`single` or `ha`)
   - Falls back to the default deployment mode from sidebar if not specified

3. **Exact Match Search**
   - Looks for exact vCPU and RAM match in the appropriate database catalog

4. **Upgrade Match (if no exact match)**
   - Finds the next larger configuration
   - Marks status as "Upgraded"

5. **Partial Match or No Match**
   - Similar logic to ECS matching

### What "Needs Review" Means

Resources flagged with "Needs Review" require manual attention:

| Status | Meaning | Action Needed |
|--------|---------|---------------|
| **Needs Review** | No matching flavor found | Check your specifications, consider adjusting vCPUs/RAM |
| **Needs Review - Partial Match** | Suboptimal match found | Review the mapped flavor to ensure it meets requirements |
| **Unknown Resource Type** | Invalid Resource Type value | Use only `ECS`, `Database`, or `OBS` |
| **Unknown DB Type: X** | Invalid database type specified | Use only `mysql` or `postgresql` |

---

## Troubleshooting

### Common Errors and Solutions

#### Error: "Missing required columns: X, Y, Z"

**Cause:** Your Excel file doesn't have all the required columns.

**Solution:**
1. Download a fresh template from the sidebar
2. Copy your data into the template, ensuring all columns are filled
3. Required columns: Resource Type, vCPUs, RAM (GB), Storage (GB), Storage Type, Quantity

#### Error: "Invalid Resource Type: 'X'. Valid values: ECS, Database, OBS"

**Cause:** The Resource Type column contains an unrecognized value.

**Solution:**
- Check for typos (case-sensitive: use `ECS`, not `ecs`)
- Use only: `ECS`, `Database`, or `OBS`
- Remove any extra spaces before or after the value

#### Error: "Unknown Storage Type 'X'"

**Cause:** The Storage Type value doesn't match valid options.

**Solution:**
- For ECS/Database: Use `SSD`, `HighIO`, `UltraHighIO`, `GeneralSSDv2`, or `ExtremeSSD`
- For OBS: Use `Standard`, `InfrequentAccess`, `Archive`, or `DeepArchive`
- Check for extra spaces or typos

#### Warning: "Database not mapping"

**Cause:** Database rows don't have DB Type specified and no default is set.

**Solution:**
1. Add a `DB Type` column with values `mysql` or `postgresql`
2. Or set the Default DB Type in the sidebar before running calculation

#### Error: "Column 'X' contains invalid numeric values"

**Cause:** Non-numeric data in a column that should contain numbers.

**Solution:**
- Ensure vCPUs, RAM, Storage, and Quantity columns contain only numbers
- Remove any text, commas, or units (e.g., use `16` not `16 GB`)

#### Application Won't Start (Executable)

**Cause:** Missing dependencies or Windows blocking the file.

**Solution:**
1. Right-click the .exe file and select "Run as administrator"
2. If Windows Defender blocks it, click "More info" then "Run anyway"
3. Ensure you're running Windows 10 or later
4. Try running from source instead (see Installation section)

#### Browser Doesn't Open (Python Source)

**Cause:** Streamlit couldn't launch the browser automatically.

**Solution:**
1. Check the terminal for the URL (usually `http://localhost:8501`)
2. Open your browser manually and navigate to that URL
3. If the port is in use, specify a different port: `streamlit run app/huawei_pricing_app.py --server.port 8502`

### FAQ

**Q: Can I use this for regions other than AP-Jakarta?**
A: Currently, the tool is locked to AP-Jakarta (`ap-southeast-3`). The region can be changed by modifying the pricing JSON files in `app/data/`.

**Q: How often are the prices updated?**
A: Prices are embedded in the JSON data files. Contact your administrator to update pricing data from Huawei Cloud's latest price lists.

**Q: Can I save my configuration settings?**
A: Settings like default DB type and pricing model reset each session. Consider documenting your preferred settings in a text file.

**Q: What file formats are supported?**
A: Only Excel files (.xlsx and .xls) are supported for upload. The export is always .xlsx format.

**Q: Can I process multiple files at once?**
A: No, process one file at a time. For batch processing, consider writing a Python script using the underlying modules.

**Q: Are the costs in USD?**
A: Yes, all costs are displayed in US Dollars ($).

**Q: Why is the Yearly cost shown as a monthly equivalent?**
A: To make comparison easier across pricing models, yearly costs are divided by 12. The actual yearly cost is 12x the displayed amount.

---

## File Structure

```
vm-database-mapper-HWC/
├── app/                              # Main application code
│   ├── huawei_pricing_app.py         # Streamlit UI and main logic
│   ├── mapping_engine.py             # Flavor matching algorithms
│   ├── pricing_calculator.py         # Cost calculation functions
│   ├── __init__.py                   # Package initialization
│   └── data/                         # Pricing data files
│       ├── ecs_pricing.json          # ECS flavors and pricing
│       ├── db_pricing.json           # RDS flavors and pricing
│       ├── storage_pricing.json      # Block storage pricing
│       └── oss_pricing.json          # Object Storage pricing
├── templates/                        # Generated templates (runtime)
├── tests/                            # Test files
│   ├── README.md                     # Testing documentation
│   └── generate_comprehensive_test.py # Test data generator
├── requirements.txt                  # Python dependencies
├── build_exe.bat                     # Windows executable builder
├── BRANCHING.md                      # Git branching strategy
└── README.md                         # This file
```

### Key Files Explained

| File | Purpose |
|------|---------|
| `app/huawei_pricing_app.py` | Main entry point, Streamlit web interface |
| `app/mapping_engine.py` | Logic for matching specifications to flavors |
| `app/pricing_calculator.py` | Cost computation for all resource types |
| `app/data/*.json` | Pricing data from Huawei Cloud |
| `requirements.txt` | List of Python packages to install |
| `build_exe.bat` | Script to create Windows executable |

---

## Building from Source

### Prerequisites

- Python 3.8 or higher
- pip
- Windows (for .exe build)
- PyInstaller (`pip install pyinstaller`)

### Build Steps

1. **Ensure all dependencies are installed:**
   ```bash
   pip install -r requirements.txt
   pip install pyinstaller
   ```

2. **Run the build script:**
   ```bash
   build_exe.bat
   ```

   Or manually:
   ```bash
   pyinstaller --onefile --windowed --add-data "app/data;data" --add-data "templates;templates" app/huawei_pricing_app.py
   ```

3. **Find your executable:**
   - The compiled executable will be in the `dist/` folder
   - File name: `huawei_pricing_app.exe`
   - File size: approximately 200-300 MB (includes Python runtime)

4. **Distribute:**
   - Copy `huawei_pricing_app.exe` from the `dist/` folder
   - No other files needed, it's self-contained
   - Users don't need Python installed

### Build Options Explained

| Option | Description |
|--------|-------------|
| `--onefile` | Creates a single .exe file (easier distribution) |
| `--windowed` | No console window appears (GUI mode) |
| `--add-data "app/data;data"` | Includes pricing data files in the executable |
| `--add-data "templates;templates"` | Includes template folder |

### Troubleshooting Builds

**Error: "PyInstaller not found"**
```bash
pip install pyinstaller
```

**Error: "Failed to execute script"**
- Check that all data files exist in `app/data/`
- Verify the `--add-data` paths are correct
- Try building without `--windowed` to see error messages

**Executable is too large**
- This is normal, PyInstaller bundles the entire Python interpreter
- Consider using UPX compression (install UPX and add `--upx-dir` flag)

---

## Data Files Reference

### ECS Pricing Format (`ecs_pricing.json`)

```json
{
  "region": "ap-southeast-3",
  "region_name": "AP-Jakarta",
  "flavors": [
    {
      "name": "s6.large.2",
      "family": "general-computing-plus",
      "cpu_type": "Intel",
      "generation": "6",
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
    "postgresql": [...]
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
    {"name": "UltraHighIO", "price_per_gb": 0.20},
    {"name": "GeneralSSDv2", "price_per_gb": 0.12},
    {"name": "ExtremeSSD", "price_per_gb": 0.25}
  ]
}
```

### OBS Pricing Format (`oss_pricing.json`)

The OBS pricing file contains detailed pricing for storage classes, requests, data retrieval, and traffic. See the full file for complete structure.

---

## Support

For issues, questions, or feature requests:

1. Check the [Troubleshooting](#troubleshooting) section above
2. Review the [FAQ](#faq) for common questions
3. Contact the development team with:
   - Your operating system and version
   - Application version
   - Description of the issue
   - Steps to reproduce
   - Any error messages

---

## License

Internal tool for Huawei Cloud pricing automation.

Copyright (c) 2024. All rights reserved.

---

## Changelog

### Version 1.0
- Initial release
- Support for ECS, RDS (MySQL/PostgreSQL), and OBS
- Hourly, Monthly, and Yearly pricing models
- Excel import/export functionality
- Windows executable build support
