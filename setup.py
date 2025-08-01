#!/usr/bin/env python3
"""
Setup and initialization script for Bermuda MVP
Helps configure Firebase, environment variables, and project setup.
"""

import os
import json
import subprocess
import sys
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    return True

def check_virtual_environment():
    """Check if virtual environment is active"""
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ Virtual environment is active")
        return True
    else:
        print("⚠️  Virtual environment not detected")
        print("   Recommendation: Create and activate a virtual environment:")
        print("   python -m venv venv")
        print("   source venv/bin/activate  # On Windows: venv\\Scripts\\activate")
        return False

def install_dependencies():
    """Install Python dependencies"""
    print("📦 Installing Python dependencies...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                      check=True, capture_output=True)
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def check_firebase_service_account():
    """Check if Firebase service account file exists"""
    service_account_file = "bermuda-01-firebase-adminsdk-fbsvc-660474f630.json"
    if os.path.exists(service_account_file):
        print("✅ Firebase service account file found")
        return True
    else:
        print(f"❌ Firebase service account file not found: {service_account_file}")
        print("   Please download the service account key from Firebase Console")
        return False

def create_env_file():
    """Create .env file from template if it doesn't exist"""
    if os.path.exists(".env"):
        print("✅ .env file already exists")
        return True
    
    if os.path.exists(".env.example"):
        print("📝 Creating .env file from template...")
        with open(".env.example", "r") as template:
            content = template.read()
        
        # Generate a random secret key
        import secrets
        secret_key = secrets.token_urlsafe(32)
        content = content.replace("your-secret-key-here", secret_key)
        
        with open(".env", "w") as env_file:
            env_file.write(content)
        
        print("✅ .env file created")
        print("⚠️  Please update Firebase configuration in .env file")
        return True
    else:
        print("❌ .env.example template not found")
        return False

def check_firebase_project():
    """Validate Firebase service account and project"""
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
        
        # Initialize Firebase (if not already initialized)
        if not firebase_admin._apps:
            cred = credentials.Certificate('bermuda-01-firebase-adminsdk-fbsvc-660474f630.json')
            firebase_admin.initialize_app(cred)
        
        # Test Firestore connection
        db = firestore.client()
        # Try to read from a test collection (this will create it if it doesn't exist)
        test_ref = db.collection('_test').document('connection')
        test_ref.set({'timestamp': firestore.SERVER_TIMESTAMP, 'status': 'connected'})
        
        print("✅ Firebase connection successful")
        
        # Clean up test document
        test_ref.delete()
        return True
        
    except Exception as e:
        print(f"❌ Firebase connection failed: {e}")
        return False

def create_directory_structure():
    """Ensure all required directories exist"""
    directories = [
        "templates",
        "static/css",
        "static/js",
        "static/images"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    print("✅ Directory structure created")
    return True

def run_setup():
    """Run the complete setup process"""
    print("🚀 Setting up Bermuda MVP - Module 1")
    print("=" * 50)
    
    checks = [
        ("Python Version", check_python_version),
        ("Virtual Environment", check_virtual_environment),
        ("Directory Structure", create_directory_structure),
        ("Dependencies", install_dependencies),
        ("Firebase Service Account", check_firebase_service_account),
        ("Environment File", create_env_file),
        ("Firebase Connection", check_firebase_project),
    ]
    
    all_passed = True
    for name, check_func in checks:
        print(f"\n🔍 Checking {name}...")
        if not check_func():
            all_passed = False
    
    print("\n" + "=" * 50)
    
    if all_passed:
        print("🎉 Setup completed successfully!")
        print("\n📋 Next steps:")
        print("1. Update .env file with your Firebase configuration")
        print("2. Run the application: python app.py")
        print("3. Run tests: python test_auth.py")
        print("4. Open http://localhost:5000 in your browser")
    else:
        print("⚠️  Setup completed with warnings. Please address the issues above.")
    
    return all_passed

if __name__ == "__main__":
    success = run_setup()
    exit(0 if success else 1)