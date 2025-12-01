"""
Simple test script to verify Gemini API key works
"""
import os
from google import genai

# Get API key from environment or paste it here for testing
API_KEY = os.getenv("GEMINI_API_KEY", "paste-your-api-key-here")

print(f"Testing API key: {API_KEY[:20]}...")

try:
    # Initialize client
    client = genai.Client(api_key=API_KEY)

    # Try to generate content with gemini-pro
    print("\nTesting gemini-pro model...")
    response = client.models.generate_content(
        model="gemini-pro",
        contents=["Say 'Hello, this API key works!'"]
    )
    print(f"✅ Success! Response: {response.text}")

except Exception as e:
    print(f"❌ Error: {e}")
    print("\nTry these models instead:")
    models_to_try = ["gemini-1.5-flash", "gemini-1.5-pro", "models/gemini-pro"]
    for model in models_to_try:
        try:
            print(f"\nTrying {model}...")
            response = client.models.generate_content(
                model=model,
                contents=["Test"]
            )
            print(f"✅ {model} works!")
        except Exception as model_error:
            print(f"❌ {model} failed: {model_error}")
