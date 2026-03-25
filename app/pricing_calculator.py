import json
import os
from typing import Dict, List, Optional, Union, Tuple
from io import BytesIO
import pandas as pd
from mapping_engine import (
    load_ecs_pricing, load_db_pricing, load_storage_pricing, load_oss_pricing,
    get_region, get_ecs_flavors, get_db_flavors, get_available_db_types,
    get_oss_storage_classes
)


def find_cheaper_ecs_alternatives(
    current_flavor_name: str,
    vcpus: int,
    ram_gb: int,
    pricing_model: str,
    hours_per_month: float,
    ecs_data: Dict
) -> List[Dict]:
    """
    Find ECS flavors that meet requirements but are cheaper than current selection.
    Returns list of cheaper alternatives sorted by price (lowest first).
    """
    current_price = get_flavor_price(
        current_flavor_name, 'ecs', None, None,
        pricing_model, hours_per_month, ecs_data, {}
    )
    
    # Skip if current flavor has no price or price is 0 (unavailable)
    if current_price is None or current_price <= 0:
        return []
    
    flavors = get_ecs_flavors(ecs_data)
    cheaper_alternatives = []
    
    for flavor in flavors:
        # Skip current flavor
        if flavor['name'] == current_flavor_name:
            continue
            
        # Check for EXACT spec match only (same vCPUs and same RAM)
        if flavor['vcpus'] == vcpus and flavor['ram_gb'] == ram_gb:
            alt_price = get_flavor_price(
                flavor['name'], 'ecs', None, None,
                pricing_model, hours_per_month, ecs_data, {}
            )
            
            # Skip alternatives with no price or price is 0 (unavailable)
            if alt_price is not None and alt_price > 0 and alt_price < current_price:
                savings = current_price - alt_price
                savings_percent = (savings / current_price) * 100 if current_price > 0 else 0
                
                cheaper_alternatives.append({
                    'name': flavor['name'],
                    'family': flavor.get('family', 'N/A'),
                    'vcpus': flavor['vcpus'],
                    'ram_gb': flavor['ram_gb'],
                    'cpu_type': flavor.get('cpu_type', 'Intel'),
                    'price': alt_price,
                    'savings': savings,
                    'savings_percent': round(savings_percent, 1)
                })

    # Sort by: 1) Non-t flavors prioritized, 2) Savings (highest first)
    # "t" flavors (t6, t7) are deprioritized - they come last
    cheaper_alternatives.sort(key=lambda x: (x['name'].startswith('t'), -x['savings']))
    return cheaper_alternatives[:3]  # Return top 3 alternatives


def find_cheaper_db_alternatives(
    current_flavor_name: str,
    vcpus: int,
    ram_gb: int,
    db_type: str,
    deployment: str,
    pricing_model: str,
    hours_per_month: float,
    db_data: Dict
) -> List[Dict]:
    """
    Find database flavors that meet requirements but are cheaper than current selection.
    Returns list of cheaper alternatives sorted by price (lowest first).
    """
    current_price = get_flavor_price(
        current_flavor_name, 'database', db_type, deployment,
        pricing_model, hours_per_month, {}, db_data
    )
    
    # Skip if current flavor has no price or price is 0 (unavailable)
    if current_price is None or current_price <= 0:
        return []
    
    db_flavors = get_db_flavors(db_data, db_type)
    cheaper_alternatives = []
    
    for flavor in db_flavors:
        # Skip current flavor
        if flavor['name'] == current_flavor_name:
            continue

        # Check for EXACT spec match only (same vCPUs and same RAM)
        if flavor['vcpus'] == vcpus and flavor['ram_gb'] == ram_gb:
            alt_price = get_flavor_price(
                flavor['name'], 'database', db_type, deployment,
                pricing_model, hours_per_month, {}, db_data
            )
            
            # Skip alternatives with no price or price is 0 (unavailable)
            if alt_price is not None and alt_price > 0 and alt_price < current_price:
                savings = current_price - alt_price
                savings_percent = (savings / current_price) * 100 if current_price > 0 else 0
                
                cheaper_alternatives.append({
                    'name': flavor['name'],
                    'vcpus': flavor['vcpus'],
                    'ram_gb': flavor['ram_gb'],
                    'price': alt_price,
                    'savings': savings,
                    'savings_percent': round(savings_percent, 1)
                })
    
    # Sort by savings (highest first)
    cheaper_alternatives.sort(key=lambda x: x['savings'], reverse=True)
    return cheaper_alternatives[:3]  # Return top 3 alternatives


def get_cost_savings_summary(
    result_df: pd.DataFrame,
    pricing_model: str,
    hours_per_month: float,
    ecs_data: Dict,
    db_data: Dict,
    original_summary: Optional[Dict] = None
) -> Dict:
    """
    Calculate total potential savings across all resources.
    Returns summary with total savings and per-resource breakdown.
    """
    total_current_cost = 0
    total_potential_savings = 0
    savings_opportunities = []
    
    for idx, row in result_df.iterrows():
        resource_type = str(row.get('Resource Type', '')).lower()
        flavor_name = row.get('Mapped Flavor')
        vcpus = int(row.get('vCPUs', 0) or 0) if pd.notna(row.get('vCPUs')) else 0
        ram_gb = int(row.get('RAM (GB)', 0) or 0) if pd.notna(row.get('RAM (GB)')) else 0
        quantity = int(row.get('Quantity', 1) or 1) if pd.notna(row.get('Quantity')) else 1
        
        if not flavor_name or pd.isna(flavor_name):
            continue
            
        current_cost = row.get('Compute Cost (Monthly)', 0)
        
        # Track current cost for ALL resources (ECS, Database, OSS)
        total_current_cost += current_cost
        
        if resource_type == 'ecs':
            alternatives = find_cheaper_ecs_alternatives(
                flavor_name, vcpus, ram_gb, pricing_model, hours_per_month, ecs_data
            )
        elif resource_type == 'database':
            db_type = row.get('DB Type', 'mysql')
            deployment = row.get('Deployment', 'single')
            alternatives = find_cheaper_db_alternatives(
                flavor_name, vcpus, ram_gb, db_type, deployment,
                pricing_model, hours_per_month, db_data
            )
        else:
            continue
        
        if alternatives:
            best_alt = alternatives[0]
            monthly_savings = best_alt['savings'] * quantity
            yearly_savings = monthly_savings * 12
            
            total_potential_savings += monthly_savings
            
            savings_opportunities.append({
                'row_index': idx,
                'resource_type': resource_type.upper(),
                'current_flavor': flavor_name,
                'current_cost': current_cost,
                'recommended_flavor': best_alt['name'],
                'recommended_cost': best_alt['price'] * quantity,
                'monthly_savings': round(monthly_savings, 2),
                'yearly_savings': round(yearly_savings, 2),
                'savings_percent': best_alt['savings_percent'],
                'alternative_specs': f"{best_alt['vcpus']}vCPU/{best_alt['ram_gb']}GB",
                'all_alternatives': alternatives
            })
    
    total_optimized_monthly = total_current_cost - total_potential_savings
    total_optimized_yearly = total_optimized_monthly * 12
    
    return {
        'total_monthly_savings': round(total_potential_savings, 2),
        'total_yearly_savings': round(total_potential_savings * 12, 2),
        'total_current_monthly': round(total_current_cost, 2),
        'total_current_yearly': round(total_current_cost * 12, 2),
        'total_optimized_monthly': round(total_optimized_monthly, 2),
        'total_optimized_yearly': round(total_optimized_yearly, 2),
        'savings_percent': round((total_potential_savings / total_current_cost) * 100, 1) if total_current_cost > 0 else 0,
        'opportunities_count': len(savings_opportunities),
        'opportunities': savings_opportunities,
        'total_optimizable_resources': len(savings_opportunities)
    }


def apply_x_mode(
    result_df: pd.DataFrame,
    x_family: Optional[str],
    ecs_data: Dict,
    pricing_model: str,
    hours_per_month: float
) -> Tuple[pd.DataFrame, Dict]:
    """
    Apply X-Mode: Transform ALL ECS to X-series flavors.

    Args:
        result_df: Original results DataFrame
        x_family: Target X family ('x1', 'x2e', or None for auto)
        ecs_data: ECS pricing data
        pricing_model: Pricing model (Hourly/Monthly/Yearly)
        hours_per_month: Hours per month for hourly pricing

    Returns:
        Tuple of (transformed DataFrame, summary dict)
    """
    flavors = ecs_data.get('flavors', [])
    transformed_df = result_df.copy()

    total_original_cost = 0
    total_new_cost = 0
    transformed_count = 0
    transformations = []

    for idx, row in transformed_df.iterrows():
        if row.get('Resource Type', '').lower() != 'ecs':
            continue

        original_flavor = row.get('Mapped Flavor', '')
        vcpus = int(row.get('vCPUs', 0) or 0)
        ram_gb = int(row.get('RAM (GB)', 0) or 0)
        quantity = int(row.get('Quantity', 1) or 1)

        if not original_flavor or vcpus == 0:
            continue

        original_cost = row.get('Compute Cost (Monthly)', 0) * quantity
        total_original_cost += original_cost

        # Find best X-series flavor
        target_family = x_family if x_family else 'auto'

        if target_family == 'auto':
            # Auto: Pick cheapest X-series (x1 or x2e)
            best_flavor = None
            best_price = float('inf')

            for flavor in flavors:
                if not flavor['name'].lower().startswith(('x1.', 'x2e.')):
                    continue
                if flavor['vcpus'] == vcpus and flavor['ram_gb'] == ram_gb:
                    price = get_flavor_price(
                        flavor['name'], 'ecs', None, None,
                        pricing_model, hours_per_month, ecs_data, {}
                    )
                    if price and price > 0 and price < best_price:
                        best_price = price
                        best_flavor = flavor
        else:
            # Specific family (x1 or x2e)
            best_flavor = None
            best_price = float('inf')
            prefix = target_family.lower() + '.'

            for flavor in flavors:
                if not flavor['name'].lower().startswith(prefix):
                    continue
                if flavor['vcpus'] == vcpus and flavor['ram_gb'] == ram_gb:
                    price = get_flavor_price(
                        flavor['name'], 'ecs', None, None,
                        pricing_model, hours_per_month, ecs_data, {}
                    )
                    if price and price > 0 and price < best_price:
                        best_price = price
                        best_flavor = flavor

        if best_flavor:
            new_cost = best_price * quantity
            savings = original_cost - new_cost

            transformed_df.at[idx, 'Mapped Flavor'] = best_flavor['name']
            transformed_df.at[idx, 'Flavor Family'] = best_flavor.get('family', 'N/A')
            transformed_df.at[idx, 'Compute Cost (Monthly)'] = best_price

            # Recalculate total costs
            storage_cost = row.get('Storage Cost (Monthly)', 0)
            transformed_df.at[idx, 'Total Cost per Instance'] = best_price + storage_cost
            transformed_df.at[idx, 'Total Cost for Quantity'] = (best_price + storage_cost) * quantity

            total_new_cost += new_cost
            transformed_count += 1

            transformations.append({
                'row_index': idx,
                'original_flavor': original_flavor,
                'new_flavor': best_flavor['name'],
                'vcpus': vcpus,
                'ram_gb': ram_gb,
                'original_cost': original_cost,
                'new_cost': new_cost,
                'savings': savings,
                'quantity': quantity
            })
        else:
            # No matching X-series flavor found
            total_new_cost += original_cost
            transformations.append({
                'row_index': idx,
                'original_flavor': original_flavor,
                'new_flavor': 'NOT FOUND',
                'vcpus': vcpus,
                'ram_gb': ram_gb,
                'original_cost': original_cost,
                'new_cost': original_cost,
                'savings': 0,
                'quantity': quantity,
                'warning': f'No X-series flavor found for {vcpus}vCPU/{ram_gb}GB'
            })

    total_savings = total_original_cost - total_new_cost
    savings_percent = (total_savings / total_original_cost * 100) if total_original_cost > 0 else 0

    summary = {
        'x_family': x_family or 'auto',
        'total_original_cost': round(total_original_cost, 2),
        'total_new_cost': round(total_new_cost, 2),
        'total_savings': round(total_savings, 2),
        'savings_percent': round(savings_percent, 1),
        'transformed_count': transformed_count,
        'total_ecs_count': len([r for _, r in result_df.iterrows() if r.get('Resource Type', '').lower() == 'ecs']),
        'transformations': transformations
    }

    return transformed_df, summary


def create_optimized_excel(
    result_df: pd.DataFrame,
    savings_summary: Dict,
    summary: Dict,
    output: Union[str, BytesIO]
) -> None:
    """
    Create an Excel file with optimized pricing applied.
    Replaces current flavors with recommended cheaper alternatives.
    """
    # Create a copy of the result DataFrame
    optimized_df = result_df.copy()
    
    # Track which rows were optimized
    optimization_map = {opp['row_index']: opp for opp in savings_summary['opportunities']}
    
    # Apply optimizations
    optimized_df['Original Flavor'] = optimized_df['Mapped Flavor']
    optimized_df['Original Compute Cost'] = optimized_df['Compute Cost (Monthly)']
    optimized_df['Original Total Cost'] = optimized_df['Total Cost for Quantity']
    optimized_df['Optimization Applied'] = 'No'
    optimized_df['Savings Amount'] = 0.0
    optimized_df['Savings Percent'] = '0%'
    
    for idx, row in optimized_df.iterrows():
        if idx in optimization_map:
            opp = optimization_map[idx]
            # Update the flavor
            optimized_df.at[idx, 'Mapped Flavor'] = opp['recommended_flavor']
            # Update compute cost
            optimized_df.at[idx, 'Compute Cost (Monthly)'] = opp['recommended_cost'] / row.get('Quantity', 1) if row.get('Quantity', 1) > 0 else opp['recommended_cost']
            # Recalculate total cost
            storage_cost = row.get('Storage Cost (Monthly)', 0)
            quantity = row.get('Quantity', 1)
            new_compute_cost = opp['recommended_cost'] / quantity if quantity > 0 else opp['recommended_cost']
            optimized_df.at[idx, 'Total Cost per Instance'] = new_compute_cost + storage_cost
            optimized_df.at[idx, 'Total Cost for Quantity'] = opp['recommended_cost'] + (storage_cost * quantity)
            # Mark as optimized
            optimized_df.at[idx, 'Optimization Applied'] = 'Yes'
            optimized_df.at[idx, 'Savings Amount'] = opp['monthly_savings']
            optimized_df.at[idx, 'Savings Percent'] = f"{opp['savings_percent']:.1f}%"
    
    # Create Excel with multiple sheets
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Sheet 1: Optimized Results
        optimized_df.to_excel(writer, sheet_name='Optimized Results', index=False)
        
        # Sheet 2: Optimization Summary
        summary_data = {
            'Metric': [
                'Current Total Monthly Cost',
                'Optimized Total Monthly Cost',
                'Total Monthly Savings',
                'Current Total Yearly Cost',
                'Optimized Total Yearly Cost', 
                'Total Yearly Savings',
                'Savings Percentage',
                'Resources Optimized',
                'Total Resources'
            ],
            'Value': [
                f"${savings_summary['total_current_monthly']:,.2f}",
                f"${savings_summary['total_optimized_monthly']:,.2f}",
                f"${savings_summary['total_monthly_savings']:,.2f}",
                f"${savings_summary['total_current_yearly']:,.2f}",
                f"${savings_summary['total_optimized_yearly']:,.2f}",
                f"${savings_summary['total_yearly_savings']:,.2f}",
                f"{savings_summary['savings_percent']:.1f}%",
                savings_summary['opportunities_count'],
                len(result_df)
            ]
        }
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Optimization Summary', index=False)
        
        # Sheet 3: Detailed Changes
        if savings_summary['opportunities']:
            changes_df = pd.DataFrame([
                {
                    'Row': opp['row_index'] + 1,
                    'Resource Type': opp['resource_type'],
                    'Original Flavor': opp['current_flavor'],
                    'Optimized Flavor': opp['recommended_flavor'],
                    'Specs': opp['alternative_specs'],
                    'Original Cost': f"${opp['current_cost']:,.2f}",
                    'Optimized Cost': f"${opp['recommended_cost']:,.2f}",
                    'Monthly Savings': f"${opp['monthly_savings']:,.2f}",
                    'Yearly Savings': f"${opp['yearly_savings']:,.2f}",
                    'Savings %': f"{opp['savings_percent']:.1f}%"
                }
                for opp in savings_summary['opportunities']
            ])
            changes_df.to_excel(writer, sheet_name='Detailed Changes', index=False)
        
        # Sheet 4: Original Results (for comparison)
        result_df.to_excel(writer, sheet_name='Original Results', index=False)


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
        # 1. Results sheet - all data unchanged
        df.to_excel(writer, sheet_name='Results', index=False)
        
        # 2. Summary sheet - table format with Service, Count, Total Cost
        ecs_df = df[df['Resource Type'].str.lower() == 'ecs']
        db_df = df[df['Resource Type'].str.lower() == 'database']
        oss_df = df[df['Resource Type'].str.lower() == 'oss']
        
        summary_table = pd.DataFrame([
            {'Service': 'ECS', 'Count': int(ecs_df['Quantity'].sum()), 'Total Cost': summary['by_type'].get('ECS', 0)},
            {'Service': 'Database', 'Count': int(db_df['Quantity'].sum()), 'Total Cost': summary['by_type'].get('Database', 0)},
            {'Service': 'OSS', 'Count': int(oss_df['Quantity'].sum()), 'Total Cost': summary['by_type'].get('OSS', 0)},
            {'Service': 'GRAND TOTAL', 'Count': int(df['Quantity'].sum()), 'Total Cost': summary['total_monthly_cost']}
        ])
        summary_table.to_excel(writer, sheet_name='Summary', index=False)
        
        # 3. ECS sheet - ECS rows + Flavor Family summary
        if not ecs_df.empty:
            ecs_df.to_excel(writer, sheet_name='ECS', index=False)
            if summary.get('by_flavor_family'):
                family_df = pd.DataFrame([
                    {'Flavor Family': k, 'Total Cost': v}
                    for k, v in summary['by_flavor_family'].items()
                ])
                family_df.to_excel(writer, sheet_name='ECS', index=False, startrow=len(ecs_df) + 3)
        
        # 4. Database sheet - DB rows + DB Type summary + Deployment summary
        if not db_df.empty:
            db_df.to_excel(writer, sheet_name='Database', index=False)
            start_row = len(db_df) + 3
            
            if summary.get('by_db_type'):
                db_type_df = pd.DataFrame([
                    {'DB Type': k, 'Total Cost': v}
                    for k, v in summary['by_db_type'].items()
                ])
                db_type_df.to_excel(writer, sheet_name='Database', index=False, startrow=start_row)
                start_row += len(db_type_df) + 3
            
            if summary.get('by_deployment'):
                deployment_df = pd.DataFrame([
                    {'Deployment': k, 'Total Cost': v}
                    for k, v in summary['by_deployment'].items()
                ])
                deployment_df.to_excel(writer, sheet_name='Database', index=False, startrow=start_row)
        
        # 5. OSS sheet - OSS rows + OSS metrics summary
        if not oss_df.empty:
            oss_df.to_excel(writer, sheet_name='OSS', index=False)
            oss_summary_df = pd.DataFrame([
                {'OSS Metric': 'Total Storage Cost', 'Value': summary.get('oss_storage_cost', 0)},
                {'OSS Metric': 'Total Request Cost', 'Value': summary.get('oss_request_cost', 0)},
                {'OSS Metric': 'Total Retrieval Cost', 'Value': summary.get('oss_retrieval_cost', 0)},
                {'OSS Metric': 'Total Traffic Cost', 'Value': summary.get('oss_traffic_cost', 0)}
            ])
            oss_summary_df.to_excel(writer, sheet_name='OSS', index=False, startrow=len(oss_df) + 3)
        
        # 6. Unmapped Resources sheet - unchanged
        unmapped_df = df[df['Mapping Status'].str.contains('Review', case=False, na=False)]
        if not unmapped_df.empty:
            unmapped_df.to_excel(writer, sheet_name='Unmapped Resources', index=False)
