"""
Generate comprehensive test Excel file for Huawei Cloud Pricing Tool
Covers: ECS, Database, OSS with various edge cases and configurations
"""

import pandas as pd
import random
from datetime import datetime

# ECS configurations
ECS_FLAVOR_FAMILIES = [
    'general-computing-plus',
    'general-computing-basic', 
    'memory-optimized',
    'compute-optimized',
    'disk-intensive',
    'large-memory'
]

ECS_VCPUS_RAM = [
    (2, 8), (4, 8), (4, 16), (8, 16), (8, 32), (16, 32), (16, 64), (32, 64), (32, 128)
]

STORAGE_TYPES = ['SSD', 'HighIO', 'UltraHighIO', 'GeneralSSDv2', 'ExtremeSSD']

# Database configurations
DB_TYPES = ['mysql', 'postgresql']
DEPLOYMENTS = ['single', 'ha']
DB_VCPUS_RAM = [
    (2, 8), (4, 8), (4, 16), (8, 16), (8, 32), (16, 64)
]

# OSS configurations
OSS_STORAGE_CLASSES = ['Standard', 'InfrequentAccess', 'Archive', 'DeepArchive']
AZ_TYPES = ['single-az', 'multi-az']
RETRIEVAL_TYPES = ['Standard', 'Urgent', 'DirectReading', '']

def generate_ecs_entries(count=20):
    """Generate ECS test entries with various configurations"""
    entries = []
    
    # Edge cases
    entries.append({
        'Resource Type': 'ECS',
        'vCPUs': 2,
        'RAM (GB)': 8,
        'Storage (GB)': 100,
        'Storage Type': 'SSD',
        'Region': 'ap-southeast-3',
        'Quantity': 1,
        'Desired Tier': 'general-computing-plus',
        'DB Type': '',
        'Deployment': '',
        'Availability Zone': '',
        'Requests Read': '',
        'Requests Write': '',
        'Requests Delete': '',
        'Data Retrieval GB': '',
        'Retrieval Type': '',
        'Internet Outbound GB': ''
    })
    
    # Minimum resources
    entries.append({
        'Resource Type': 'ECS',
        'vCPUs': 1,
        'RAM (GB)': 2,
        'Storage (GB)': 20,
        'Storage Type': 'SSD',
        'Region': 'ap-southeast-3',
        'Quantity': 1,
        'Desired Tier': 'general-computing-basic',
        'DB Type': '',
        'Deployment': '',
        'Availability Zone': '',
        'Requests Read': '',
        'Requests Write': '',
        'Requests Delete': '',
        'Data Retrieval GB': '',
        'Retrieval Type': '',
        'Internet Outbound GB': ''
    })
    
    # Large instance
    entries.append({
        'Resource Type': 'ECS',
        'vCPUs': 32,
        'RAM (GB)': 128,
        'Storage (GB)': 2000,
        'Storage Type': 'UltraHighIO',
        'Region': 'ap-southeast-3',
        'Quantity': 1,
        'Desired Tier': 'large-memory',
        'DB Type': '',
        'Deployment': '',
        'Availability Zone': '',
        'Requests Read': '',
        'Requests Write': '',
        'Requests Delete': '',
        'Data Retrieval GB': '',
        'Retrieval Type': '',
        'Internet Outbound GB': ''
    })
    
    # High quantity
    entries.append({
        'Resource Type': 'ECS',
        'vCPUs': 4,
        'RAM (GB)': 16,
        'Storage (GB)': 200,
        'Storage Type': 'HighIO',
        'Region': 'ap-southeast-3',
        'Quantity': 50,
        'Desired Tier': 'compute-optimized',
        'DB Type': '',
        'Deployment': '',
        'Availability Zone': '',
        'Requests Read': '',
        'Requests Write': '',
        'Requests Delete': '',
        'Data Retrieval GB': '',
        'Retrieval Type': '',
        'Internet Outbound GB': ''
    })
    
    # Various storage types
    for storage_type in STORAGE_TYPES:
        entries.append({
            'Resource Type': 'ECS',
            'vCPUs': 8,
            'RAM (GB)': 32,
            'Storage (GB)': 500,
            'Storage Type': storage_type,
            'Region': 'ap-southeast-3',
            'Quantity': random.randint(1, 10),
            'Desired Tier': random.choice(ECS_FLAVOR_FAMILIES),
            'DB Type': '',
            'Deployment': '',
            'Availability Zone': '',
            'Requests Read': '',
            'Requests Write': '',
            'Requests Delete': '',
            'Data Retrieval GB': '',
            'Retrieval Type': '',
            'Internet Outbound GB': ''
        })
    
    # Random combinations for remaining entries
    remaining = count - len(entries)
    for _ in range(remaining):
        vcpus, ram = random.choice(ECS_VCPUS_RAM)
        entries.append({
            'Resource Type': 'ECS',
            'vCPUs': vcpus,
            'RAM (GB)': ram,
            'Storage (GB)': random.choice([100, 200, 500, 1000, 2000]),
            'Storage Type': random.choice(STORAGE_TYPES),
            'Region': 'ap-southeast-3',
            'Quantity': random.randint(1, 20),
            'Desired Tier': random.choice(ECS_FLAVOR_FAMILIES),
            'DB Type': '',
            'Deployment': '',
            'Availability Zone': '',
            'Requests Read': '',
            'Requests Write': '',
            'Requests Delete': '',
            'Data Retrieval GB': '',
            'Retrieval Type': '',
            'Internet Outbound GB': ''
        })
    
    return entries

def generate_database_entries(count=20):
    """Generate Database test entries with various configurations"""
    entries = []
    
    # Edge cases
    entries.append({
        'Resource Type': 'Database',
        'vCPUs': 2,
        'RAM (GB)': 8,
        'Storage (GB)': 100,
        'Storage Type': 'SSD',
        'Region': 'ap-southeast-3',
        'Quantity': 1,
        'Desired Tier': '',
        'DB Type': 'mysql',
        'Deployment': 'single',
        'Availability Zone': '',
        'Requests Read': '',
        'Requests Write': '',
        'Requests Delete': '',
        'Data Retrieval GB': '',
        'Retrieval Type': '',
        'Internet Outbound GB': ''
    })
    
    # MySQL HA
    entries.append({
        'Resource Type': 'Database',
        'vCPUs': 8,
        'RAM (GB)': 32,
        'Storage (GB)': 1000,
        'Storage Type': 'UltraHighIO',
        'Region': 'ap-southeast-3',
        'Quantity': 1,
        'Desired Tier': '',
        'DB Type': 'mysql',
        'Deployment': 'ha',
        'Availability Zone': '',
        'Requests Read': '',
        'Requests Write': '',
        'Requests Delete': '',
        'Data Retrieval GB': '',
        'Retrieval Type': '',
        'Internet Outbound GB': ''
    })
    
    # PostgreSQL Single
    entries.append({
        'Resource Type': 'Database',
        'vCPUs': 4,
        'RAM (GB)': 16,
        'Storage (GB)': 500,
        'Storage Type': 'HighIO',
        'Region': 'ap-southeast-3',
        'Quantity': 1,
        'Desired Tier': '',
        'DB Type': 'postgresql',
        'Deployment': 'single',
        'Availability Zone': '',
        'Requests Read': '',
        'Requests Write': '',
        'Requests Delete': '',
        'Data Retrieval GB': '',
        'Retrieval Type': '',
        'Internet Outbound GB': ''
    })
    
    # PostgreSQL HA
    entries.append({
        'Resource Type': 'Database',
        'vCPUs': 16,
        'RAM (GB)': 64,
        'Storage (GB)': 2000,
        'Storage Type': 'UltraHighIO',
        'Region': 'ap-southeast-3',
        'Quantity': 3,
        'Desired Tier': '',
        'DB Type': 'postgresql',
        'Deployment': 'ha',
        'Availability Zone': '',
        'Requests Read': '',
        'Requests Write': '',
        'Requests Delete': '',
        'Data Retrieval GB': '',
        'Retrieval Type': '',
        'Internet Outbound GB': ''
    })
    
    # Small MySQL
    entries.append({
        'Resource Type': 'Database',
        'vCPUs': 2,
        'RAM (GB)': 4,
        'Storage (GB)': 50,
        'Storage Type': 'SSD',
        'Region': 'ap-southeast-3',
        'Quantity': 1,
        'Desired Tier': '',
        'DB Type': 'mysql',
        'Deployment': 'single',
        'Availability Zone': '',
        'Requests Read': '',
        'Requests Write': '',
        'Requests Delete': '',
        'Data Retrieval GB': '',
        'Retrieval Type': '',
        'Internet Outbound GB': ''
    })
    
    # Random combinations for remaining entries
    remaining = count - len(entries)
    for _ in range(remaining):
        vcpus, ram = random.choice(DB_VCPUS_RAM)
        entries.append({
            'Resource Type': 'Database',
            'vCPUs': vcpus,
            'RAM (GB)': ram,
            'Storage (GB)': random.choice([100, 200, 500, 1000, 2000]),
            'Storage Type': random.choice(STORAGE_TYPES),
            'Region': 'ap-southeast-3',
            'Quantity': random.randint(1, 5),
            'Desired Tier': '',
            'DB Type': random.choice(DB_TYPES),
            'Deployment': random.choice(DEPLOYMENTS),
            'Availability Zone': '',
            'Requests Read': '',
            'Requests Write': '',
            'Requests Delete': '',
            'Data Retrieval GB': '',
            'Retrieval Type': '',
            'Internet Outbound GB': ''
        })
    
    return entries

def generate_oss_entries(count=10):
    """Generate OSS test entries with various configurations"""
    entries = []
    
    # Standard storage
    entries.append({
        'Resource Type': 'OSS',
        'vCPUs': '',
        'RAM (GB)': '',
        'Storage (GB)': 1000,
        'Storage Type': 'Standard',
        'Region': 'ap-southeast-3',
        'Quantity': 1,
        'Desired Tier': '',
        'DB Type': '',
        'Deployment': '',
        'Availability Zone': 'single-az',
        'Requests Read': 100000,
        'Requests Write': 50000,
        'Requests Delete': 10000,
        'Data Retrieval GB': 0,
        'Retrieval Type': '',
        'Internet Outbound GB': 500
    })
    
    # Infrequent Access
    entries.append({
        'Resource Type': 'OSS',
        'vCPUs': '',
        'RAM (GB)': '',
        'Storage (GB)': 5000,
        'Storage Type': 'InfrequentAccess',
        'Region': 'ap-southeast-3',
        'Quantity': 1,
        'Desired Tier': '',
        'DB Type': '',
        'Deployment': '',
        'Availability Zone': 'single-az',
        'Requests Read': 50000,
        'Requests Write': 20000,
        'Requests Delete': 5000,
        'Data Retrieval GB': 1000,
        'Retrieval Type': 'Standard',
        'Internet Outbound GB': 200
    })
    
    # Archive
    entries.append({
        'Resource Type': 'OSS',
        'vCPUs': '',
        'RAM (GB)': '',
        'Storage (GB)': 10000,
        'Storage Type': 'Archive',
        'Region': 'ap-southeast-3',
        'Quantity': 1,
        'Desired Tier': '',
        'DB Type': '',
        'Deployment': '',
        'Availability Zone': 'single-az',
        'Requests Read': 10000,
        'Requests Write': 5000,
        'Requests Delete': 1000,
        'Data Retrieval GB': 5000,
        'Retrieval Type': 'Urgent',
        'Internet Outbound GB': 100
    })
    
    # Deep Archive
    entries.append({
        'Resource Type': 'OSS',
        'vCPUs': '',
        'RAM (GB)': '',
        'Storage (GB)': 50000,
        'Storage Type': 'DeepArchive',
        'Region': 'ap-southeast-3',
        'Quantity': 1,
        'Desired Tier': '',
        'DB Type': '',
        'Deployment': '',
        'Availability Zone': 'multi-az',
        'Requests Read': 5000,
        'Requests Write': 2000,
        'Requests Delete': 500,
        'Data Retrieval GB': 10000,
        'Retrieval Type': 'DirectReading',
        'Internet Outbound GB': 50
    })
    
    # Multi-az Standard
    entries.append({
        'Resource Type': 'OSS',
        'vCPUs': '',
        'RAM (GB)': '',
        'Storage (GB)': 2000,
        'Storage Type': 'Standard',
        'Region': 'ap-southeast-3',
        'Quantity': 1,
        'Desired Tier': '',
        'DB Type': '',
        'Deployment': '',
        'Availability Zone': 'multi-az',
        'Requests Read': 200000,
        'Requests Write': 100000,
        'Requests Delete': 20000,
        'Data Retrieval GB': 0,
        'Retrieval Type': '',
        'Internet Outbound GB': 1000
    })
    
    # Random combinations for remaining entries
    remaining = count - len(entries)
    for _ in range(remaining):
        storage_class = random.choice(OSS_STORAGE_CLASSES)
        # Archive and DeepArchive have retrieval costs
        retrieval_gb = random.choice([0, 100, 500, 1000]) if 'Archive' in storage_class else 0
        retrieval_type = random.choice(RETRIEVAL_TYPES) if retrieval_gb > 0 else ''
        
        entries.append({
            'Resource Type': 'OSS',
            'vCPUs': '',
            'RAM (GB)': '',
            'Storage (GB)': random.choice([500, 1000, 5000, 10000, 50000]),
            'Storage Type': storage_class,
            'Region': 'ap-southeast-3',
            'Quantity': 1,
            'Desired Tier': '',
            'DB Type': '',
            'Deployment': '',
            'Availability Zone': random.choice(AZ_TYPES),
            'Requests Read': random.randint(1000, 500000),
            'Requests Write': random.randint(500, 200000),
            'Requests Delete': random.randint(100, 50000),
            'Data Retrieval GB': retrieval_gb,
            'Retrieval Type': retrieval_type,
            'Internet Outbound GB': random.choice([0, 50, 100, 500, 1000, 5000])
        })
    
    return entries

def main():
    """Generate comprehensive test Excel file"""
    print("Generating comprehensive test file...")
    
    # Generate entries
    ecs_entries = generate_ecs_entries(20)
    db_entries = generate_database_entries(20)
    oss_entries = generate_oss_entries(10)
    
    # Combine all entries
    all_entries = ecs_entries + db_entries + oss_entries
    
    # Shuffle to mix resource types
    random.shuffle(all_entries)
    
    # Create DataFrame
    df = pd.DataFrame(all_entries)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"comprehensive_test_{timestamp}.xlsx"
    
    # Save to Excel
    output_path = f"tests/{filename}"
    df.to_excel(output_path, index=False)
    
    print(f"\nTest file generated: {output_path}")
    print(f"\nSummary:")
    print(f"  - ECS entries: {len(ecs_entries)}")
    print(f"  - Database entries: {len(db_entries)}")
    print(f"  - OSS entries: {len(oss_entries)}")
    print(f"  - Total entries: {len(all_entries)}")
    print(f"\nFile saved to: {output_path}")
    print(f"\nYou can now test the app by uploading this file to the Streamlit interface.")

if __name__ == "__main__":
    main()
