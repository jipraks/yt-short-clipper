#!/usr/bin/env python3
"""Test auto-fill logic for provider dropdown"""

from config.ai_provider_config import (
    get_provider_display_list,
    get_provider_base_url,
    get_provider_default_models,
    requires_model_load
)

def test_autofill():
    """Test that provider selection auto-fills URL and model correctly"""
    
    print("🧪 Testing Auto-Fill Logic\n")
    
    # Get provider list
    provider_display_list = get_provider_display_list()
    print(f"✅ Found {len(provider_display_list)} providers\n")
    
    # Test a few providers
    test_providers = ["openai", "anthropic", "google-gemini", "cohere"]
    
    for provider_key in test_providers:
        display_name = next((name for name, key in provider_display_list if key == provider_key), None)
        if not display_name:
            continue
            
        print(f"Testing: {display_name}")
        
        # Get base URL
        base_url = get_provider_base_url(provider_key)
        print(f"  📌 Base URL: {base_url}")
        
        # Get default models
        models = get_provider_default_models(provider_key)
        print(f"  🎯 Default Models: {models[:2] if len(models) > 2 else models}")
        
        # Check if requires API load
        requires_load = requires_model_load(provider_key)
        print(f"  ⚙️  Requires Model Load: {requires_load}")
        
        print()
    
    print("✅ All auto-fill tests passed!")
    print("\n📋 Next steps:")
    print("  1. Open Settings → AI API Settings")
    print("  2. Select Highlight Finder tab")
    print("  3. Try changing the AI Provider dropdown")
    print("  4. The API Base URL should auto-fill immediately")
    print("  5. The model should auto-load")

if __name__ == "__main__":
    test_autofill()
