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

def validate_row(row: pd.Series, row_num: int) -> Tuple[bool, List[str]]:
    """
    Validate a single row and return detailed error messages.
    Returns (is_valid, list_of_errors).
    """
    errors = []
    resource_type = str(row.get('Resource Type', '')).strip()
    
    # Check Resource Type
    if not resource_type:
        errors.append(f"Row {row_num}: Resource Type is empty. Must be one of: ECS, Database, OSS")
    elif resource_type not in ['ECS', 'Database', 'OSS']:
        errors.append(f"Row {row_num}: Invalid Resource Type '{resource_type}'. Valid values: ECS, Database, OSS")
    
    # Check numeric values based on resource type
    if resource_type and resource_type != 'OSS':
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
        
        if resource_type == 'OSS':
            valid_oss = ['standard', 'infrequentaccess', 'archive', 'deeparchive']
            if stype_lower not in valid_oss:
                errors.append(f"Row {row_num}: Invalid OSS Storage Class '{stype}'. Valid: Standard, InfrequentAccess, Archive, DeepArchive")
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
                    st.info(f"Found **{savings_summary['opportunities_count']}** resources with potential savings!")

                    # Show Current vs Optimized costs
                    st.markdown("#### 📊 Pricing Comparison")
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

                    # Bulk action buttons
                    bulk_col1, bulk_col2, bulk_col3 = st.columns(3)
                    with bulk_col1:
                        if st.button("☑️ Select All", key="select_all"):
                            st.session_state.selected_optimizations = set(
                                range(len(savings_summary['opportunities']))
                            )
                            st.rerun()
                    with bulk_col2:
                        if st.button("⬜ Select None", key="select_none"):
                            st.session_state.selected_optimizations = set()
                            st.rerun()
                    with bulk_col3:
                        if st.button("🔄 Reset", key="reset_selection"):
                            st.session_state.selected_optimizations = set()
                            st.session_state.applied_optimizations = None
                            st.session_state.show_transformed = False
                            st.rerun()

                    # Display checkboxes for each optimization
                    st.markdown("**Select optimizations to apply:**")

                    # Generate unique keys for each checkbox
                    checkbox_keys = [f"opt_checkbox_{i}" for i in range(len(savings_summary['opportunities']))]

                    # Display checkboxes with details
                    for idx, opp in enumerate(savings_summary['opportunities']):
                        cb_col, detail_col = st.columns([0.1, 0.9])
                        with cb_col:
                            st.checkbox(
                                "",
                                key=checkbox_keys[idx],
                                label_visibility="collapsed"
                            )
                        with detail_col:
                            st.markdown(
                                f"**{opp['resource_type']}**: {opp['current_flavor']} → "
                                f"**{opp['recommended_flavor']}** | "
                                f"Save **${opp['monthly_savings']:,.2f}/mo** ({opp['savings_percent']:.1f}%) | "
                                f"Specs: {opp['alternative_specs']}"
                            )

                    # Apply button - collects checkbox values when clicked
                    if st.button("🚀 Apply Selected Optimizations", type="primary"):
                        # Collect which checkboxes are checked
                        selected_indices = {
                            idx for idx, key in enumerate(checkbox_keys)
                            if st.session_state.get(key, False)
                        }

                        if selected_indices:
                            st.session_state.applied_optimizations = selected_indices
                            st.session_state.show_transformed = True
                            st.rerun()
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