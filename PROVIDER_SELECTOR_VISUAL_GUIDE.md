# 🎨 AI Provider Selector - Visual Guide

## UI Walkthroughs

### Flow 1: Setup Baru dengan Google Gemini

```
HOME SCREEN
├─ Settings Button (⚙️)
│
SETTINGS PAGE
├─ Tab: "AI API Settings"
│
TAB: 🎯 Highlight Finder
├─────────────────────────────────────────┐
│ ℹ️ Highlight Finder                     │
│ AI model for analyzing video transcripts│
│                                          │
│ AI Provider ✨ BARU!                    │
│ ┌────────────────────────────────────┐  │
│ │ 🔵 Google Gemini        [▼]        │  │ ← CLICK HERE
│ └────────────────────────────────────┘  │
│                                          │
│ API Base URL (Auto-filled ✅)           │
│ ┌────────────────────────────────────┐  │
│ │ https://generativelanguage.       │  │
│ │ googleapis.com/v1beta/models       │  │
│ └────────────────────────────────────┘  │
│                                          │
│ API Key (Manual entry)                  │
│ ┌────────────────────────────────────┐  │
│ │ AIza... [password hidden]          │  │ ← PASTE KEY HERE
│ └────────────────────────────────────┘  │
│                                          │
│ Model (Auto-loaded ✅)                  │
│ ┌────────────────────────────────────┐  │
│ │ gemini-2.5-flash  [📋 Select]     │  │
│ └────────────────────────────────────┘  │
│                                          │
│ [🔍 Validate Configuration]             │
│ [📋 Apply URL & Key to All]             │
└─────────────────────────────────────────┘

↓ Scroll Down ↓

│ [💾 Save All Settings]
```

### Flow 2: Provider Dropdown Expanded

```
AI Provider
┌──────────────────────────────┐
│ 🔵 Google Gemini       [▼]   │ ← CLICK
└──────────────────────────────┘

Dropdown Opens:
┌──────────────────────────────┐
│ 🔴 OpenAI                    │
│ 🔵 Google Gemini       ← ✓   │
│ ⚡ Groq                      │
│ 🤖 Anthropic Claude          │
│ 🟢 Cohere                    │
│ 🟠 Mistral AI                │
│ 🤗 HuggingFace               │
│ 🔗 Together AI               │
│ 🔴 Replicate                 │
│ ⚙️ Custom/Local              │
└──────────────────────────────┘
   ↓ SELECT GROQ

Auto-Update Happens:
• Base URL changes → https://api.groq.com/openai/v1
• Model changes → mixtral-8x7b-32768
• Info popup → Shows Groq description
```

### Flow 3: Model Selector Dialog

```
🎯 Highlight Finder
├─ AI Provider: [🔴 OpenAI]
├─ Model: [gpt-4o][📋 Select] ← CLICK

Model Selector Dialog Opens:
┌────────────────────────────────┐
│ Select Model                   │
│                                │
│ Search: [________]             │
│                                │
│ Available Models:              │
│ ☐ gpt-4o                       │
│ ☑ gpt-4-turbo       ← Selected │
│ ☐ gpt-4                        │
│ ☐ gpt-3.5-turbo                │
│ ☐ gpt-3.5                      │
│                                │
│ [Cancel]  [Confirm Selection]  │
└────────────────────────────────┘
```

---

## Step-by-Step Examples

### Example 1: Setup Highlight Finder dengan Groq

**BEFORE (Manual Setup - Risky):**
```
1. Open Settings
2. Manually type URL: "https://api.groq.com/openai/v1"
   ⚠️ Easy to typo → API call fails
3. Manually find model name
   ⚠️ Perlu cek docs → mixtral-8x7b-32768?
   ⚠️ Sering salah ketik → MODEL_NOT_FOUND error
4. Paste API key
5. Test configuration
6. Save

Result: 5 langkah + high error rate ❌
```

**AFTER (Auto-Fill Setup - Easy):**
```
1. Settings → AI API Settings → Highlight Finder
2. Click dropdown: Select "⚡ Groq"
   ✅ URL auto-fills: https://api.groq.com/openai/v1
   ✅ Model auto-loads: mixtral-8x7b-32768
3. Paste API key: gsk-...
4. Click "Validate Configuration"
5. "Save All Settings"

Result: 3 langkah + zero typos ✅
```

---

## Visual Comparison

### Settings Form Layout - BEFORE vs AFTER

**BEFORE:**
```
┌─────────────────────────────────┐
│ 🎯 Highlight Finder             │
├─────────────────────────────────┤
│ API Base URL                    │
│ [________________________]       │ ← Manual
│ placeholder: https://...        │
│                                 │
│ API Key                         │
│ [________________________]       │ ← Manual
│ placeholder: sk-...             │
│                                 │
│ Model                           │
│ [________________________]       │ ← Manual
│ placeholder: gpt-4              │
│                                 │
│ [Validate] [Apply URL & Key]    │
└─────────────────────────────────┘
```

**AFTER:**
```
┌─────────────────────────────────┐
│ 🎯 Highlight Finder             │
├─────────────────────────────────┤
│ AI Provider ✨                  │
│ [🔴 OpenAI        ▼]            │ ← Dropdown (NEW!)
│                                 │
│ API Base URL ✅                 │
│ [https://api.openai.com/v1]     │ ← Auto-filled
│                                 │
│ API Key 🔑                      │
│ [sk-...        ]                │ ← Manual only
│                                 │
│ Model ✅                        │
│ [gpt-4o] [Select] [Load]        │ ← Auto-loaded
│                                 │
│ [Validate] [Apply URL & Key]    │
└─────────────────────────────────┘
```

---

## Color & Icon Guide

### Provider Icons
```
🔴 OpenAI           - Red circle (official color)
🔵 Google Gemini    - Blue circle (official color)
⚡ Groq             - Lightning (fast inference)
🤖 Anthropic Claude - Robot (AI)
🟢 Cohere           - Green circle
🟠 Mistral AI       - Orange circle
🤗 HuggingFace      - Hugging face emoji
🔗 Together AI      - Chain link (together)
🔴 Replicate        - Red circle (infrastructure)
⚙️ Custom/Local     - Gear (customizable)
```

### Status Indicators
```
✅ Auto-filled        - Green checkmark
✨ New feature        - Sparkles
🔄 Load/Refresh       - Circular arrows
📋 Select/Copy        - Clipboard
🔍 Validate           - Magnifying glass
💾 Save               - Floppy disk
🔑 API Key            - Key emoji
✓ Ready              - Done state
▼ Dropdown            - Down arrow
```

---

## Interaction Flow Diagram

```
USER OPENS SETTINGS
        ↓
    Select "AI API Settings"
        ↓
    Choose Tab (🎯/📝/🎤/📺)
        ↓
    ┌─────────────────────────────┐
    │  AI Provider Dropdown       │
    │  [Select from 10 providers] │
    └──────────────┬──────────────┘
                   ↓
         Provider Selected
         ┌────────────┴────────────┐
         │                         │
      ✅ URL Auto-Fills      ✅ Model Auto-Loads
         │                         │
         └────────────┬────────────┘
                      ↓
         User Pastes API Key
                      ↓
         Clicks "Validate Configuration"
                      ↓
         Connection & Model Verified
                      ↓
         Clicks "Save All Settings"
                      ↓
         ✅ Setup Complete!
```

---

## Responsive Design

### Desktop (Full Width)
```
┌────────────────────────────────────────────────┐
│ AI Provider                                    │
│ [🔴 OpenAI                        ▼]           │
│                                                │
│ API Base URL                                   │
│ [https://api.openai.com/v1                    ] │
│                                                │
│ API Key                                        │
│ [sk-...                                       ] │
│                                                │
│ Model                                          │
│ [gpt-4o        ] [📋 Select] [🔄 Load]        │
└────────────────────────────────────────────────┘
```

### Mobile (Responsive)
```
┌──────────────────────────┐
│ AI Provider              │
│ [🔴 OpenAI    ▼]        │
│                          │
│ API Base URL             │
│ [https://api.openai.com  │
│  /v1                    ] │
│                          │
│ API Key                  │
│ [sk-...               ]  │
│                          │
│ Model                    │
│ [gpt-4o     ] [Select]   │
│             [Load]       │
└──────────────────────────┘
```

---

## Error States

### Error: API Key Not Set
```
┌─────────────────────────────────────────┐
│ ⚠️ Validation Failed                    │
│                                          │
│ API Key is required                     │
│                                          │
│ [OK]                                    │
└─────────────────────────────────────────┘

Form shows:
┌─────────────────────────────────────────┐
│ API Key 🔴 (Red border)                 │
│ [                              ]        │
│ ⚠️ Please enter API key                  │
└─────────────────────────────────────────┘
```

### Error: Model Not Available
```
┌─────────────────────────────────────────┐
│ ⚠️ Model Not Found                      │
│                                          │
│ Model 'gpt-4.1' not found in            │
│ available models.                       │
│                                          │
│ Available models:                       │
│ • gpt-4o                                │
│ • gpt-4-turbo                           │
│ • gpt-3.5-turbo                         │
│                                          │
│ [OK]                                    │
└─────────────────────────────────────────┘
```

### Success: Configuration Valid
```
┌─────────────────────────────────────────┐
│ ✅ Configuration Validated Successfully  │
│                                          │
│ ✓ Configuration validated successfully!  │
│                                          │
│ Model: gpt-4o                           │
│ Provider: https://api.openai.com/v1     │
│                                          │
│ [OK]                                    │
└─────────────────────────────────────────┘
```

---

## Quick Reference Card

### Provider Setup Cheat Sheet

| Task | Provider | Recommendation | Steps |
|------|----------|-----------------|-------|
| Highlight Finder | Any | GPT-4o or Gemini | 1. Select 2. Paste Key 3. Save |
| Caption Maker | OpenAI | whisper-1 only | 1. Select OpenAI 2. Key 3. Save |
| Hook Maker | OpenAI | tts-1-hd | 1. Select OpenAI 2. Key 3. Save |
| YouTube Title | Any | GPT-4o or Groq | 1. Select 2. Paste Key 3. Save |

### Keyboard Shortcuts

```
Settings Page:
• Tab        - Move between fields
• Enter      - Select from dropdown
• Ctrl+S     - Save settings
• Ctrl+V     - Paste API key
```

---

## Animation & Transitions

### Dropdown Open Animation
```
[🔴 OpenAI ▼] 
    ↓ (smooth slide-down)
┌──────────────┐
│ 🔴 OpenAI    │
│ 🔵 Gemini    │ ← Highlight
│ ⚡ Groq      │
└──────────────┘
```

### Auto-Fill Animation
```
Field: [empty]
  ↓ (provider selected)
  ↓ (brief fade-in)
Field: [https://api.openai.com/v1] ✨
```

### Loading State
```
Button: [🔄 Load]
  ↓ (click)
Button: [⏳ Loading...]
  ↓ (fetch from API)
Button: [✓ Loaded]
```

---

## Accessibility Features

### For Screen Readers
```
<label>AI Provider</label>
<select aria-label="AI Provider Dropdown">
  <option>🔴 OpenAI</option>
  <option>🔵 Google Gemini</option>
  ...
</select>

<label>API Base URL</label>
<input aria-label="API Base URL Input"
       value="https://api.openai.com/v1"
       aria-readonly="true" />

<label>API Key</label>
<input aria-label="API Key Input" 
       type="password" />
```

### Color Contrast
```
✅ All text: WCAG AA compliant
✅ Icons have text labels
✅ Error states use more than just color
✅ Focus states visible for keyboard users
```

---

**This visual guide helps understand the UI/UX improvements made to the AI Provider Selector feature.**

Last Updated: January 28, 2026
