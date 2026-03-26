import streamlit as st
import pandas as pd
import os
from io import BytesIO
from typing import Dict, Optional, Tuple, List
from mapping_engine import (
    load_ecs_pricing, load_db_pricing, load_storage_pricing, load_oss_pricing,
    get_region, get_available_db_types, map_resources
)
from pricing_calculator import calculate_all_costs, compute_summary, create_output_excel, get_cost_savings_summary, create_optimized_excel, apply_x_mode

DEFAULT_REGION = "ap-southeast-3"
DEFAULT_REGION_NAME = "AP-Jakarta"

REQUIRED_COLUMNS = [
    'Resource Type', 'vCPUs', 'RAM (GB)', 'Storage (GB)',
    'Storage Type', 'Region', 'Quantity', 'Desired Tier'
]

def create_standard_template() -> pd.DataFrame:
    data = {
        'Resource Type': ['ECS', 'ECS', 'Database', 'ECS', 'Database', 'OBS'],
        'vCPUs': [2, 4, 4, 8, 2, 0],
        'RAM (GB)': [8, 16, 16, 32, 8, 0],
        'Storage (GB)': [100, 200, 500, 400, 100, 1000],
        'Storage Type': ['SSD', 'HighIO', 'UltraHighIO', 'GeneralSSDv2', 'HighIO', 'Standard'],
        'Region': [DEFAULT_REGION, DEFAULT_REGION, DEFAULT_REGION, DEFAULT_REGION, DEFAULT_REGION, DEFAULT_REGION],
        'Quantity': [1, 2, 1, 3, 1, 1],
        'Desired Tier': ['general-computing-plus', 'general-computing-plus', '', 'memory-optimized', '', ''],
        'DB Type': ['', '', 'mysql', '', 'postgresql', ''],
        'Deployment': ['', '', 'single', '', 'ha', ''],
        'Availability Zone': ['', '', '', '', '', 'single-az'],
        'Requests Read': [0, 0, 0, 0, 0, 10000],
        'Requests Write': [0, 0, 0, 0, 0, 5000],
        'Requests Delete': [0, 0, 0, 0, 0, 1000],
        'Data Retrieval GB': [0, 0, 0, 0, 0, 0],
        'Retrieval Type': ['', '', '', '', '', ''],
        'Internet Outbound GB': [0, 0, 0, 0, 0, 100]
    }
    return pd.DataFrame(data)

def validate_row(row: pd.Series, row_num: int) -> Tuple[bool, List[str]]:
    """
    Validate a single row and return detailed error messages.
    Returns (is_valid, list_of_errors).
    """
    errors = []
    resource_type = str(row.get('Resource Type', '')).strip()
    
    # Check Resource Type
    if not resource_type:
        errors.append(f"Row {row_num}: Resource Type is empty. Must be one of: ECS, Database, OBS")
    elif resource_type not in ['ECS', 'Database', 'OBS']:
        errors.append(f"Row {row_num}: Invalid Resource Type '{resource_type}'. Valid values: ECS, Database, OBS")
    
    # Check numeric values based on resource type
    if resource_type and resource_type != 'OBS':
        vcpus = row.get('vCPUs')
        if pd.isna(vcpus) or str(vcpus).strip() == '':
            errors.append(f"Row {row_num}: vCPUs is required for {resource_type} resources")
        else:
            try:
                vcpus_val = int(float(str(vcpus).strip()))
                if vcpus_val <= 0:
                    errors.append(f"Row {row_num}: vCPUs must be greater than 0, got {vcpus_val}")
            except (ValueError, TypeError):
                errors.append(f"Row {row_num}: vCPUs '{vcpus}' is not a valid number")
        
        ram = row.get('RAM (GB)')
        if pd.isna(ram) or str(ram).strip() == '':
            errors.append(f"Row {row_num}: RAM (GB) is required for {resource_type} resources")
        else:
            try:
                ram_val = int(float(str(ram).strip()))
                if ram_val <= 0:
                    errors.append(f"Row {row_num}: RAM (GB) must be greater than 0, got {ram_val}")
            except (ValueError, TypeError):
                errors.append(f"Row {row_num}: RAM (GB) '{ram}' is not a valid number")
    
    # Check Storage
    storage = row.get('Storage (GB)')
    if pd.isna(storage) or str(storage).strip() == '':
        errors.append(f"Row {row_num}: Storage (GB) is required")
    else:
        try:
            storage_val = int(float(str(storage).strip()))
            if storage_val < 0:
                errors.append(f"Row {row_num}: Storage (GB) cannot be negative, got {storage_val}")
        except (ValueError, TypeError):
            errors.append(f"Row {row_num}: Storage (GB) '{storage}' is not a valid number")
    
    # Check Storage Type
    stype = str(row.get('Storage Type', '')).strip()
    if not stype or stype == 'nan':
        errors.append(f"Row {row_num}: Storage Type is required")
    else:
        stype_lower = stype.lower().replace('-', '').replace(' ', '').replace('_', '')
        
        if resource_type == 'OBS':
            valid_oss = ['standard', 'infrequentaccess', 'archive', 'deeparchive']
            if stype_lower not in valid_oss:
                errors.append(f"Row {row_num}: Invalid OBS Storage Class '{stype}'. Valid: Standard, InfrequentAccess, Archive, DeepArchive")
        else:
            valid_block = ['ssd', 'highio', 'ultrahighio', 'generalssdv2', 'extremessd', 'generalpurposessd']
            if stype_lower not in valid_block:
                errors.append(f"Row {row_num}: Invalid Storage Type '{stype}'. Valid: SSD, HighIO, UltraHighIO, GeneralSSDv2, ExtremeSSD")
    
    # Check Quantity
    quantity = row.get('Quantity')
    if pd.notna(quantity) and str(quantity).strip() != '':
        try:
            qty_val = int(float(str(quantity).strip()))
            if qty_val <= 0:
                errors.append(f"Row {row_num}: Quantity must be greater than 0, got {qty_val}")
        except (ValueError, TypeError):
            errors.append(f"Row {row_num}: Quantity '{quantity}' is not a valid number")
    
    # Check Database-specific fields
    if resource_type == 'Database':
        db_type = str(row.get('DB Type', '')).strip()
        if db_type and db_type != 'nan':
            if db_type.lower() not in ['mysql', 'postgresql']:
                errors.append(f"Row {row_num}: Invalid DB Type '{db_type}'. Valid: mysql, postgresql")
        
        deployment = str(row.get('Deployment', '')).strip()
        if deployment and deployment != 'nan':
            if deployment.lower() not in ['single', 'ha']:
                errors.append(f"Row {row_num}: Invalid Deployment '{deployment}'. Valid: single, ha")
    
    return len(errors) == 0, errors


def validate_dataframe(df: pd.DataFrame) -> Tuple[bool, str, List[str]]:
    """
    Enhanced dataframe validation with detailed error messages.
    Returns (is_valid, summary_message, detailed_errors).
    """
    df_cols = list(df.columns)
    required_cols = ['Resource Type', 'vCPUs', 'RAM (GB)', 'Storage (GB)', 'Storage Type', 'Quantity']
    missing = [col for col in required_cols if col not in df_cols]
    
    if missing:
        suggestion = "Please download the template from the sidebar to see the correct format."
        return False, f"Missing required columns: {', '.join(missing)}. {suggestion}", []
    
    all_errors = []
    
    # Validate each row
    for idx, row in df.iterrows():
        row_num = idx + 1  # 1-based for user-friendliness
        is_valid, row_errors = validate_row(row, row_num)
        all_errors.extend(row_errors)
    
    if all_errors:
        error_count = len(all_errors)
        error_preview = all_errors[:5]  # Show first 5 errors
        summary = f"Found {error_count} validation error(s):"
        detailed = error_preview
        if error_count > 5:
            detailed.append(f"... and {error_count - 5} more errors")
        return False, summary, detailed
    
    # Convert numeric columns
    for col in ['vCPUs', 'RAM (GB)', 'Storage (GB)', 'Quantity']:
        if col in df_cols:
            if not pd.api.types.is_numeric_dtype(df[col]):
                try:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                except:
                    return False, f"Column '{col}' contains invalid numeric values", []
    
    # Convert string columns to string type
    for col in ['Resource Type', 'Storage Type', 'Desired Tier', 'DB Type', 'Deployment']:
        if col in df_cols:
            df[col] = df[col].astype(str)
    
    return True, f"Validation successful! {len(df)} row(s) ready for processing.", []

def process_file(
    df: pd.DataFrame,
    pricing_model: str,
    hours_per_month: float,
    default_db_type: str,
    default_deployment: str,
    ecs_data: Dict,
    db_data: Dict,
    storage_data: Dict,
    oss_data: Dict
) -> Tuple[pd.DataFrame, Dict]:
    mapping_results, ecs_flavors = map_resources(
        df, ecs_data, db_data, default_db_type, default_deployment
    )
    region = get_region(ecs_data)
    result_df = calculate_all_costs(
        df, mapping_results, ecs_flavors, region,
        pricing_model, hours_per_month,
        ecs_data, db_data, storage_data, oss_data
    )
    summary = compute_summary(result_df, pricing_model, hours_per_month)
    return result_df, summary

def to_excel_bytes(df: pd.DataFrame, summary: Dict) -> bytes:
    output = BytesIO()
    create_output_excel(df, summary, output)
    output.seek(0)
    return output.getvalue()


def create_enhanced_template() -> pd.DataFrame:
    data = {
        'Resource Type': ['ECS', 'ECS', 'Database', 'ECS', 'Database', 'OBS'],
        'vCPUs': [2, 4, 4, 8, 2, 0],
        'RAM (GB)': [8, 16, 16, 32, 8, 0],
        'Storage (GB)': [100, 200, 500, 400, 100, 1000],
        'Storage Type': ['SSD', 'HighIO', 'UltraHighIO', 'GeneralSSDv2', 'HighIO', 'Standard'],
        'Region': [DEFAULT_REGION, DEFAULT_REGION, DEFAULT_REGION, DEFAULT_REGION, DEFAULT_REGION, DEFAULT_REGION],
        'Quantity': [1, 2, 1, 3, 1, 1],
        'Desired Tier': ['general-computing-plus', 'general-computing-plus', '', 'memory-optimized', '', ''],
        'DB Type': ['', '', 'mysql', '', 'postgresql', ''],
        'Deployment': ['', '', 'single', '', 'ha', ''],
        'Availability Zone': ['', '', '', '', '', 'single-az'],
        'Requests Read': [0, 0, 0, 0, 0, 10000],
        'Requests Write': [0, 0, 0, 0, 0, 5000],
        'Requests Delete': [0, 0, 0, 0, 0, 1000],
        'Data Retrieval GB': [0, 0, 0, 0, 0, 0],
        'Retrieval Type': ['', '', '', '', '', ''],
        'Internet Outbound GB': [0, 0, 0, 0, 0, 100]
    }
    return pd.DataFrame(data)


def get_column_descriptions() -> Dict[str, str]:
    return {
        'Resource Type': 'Type of cloud resource: ECS (Virtual Machine), Database (RDS), or OBS (Object Storage)',
        'vCPUs': 'Number of virtual CPUs. Required for ECS and Database. Set to 0 for OBS.',
        'RAM (GB)': 'Memory in gigabytes. Required for ECS and Database. Set to 0 for OBS.',
        'Storage (GB)': 'Storage size in gigabytes. Required for all resource types.',
        'Storage Type': 'Storage class: SSD/HighIO/UltraHighIO/GeneralSSDv2/ExtremeSSD for ECS/DB; Standard/InfrequentAccess/Archive/DeepArchive for OBS',
        'Region': 'Huawei Cloud region. Currently locked to ap-southeast-3 (AP-Jakarta).',
        'Quantity': 'Number of instances. Default: 1.',
        'Desired Tier': 'ECS flavor family preference: general-computing-plus, general-computing-basic, memory-optimized, disk-intensive, large-memory',
        'DB Type': 'Database engine: mysql or postgresql. Only required for Database resources.',
        'Deployment': 'Database deployment mode: single or ha (High Availability). Only for Database resources.',
        'Availability Zone': 'OBS availability zone type: single-az or multi-az. Only for OBS resources.',
        'Requests Read': 'Number of read requests per month. Only for OBS resources.',
        'Requests Write': 'Number of write requests per month. Only for OBS resources.',
        'Requests Delete': 'Number of delete requests per month. Only for OBS resources.',
        'Data Retrieval GB': 'Data retrieval volume in GB per month. Only for Archive/DeepArchive OBS.',
        'Retrieval Type': 'Archive retrieval type: Standard, Urgent, or DirectReading. Only for archived OBS data.',
        'Internet Outbound GB': 'Internet outbound traffic in GB per month. Only for OBS resources.'
    }


def render_getting_started_tab():
    st.markdown("## 🚀 Getting Started with Huawei Cloud Pricing")
    st.markdown("Follow these 3 simple steps to calculate your cloud infrastructure costs:")
    st.markdown("---")
    
    st.markdown("### Step 1: Download the Template")
    st.markdown("Start with our pre-formatted Excel template. It includes examples for all resource types.")
    
    template_df = create_enhanced_template()
    st.markdown("**Preview of what you'll get:**")
    st.dataframe(template_df.head(3), use_container_width=True, hide_index=True)
    
    col1, col2 = st.columns([1, 3])
    with col1:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            template_df.to_excel(writer, sheet_name='Resources', index=False)
        output.seek(0)
        st.download_button(
            label="📥 Download Template",
            data=output.getvalue(),
            file_name="huawei_cloud_template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )
    
    with col2:
        st.info("💡 The template includes example rows for ECS (virtual machines), Database (RDS), and OBS (object storage). You can delete the examples and replace them with your actual requirements.")
    
    st.markdown("---")
    
    st.markdown("### Step 2: Fill with Your Data")
    st.markdown("Open the downloaded template in Excel or Google Sheets and fill in your resource specifications.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Option A: Manual Entry**")
        st.markdown("""
        - Open the template in Excel
        - Replace example rows with your data
        - Refer to the 🤖 LLM Guide tab for field descriptions
        """)
    with col2:
        st.markdown("**Option B: Use AI Assistant** 🤖 *(Recommended)*")
        st.markdown("""
        - Let ChatGPT, Claude, or your favorite AI fill the template
        - Check the 🤖 LLM Guide tab for ready-to-use prompts
        - Just describe your infrastructure in plain English
        """)
    
    st.markdown("---")
    
    st.markdown("### Step 3: Upload & Calculate")
    st.markdown("Return to the **📊 Calculator** tab, upload your filled template, and click 'Run Calculation' to get your pricing.")
    
    st.success("✨ That's it! You'll get detailed cost breakdowns, optimization suggestions, and downloadable reports.")
    
    st.markdown("---")
    
    with st.expander("📋 Quick Reference: Resource Types"):
        st.markdown("""
        **🖥️ ECS (Elastic Cloud Server)** — Virtual Machines
        - Use for: Web servers, application servers, general compute
        - Required fields: Resource Type, vCPUs, RAM (GB), Storage (GB), Storage Type
        - Example: 4 vCPUs, 16 GB RAM, 200 GB SSD
        
        **🗄️ Database (RDS)** — Managed Databases
        - Use for: MySQL or PostgreSQL databases
        - Required fields: All ECS fields + DB Type (mysql/postgresql), Deployment (single/ha)
        - Example: 4 vCPUs, 16 GB RAM, 500 GB UltraHighIO, MySQL, HA mode
        
        **📦 OBS (Object Storage Service)** — Cloud Storage
        - Use for: File storage, backups, static assets
        - Required fields: Resource Type, Storage (GB), Storage Type, Requests Read/Write/Delete, Internet Outbound GB
        - vCPUs and RAM should be 0 for OBS
        - Example: 1000 GB Standard storage, 10000 read requests, 5000 write requests
        """)


def render_llm_guide_tab():
    st.markdown("## 🤖 Using AI to Fill Your Template")
    st.markdown("Let ChatGPT, Claude, or your favorite AI assistant do the work! Copy these prompts and get perfectly formatted template data in seconds.")
    st.markdown("---")
    
    # Master Prompt Section
    st.markdown("### 🎯 Master Prompt (Use This First)")
    st.markdown("This universal prompt works for any infrastructure setup. Copy it and paste into ChatGPT, Claude, or Gemini.")
    
    master_prompt = """I need to create a Huawei Cloud resource inventory. Convert my infrastructure requirements into a table with these EXACT columns:

REQUIRED COLUMNS:
• Resource Type: ECS (Virtual Machine), Database (RDS), or OBS (Object Storage)
• vCPUs: Number of virtual CPUs (set to 0 for OBS)
• RAM (GB): Memory in gigabytes (set to 0 for OBS)
• Storage (GB): Storage size in gigabytes
• Storage Type: For ECS/Database use SSD, HighIO, UltraHighIO, GeneralSSDv2, or ExtremeSSD. For OBS use Standard, InfrequentAccess, Archive, or DeepArchive
• Quantity: Number of instances (default: 1)

OPTIONAL COLUMNS (include if relevant):
• Desired Tier (ECS only): general-computing-plus, general-computing-basic, memory-optimized, disk-intensive, or large-memory
• DB Type (Database only): mysql or postgresql
• Deployment (Database only): single or ha (High Availability)
• Availability Zone (OBS only): single-az or multi-az
• Requests Read (OBS only): Number of read requests per month
• Requests Write (OBS only): Number of write requests per month
• Requests Delete (OBS only): Number of delete requests per month
• Data Retrieval GB (OBS only): Data retrieval volume in GB per month
• Retrieval Type (OBS only): Standard, Urgent, or DirectReading
• Internet Outbound GB (OBS only): Internet outbound traffic in GB per month

MY INFRASTRUCTURE REQUIREMENTS:
[PASTE YOUR REQUIREMENTS HERE - Example: "I need 3 web servers with 4 CPU, 16GB RAM, 200GB SSD each, and one PostgreSQL database with 8 CPU, 32GB RAM, 500GB storage in HA mode"]

INSTRUCTIONS FOR AI:
1. Create one row per resource instance
2. Use exact column names as shown above
3. For ECS and Database: vCPUs and RAM must be greater than 0
4. For OBS: Set vCPUs and RAM to 0
5. Choose appropriate Storage Type based on performance needs
6. Include all optional columns that are relevant
7. Return as a markdown table that can be copied into Excel

OUTPUT FORMAT:
Return a markdown table with headers matching the column names above."""
    
    st.code(master_prompt, language="text")
    
    col1, col2 = st.columns([1, 3])
    with col1:
        st.button("📋 Copy Master Prompt", key="copy_master", on_click=lambda: st.write("Copied! (Use Ctrl+C to copy from the code block above)"))
    with col2:
        st.info("💡 **Pro Tip:** Replace the text in brackets [PASTE YOUR REQUIREMENTS HERE] with your actual infrastructure needs before sending to AI.")
    
    st.markdown("---")
    
    # Resource-Specific Prompts
    st.markdown("### 🎯 Resource-Specific Prompts")
    st.markdown("Use these specialized prompts when you only need one type of resource.")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**🖥️ ECS (Virtual Machines)**")
        ecs_prompt = """Create Huawei Cloud ECS (virtual machine) specifications.

Required fields:
- Resource Type: ECS
- vCPUs: [number]
- RAM (GB): [number]
- Storage (GB): [number]
- Storage Type: [SSD/HighIO/UltraHighIO/GeneralSSDv2/ExtremeSSD]
- Quantity: [number]

Optional:
- Desired Tier: [general-computing-plus/memory-optimized/disk-intensive/large-memory]

My requirements: [DESCRIBE YOUR VM NEEDS]

Return as a markdown table."""
        st.code(ecs_prompt, language="text")
        st.caption("Example: \"I need 2 web servers with 4 CPU, 16GB RAM, 200GB SSD\"")
    
    with col2:
        st.markdown("**🗄️ Database (RDS)**")
        db_prompt = """Create Huawei Cloud Database (RDS) specifications.

Required fields:
- Resource Type: Database
- vCPUs: [number]
- RAM (GB): [number]
- Storage (GB): [number]
- Storage Type: [SSD/HighIO/UltraHighIO/GeneralSSDv2/ExtremeSSD]
- DB Type: [mysql/postgresql]
- Deployment: [single/ha]
- Quantity: [number]

My requirements: [DESCRIBE YOUR DATABASE NEEDS]

Return as a markdown table."""
        st.code(db_prompt, language="text")
        st.caption("Example: \"One PostgreSQL database with 8 CPU, 32GB RAM, 500GB in HA mode\"")
    
    with col3:
        st.markdown("**📦 Object Storage (OBS)**")
        oss_prompt = """Create Huawei Cloud OBS (object storage) specifications.

Required fields:
- Resource Type: OBS
- vCPUs: 0
- RAM (GB): 0
- Storage (GB): [number]
- Storage Type: [Standard/InfrequentAccess/Archive/DeepArchive]
- Requests Read: [number per month]
- Requests Write: [number per month]
- Internet Outbound GB: [number per month]
- Quantity: 1

Optional:
- Availability Zone: [single-az/multi-az]
- Requests Delete: [number per month]

My requirements: [DESCRIBE YOUR STORAGE NEEDS]

Return as a markdown table."""
        st.code(oss_prompt, language="text")
        st.caption("Example: \"1000GB Standard storage, 10000 reads, 5000 writes per month\"")
    
    st.markdown("---")
    
    # Example Conversations
    st.markdown("### 💬 Example Conversations")
    st.markdown("See how real users leverage AI to fill their templates:")
    
    with st.expander("📖 Example 1: Web Application Infrastructure"):
        st.markdown("""
        **User:** I need infrastructure for a web application:
        - 2 web servers with 4 CPU, 16GB RAM, 200GB SSD each
        - 1 API server with 8 CPU, 32GB RAM, 400GB SSD
        - 1 MySQL database with 4 CPU, 16GB RAM, 500GB storage in HA mode
        - 500GB object storage for user uploads, about 5000 reads and 2000 writes per month
        
        **AI Output:**
        ```
        | Resource Type | vCPUs | RAM (GB) | Storage (GB) | Storage Type | DB Type | Deployment | Availability Zone | Requests Read | Requests Write | Internet Outbound GB | Quantity | Desired Tier |
        |---------------|-------|----------|--------------|--------------|---------|------------|-------------------|---------------|----------------|---------------------|----------|--------------|
        | ECS | 4 | 16 | 200 | SSD | | | | | | | 2 | general-computing-plus |
        | ECS | 8 | 32 | 400 | SSD | | | | | | | 1 | general-computing-plus |
        | Database | 4 | 16 | 500 | SSD | mysql | ha | | | | | 1 | |
        | OBS | 0 | 0 | 500 | Standard | | | single-az | 5000 | 2000 | 100 | 1 | |
        ```
        
        **✅ Result:** User copies this table into the Excel template and uploads it. Done!
        """)
    
    with st.expander("📖 Example 2: Enterprise Database Migration"):
        st.markdown("""
        **User:** We're migrating our enterprise databases to Huawei Cloud:
        - Primary PostgreSQL: 16 CPU, 64GB RAM, 2TB storage, needs to be highly available
        - Reporting MySQL: 8 CPU, 32GB RAM, 1TB storage, single instance is fine
        - Archive storage: 5TB for old data, rarely accessed, maybe 100 retrieval requests per month
        
        **AI Output:**
        ```
        | Resource Type | vCPUs | RAM (GB) | Storage (GB) | Storage Type | DB Type | Deployment | Availability Zone | Requests Read | Requests Write | Internet Outbound GB | Quantity | Desired Tier |
        |---------------|-------|----------|--------------|--------------|---------|------------|-------------------|---------------|----------------|---------------------|----------|--------------|
        | Database | 16 | 64 | 2048 | UltraHighIO | postgresql | ha | | | | | 1 | |
        | Database | 8 | 32 | 1024 | SSD | mysql | single | | | | | 1 | |
        | OBS | 0 | 0 | 5120 | Archive | | | single-az | 0 | 0 | 100 | 1 | |
        ```
        
        **✅ Result:** AI correctly identified UltraHighIO for the primary database and Archive storage for the old data!
        """)
    
    with st.expander("📖 Example 3: Simple Starter Setup"):
        st.markdown("""
        **User:** Just starting out, need basic setup:
        - 1 small server for a WordPress site
        - Basic database for the WordPress
        
        **AI Output:**
        ```
        | Resource Type | vCPUs | RAM (GB) | Storage (GB) | Storage Type | DB Type | Deployment | Quantity | Desired Tier |
        |---------------|-------|----------|--------------|--------------|---------|------------|----------|--------------|
        | ECS | 2 | 8 | 100 | SSD | | | 1 | general-computing-basic |
        | Database | 2 | 8 | 200 | SSD | mysql | single | 1 | |
        ```
        
        **✅ Result:** AI chose conservative specs appropriate for a starter WordPress site!
        """)
    
    st.markdown("---")
    
    # Tips Section
    st.markdown("### 💡 Pro Tips for Best Results")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**✅ DO:**")
        st.markdown("""
        - Be specific: "3 servers" → "3 web servers with 4 CPU, 16GB RAM each"
        - Include quantities for everything
        - Mention performance needs: "fast storage" → "UltraHighIO"
        - Specify database type: MySQL or PostgreSQL
        - Mention if you need HA (High Availability) for databases
        - Ask AI to "return as a markdown table"
        """)
    
    with col2:
        st.markdown("**❌ AVOID:**")
        st.markdown("""
        - Vague terms: "some servers", "a few databases"
        - Ambiguous specs: "medium size", "fast enough"
        - Mixing requirements: "2 servers with different specs" (list them separately)
        - Forgetting units: "16GB memory" → "16GB RAM"
        - Unclear storage needs: "lots of storage" → "2TB"
        """)
    
    st.markdown("---")
    
    # Workflow Summary
    st.markdown("### 🔄 Quick Workflow Reminder")
    st.markdown("""
    1. **Copy the master prompt** from above
    2. **Paste into ChatGPT/Claude** (or your preferred AI)
    3. **Add your requirements** where it says [PASTE YOUR REQUIREMENTS HERE]
    4. **Get back a formatted table** from the AI
    5. **Copy the table** and paste into the Excel template
    6. **Upload to the Calculator tab** and get your pricing!
    """)
    
    st.success("🎉 That's it! No more struggling with column names or valid values — let AI handle the formatting while you focus on your infrastructure needs.")


def main():
    st.set_page_config(
        page_title="Huawei Cloud Pricing Tool",
        page_icon="☁️",
        layout="wide"
    )

    if 'calculation_results' not in st.session_state:
        st.session_state.calculation_results = None
    if 'selected_optimizations' not in st.session_state:
        st.session_state.selected_optimizations = set()
    if 'applied_optimizations' not in st.session_state:
        st.session_state.applied_optimizations = None
    if 'show_transformed' not in st.session_state:
        st.session_state.show_transformed = False

    st.title("☁️ Huawei Cloud Pricing Tool")
    st.markdown(f"**Region:** {DEFAULT_REGION_NAME} (`{DEFAULT_REGION}`)")
    st.markdown("---")
    
    # Load data for all tabs
    ecs_data = load_ecs_pricing()
    db_data = load_db_pricing()
    storage_data = load_storage_pricing()
    oss_data = load_oss_pricing()
    available_db_types = get_available_db_types(db_data)
    
    # Tab navigation
    tab_calc, tab_guide, tab_llm = st.tabs(["📊 Calculator", "🚀 Getting Started", "🤖 LLM Guide"])
    
    with tab_calc:
        render_calculator_tab(ecs_data, db_data, storage_data, oss_data, available_db_types)
    
    with tab_guide:
        render_getting_started_tab()
    
    with tab_llm:
        render_llm_guide_tab()


def render_calculator_tab(ecs_data, db_data, storage_data, oss_data, available_db_types):
    with st.sidebar:
        st.header("Configuration")
        st.subheader("Upload File")
        uploaded_file = st.file_uploader(
            "Upload Excel File",
            type=['xlsx', 'xls'],
            help="Upload a file with VM and database specifications"
        )
        st.markdown("---")
        st.subheader("Pricing Model")
        pricing_model = st.radio(
            "Select Pricing Model",
            options=["Hourly (Pay-per-use)", "Monthly", "Yearly"],
            index=0
        )
        hours_per_month = 730
        if pricing_model == "Hourly (Pay-per-use)":
            hours_per_month = st.number_input(
                "Hours per Month",
                min_value=1,
                max_value=744,
                value=730,
                help="Number of hours to calculate for monthly cost"
            )
        st.markdown("---")
        st.subheader("Database Defaults")
        if available_db_types:
            default_db_type = st.selectbox(
                "Default DB Type",
                options=available_db_types,
                index=0,
                help="Default database type for rows without DB Type specified"
            )
        else:
            default_db_type = 'mysql'
        default_deployment = st.selectbox(
            "Default Deployment Mode",
            options=["single", "ha"],
            index=0,
            help="Default deployment mode (single or HA) for databases"
        )
        st.markdown("---")
        st.subheader("Region")
        st.info(f"🔒 Region locked to: **{DEFAULT_REGION_NAME}**")
        st.caption("Region selection disabled for this version.")
        st.markdown("---")

        x_mode_enabled = st.checkbox(
            "Enable X-Mode",
            value=False,
            help="Switch ALL ECS to X-series flavors for maximum cost savings"
        )

        x_family = None
        if x_mode_enabled:
            x_family_select = st.selectbox(
                "Target X-Series",
                options=["X1 (FlexusX - Small/Medium)", "X2E (FlexusX - Large)", "Auto (Best Match)"],
                index=0,
                help="X1: 1-16 vCPUs | X2E: 2-64 vCPUs | Auto: Choose based on specs"
            )
            x_family_select_str = str(x_family_select) if x_family_select else ""
            if "X1" in x_family_select_str:
                x_family = "x1"
            elif "X2E" in x_family_select_str:
                x_family = "x2e"
            else:
                x_family = "auto"

            st.info("📊 X-Mode will transform all ECS to X-series flavors")
            st.caption("⚠️ Review preview before applying")

        st.markdown("---")
        if st.button("📥 Download Template", type="secondary"):
            template_df = create_standard_template()
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                template_df.to_excel(writer, sheet_name='Resources', index=False)
            output.seek(0)
            st.download_button(
                label="💾 Save Template",
                data=output.getvalue(),
                file_name="huawei_cloud_template.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        st.markdown("---")
        run_calculation = st.button("🚀 Run Calculation", type="primary")
    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file)
            if 'Region' not in df.columns:
                df['Region'] = DEFAULT_REGION
            if 'DB Type' not in df.columns:
                df['DB Type'] = ''
            if 'Deployment' not in df.columns:
                df['Deployment'] = ''
            st.subheader("📋 Data Preview (First 10 Rows)")
            st.dataframe(df.head(10), use_container_width=True)

            if run_calculation:
                is_valid, message, errors = validate_dataframe(df)
                if not is_valid:
                    st.error(message)
                    if errors:
                        for error in errors:
                            st.warning(error)
                    return

                with st.spinner("Processing..."):
                    result_df, summary = process_file(
                        df, pricing_model, hours_per_month,
                        default_db_type, default_deployment,
                        ecs_data, db_data, storage_data, oss_data
                    )

                # Calculate cost savings
                with st.spinner("Analyzing cost optimization opportunities..."):
                    savings_summary = get_cost_savings_summary(
                        result_df, pricing_model, hours_per_month,
                        ecs_data, db_data
                    )

                # Store results in session state
                st.session_state.calculation_results = {
                    'result_df': result_df,
                    'summary': summary,
                    'savings_summary': savings_summary,
                    'pricing_model': pricing_model,
                    'hours_per_month': hours_per_month,
                    'x_mode_enabled': x_mode_enabled,
                    'x_family': x_family
                }

                # Reset selective optimization state
                st.session_state.selected_optimizations = set()
                st.session_state.applied_optimizations = None
                st.session_state.show_transformed = False

                st.success("✅ Processing complete!")

            # Display results from session state if available
            if st.session_state.calculation_results is not None:
                results = st.session_state.calculation_results
                result_df = results['result_df']
                summary = results['summary']
                savings_summary = results['savings_summary']
                pricing_model = results['pricing_model']
                hours_per_month = results['hours_per_month']
                x_mode_enabled = results['x_mode_enabled']
                x_family = results['x_family']

                st.markdown("---")

                # Cost Summary (Non-optimized - shown first)
                st.subheader("💰 Cost Summary")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Monthly Cost", f"${summary['total_monthly_cost']:,.2f}")
                with col2:
                    st.metric("Total Yearly Cost", f"${summary['total_yearly_cost']:,.2f}")
                with col3:
                    st.metric("Total Instances", summary['total_instances'])
                with col4:
                    st.metric("Needs Review", summary['needs_review_count'])

                # Cost Breakdown Visualization
                st.markdown("---")
                with st.expander("📈 Cost Breakdown Visualization", expanded=True):
                    viz_col1, viz_col2 = st.columns(2)

                    with viz_col1:
                        st.markdown("**Cost by Resource Type**")
                        cost_by_type = result_df.groupby('Resource Type')['Total Cost for Quantity'].sum().reset_index()
                        st.bar_chart(cost_by_type.set_index('Resource Type'))

                    with viz_col2:
                        st.markdown("**Instance Count by Type**")
                        count_by_type = result_df.groupby('Resource Type')['Quantity'].sum().reset_index()
                        st.bar_chart(count_by_type.set_index('Resource Type'))

                    # Top 10 most expensive resources
                    st.markdown("**Top 10 Most Expensive Resources**")
                    top_expensive = result_df.nlargest(10, 'Total Cost for Quantity')[
                        ['Resource Type', 'Mapped Flavor', 'vCPUs', 'RAM (GB)', 'Total Cost for Quantity']
                    ]
                    top_expensive['Total Cost'] = top_expensive['Total Cost for Quantity'].apply(lambda x: f"${x:,.2f}")
                    st.dataframe(top_expensive[['Resource Type', 'Mapped Flavor', 'vCPUs', 'RAM (GB)', 'Total Cost']], use_container_width=True)

                st.markdown("---")

                # Display X-Mode Preview if enabled
                if x_mode_enabled and x_family:
                    st.subheader("🚀 X-Mode Transformation Preview")
                    st.info(f"Switching ALL ECS to **{x_family.upper()}** series flavors")

                    with st.spinner("Calculating X-Mode transformation..."):
                        x_transformed_df, x_summary = apply_x_mode(
                            result_df, x_family, ecs_data, pricing_model, hours_per_month
                        )

                    # Show X-Mode summary metrics
                    x_col1, x_col2, x_col3 = st.columns(3)
                    with x_col1:
                        st.metric(
                            "Original ECS Cost",
                            f"${x_summary['total_original_cost']:,.2f}"
                        )
                    with x_col2:
                        st.metric(
                            "X-Mode Cost",
                            f"${x_summary['total_new_cost']:,.2f}",
                            delta=f"-${x_summary['total_savings']:,.2f} ({x_summary['savings_percent']:.1f}%)"
                        )
                    with x_col3:
                        st.metric(
                            "Resources Transformed",
                            f"{x_summary['transformed_count']}/{x_summary['total_ecs_count']}"
                        )

                    # Show transformation details
                    with st.expander("📋 View X-Mode Transformations"):
                        x_df = pd.DataFrame([
                            {
                                'Original Flavor': t['original_flavor'],
                                'New Flavor': t['new_flavor'],
                                'Specs': f"{t['vcpus']}vCPU/{t['ram_gb']}GB",
                                'Quantity': t['quantity'],
                                'Original Cost': f"${t['original_cost']:,.2f}",
                                'New Cost': f"${t['new_cost']:,.2f}",
                                'Savings': f"${t['savings']:,.2f}"
                            }
                            for t in x_summary['transformations']
                        ])
                        st.dataframe(x_df, use_container_width=True, height=300)

                        # Show warnings for missing flavors
                        warnings = [t for t in x_summary['transformations'] if 'warning' in t]
                        if warnings:
                            st.warning("⚠️ Some resources couldn't be transformed:")
                            for w in warnings:
                                st.caption(f"• {w['warning']}")

                    # Add download button for X-Mode results
                    st.markdown("#### 📥 Download X-Mode Quote")
                    x_output = BytesIO()
                    create_optimized_excel(x_transformed_df, {
                        'total_current_monthly': x_summary['total_original_cost'],
                        'total_current_yearly': x_summary['total_original_cost'] * 12,
                        'total_optimized_monthly': x_summary['total_new_cost'],
                        'total_optimized_yearly': x_summary['total_new_cost'] * 12,
                        'total_monthly_savings': x_summary['total_savings'],
                        'total_yearly_savings': x_summary['total_savings'] * 12,
                        'savings_percent': x_summary['savings_percent'],
                        'opportunities_count': x_summary['transformed_count'],
                        'opportunities': []
                    }, summary, x_output)
                    x_output.seek(0)
                    st.download_button(
                        label="💾 Download X-Mode Quote",
                        data=x_output.getvalue(),
                        file_name=f"huawei_cloud_xmode_{x_family}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

                    st.markdown("---")

                # Display Cost Optimization Section if opportunities exist
                if not x_mode_enabled and savings_summary['opportunities_count'] > 0:
                    st.subheader("💡 Cost Optimization Opportunities")
                    
                    # Check if optimizations have been applied
                    if st.session_state.show_transformed and st.session_state.applied_optimizations:
                        # Show ACTUAL applied results
                        st.info(f"Applied **{len(st.session_state.applied_optimizations)}** of **{savings_summary['opportunities_count']}** available optimizations")
                        
                        # Recalculate totals based on ACTUAL applied optimizations
                        applied_total_savings = sum(
                            savings_summary['opportunities'][idx]['monthly_savings']
                            for idx in st.session_state.applied_optimizations
                        )
                        applied_optimized_cost = savings_summary['total_current_monthly'] - applied_total_savings
                        applied_savings_percent = (applied_total_savings / savings_summary['total_current_monthly'] * 100) if savings_summary['total_current_monthly'] > 0 else 0
                        
                        st.markdown("#### 📊 Applied Optimization Results")
                        comp_col1, comp_col2, comp_col3 = st.columns(3)
                        with comp_col1:
                            st.metric(
                                "Current Total (Monthly)",
                                f"${savings_summary['total_current_monthly']:,.2f}"
                            )
                        with comp_col2:
                            st.metric(
                                "With Applied Optimizations",
                                f"${applied_optimized_cost:,.2f}",
                                delta=f"-${applied_total_savings:,.2f} ({applied_savings_percent:.1f}%)"
                            )
                        with comp_col3:
                            st.metric(
                                "Applied Savings (Yearly)",
                                f"${applied_total_savings * 12:,.2f}"
                            )
                    else:
                        # Show POTENTIAL results (all optimizations)
                        st.info(f"Found **{savings_summary['opportunities_count']}** resources with potential savings!")
                        
                        st.markdown("#### 📊 Potential Savings (All Optimizations)")
                        comp_col1, comp_col2, comp_col3 = st.columns(3)
                        with comp_col1:
                            st.metric(
                                "Current Total (Monthly)",
                                f"${savings_summary['total_current_monthly']:,.2f}"
                            )
                        with comp_col2:
                            st.metric(
                                "Optimized Total (Monthly)",
                                f"${savings_summary['total_optimized_monthly']:,.2f}",
                                delta=f"-${savings_summary['total_monthly_savings']:,.2f} ({savings_summary['savings_percent']:.1f}%)"
                            )
                        with comp_col3:
                            st.metric(
                                "Total Savings (Yearly)",
                                f"${savings_summary['total_yearly_savings']:,.2f}"
                            )

                    # Selective Optimization UI
                    st.markdown("#### 🎯 Selective Optimization")
                    st.caption("Select which optimizations to apply:")

                    st.markdown("**Select optimizations to apply:**")
                    
                    # Initialize select all state if not exists
                    if 'select_all_state' not in st.session_state:
                        st.session_state.select_all_state = None
                    
                    # Display opportunities as a table with checkboxes
                    checkbox_keys = []
                    for idx, opp in enumerate(savings_summary['opportunities']):
                        key = f"opt_cb_{idx}"
                        checkbox_keys.append(key)
                        # Determine default value based on select_all_state
                        default_value = False
                        if st.session_state.select_all_state == 'all':
                            default_value = True
                        elif st.session_state.select_all_state == 'none':
                            default_value = False
                        else:
                            default_value = st.session_state.get(key, False)
                        
                        st.checkbox(
                            f"Row {idx+1}: {opp['resource_type']} {opp['current_flavor']} → {opp['recommended_flavor']} (${opp['monthly_savings']:,.2f}/mo)",
                            key=key,
                            value=default_value
                        )
                    
                    # Reset select_all_state after rendering checkboxes
                    if st.session_state.select_all_state in ['all', 'none']:
                        st.session_state.select_all_state = None
                    
                    # Action buttons in columns
                    btn_col1, btn_col2, btn_col3 = st.columns(3)
                    
                    with btn_col1:
                        if st.button("☑️ Select All", key="select_all_btn"):
                            st.session_state.select_all_state = 'all'
                    
                    with btn_col2:
                        if st.button("⬜ Clear All", key="clear_all_btn"):
                            st.session_state.select_all_state = 'none'
                    
                    with btn_col3:
                        if st.button("🚀 Apply Selected", type="primary", key="apply_selected_btn"):
                            # Collect which checkboxes are checked
                            selected_indices = {
                                idx for idx, key in enumerate(checkbox_keys)
                                if st.session_state.get(key, False)
                            }
                            
                            if selected_indices:
                                st.session_state.applied_optimizations = selected_indices
                                st.session_state.show_transformed = True
                            else:
                                st.warning("Please select at least one optimization")

                    # Show transformed results if applied
                    if st.session_state.show_transformed and st.session_state.applied_optimizations:
                        st.markdown("---")
                        st.subheader("✅ Applied Optimizations Preview")

                        # Create transformed dataframe
                        transformed_df = result_df.copy()
                        applied_map = {
                            savings_summary['opportunities'][idx]['row_index']: savings_summary['opportunities'][idx]
                            for idx in st.session_state.applied_optimizations
                        }

                        for idx, row in transformed_df.iterrows():
                            if idx in applied_map:
                                opp = applied_map[idx]
                                transformed_df.at[idx, 'Mapped Flavor'] = opp['recommended_flavor']
                                transformed_df.at[idx, 'Flavor Family'] = opp.get('recommended_family', 'N/A')
                                new_compute_cost = opp['recommended_cost'] / row.get('Quantity', 1)
                                transformed_df.at[idx, 'Compute Cost (Monthly)'] = new_compute_cost
                                storage_cost = row.get('Storage Cost (Monthly)', 0)
                                transformed_df.at[idx, 'Total Cost per Instance'] = new_compute_cost + storage_cost
                                transformed_df.at[idx, 'Total Cost for Quantity'] = (new_compute_cost + storage_cost) * row.get('Quantity', 1)

                        # Show metrics
                        new_total = transformed_df['Total Cost for Quantity'].sum()
                        original_total = result_df['Total Cost for Quantity'].sum()
                        actual_savings = original_total - new_total

                        met_col1, met_col2, met_col3 = st.columns(3)
                        with met_col1:
                            st.metric("Original Total", f"${original_total:,.2f}")
                        with met_col2:
                            st.metric("With Optimizations", f"${new_total:,.2f}", delta=f"-${actual_savings:,.2f}")
                        with met_col3:
                            st.metric("Applied Count", f"{len(st.session_state.applied_optimizations)}")

                        # Show comparison table
                        with st.expander("📋 View Transformation Details"):
                            comparison_data = []
                            for idx in st.session_state.applied_optimizations:
                                opp = savings_summary['opportunities'][idx]
                                comparison_data.append({
                                    'Resource': f"Row {opp['row_index'] + 1}",
                                    'Type': opp['resource_type'],
                                    'Original': opp['current_flavor'],
                                    'New': opp['recommended_flavor'],
                                    'Savings': f"${opp['monthly_savings']:,.2f}/mo"
                                })

                            comp_df = pd.DataFrame(comparison_data)
                            st.dataframe(comp_df, use_container_width=True)

                        # Side-by-side comparison view
                        with st.expander("📊 Side-by-Side Comparison"):
                            st.markdown("**Original vs Optimized (Changed Resources Only)**")

                            for idx in st.session_state.applied_optimizations:
                                opp = savings_summary['opportunities'][idx]
                                row_idx = opp['row_index']

                                original_row = result_df.loc[row_idx]
                                new_row = transformed_df.loc[row_idx]

                                comp_cols = st.columns(2)
                                with comp_cols[0]:
                                    st.markdown(f"**BEFORE (Row {row_idx + 1})**")
                                    st.text(f"Flavor: {original_row['Mapped Flavor']}")
                                    st.text(f"Cost: ${original_row['Total Cost for Quantity']:,.2f}")
                                    st.text(f"Specs: {original_row.get('vCPUs', 0)}vCPU/{original_row.get('RAM (GB)', 0)}GB")

                                with comp_cols[1]:
                                    st.markdown(f"**AFTER** ✅")
                                    st.text(f"Flavor: {new_row['Mapped Flavor']}")
                                    st.text(f"Cost: ${new_row['Total Cost for Quantity']:,.2f}")
                                    st.text(f"Savings: ${opp['monthly_savings']:,.2f}/mo")

                                st.markdown("---")

                        # Download button for selective optimization
                        st.markdown("#### 📥 Download Selectively Optimized Quote")
                        sel_output = BytesIO()

                        # Create summary for selected optimizations
                        sel_summary = {
                            'total_current_monthly': original_total,
                            'total_current_yearly': original_total * 12,
                            'total_optimized_monthly': new_total,
                            'total_optimized_yearly': new_total * 12,
                            'total_monthly_savings': actual_savings,
                            'total_yearly_savings': actual_savings * 12,
                            'savings_percent': (actual_savings / original_total * 100) if original_total > 0 else 0,
                            'opportunities_count': len(st.session_state.applied_optimizations),
                            'opportunities': [savings_summary['opportunities'][idx] for idx in st.session_state.applied_optimizations]
                        }

                        create_optimized_excel(transformed_df, sel_summary, summary, sel_output)
                        sel_output.seek(0)
                        st.download_button(
                            label="💾 Download Optimized Quote",
                            data=sel_output.getvalue(),
                            file_name="huawei_cloud_selective_optimized.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )

                    st.markdown("---")
                
                st.markdown("---")
                st.subheader("📊 Detailed Results")
                st.dataframe(result_df, use_container_width=True)
                st.markdown("---")
                st.subheader("📥 Download Results")
                
                # Create two columns for download buttons
                dl_col1, dl_col2 = st.columns(2)
                
                with dl_col1:
                    excel_bytes = to_excel_bytes(result_df, summary)
                    st.download_button(
                        label="💾 Download Original Results",
                        data=excel_bytes,
                        file_name="huawei_cloud_pricing_results.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
                with dl_col2:
                    if savings_summary['opportunities_count'] > 0:
                        optimized_output = BytesIO()
                        create_optimized_excel(result_df, savings_summary, summary, optimized_output)
                        optimized_output.seek(0)
                        st.download_button(
                            label="✨ Download Optimized Quote",
                            data=optimized_output.getvalue(),
                            file_name="huawei_cloud_pricing_optimized.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                        st.caption(f"Applied {savings_summary['opportunities_count']} optimizations, saves ${savings_summary['total_monthly_savings']:,.2f}/mo")
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            st.info("Please check that your file matches the required format.")
    else:
        st.info("👆 Please upload an Excel file to begin.")
        st.markdown("### Required Columns:")
        st.markdown("- **Resource Type**: ECS, Database, or OBS")
        st.markdown("- **vCPUs**: Number of virtual CPUs")
        st.markdown("- **RAM (GB)**: Memory in gigabytes")
        st.markdown("- **Storage (GB)**: Storage size in gigabytes")
        st.markdown("- **Storage Type**: SSD, HighIO, UltraHighIO, GeneralSSDv2, ExtremeSSD (ECS/DB) or Standard, InfrequentAccess, Archive, DeepArchive (OBS)")
        st.markdown("- **Quantity**: Number of instances (default: 1)")
        st.markdown("---")
        st.markdown("### Optional Columns:")
        st.markdown("- **Desired Tier** *(ECS only)*: general-computing-plus, general-computing-basic, memory-optimized, disk-intensive, large-memory")
        st.markdown("- **DB Type** *(Database only)*: mysql, postgresql")
        st.markdown("- **Deployment** *(Database only)*: single or ha")
        st.markdown("- **Availability Zone** *(OBS only)*: single-az or multi-az")
        st.markdown("- **Requests Read** *(OBS only)*: Number of read requests")
        st.markdown("- **Requests Write** *(OBS only)*: Number of write requests")
        st.markdown("- **Requests Delete** *(OBS only)*: Number of delete requests")
        st.markdown("- **Data Retrieval GB** *(OBS only)*: Data retrieval volume in GB")
        st.markdown("- **Retrieval Type** *(OBS only)*: Standard, Urgent, DirectReading")
        st.markdown("- **Internet Outbound GB** *(OBS only)*: Internet outbound traffic in GB")

if __name__ == "__main__":
    main()