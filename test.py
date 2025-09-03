import requests
import json

# Replace with your actual API key
API_KEY = "AIzaSyB-iT009N2GOlkZKQCXVnHExrgwK2-fT4U"

url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

headers = {
    "Content-Type": "application/json",
    "X-goog-api-key": API_KEY,
}

data = {
    "contents": [
        {
            "parts": [
                {"text": "Explain how AI works in a few words"}
            ]
        }
    ]
}

response = requests.post(url, headers=headers, data=json.dumps(data))

if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print("Error:", response.status_code, response.text)