#!/usr/bin/env python3
"""Test Groq API to debug the 400 error."""

import httpx
import json
from backend.config import GROQ_API_KEY

print("Testing Groq API with current model...")
print(f"API Key: {GROQ_API_KEY[:20]}...")

# Test with different models until one works - trying VERY new ones
models_to_try = [
    "llama-3.3-70b-versatile",
    "llama3-groq-70b-8192-tool-use-preview",
    "llama3-groq-8b-tool-use-preview",
]

print("Trying latest Groq models from 2025...")

for model_name in models_to_try:
    print(f"\n--- Testing {model_name} ---")
    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "user",
                "content": "Return only valid JSON: {\"test\": \"value\"}"
            }
        ],
        "temperature": 0.1,
        "max_tokens": 100,
    }
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                json=payload,
                headers=headers
            )
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                print(f"✅ SUCCESS with {model_name}!")
                data = response.json()
                print(f"Response preview: {data['choices'][0]['message']['content'][:100]}")
                print(f"\n>>> USE THIS MODEL: {model_name}")
                break
            else:
                resp = response.json()
                if "error" in resp:
                    print(f"Error: {resp['error']['message'][:100]}")
    except Exception as e:
        print(f"Exception: {e}")

print("\n✋ NOTE: All models tested have been decommissioned or are unavailable.")
print("This API key may have limited access. Check your Groq account at https://console.groq.com")
