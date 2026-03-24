import json
import os
from typing import Dict, List, Optional, Union
from io import BytesIO
import pandas as pd
from mapping_engine import (
    load_ecs_pricing, load_db_pricing, load_storage_pricing,
    get_region, get_ecs_flavors, get_db_flavors, get_available_db_types
)


def get_flavor_price(
    flavor_name: str,
    resource_type: str,
    db_type: Optional[str],
    deployment: Optional[str],
    pricing_model: str,
    hours_per_month: float,
    ecs_data: Dict,
    db_data: Dict
) -> Optional[float]:
    if resource_type.lower() == 'ecs':
        flavors = get_ecs_flavors(ecs_data)
        flavor = next((f for f in flavors if f['name'] == flavor_name), None)
        if not flavor:
            return None
        if pricing_model == "Hourly (Pay-per-use)":
            return flavor.get('hourly', 0) * hours_per_month
        elif pricing_model == "Monthly":
            return flavor.get('monthly', 0)
        elif pricing_model == "Yearly":
            return flavor.get('yearly', 0) / 12
    elif resource_type.lower() == 'database':
        if not db_type:
            db_type = 'mysql'
        if not deployment:
            deployment = 'single'
        db_flavors = get_db_flavors(db_data, db_type)
        flavor = next((f for f in db_flavors if f['name'] == flavor_name), None)
        if not flavor:
            return None
        pricing = flavor.get('pricing', {}).get(deployment, {})
        if pricing_model == "Hourly (Pay-per-use)":
            return pricing.get('hourly', 0) * hours_per_month
        elif pricing_model == "Monthly":
            return pricing.get('monthly', 0)
        elif pricing_model == "Yearly":
            return pricing.get('yearly', 0) / 12
    return None


def get_storage_cost(
    storage_gb: float,
    storage_type: str,
    storage_data: Dict
) -> float:
    types = storage_data.get('types', [])
    storage_info = next((t for t in types if t['name'].lower() == storage_type.lower()), None)
    if not storage_info:
        return 0
    return storage_gb * storage_info.get('price_per_gb', 0)


def calculate_all_costs(
    df: pd.DataFrame,
    mapping_results: List[Dict],
    ecs_flavors: List[Dict],
    default_region: str,
    pricing_model: str,
    hours_per_month: float,
    ecs_data: Dict,
    db_data: Dict,
    storage_data: Dict
) -> pd.DataFrame:
    result_rows = []
    for idx, row in df.iterrows():
        mapping = mapping_results[idx]
        resource_type = str(row.get('Resource Type', 'ECS')).strip()
        vcpus = int(row.get('vCPUs', 0) or 0)
        ram_gb = int(row.get('RAM (GB)', 0) or 0)
        storage_gb = int(row.get('Storage (GB)', 0) or 0)
        storage_type = str(row.get('Storage Type', 'SSD')).strip()
        region = default_region
        quantity = int(row.get('Quantity', 1) or 1)
        desired_tier = row.get('Desired Tier', '')
        flavor_name = mapping.get('flavor')
        flavor_family = mapping.get('flavor_family')
        db_type = mapping.get('db_type')
        deployment = mapping.get('deployment')
        status = mapping.get('status', 'Unknown')
        compute_cost = 0
        storage_cost = 0
        if flavor_name:
            compute_cost = get_flavor_price(
                flavor_name, resource_type, db_type, deployment,
                pricing_model, hours_per_month, ecs_data, db_data
            ) or 0
            storage_cost = get_storage_cost(storage_gb, storage_type, storage_data)
        total_cost_per_instance = compute_cost + storage_cost
        total_cost_for_quantity = total_cost_per_instance * quantity
        result_row = {
            'Resource Type': resource_type,
            'vCPUs': vcpus,
            'RAM (GB)': ram_gb,
            'Storage (GB)': storage_gb,
            'Storage Type': storage_type,
            'Region': region,
            'Quantity': quantity,
            'Desired Tier': desired_tier,
            'DB Type': db_type if resource_type.lower() == 'database' else '',
            'Deployment': deployment if resource_type.lower() == 'database' else '',
            'Mapped Flavor': flavor_name,
            'Flavor Family': flavor_family if resource_type.lower() == 'ecs' else 'N/A',
            'Compute Cost (Monthly)': round(compute_cost, 2),
            'Storage Cost (Monthly)': round(storage_cost, 2),
            'Total Cost per Instance': round(total_cost_per_instance, 2),
            'Total Cost for Quantity': round(total_cost_for_quantity, 2),
            'Mapping Status': status
        }
        result_rows.append(result_row)
    return pd.DataFrame(result_rows)


def compute_summary(df: pd.DataFrame, pricing_model: str, hours_per_month: float) -> Dict:
    total_monthly_cost = df['Total Cost for Quantity'].sum()
    total_yearly_cost = total_monthly_cost * 12
    total_instances = df['Quantity'].sum()
    needs_review_count = df[df['Mapping Status'].str.contains('Review', case=False, na=False)].shape[0]
    summary_by_type = df.groupby('Resource Type')['Total Cost for Quantity'].sum().to_dict()
    ecs_df = df[df['Resource Type'].str.lower() == 'ecs']
    if not ecs_df.empty:
        summary_by_family = ecs_df.groupby('Flavor Family')['Total Cost for Quantity'].sum().to_dict()
    else:
        summary_by_family = {}
    db_df = df[df['Resource Type'].str.lower() == 'database']
    if not db_df.empty:
        summary_by_db_type = db_df.groupby('DB Type')['Total Cost for Quantity'].sum().to_dict()
        summary_by_deployment = db_df.groupby('Deployment')['Total Cost for Quantity'].sum().to_dict()
    else:
        summary_by_db_type = {}
        summary_by_deployment = {}
    return {
        'total_monthly_cost': round(total_monthly_cost, 2),
        'total_yearly_cost': round(total_yearly_cost, 2),
        'total_instances': int(total_instances),
        'needs_review_count': needs_review_count,
        'by_type': summary_by_type,
        'by_flavor_family': summary_by_family,
        'by_db_type': summary_by_db_type,
        'by_deployment': summary_by_deployment
    }


def create_output_excel(df: pd.DataFrame, summary: Dict, output: Union[str, BytesIO]) -> None:
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Results', index=False)
        summary_df = pd.DataFrame([
            {'Category': 'Total Monthly Cost', 'Value': summary['total_monthly_cost']},
            {'Category': 'Total Yearly Cost', 'Value': summary['total_yearly_cost']},
            {'Category': 'Total Instances', 'Value': summary['total_instances']},
            {'Category': 'Resources Needing Review', 'Value': summary['needs_review_count']}
        ])
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        type_summary_df = pd.DataFrame([
            {'Resource Type': k, 'Total Cost': v}
            for k, v in summary['by_type'].items()
        ])
        if not type_summary_df.empty:
            type_summary_df.to_excel(writer, sheet_name='By Resource Type', index=False)
        family_summary_df = pd.DataFrame([
            {'Flavor Family': k, 'Total Cost': v}
            for k, v in summary['by_flavor_family'].items()
        ])
        if not family_summary_df.empty:
            family_summary_df.to_excel(writer, sheet_name='By Flavor Family', index=False)
        db_type_summary_df = pd.DataFrame([
            {'DB Type': k, 'Total Cost': v}
            for k, v in summary['by_db_type'].items()
        ])
        if not db_type_summary_df.empty:
            db_type_summary_df.to_excel(writer, sheet_name='By DB Type', index=False)
        deployment_summary_df = pd.DataFrame([
            {'Deployment': k, 'Total Cost': v}
            for k, v in summary['by_deployment'].items()
        ])
        if not deployment_summary_df.empty:
            deployment_summary_df.to_excel(writer, sheet_name='By Deployment', index=False)
        unmapped_df = df[df['Mapping Status'].str.contains('Review', case=False, na=False)]
        if not unmapped_df.empty:
            unmapped_df.to_excel(writer, sheet_name='Unmapped Resources', index=False)