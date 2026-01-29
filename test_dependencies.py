#!/usr/bin/env python3
"""Quick test to verify all dependencies are properly installed"""

import sys
from pathlib import Path

def test_imports():
    """Test if all required packages can be imported"""
    print("🧪 Testing Dependencies\n")
    
    packages = {
        "customtkinter": "GUI Framework",
        "openai": "OpenAI API",
        "cv2": "OpenCV (Video Processing)",
        "numpy": "Numerical Computing",
        "PIL": "Image Processing",
        "mediapipe": "Face Detection",
        "requests": "HTTP Requests",
        "google.oauth2": "Google OAuth",
    }
    
    failed = []
    for package, desc in packages.items():
        try:
            __import__(package)
            print(f"✅ {package:30} - {desc}")
        except ImportError as e:
            print(f"❌ {package:30} - {desc}")
            failed.append((package, str(e)))
    
    return len(failed) == 0, failed

def test_ytdlp():
    """Test if yt-dlp is available"""
    print("\n🎥 Testing yt-dlp\n")
    
    try:
        from utils.helpers import get_ytdlp_path
        ytdlp = get_ytdlp_path()
        print(f"✅ yt-dlp found at: {ytdlp}")
        return True
    except Exception as e:
        print(f"❌ yt-dlp not found: {e}")
        return False

def test_config():
    """Test if AI provider config works"""
    print("\n⚙️  Testing AI Provider Config\n")
    
    try:
        from config.ai_provider_config import (
            get_provider_display_list,
            get_provider_base_url,
            get_provider_default_models
        )
        
        providers = get_provider_display_list()
        print(f"✅ Found {len(providers)} AI providers")
        
        # Test OpenAI
        openai_url = get_provider_base_url("openai")
        openai_models = get_provider_default_models("openai")
        print(f"✅ OpenAI URL: {openai_url}")
        print(f"✅ OpenAI models: {openai_models[:2]}")
        
        return True
    except Exception as e:
        print(f"❌ Config error: {e}")
        return False

def main():
    print("=" * 60)
    print("YT SHORT CLIPPER - DEPENDENCY TEST")
    print("=" * 60)
    
    imports_ok, failed = test_imports()
    ytdlp_ok = test_ytdlp()
    config_ok = test_config()
    
    print("\n" + "=" * 60)
    if imports_ok and ytdlp_ok and config_ok:
        print("🎉 ALL TESTS PASSED!")
        print("=" * 60)
        print("\n✅ App is ready to use!")
        print("\nTo start the app:")
        print("  python app.py")
        return 0
    else:
        print("⚠️  SOME TESTS FAILED")
        print("=" * 60)
        if failed:
            print("\nFailed packages:")
            for pkg, err in failed:
                print(f"  - {pkg}: {err}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
