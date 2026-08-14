"""
build_index.py - Run this once to generate mock Argo data and build the index.
Usage: python build_index.py
"""

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

print("=" * 55)
print("  ARGO FloatChat — Data Setup")
print("=" * 55)

# Step 1: Generate mock Argo floats
print("\n[1/2] Generating synthetic Argo float profiles…")
from backend.downloader import generate_all_mock_floats
results = generate_all_mock_floats(verbose=True)
for wmo, n in results.items():
    print(f"  WMO {wmo}: {n} profiles created")

# Step 2: Build the index
print("\n[2/2] Building metadata index…")
from backend.indexer import build_index, get_index_stats
build_index(verbose=True)
stats = get_index_stats()
print(f"\n  Total floats:   {stats['total_floats']}")
print(f"  Total profiles: {stats['total_profiles']}")
for ocean in stats.get("by_ocean", []):
    print(f"  {ocean['ocean']}: {ocean['n']} floats")

print("\n[OK] Setup complete. Run: python main.py")
