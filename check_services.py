import requests

services = [
    ('Backend', 'http://127.0.0.1:8000/health'),
    ('Chainlit', 'http://127.0.0.1:8001'),
    ('Voice', 'http://127.0.0.1:5000/health')
]

print("\n🔍 Service Health Check\n" + "="*30)
for name, url in services:
    try:
        r = requests.get(url, timeout=2)
        print(f"✓ {name:12} OK ({r.status_code})")
    except Exception as e:
        print(f"✗ {name:12} DOWN")
print("="*30 + "\n")
