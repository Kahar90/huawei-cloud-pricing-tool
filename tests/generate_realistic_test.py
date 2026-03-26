"""
Generate realistic test Excel file for Huawei Cloud Pricing Tool
Simple, realistic values for testing cost optimization feature
"""

import pandas as pd
from datetime import datetime

# Realistic ECS configurations (common use cases)
ECS_CONFIGS = [
    {'vCPUs': 2, 'RAM (GB)': 4, 'Storage (GB)': 100, 'Storage Type': 'SSD', 'Quantity': 2, 'Desired Tier': 'general-computing-plus'},
    {'vCPUs': 2, 'RAM (GB)': 8, 'Storage (GB)': 200, 'Storage Type': 'SSD', 'Quantity': 3, 'Desired Tier': 'general-computing-plus'},
    {'vCPUs': 4, 'RAM (GB)': 8, 'Storage (GB)': 200, 'Storage Type': 'HighIO', 'Quantity': 2, 'Desired Tier': 'general-computing-plus'},
    {'vCPUs': 4, 'RAM (GB)': 16, 'Storage (GB)': 500, 'Storage Type': 'SSD', 'Quantity': 1, 'Desired Tier': 'memory-optimized'},
    {'vCPUs': 8, 'RAM (GB)': 16, 'Storage (GB)': 500, 'Storage Type': 'UltraHighIO', 'Quantity': 2, 'Desired Tier': 'general-computing-plus'},
    {'vCPUs': 8, 'RAM (GB)': 32, 'Storage (GB)': 1000, 'Storage Type': 'SSD', 'Quantity': 1, 'Desired Tier': 'memory-optimized'},
    {'vCPUs': 16, 'RAM (GB)': 32, 'Storage (GB)': 1000, 'Storage Type': 'HighIO', 'Quantity': 1, 'Desired Tier': 'compute-optimized'},
    {'vCPUs': 16, 'RAM (GB)': 64, 'Storage (GB)': 2000, 'Storage Type': 'SSD', 'Quantity': 1, 'Desired Tier': 'memory-optimized'},
    {'vCPUs': 32, 'RAM (GB)': 64, 'Storage (GB)': 2000, 'Storage Type': 'ExtremeSSD', 'Quantity': 1, 'Desired Tier': 'compute-optimized'},
    {'vCPUs': 32, 'RAM (GB)': 128, 'Storage (GB)': 4000, 'Storage Type': 'SSD', 'Quantity': 1, 'Desired Tier': 'large-memory'},
]

# Realistic Database configurations
DB_CONFIGS = [
    {'vCPUs': 2, 'RAM (GB)': 8, 'Storage (GB)': 500, 'Storage Type': 'SSD', 'Quantity': 1, 'DB Type': 'mysql', 'Deployment': 'single'},
    {'vCPUs': 4, 'RAM (GB)': 16, 'Storage (GB)': 1000, 'Storage Type': 'UltraHighIO', 'Quantity': 1, 'DB Type': 'mysql', 'Deployment': 'ha'},
    {'vCPUs': 8, 'RAM (GB)': 32, 'Storage (GB)': 2000, 'Storage Type': 'SSD', 'Quantity': 1, 'DB Type': 'postgresql', 'Deployment': 'single'},
    {'vCPUs': 16, 'RAM (GB)': 64, 'Storage (GB)': 4000, 'Storage Type': 'HighIO', 'Quantity': 1, 'DB Type': 'postgresql', 'Deployment': 'ha'},
    {'vCPUs': 8, 'RAM (GB)': 16, 'Storage (GB)': 1000, 'Storage Type': 'SSD', 'Quantity': 2, 'DB Type': 'mysql', 'Deployment': 'single'},
]

# OBS configurations (2 rows, 500GB each)
OBS_CONFIGS = [
    {'Storage (GB)': 500, 'Storage Type': 'Standard', 'Quantity': 1, 'Availability Zone': 'single-az'},
    {'Storage (GB)': 500, 'Storage Type': 'Standard', 'Quantity': 1, 'Availability Zone': 'multi-az'},
]

def generate_realistic_test_file():
    """Generate realistic test data"""
    entries = []
    
    # Add ECS entries (10 rows)
    for config in ECS_CONFIGS:
        entry = {
            'Resource Type': 'ECS',
            'vCPUs': config['vCPUs'],
            'RAM (GB)': config['RAM (GB)'],
            'Storage (GB)': config['Storage (GB)'],
            'Storage Type': config['Storage Type'],
            'Region': 'ap-southeast-3',
            'Quantity': config['Quantity'],
            'Desired Tier': config['Desired Tier'],
            'DB Type': '',
            'Deployment': '',
            'Availability Zone': '',
            'Requests Read': '',
            'Requests Write': '',
            'Requests Delete': '',
            'Data Retrieval GB': '',
            'Retrieval Type': '',
            'Internet Outbound GB': ''
        }
        entries.append(entry)
    
    # Add Database entries (5 rows)
    for config in DB_CONFIGS:
        entry = {
            'Resource Type': 'Database',
            'vCPUs': config['vCPUs'],
            'RAM (GB)': config['RAM (GB)'],
            'Storage (GB)': config['Storage (GB)'],
            'Storage Type': config['Storage Type'],
            'Region': 'ap-southeast-3',
            'Quantity': config['Quantity'],
            'Desired Tier': '',
            'DB Type': config['DB Type'],
            'Deployment': config['Deployment'],
            'Availability Zone': '',
            'Requests Read': '',
            'Requests Write': '',
            'Requests Delete': '',
            'Data Retrieval GB': '',
            'Retrieval Type': '',
            'Internet Outbound GB': ''
        }
        entries.append(entry)
    
    # Add OBS entries (2 rows, 500GB each)
    for config in OBS_CONFIGS:
        entry = {
            'Resource Type': 'OBS',
            'vCPUs': 0,
            'RAM (GB)': 0,
            'Storage (GB)': config['Storage (GB)'],
            'Storage Type': config['Storage Type'],
            'Region': 'ap-southeast-3',
            'Quantity': config['Quantity'],
            'Desired Tier': '',
            'DB Type': '',
            'Deployment': '',
            'Availability Zone': config['Availability Zone'],
            'Requests Read': 10000,
            'Requests Write': 5000,
            'Requests Delete': 1000,
            'Data Retrieval GB': 100,
            'Retrieval Type': 'Standard',
            'Internet Outbound GB': 500
        }
        entries.append(entry)
    
    # Create DataFrame
    df = pd.DataFrame(entries)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'realistic_test_{timestamp}.xlsx'
    
    # Save to Excel
    output_path = f'/mnt/c/Users/nabil/github/vm-database-mapper-HWC/tests/{filename}'
    df.to_excel(output_path, index=False, sheet_name='Resources')
    
    print(f"✅ Generated realistic test file: tests/{filename}")
    print(f"\n📊 File contents:")
    print(f"   - ECS: 10 rows")
    print(f"   - Database: 5 rows")
    print(f"   - OBS: 2 rows (500GB each)")
    print(f"\n📈 Summary:")
    print(f"   Total resources: {len(df)}")
    print(f"\n💡 Use this file to test cost optimization!")
    
    return output_path

if __name__ == "__main__":
    generate_realistic_test_file()
