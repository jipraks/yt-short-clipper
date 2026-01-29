# AI Provider Selector - Auto-Fill Feature

## Overview

Settings page sekarang memiliki fitur **intelligent AI provider selector** yang membuat setup lebih mudah dan cepat. Ketika Anda memilih AI provider (OpenAI, Google Gemini, Groq, dll), form secara otomatis:

1. ✅ Mengisi **API Base URL** dengan URL default provider
2. ✅ Memuat **daftar model** yang tersedia dari provider
3. ✅ Mengisi **model pertama** sebagai pilihan default

---

## Supported Providers

### 🔴 OpenAI
- **Base URL**: `https://api.openai.com/v1`
- **Models**: GPT-4o, GPT-4-turbo, GPT-4, GPT-3.5-turbo
- **Format**: `sk-*`
- **Docs**: https://platform.openai.com/api-keys

### 🔵 Google Gemini
- **Base URL**: `https://generativelanguage.googleapis.com/v1beta/models`
- **Models**: gemini-2.5-flash, gemini-2.0-flash, gemini-1.5-pro, gemini-1.5-flash
- **Format**: `AIza*`
- **Docs**: https://aistudio.google.com/app/apikey

### ⚡ Groq
- **Base URL**: `https://api.groq.com/openai/v1`
- **Models**: mixtral-8x7b-32768, llama2-70b-4096, gemma-7b-it
- **Format**: `gsk-*`
- **Docs**: https://console.groq.com/keys

### 🤖 Anthropic Claude
- **Base URL**: `https://api.anthropic.com`
- **Models**: claude-3-5-sonnet-20241022, claude-3-opus-20240229, claude-3-sonnet-20240229
- **Format**: `sk-ant-*`
- **Docs**: https://console.anthropic.com/

### 🟢 Cohere
- **Base URL**: `https://api.cohere.ai`
- **Models**: command-r-plus, command-r, command
- **Format**: `*`
- **Docs**: https://dashboard.cohere.com/api-keys

### 🟠 Mistral AI
- **Base URL**: `https://api.mistral.ai/v1`
- **Models**: mistral-large-latest, mistral-medium-latest, mistral-small-latest
- **Format**: `*`
- **Docs**: https://console.mistral.ai/api-keys/

### 🤗 HuggingFace
- **Base URL**: `https://api-inference.huggingface.co/models`
- **Models**: meta-llama/Llama-2-70b-chat-hf, mistralai/Mistral-7B-Instruct-v0.1
- **Format**: `hf_*`
- **Docs**: https://huggingface.co/settings/tokens

### 🔗 Together AI
- **Base URL**: `https://api.together.xyz/v1`
- **Models**: meta-llama/Llama-2-70b-chat-hf, mistralai/Mistral-7B-Instruct-v0.2
- **Format**: `*`
- **Docs**: https://www.together.ai/settings/api-keys

### 🔴 Replicate
- **Base URL**: `https://api.replicate.com/v1`
- **Models**: meta/llama-2-70b-chat, mistral-community/mistral-7b-instruct-v0.2
- **Format**: `*`
- **Docs**: https://replicate.com/account/api-tokens

### ⚙️ Custom/Local
- **Base URL**: `http://localhost:8000/v1` (default)
- **Models**: custom-model, llama-2, mistral, dll
- **Format**: optional
- **Docs**: https://github.com/vllm-project/vllm

---

## Penggunaan Step-by-Step

### Scenario 1: Setup Highlight Finder dengan Google Gemini

1. **Buka** Settings → Tab "AI API Settings"
2. **Klik** tab "🎯 Highlight Finder"
3. **Di bagian "AI Provider"**
   - Klik dropdown
   - Pilih **"🔵 Google Gemini"**
4. **Otomatis akan terisi:**
   - ✅ Base URL: `https://generativelanguage.googleapis.com/v1beta/models`
   - ✅ Model: `gemini-2.5-flash` (first default model)
5. **Tinggal masukkan API Key:**
   - Paste API key dari: https://aistudio.google.com/app/apikey
6. **Klik "Validate Configuration"**
7. **Klik "Save All Settings"**

### Scenario 2: Setup Caption Maker dengan OpenAI

1. **Buka** Settings → Tab "AI API Settings"
2. **Klik** tab "📝 Caption Maker"
3. **Di bagian "AI Provider"**
   - Dropdown sudah default ke **"🔴 OpenAI"**
4. **Otomatis akan terisi:**
   - ✅ Base URL: `https://api.openai.com/v1`
   - ✅ Model: `whisper-1` (default caption model)
5. **Masukkan API Key:** sk-...
6. **Validate & Save**

### Scenario 3: Switch dari OpenAI ke Groq

1. **Sudah ada setup OpenAI**
2. **Di dropdown "AI Provider"**, pilih **"⚡ Groq"**
3. **Otomatis berubah:**
   - ✅ Base URL: `https://api.groq.com/openai/v1`
   - ✅ Model: `mixtral-8x7b-32768`
4. **Update API Key** ke Groq key Anda
5. **Validate & Save**

---

## Form Sections di Setiap Tab

Setiap tab punya struktur yang sama:

### 1. **AI Provider** (BARU ✨)
```
Dropdown: [🔴 OpenAI ▼]
```
- Pilih provider dari dropdown
- Otomatis isi URL dan model

### 2. **API Base URL** (Auto-filled)
```
Input: https://api.openai.com/v1
```
- Auto-filled saat provider dipilih
- Bisa di-edit manual untuk custom endpoints

### 3. **API Key** (Manual)
```
Password Input: [sk-... ▶▶▶▶▶▶▶▶]
```
- Tetap harus diisi manual
- Format berbeda per provider

### 4. **Model** (Auto-filled/Selectable)

**Untuk Highlight Finder & YouTube Title:**
```
Display: [gpt-4o        ]  [📋 Select] [🔄 Load]
```
- Model name display
- Select button untuk buka model picker
- Load button untuk fetch models dari API

**Untuk Caption Maker & Hook Maker:**
```
Input: [whisper-1                      ]
```
- Simple input field
- Model nama yang sesuai task

### 5. **Validation & Actions**
```
[🔍 Validate Configuration] [📋 Apply URL & Key to All]
```
- Test konfigurasi
- Copy settings ke tab lainnya

---

## Provider-Specific Features

### Auto-Loading Models

Beberapa provider butuh fetch models dari API:

| Provider | Requires Load | How It Works |
|----------|---|---|
| OpenAI | ✅ Yes | Klik "Load" untuk fetch model list via API |
| Google Gemini | ❌ No | Models sudah diketahui, langsung siap pakai |
| Groq | ✅ Yes | Fetch dari Groq API |
| Custom | ❌ No | Manual entry |

**Button Status:**
- `🔄 Load` - Provider perlu fetch models
- `✓ Ready` - Models sudah siap tanpa fetch

### Specialized Models

Setiap task punya model rekomendasi berbeda:

**Highlight Finder (GPT):**
- OpenAI: gpt-4o, gpt-4-turbo, gpt-4
- Google Gemini: gemini-2.5-flash, gemini-1.5-pro
- Groq: mixtral-8x7b-32768

**Caption Maker (Whisper):**
- OpenAI: whisper-1 (only option)
- Groq: Limited support
- Others: Not recommended

**Hook Maker (TTS):**
- OpenAI: tts-1-hd, tts-1
- Others: Limited TTS support

**YouTube Title Maker (GPT):**
- OpenAI: gpt-4o, gpt-4-turbo, gpt-4
- Google Gemini: gemini-2.5-flash
- Groq: mixtral-8x7b-32768

---

## Tips & Tricks

### ⚡ Quick Setup
1. Pilih provider dari dropdown → URL auto-fill ✅
2. Copy-paste API key
3. Validate & save ✅
4. Done! Cuma 3 step

### 🔄 Switch Provider Cepat
- Ubah provider dropdown → URL auto-update
- Model default berubah
- Tinggal update API key saja

### 📋 Copy Settings Antar Tab
- Klik **"Apply URL & Key to All"**
- Settings dicopy ke 3 tab lainnya
- Hemat waktu kalo gunakan provider sama

### ✓ Validate Sebelum Save
- Klik **"Validate Configuration"**
- Test koneksi API + model availability
- Cegah error saat processing video

### 🎯 Custom Endpoints
- Gunakan provider "⚙️ Custom/Local"
- Atau edit URL manual (tidak auto-fill)
- Support untuk local Ollama, vLLM, dll

---

## File Structure

```
yt-short-clipper/
├── config/
│   └── ai_provider_config.py         ← Provider configurations
│       ├── AI_PROVIDERS_CONFIG        ← URL & models per provider
│       ├── SPECIALIZED_MODELS         ← Task-specific recommendations
│       └── Helper functions           ← Get provider info
│
└── pages/
    └── settings_page.py              ← Enhanced with provider selector
        ├── _on_hf_provider_changed() ← Highlight Finder
        ├── _on_cm_provider_changed() ← Caption Maker
        ├── _on_hm_provider_changed() ← Hook Maker
        └── _on_yt_provider_changed() ← YouTube Title
```

---

## Configuration File

### Config Structure
```json
{
  "ai_providers": {
    "default": "openai",
    "openai": {
      "api_key": "sk-...",
      "model": "gpt-4o",
      "base_url": "https://api.openai.com/v1"
    },
    "google": {
      "api_key": "AIza...",
      "model": "gemini-2.5-flash",
      "base_url": "https://generativelanguage.googleapis.com/v1beta/models"
    }
  }
}
```

---

## Advanced: Add New Provider

To add a new provider:

1. **Edit** `config/ai_provider_config.py`

2. **Add to** `AI_PROVIDERS_CONFIG`:
```python
"new_provider": {
    "name": "🟣 New Provider",
    "base_url": "https://api.new-provider.com/v1",
    "description": "Description here",
    "default_models": ["model-1", "model-2"],
    "api_key_format": "pattern*",
    "docs_url": "https://...",
    "requires_load": True/False
}
```

3. **Add models to** `SPECIALIZED_MODELS`:
```python
"highlight_finder": {
    "new_provider": ["model-1", "model-2"]
}
```

4. **Provider will automatically** appear in dropdown ✅

---

## Troubleshooting

### Problem: URL tidak auto-fill
**Solution:**
- Refresh page (F5)
- Pilih provider lagi
- Jika masih tidak work, bisa edit manual

### Problem: Model list tidak load
**Solution:**
- Klik "Load" button
- Pastikan API key benar
- Check internet connection
- Beberapa provider tidak support models.list()

### Problem: Model tidak ada di list
**Solution:**
- Klik "Load" untuk refresh
- Atau ketik manual nama model

### Problem: "API key required" error
**Solution:**
- Pastikan API key sudah diisi
- Format key sesuai provider (sk-* untuk OpenAI, AIza* untuk Gemini)
- Check bahwa key tidak expired

---

## Summary

✨ **Fitur Baru:**
- ✅ Provider selector dropdown dengan 10+ providers
- ✅ Auto-fill API Base URL saat provider dipilih
- ✅ Auto-load default models untuk setiap provider
- ✅ Task-specific model recommendations
- ✅ Easy switch between providers
- ✅ Validation built-in
- ✅ Copy settings antar tab

🎯 **Benefit:**
- Faster setup (3 steps instead of 5)
- Fewer mistakes (auto-filled URLs)
- Easy provider switching
- Better model recommendations
- Consistent across all tabs

🚀 **Ready to use!**
