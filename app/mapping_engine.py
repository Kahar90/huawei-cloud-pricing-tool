import json
import os
from typing import Dict, List, Optional, Tuple, Any


def get_data_path(filename: str) -> str:
    return os.path.join(os.path.dirname(__file__), 'data', filename)


def load_ecs_pricing() -> Dict:
    with open(get_data_path('ecs_pricing.json'), 'r') as f:
        return json.load(f)


def load_db_pricing() -> Dict:
    with open(get_data_path('db_pricing.json'), 'r') as f:
        return json.load(f)


def load_storage_pricing() -> Dict:
    with open(get_data_path('storage_pricing.json'), 'r') as f:
        return json.load(f)


def get_region(ecs_data: Dict) -> str:
    return ecs_data.get('region', 'ap-southeast-3')


def get_ecs_flavors(ecs_data: Dict) -> List[Dict]:
    return ecs_data.get('flavors', [])


def get_db_flavors(db_data: Dict, db_type: str) -> List[Dict]:
    return db_data.get('databases', {}).get(db_type, [])


def get_available_db_types(db_data: Dict) -> List[str]:
    return list(db_data.get('databases', {}).keys())


def find_best_ecs_flavor(
    vcpus: int,
    ram_gb: int,
    desired_tier: Optional[str],
    flavors: List[Dict]
) -> Tuple[Optional[Dict], str]:
    candidates = flavors
    if desired_tier and desired_tier.lower() not in ['any', '', 'none']:
        candidates = [f for f in flavors if f.get('family', '').lower() == desired_tier.lower()]
    if not candidates:
        candidates = flavors
    exact_matches = [f for f in candidates if f['vcpus'] == vcpus and f['ram_gb'] >= ram_gb]
    if exact_matches:
        exact_matches.sort(key=lambda x: (
            0 if x.get('cpu_type', 'Intel') == 'AMD' else 1,
            x['vcpus'],
            x['ram_gb']
        ))
        return exact_matches[0], "Matched"
    larger_vcpu_matches = [f for f in candidates if f['vcpus'] > vcpus and f['ram_gb'] >= ram_gb]
    if larger_vcpu_matches:
        larger_vcpu_matches.sort(key=lambda x: (
            0 if x.get('cpu_type', 'Intel') == 'AMD' else 1,
            x['vcpus'],
            x['ram_gb']
        ))
        return larger_vcpu_matches[0], "Upgraded"
    ram_matches = [f for f in candidates if f['ram_gb'] >= ram_gb]
    if ram_matches:
        ram_matches.sort(key=lambda x: (
            0 if x.get('cpu_type', 'Intel') == 'AMD' else 1,
            x['vcpus'],
            x['ram_gb']
        ))
        return ram_matches[0], "Needs Review - Partial Match"
    return None, "Needs Review"


def find_best_db_flavor(
    vcpus: int,
    ram_gb: int,
    db_flavors: List[Dict]
) -> Tuple[Optional[Dict], str]:
    exact_matches = [f for f in db_flavors if f['vcpus'] == vcpus and f['ram_gb'] >= ram_gb]
    if exact_matches:
        exact_matches.sort(key=lambda x: (x['vcpus'], x['ram_gb']))
        return exact_matches[0], "Matched"
    larger_matches = [f for f in db_flavors if f['vcpus'] >= vcpus and f['ram_gb'] >= ram_gb]
    if larger_matches:
        larger_matches.sort(key=lambda x: (x['vcpus'], x['ram_gb']))
        return larger_matches[0], "Upgraded"
    ram_matches = [f for f in db_flavors if f['ram_gb'] >= ram_gb]
    if ram_matches:
        ram_matches.sort(key=lambda x: (x['vcpus'], x['ram_gb']))
        return ram_matches[0], "Needs Review - Partial Match"
    return None, "Needs Review"


def map_resource(
    resource_type: str,
    vcpus: int,
    ram_gb: int,
    desired_tier: Optional[str],
    db_type: Optional[str],
    ecs_flavors: List[Dict],
    db_data: Dict
) -> Tuple[Optional[Dict], str]:
    if resource_type.lower() == 'ecs':
        return find_best_ecs_flavor(vcpus, ram_gb, desired_tier, ecs_flavors)
    elif resource_type.lower() == 'database':
        if not db_type:
            db_type = 'mysql'
        db_flavors = get_db_flavors(db_data, db_type)
        if not db_flavors:
            return None, f"Unknown DB Type: {db_type}"
        return find_best_db_flavor(vcpus, ram_gb, db_flavors)
    else:
        return None, "Unknown Resource Type"


def map_resources(
    df,
    ecs_data: Dict,
    db_data: Dict,
    default_db_type: str = 'mysql',
    default_deployment: str = 'single'
) -> Tuple[List[Dict], List[Dict]]:
    results = []
    ecs_flavors = get_ecs_flavors(ecs_data)
    for _, row in df.iterrows():
        resource_type = str(row.get('Resource Type', 'ECS')).strip()
        vcpus = int(row.get('vCPUs', 0) or 0)
        ram_gb = int(row.get('RAM (GB)', 0) or 0)
        desired_tier = row.get('Desired Tier')
        if desired_tier is not None and str(desired_tier).strip() == '':
            desired_tier = None
        db_type = row.get('DB Type')
        if db_type is not None and str(db_type).strip() == '':
            db_type = None
        deployment = row.get('Deployment')
        if deployment is not None and str(deployment).strip() == '':
            deployment = None
        if resource_type.lower() == 'database':
            if not db_type:
                db_type = default_db_type
            if not deployment:
                deployment = default_deployment
        else:
            db_type = None
            deployment = None
        flavor, status = map_resource(
            resource_type, vcpus, ram_gb, desired_tier,
            db_type, ecs_flavors, db_data
        )
        result = {
            'flavor': flavor['name'] if flavor else None,
            'flavor_family': flavor.get('family', 'N/A') if flavor else None,
            'db_type': db_type if resource_type.lower() == 'database' else None,
            'deployment': deployment if resource_type.lower() == 'database' else None,
            'status': status,
            'original_vcpus': vcpus,
            'original_ram': ram_gb
        }
        results.append(result)
    return results, ecs_flavors