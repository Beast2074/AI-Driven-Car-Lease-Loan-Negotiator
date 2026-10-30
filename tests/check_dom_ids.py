import re

with open('frontend/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

with open('frontend/app.js', 'r', encoding='utf-8') as f:
    js = f.read()

# Extract all IDs defined in HTML
html_ids = set(re.findall(r'id=["\']([^"\']+)["\']', html))
print(f"Total HTML IDs defined: {len(html_ids)}")

# Extract all getElementById in JS
js_get_ids = set(re.findall(r'getElementById\(["\']([^"\']+)["\']\)', js))
print(f"Total getElementById calls in JS: {len(js_get_ids)}")

missing_ids = js_get_ids - html_ids
if missing_ids:
    print(f"Missing IDs ({len(missing_ids)}) in index.html referenced by app.js:")
    for mid in sorted(missing_ids):
        print(f"  - {mid}")
else:
    print("All getElementById calls in app.js match valid HTML elements in index.html!")

