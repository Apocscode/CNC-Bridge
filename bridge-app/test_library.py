"""Quick test of the reference library."""
import sys
sys.path.insert(0, ".")
from src.core.reference_library import get_library, search_library, get_categories

lib = get_library()
print(f"Library built: {len(lib)} entries")

cats = get_categories()
print(f"Categories: {len(cats)}")
for c in cats:
    print(f"  {c.value}")

print()
for q in ["baud", "mirror", "G83", "servo balance", "XON", "rapid speed", "supermax", "tool change"]:
    results = search_library(q)
    print(f'Search "{q}": {len(results)} results')
    for r in results[:3]:
        print(f"  {r.code}: {r.title}")
    print()
