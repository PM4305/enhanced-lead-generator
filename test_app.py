#!/usr/bin/env python3
"""
Essential test script for Enhanced Lead Generation Tool
Author: Prakhar Madnani
"""

import subprocess
import sys
import importlib
import os

def test_dependencies():
    """Test if required packages are installed"""
    print("🔍 Testing Dependencies...")
    
    required_packages = [
        'streamlit', 'pandas', 'requests', 'bs4', 
        'email_validator', 'plotly', 'playwright'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'bs4':
                importlib.import_module('bs4')
            else:
                importlib.import_module(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package}")
            missing_packages.append(package)
    
    return len(missing_packages) == 0

def test_main_app():
    """Test if main Streamlit app has valid syntax"""
    print("\n📋 Testing Main App...")
    
    try:
        with open('lead_generator.py', 'r') as f:
            code = f.read()
        compile(code, 'lead_generator.py', 'exec')
        print("✅ Main app syntax is valid")
        return True
    except Exception as e:
        print(f"❌ Main app error: {str(e)}")
        return False

def test_demo_script():
    """Test demo script functionality"""
    print("\n🧪 Testing Demo Script...")
    
    try:
        if os.path.exists('demo.py'):
            with open('demo.py', 'r') as f:
                code = f.read()
            compile(code, 'demo.py', 'exec')
            print("✅ Demo script syntax is valid")
            return True
        else:
            print("⚠️  Demo script not found")
            return False
    except Exception as e:
        print(f"❌ Demo script error: {str(e)}")
        return False

def check_file_structure():
    """Check essential files"""
    print("\n📁 Checking Essential Files...")
    
    essential_files = [
        'lead_generator.py',
        'requirements.txt',
        'README.md'
    ]
    
    all_present = True
    for file in essential_files:
        if os.path.exists(file):
            print(f"✅ {file}")
        else:
            print(f"❌ {file}")
            all_present = False
    
    return all_present

def main():
    """Run essential tests"""
    print("🎯 Enhanced Lead Generation Tool - Essential Tests")
    print("=" * 50)
    
    tests = [
        ("Dependencies", test_dependencies),
        ("File Structure", check_file_structure),
        ("Main App", test_main_app),
        ("Demo Script", test_demo_script)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*15} {test_name} {'='*15}")
        if test_func():
            passed += 1
    
    print(f"\n{'='*50}")
    print(f"🏁 RESULT: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 Ready for submission!")
        print("\nNext steps:")
        print("1. Run: streamlit run lead_generator.py")
        print("2. Take screenshots")
        print("3. Record demo video")
    else:
        print("⚠️  Fix issues before submission")

if __name__ == "__main__":
    main()