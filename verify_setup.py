#!/usr/bin/env python3
"""GameMatch Setup Verification Script"""

from pathlib import Path
import sys

print("🔍 GameMatch Project Verification\n")
print("=" * 60)

# Check files
required_files = [
    "app/main.py",
    "app/schemas.py",
    "app/models.py",
    "app/database.py",
    "app/crud.py",
    "requirements.txt",
    "README.md",
    "examples.json"
]

print("\n📁 File Check:")
for file in required_files:
    path = Path(file)
    status = "✅" if path.exists() else "❌"
    print(f"  {status} {file}")

# Check Python imports
print("\n📦 Import Check:")
try:
    from app.schemas import UserRead, GameRead, TeamRead, MatchRead
    print("  ✅ Schemas imported")
except Exception as e:
    print(f"  ❌ Schemas: {e}")

try:
    from app.database import engine, init_db, get_db
    print("  ✅ Database module OK")
except Exception as e:
    print(f"  ❌ Database: {e}")

try:
    from app.main import app
    routes = [r.path for r in app.routes if hasattr(r, 'path')]
    print(f"  ✅ Main app OK ({len(routes)} routes)")
except Exception as e:
    print(f"  ❌ Main: {e}")

# FastAPI routes
print("\n🔗 FastAPI Routes:")
try:
    from app.main import app
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            methods = ','.join(route.methods)
            print(f"  {route.path:25} [{methods}]")
except Exception as e:
    print(f"  ❌ Error: {e}")

print("\n" + "=" * 60)
print("✅ Setup verification complete!")
