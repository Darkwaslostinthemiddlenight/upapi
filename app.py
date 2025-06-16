from flask import Flask, render_template_string, request, redirect, url_for, jsonify
import threading
import requests
import time
from datetime import datetime

app = Flask(__name__)

monitors = []  # Store monitors here

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Storm X Up</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            margin: 0;
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(to right, #0f2027, #203a43, #2c5364);
            color: white;
            transition: 0.3s;
        }
        header {
            background: #111;
            padding: 20px;
            text-align: center;
            font-size: 28px;
            font-weight: bold;
            letter-spacing: 1px;
            color: #0ff;
            border-bottom: 2px solid #0ff;
        }
        .container {
            padding: 20px;
        }
        .menu {
            margin-bottom: 20px;
            display: flex;
            gap: 10px;
        }
        .menu button {
            padding: 10px 20px;
            border: none;
            background: #0ff;
            color: black;
            font-weight: bold;
            cursor: pointer;
            border-radius: 10px;
            transition: 0.3s;
        }
        .menu button:hover {
            background: #00c0c0;
        }
        .form-box, .status-box {
            display: none;
            background: rgba(255, 255, 255, 0.05);
            padding: 20px;
            border-radius: 15px;
            margin-top: 10px;
        }
        .monitor-card {
            padding: 10px;
            margin-top: 10px;
            background: rgba(0, 255, 255, 0.1);
            border-left: 5px solid #0ff;
            border-radius: 10px;
        }
    </style>
</head>
<body>
    <header>Storm X Up</header>
    <div class="container">
        <div class="menu">
            <button onclick="showForm()">＋ Add Monitor</button>
            <button onclick="showStatus()">📊 View Status</button>
        </div>

        <div class="form-box" id="formBox">
            <form method="post" action="/add">
                <input name="name" placeholder="Monitor Name" required>
                <input name="url" placeholder="Site URL (https://...)" required>
                <input name="interval" type="number" placeholder="Interval (seconds)" required>
                <button type="submit">Add Monitor</button>
            </form>
        </div>

        <div class="status-box" id="statusBox">
            {% for m in monitors %}
            <div class="monitor-card">
                <strong>{{ m['name'] }}</strong><br>
                URL: <a href="{{ m['url'] }}" style="color: #0ff">{{ m['url'] }}</a><br>
                Status: {{ m['last_status'] }}<br>
                Last Checked: {{ m['last_checked'] }}<br>
                Avg Response: {{ m['avg_response']|round(2) }} ms
            </div>
            {% else %}
            <p>No monitors added yet.</p>
            {% endfor %}
        </div>
    </div>

    <script>
        function showForm() {
            document.getElementById('formBox').style.display = 'block';
            document.getElementById('statusBox').style.display = 'none';
        }
        function showStatus() {
            document.getElementById('statusBox').style.display = 'block';
            document.getElementById('formBox').style.display = 'none';
        }
    </script>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def home():
    return render_template_string(HTML_TEMPLATE, monitors=monitors)

@app.route("/add", methods=["POST"])
def add_monitor():
    name = request.form["name"]
    url = request.form["url"]
    interval = int(request.form["interval"])
    monitor = {
        "name": name,
        "url": url,
        "interval": interval,
        "last_status": "Pending",
        "last_checked": "Never",
        "avg_response": 0.0,
        "response_times": []
    }
    monitors.append(monitor)
    threading.Thread(target=monitor_thread, args=(monitor,), daemon=True).start()
    return redirect(url_for("home"))

def monitor_thread(monitor):
    while True:
        try:
            start = time.time()
            r = requests.get(monitor["url"], timeout=10)
            elapsed = (time.time() - start) * 1000
            monitor["last_status"] = f"{r.status_code} OK" if r.ok else f"{r.status_code} Error"
        except Exception as e:
            monitor["last_status"] = f"DOWN ({e.__class__.__name__})"
            elapsed = 0
        monitor["last_checked"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        monitor["response_times"].append(elapsed)
        if len(monitor["response_times"]) > 20:
            monitor["response_times"] = monitor["response_times"][-20:]
        monitor["avg_response"] = sum(monitor["response_times"]) / len(monitor["response_times"])
        time.sleep(monitor["interval"])

if __name__ == "__main__":
    app.run(debug=True, port=5000)
