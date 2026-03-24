import streamlit as st
import pandas as pd
import os
from io import BytesIO
from typing import Dict, Optional, Tuple
from mapping_engine import (
    load_ecs_pricing, load_db_pricing, load_storage_pricing, load_oss_pricing,
    get_region, get_available_db_types, map_resources
)
from pricing_calculator import calculate_all_costs, compute_summary, create_output_excel

DEFAULT_REGION = "ap-southeast-3"
DEFAULT_REGION_NAME = "AP-Jakarta"

REQUIRED_COLUMNS = [
    'Resource Type', 'vCPUs', 'RAM (GB)', 'Storage (GB)',
    'Storage Type', 'Region', 'Quantity', 'Desired Tier'
]

def create_standard_template() -> pd.DataFrame:
    data = {
        'Resource Type': ['ECS', 'ECS', 'Database', 'ECS', 'Database', 'OSS'],
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

def validate_dataframe(df: pd.DataFrame) -> Tuple[bool, str]:
    df_cols = [col for col in df.columns]
    required_cols = ['Resource Type', 'vCPUs', 'RAM (GB)', 'Storage (GB)', 'Storage Type', 'Quantity']
    missing = [col for col in required_cols if col not in df_cols]
    if missing:
        return False, f"Missing required columns: {', '.join(missing)}"
    
    # Convert numeric columns
    for col in ['vCPUs', 'RAM (GB)', 'Storage (GB)', 'Quantity']:
        if col in df_cols:
            if not pd.api.types.is_numeric_dtype(df[col]):
                try:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                except:
                    return False, f"Column '{col}' contains invalid numeric values"
    
    # Convert string columns to string type
    for col in ['Resource Type', 'Storage Type', 'Desired Tier', 'DB Type', 'Deployment']:
        if col in df_cols:
            df[col] = df[col].astype(str)
    
    valid_storage_types = ['SSD', 'HighIO', 'UltraHighIO', 'GeneralSSDv2', 'ExtremeSSD', 'General Purpose SSD', 'High I/O', 'Ultra-high I/O', 'Extreme SSD']
    if 'Storage Type' in df_cols:
        for stype in df['Storage Type'].unique():
            stype_str = str(stype).strip()
            stype_lower = stype_str.lower().replace('-', '').replace(' ', '').replace('_', '')
            valid_lower = [s.lower().replace('-', '').replace(' ', '').replace('_', '') for s in valid_storage_types]
            if stype_lower not in valid_lower:
                st.warning(f"Unknown Storage Type '{stype_str}'. Will try to match. Valid types: SSD, HighIO, UltraHighIO, GeneralSSDv2, ExtremeSSD")
    
    valid_resource_types = ['ECS', 'Database', 'OSS']
    if 'Resource Type' in df_cols:
        for rtype in df['Resource Type'].unique():
            rtype_str = str(rtype).strip()
            if rtype_str not in valid_resource_types:
                return False, f"Invalid Resource Type: '{rtype_str}'. Valid values: {', '.join(valid_resource_types)}"
    
    return True, "Validation successful"

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

def main():
    st.set_page_config(
        page_title="Huawei Cloud Pricing Tool",
        page_icon="☁️",
        layout="wide"
    )
    st.title("☁️ Huawei Cloud Pricing Tool")
    st.markdown(f"**Region:** {DEFAULT_REGION_NAME} (`{DEFAULT_REGION}`)")
    st.markdown("---")
    ecs_data = load_ecs_pricing()
    db_data = load_db_pricing()
    storage_data = load_storage_pricing()
    oss_data = load_oss_pricing()
    available_db_types = get_available_db_types(db_data)
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
                is_valid, message = validate_dataframe(df)
                if not is_valid:
                    st.error(message)
                    return
                with st.spinner("Processing..."):
                    result_df, summary = process_file(
                        df, pricing_model, hours_per_month,
                        default_db_type, default_deployment,
                        ecs_data, db_data, storage_data, oss_data
                    )
                st.success("✅ Processing complete!")
                st.markdown("---")
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
                st.markdown("---")
                st.subheader("📊 Detailed Results")
                st.dataframe(result_df, use_container_width=True)
                st.markdown("---")
                st.subheader("📥 Download Results")
                excel_bytes = to_excel_bytes(result_df, summary)
                st.download_button(
                    label="💾 Download Enriched Excel",
                    data=excel_bytes,
                    file_name="huawei_cloud_pricing_results.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            st.info("Please check that your file matches the required format.")
    else:
        st.info("👆 Please upload an Excel file to begin.")
        st.markdown("### Required Columns:")
        st.markdown("- **Resource Type**: ECS, Database, or OSS")
        st.markdown("- **vCPUs**: Number of virtual CPUs")
        st.markdown("- **RAM (GB)**: Memory in gigabytes")
        st.markdown("- **Storage (GB)**: Storage size in gigabytes")
        st.markdown("- **Storage Type**: SSD, HighIO, UltraHighIO, GeneralSSDv2, ExtremeSSD (ECS/DB) or Standard, InfrequentAccess, Archive, DeepArchive (OSS)")
        st.markdown("- **Quantity**: Number of instances (default: 1)")
        st.markdown("---")
        st.markdown("### Optional Columns:")
        st.markdown("- **Desired Tier** *(ECS only)*: general-computing-plus, general-computing-basic, memory-optimized, disk-intensive, large-memory")
        st.markdown("- **DB Type** *(Database only)*: mysql, postgresql")
        st.markdown("- **Deployment** *(Database only)*: single or ha")
        st.markdown("- **Availability Zone** *(OSS only)*: single-az or multi-az")
        st.markdown("- **Requests Read** *(OSS only)*: Number of read requests")
        st.markdown("- **Requests Write** *(OSS only)*: Number of write requests")
        st.markdown("- **Requests Delete** *(OSS only)*: Number of delete requests")
        st.markdown("- **Data Retrieval GB** *(OSS only)*: Data retrieval volume in GB")
        st.markdown("- **Retrieval Type** *(OSS only)*: Standard, Urgent, DirectReading")
        st.markdown("- **Internet Outbound GB** *(OSS only)*: Internet outbound traffic in GB")

if __name__ == "__main__":
    main()