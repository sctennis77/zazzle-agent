import os
from pathlib import Path

TEMPLATE = Path('env.production.template')
PROD = Path('.env.production')

def parse_env_keys(path):
    keys = set()
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key = line.split('=', 1)[0].strip()
                keys.add(key)
    return keys

def main():
    if not TEMPLATE.exists() or not PROD.exists():
        print('Missing env.production.template or .env.production')
        return
    template_keys = parse_env_keys(TEMPLATE)
    prod_keys = parse_env_keys(PROD)
    missing = template_keys - prod_keys
    if missing:
        print('Missing keys in .env.production:')
        for key in sorted(missing):
            print(f'  {key}')
    else:
        print('All required keys from the template are present in .env.production!')

if __name__ == '__main__':
    main() 