import json
import os
from typing import Dict, List, Optional, Union
from io import BytesIO
import pandas as pd
from mapping_engine import (
    load_ecs_pricing, load_db_pricing, load_storage_pricing, load_oss_pricing,
    get_region, get_ecs_flavors, get_db_flavors, get_available_db_types,
    get_oss_storage_classes
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
    storage_lower = storage_type.lower().replace('-', '').replace(' ', '').replace('_', '')
    type_mappings = {
        'ssd': 'SSD',
        'generalssd': 'SSD',
        'generalpurposessd': 'SSD',
        'generalssdv2': 'GeneralSSDv2',
        'highio': 'HighIO',
        'highi/o': 'HighIO',
        'ultrahighio': 'UltraHighIO',
        'ultra-highio': 'UltraHighIO',
        'extremessd': 'ExtremeSSD',
        'extreme': 'ExtremeSSD',
    }
    normalized_name = type_mappings.get(storage_lower, storage_type)
    storage_info = next((t for t in types if t['name'].lower() == normalized_name.lower()), None)
    if not storage_info:
        storage_info = next((t for t in types if t['name'].lower() == storage_lower), None)
    if not storage_info:
        return 0
    return storage_gb * storage_info.get('price_per_gb', 0)


def get_oss_cost(
    storage_gb: float,
    storage_class: str,
    availability_zone: str,
    requests_read: int,
    requests_write: int,
    requests_delete: int,
    data_retrieval_gb: float,
    retrieval_type: Optional[str],
    internet_outbound_gb: float,
    oss_data: Dict
) -> Dict:
    storage_classes = get_oss_storage_classes(oss_data)
    oss_class = next((c for c in storage_classes if c['name'].lower() == storage_class.lower()), None)
    
    if not oss_class:
        return {
            'storage_cost': 0,
            'request_cost': 0,
            'retrieval_cost': 0,
            'traffic_cost': 0,
            'total_cost': 0
        }
    
    storage_pricing = oss_class.get('storage_pricing', {})
    request_pricing = oss_class.get('request_pricing', {})
    traffic_pricing = oss_class.get('traffic_pricing', {})
    data_retrieval = oss_class.get('data_retrieval', {})
    
    az_key = 'single_az' if availability_zone == 'single-az' else 'multi_az'
    storage_price = storage_pricing.get(az_key, {}).get('price_per_gb_month', 0)
    if storage_price is None:
        storage_price = 0
    storage_cost = storage_gb * storage_price
    
    request_cost = 0
    if requests_read > 0:
        read_rate = request_pricing.get('read_per_10000', request_pricing.get('read_per_1000', 0))
        if read_rate is None:
            read_rate = 0
        if 'read_per_1000' in request_pricing:
            request_cost += (requests_read / 1000) * read_rate
        else:
            request_cost += (requests_read / 10000) * read_rate
    if requests_write > 0:
        write_rate = request_pricing.get('write_per_10000', request_pricing.get('write_per_1000', 0))
        if write_rate is None:
            write_rate = 0
        if 'write_per_1000' in request_pricing:
            request_cost += (requests_write / 1000) * write_rate
        else:
            request_cost += (requests_write / 10000) * write_rate
    if requests_delete > 0:
        delete_rate = request_pricing.get('delete_per_1000', 0)
        if delete_rate is None:
            delete_rate = 0
        request_cost += (requests_delete / 1000) * delete_rate
    
    retrieval_cost = 0
    if data_retrieval and data_retrieval.get('available', False) and data_retrieval_gb > 0:
        retrieval_types = data_retrieval.get('retrieval_types', [])
        selected_retrieval = None
        if retrieval_type:
            selected_retrieval = next((r for r in retrieval_types if r['name'].lower() == retrieval_type.lower()), None)
        if not selected_retrieval and retrieval_types:
            selected_retrieval = retrieval_types[0]
        if selected_retrieval:
            price_per_gb = selected_retrieval.get('price_per_gb', 0)
            if price_per_gb is None:
                price_per_gb = 0
            retrieval_cost = data_retrieval_gb * price_per_gb
    
    traffic_cost = 0
    if internet_outbound_gb > 0:
        tiers = traffic_pricing.get('internet_outbound_tiers', [])
        if tiers:
            remaining_gb = internet_outbound_gb
            for tier in tiers:
                tier_min = tier.get('min_gb', 0)
                tier_max = tier.get('max_gb')
                tier_price = tier.get('price_per_gb')
                
                if tier_price is None:
                    off_peak = tier.get('off_peak_price_per_gb', 0)
                    peak = tier.get('peak_price_per_gb', 0)
                    if off_peak and peak:
                        tier_price = (off_peak + peak) / 2
                    elif peak:
                        tier_price = peak
                    elif off_peak:
                        tier_price = off_peak
                    else:
                        tier_price = 0
                
                if remaining_gb <= 0:
                    break
                
                tier_volume = tier_max - tier_min if tier_max else remaining_gb
                if tier_volume > remaining_gb:
                    tier_volume = remaining_gb
                
                if tier_volume > 0 and tier_price:
                    traffic_cost += tier_volume * tier_price
                    remaining_gb -= tier_volume
    
    total_cost = storage_cost + request_cost + retrieval_cost + traffic_cost
    
    return {
        'storage_cost': round(storage_cost, 4),
        'request_cost': round(request_cost, 4),
        'retrieval_cost': round(retrieval_cost, 4),
        'traffic_cost': round(traffic_cost, 4),
        'total_cost': round(total_cost, 4)
    }



def calculate_all_costs(
    df: pd.DataFrame,
    mapping_results: List[Dict],
    ecs_flavors: List[Dict],
    default_region: str,
    pricing_model: str,
    hours_per_month: float,
    ecs_data: Dict,
    db_data: Dict,
    storage_data: Dict,
    oss_data: Dict
) -> pd.DataFrame:
    result_rows = []
    for idx, row in df.iterrows():
        mapping = mapping_results[idx]
        resource_type = str(row.get('Resource Type', 'ECS')).strip()
        
        # Handle vCPUs and RAM - OSS resources don't have these
        if resource_type.lower() == 'oss':
            vcpus = 0
            ram_gb = 0
        else:
            vcpus = int(row.get('vCPUs', 0) or 0) if pd.notna(row.get('vCPUs')) else 0
            ram_gb = int(row.get('RAM (GB)', 0) or 0) if pd.notna(row.get('RAM (GB)')) else 0
        storage_gb = int(row.get('Storage (GB)', 0) or 0) if pd.notna(row.get('Storage (GB)')) else 0
        storage_type = str(row.get('Storage Type', 'SSD')).strip()
        region = default_region
        quantity = int(row.get('Quantity', 1) or 1) if pd.notna(row.get('Quantity')) else 1
        desired_tier = row.get('Desired Tier', '')
        flavor_name = mapping.get('flavor')
        flavor_family = mapping.get('flavor_family')
        db_type = mapping.get('db_type')
        deployment = mapping.get('deployment')
        status = mapping.get('status', 'Unknown')
        compute_cost = 0
        storage_cost = 0
        
        if resource_type.lower() == 'oss':
            # Handle OSS resources
            oss_storage_class = str(row.get('Storage Type', 'Standard')).strip()
            availability_zone = str(row.get('Availability Zone', 'single-az')).strip()
            
            # Handle potential NaN values safely
            requests_read_val = row.get('Requests Read', 0)
            requests_write_val = row.get('Requests Write', 0)
            requests_delete_val = row.get('Requests Delete', 0)
            data_retrieval_val = row.get('Data Retrieval GB', 0)
            internet_outbound_val = row.get('Internet Outbound GB', 0)
            retrieval_type_val = row.get('Retrieval Type', '')
            
            requests_read = int(requests_read_val) if pd.notna(requests_read_val) and str(requests_read_val) != 'nan' else 0
            requests_write = int(requests_write_val) if pd.notna(requests_write_val) and str(requests_write_val) != 'nan' else 0
            requests_delete = int(requests_delete_val) if pd.notna(requests_delete_val) and str(requests_delete_val) != 'nan' else 0
            data_retrieval_gb = float(data_retrieval_val) if pd.notna(data_retrieval_val) and str(data_retrieval_val) != 'nan' else 0.0
            internet_outbound_gb = float(internet_outbound_val) if pd.notna(internet_outbound_val) and str(internet_outbound_val) != 'nan' else 0.0
            retrieval_type = str(retrieval_type_val).strip() if pd.notna(retrieval_type_val) and str(retrieval_type_val) != 'nan' else ''
            
            oss_costs = get_oss_cost(
                storage_gb, oss_storage_class, availability_zone,
                requests_read, requests_write, requests_delete,
                data_retrieval_gb, retrieval_type if retrieval_type else None,
                internet_outbound_gb, oss_data
            )
            compute_cost = oss_costs['total_cost']
            storage_cost = 0  # OSS storage is included in compute_cost via get_oss_cost
            total_cost_per_instance = compute_cost
            total_cost_for_quantity = total_cost_per_instance * quantity
            result_row = {
                'Resource Type': resource_type,
                'Storage (GB)': storage_gb,
                'Storage Type': oss_storage_class,
                'Region': region,
                'Quantity': quantity,
                'Availability Zone': availability_zone,
                'Requests Read': requests_read,
                'Requests Write': requests_write,
                'Requests Delete': requests_delete,
                'Data Retrieval GB': data_retrieval_gb,
                'Retrieval Type': retrieval_type,
                'Internet Outbound GB': internet_outbound_gb,
                'Compute Cost (Monthly)': round(compute_cost, 2),
                'OSS Storage Cost': round(oss_costs['storage_cost'], 4),
                'OSS Request Cost': round(oss_costs['request_cost'], 4),
                'OSS Retrieval Cost': round(oss_costs['retrieval_cost'], 4),
                'OSS Traffic Cost': round(oss_costs['traffic_cost'], 4),
                'Total Cost per Instance': round(total_cost_per_instance, 2),
                'Total Cost for Quantity': round(total_cost_for_quantity, 2),
                'Mapping Status': status
            }
            result_rows.append(result_row)
        else:
            # Handle ECS and Database resources
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
    total_instances = int(df['Quantity'].fillna(0).sum())
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
    oss_df = df[df['Resource Type'].str.lower() == 'oss']
    if not oss_df.empty:
        oss_total_storage = oss_df['OSS Storage Cost'].sum() if 'OSS Storage Cost' in oss_df.columns else 0
        oss_total_request = oss_df['OSS Request Cost'].sum() if 'OSS Request Cost' in oss_df.columns else 0
        oss_total_retrieval = oss_df['OSS Retrieval Cost'].sum() if 'OSS Retrieval Cost' in oss_df.columns else 0
        oss_total_traffic = oss_df['OSS Traffic Cost'].sum() if 'OSS Traffic Cost' in oss_df.columns else 0
        summary_by_oss_storage_class = oss_df.groupby('Storage Type')['Total Cost for Quantity'].sum().to_dict()
    else:
        oss_total_storage = 0
        oss_total_request = 0
        oss_total_retrieval = 0
        oss_total_traffic = 0
        summary_by_oss_storage_class = {}
    return {
        'total_monthly_cost': round(total_monthly_cost, 2),
        'total_yearly_cost': round(total_yearly_cost, 2),
        'total_instances': int(total_instances),
        'needs_review_count': needs_review_count,
        'by_type': summary_by_type,
        'by_flavor_family': summary_by_family,
        'by_db_type': summary_by_db_type,
        'by_deployment': summary_by_deployment,
        'oss_storage_cost': round(oss_total_storage, 4),
        'oss_request_cost': round(oss_total_request, 4),
        'oss_retrieval_cost': round(oss_total_retrieval, 4),
        'oss_traffic_cost': round(oss_total_traffic, 4),
        'by_oss_storage_class': summary_by_oss_storage_class
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
        oss_summary_data = []
        if 'oss_storage_cost' in summary and summary['oss_storage_cost'] > 0:
            oss_summary_data.extend([
                {'Category': 'OSS Storage Cost', 'Value': summary['oss_storage_cost']},
                {'Category': 'OSS Request Cost', 'Value': summary['oss_request_cost']},
                {'Category': 'OSS Retrieval Cost', 'Value': summary['oss_retrieval_cost']},
                {'Category': 'OSS Traffic Cost', 'Value': summary['oss_traffic_cost']}
            ])
            oss_storage_class_df = pd.DataFrame([
                {'Storage Class': k, 'Total Cost': v}
                for k, v in summary.get('by_oss_storage_class', {}).items()
            ])
            if not oss_storage_class_df.empty:
                oss_summary_data.append({'Category': '--- By Storage Class ---', 'Value': ''})
                for _, row in oss_storage_class_df.iterrows():
                    oss_summary_data.append({'Category': f"  {row['Storage Class']}", 'Value': row['Total Cost']})
        if oss_summary_data:
            oss_summary_df = pd.DataFrame(oss_summary_data)
            oss_summary_df.to_excel(writer, sheet_name='OSS Summary', index=False)
        unmapped_df = df[df['Mapping Status'].str.contains('Review', case=False, na=False)]
        if not unmapped_df.empty:
            unmapped_df.to_excel(writer, sheet_name='Unmapped Resources', index=False)