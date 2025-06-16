from flask import Flask, render_template_string
import threading
import requests
import time

app = Flask(__name__)

URLS = [
    "https://drlabapis.onrender.com",
    "https://ccapi-by-dark-waslost.onrender.com",
    "https://waslost-vbv-api.onrender.com",
    "https://darkwaslost-cc-api.onrender.com",
    "https://authnet-api.onrender.com",
    "https://darkwaslost-cc-api-vnhx.onrender.com",
    "https://darkwaslost-pp-api.onrender.com",
    "https://pyvbv2-api-storm.onrender.com",
    "https://darkwaslost-sp-api.onrender.com",
    "https://darkwaslost-sr-api.onrender.com",
    "https://app-py-8xke.onrender.com",
    "https://gatefinder-dark-k0st.onrender.com",
    "https://card-scrapper.onrender.com",
    "https://site5-eldd.onrender.com",
    "https://paypal-ox9w.onrender.com",
    "https://axapistormx.onrender.com"
]

# Background thread to ping URLs
def ping_urls():
    while True:
        for url in URLS:
            try:
                requests.get(url, timeout=10)
                print(f"[✓] Pinged {url}")
            except Exception as e:
                print(f"[x] Failed to ping {url} - {str(e)}")
        time.sleep(30)  # Wait 5 mins

# Start thread
threading.Thread(target=ping_urls, daemon=True).start()

# Frontend page
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>24/7 URL Uptime Monitor</title>
    <style>
        body { font-family: Arial; background: #111; color: #0f0; padding: 20px; }
        h2 { color: #0ff; }
        .url { margin-bottom: 5px; }
    </style>
</head>
<body>
    <h2>✅ Keeping the following URLs alive:</h2>
    {% for url in urls %}
        <div class="url">🔗 <a href="{{ url }}" target="_blank">{{ url }}</a></div>
    {% endfor %}
    <p>💡 This page refreshes URLs from backend every 5 minutes to keep them alive.</p>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML_TEMPLATE, urls=URLS)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
