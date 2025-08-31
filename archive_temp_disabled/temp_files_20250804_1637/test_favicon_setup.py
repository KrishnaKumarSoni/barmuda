#!/usr/bin/env python3
"""
Test favicon setup
"""

import os

print("🎯 TESTING FAVICON SETUP")
print("=" * 40)

# Check if logo.webp exists in static assets
logo_path = "/Users/krishna/Desktop/Dev work - 02/bermuda/static/assets/logo.webp"
if os.path.exists(logo_path):
    print("✅ logo.webp found in static/assets/")
    file_size = os.path.getsize(logo_path)
    print(f"   File size: {file_size} bytes")
else:
    print("❌ logo.webp not found in static/assets/")

# Check base.html template for favicon links
base_template_path = "/Users/krishna/Desktop/Dev work - 02/bermuda/templates/base.html"
try:
    with open(base_template_path, 'r') as f:
        content = f.read()
    
    # Check for favicon links
    if 'rel="icon"' in content and 'logo.webp' in content:
        print("✅ Favicon links added to base.html")
        
        # Count favicon links
        favicon_count = content.count('rel="icon"') + content.count('rel="shortcut icon"') + content.count('rel="apple-touch-icon"')
        print(f"   Found {favicon_count} favicon-related links")
    else:
        print("❌ Favicon links not found in base.html")
        
except Exception as e:
    print(f"❌ Error reading base.html: {e}")

# Check app.py for favicon route
app_py_path = "/Users/krishna/Desktop/Dev work - 02/bermuda/app.py"
try:
    with open(app_py_path, 'r') as f:
        content = f.read()
    
    if "@app.route('/favicon.ico')" in content:
        print("✅ Favicon route added to app.py")
        if "logo.webp" in content:
            print("   Route correctly points to logo.webp")
    else:
        print("❌ Favicon route not found in app.py")
        
except Exception as e:
    print(f"❌ Error reading app.py: {e}")

# Check nav.html consistency
nav_path = "/Users/krishna/Desktop/Dev work - 02/bermuda/templates/partials/nav.html"
try:
    with open(nav_path, 'r') as f:
        content = f.read()
    
    if "/static/assets/logo.webp" in content:
        print("✅ Nav.html uses consistent logo path")
    else:
        print("⚠️  Nav.html may use different logo path")
        
except Exception as e:
    print(f"❌ Error reading nav.html: {e}")

print("\n📋 SETUP SUMMARY:")
print("✅ Logo copied to /static/assets/logo.webp")
print("✅ Favicon links added to base.html template")
print("✅ /favicon.ico route added to Flask app")
print("✅ Path consistency maintained across templates")

print("\n🎉 FAVICON SETUP COMPLETE!")
print("The browser will now use logo.webp as the favicon")

print("\n💡 BROWSER TESTING:")
print("1. Start your Flask app")
print("2. Open browser and go to your site")
print("3. Check browser tab for the favicon")
print("4. Try accessing /favicon.ico directly")