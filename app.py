import asyncio
from aiohttp import web, ClientSession
import time
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, List
import json

@dataclass
class MonitoredSite:
    name: str
    url: str
    interval: int

class SiteMonitor:
    def __init__(self):
        self.monitored_sites: List[MonitoredSite] = []
        self.status_data: Dict[str, Dict] = {}
        self.app = web.Application()
        self.app.add_routes([
            web.get('/', self.handle_index),
            web.post('/add_site', self.handle_add_site),
            web.get('/status', self.handle_status),
            web.get('/status_updates', self.handle_status_updates)
            # Removed the static route since we don't need it
        ])
        self.monitor_task = None

    async def monitor_sites(self):
        while True:
            tasks = []
            for site in self.monitored_sites:
                tasks.append(self.check_site(site))
            
            await asyncio.gather(*tasks)
            
            if self.monitored_sites:
                shortest_interval = min(site.interval for site in self.monitored_sites)
                await asyncio.sleep(shortest_interval)
            else:
                await asyncio.sleep(10)

    async def check_site(self, site: MonitoredSite):
        try:
            start_time = time.time()
            async with ClientSession() as session:
                async with session.get(site.url, timeout=10) as response:
                    response_time = round((time.time() - start_time) * 1000, 2)
                    status = 'up' if response.status == 200 else 'down'
        except:
            response_time = 0
            status = 'down'
        
        if site.url not in self.status_data:
            self.status_data[site.url] = {
                'history': [],
                'uptime_percent': 0,
                'last_checked': None,
                'response_time': 0,
                'name': site.name
            }
        
        self.status_data[site.url]['history'].append({
            'time': datetime.now().strftime("%H:%M:%S"),
            'status': status,
            'response_time': response_time
        })
        
        if len(self.status_data[site.url]['history']) > 10:
            self.status_data[site.url]['history'].pop(0)
        
        up_count = sum(1 for check in self.status_data[site.url]['history'] if check['status'] == 'up')
        self.status_data[site.url]['uptime_percent'] = round(
            (up_count / len(self.status_data[site.url]['history'])) * 100, 2
        )
        self.status_data[site.url]['last_checked'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.status_data[site.url]['response_time'] = response_time

    async def handle_index(self, request):
        html = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Site Monitor</title>
            <style>
                /* All the CSS from previous version remains here */
                :root {
                    --primary: #4361ee;
                    --secondary: #3f37c9;
                    --success: #4cc9f0;
                    --danger: #f72585;
                    --light: #f8f9fa;
                    --dark: #212529;
                    --gray: #6c757d;
                }
                
                * {
                    box-sizing: border-box;
                    margin: 0;
                    padding: 0;
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                }
                
                body {
                    background-color: #f5f7fa;
                    color: var(--dark);
                    line-height: 1.6;
                }
                
                /* Rest of the CSS... */
            </style>
        </head>
        <body>
            <!-- All the HTML from previous version remains here -->
            <header>
                <div class="container">
                    <div class="header-content">
                        <h1>Website Monitor</h1>
                    </div>
                </div>
            </header>
            
            <div class="container">
                <div class="form-container">
                    <h2>Add New Site</h2>
                    <form id="addSiteForm">
                        <div class="form-group">
                            <label for="siteName">Site Name</label>
                            <input type="text" id="siteName" placeholder="My Awesome Site" required>
                        </div>
                        <div class="form-group">
                            <label for="siteUrl">Site URL</label>
                            <input type="url" id="siteUrl" placeholder="https://example.com" required>
                        </div>
                        <div class="form-group">
                            <label for="checkInterval">Check Interval (seconds)</label>
                            <select id="checkInterval">
                                <option value="10">10 seconds</option>
                                <option value="30">30 seconds</option>
                                <option value="60" selected>1 minute</option>
                                <option value="300">5 minutes</option>
                                <option value="600">10 minutes</option>
                            </select>
                        </div>
                        <button type="submit">Add Site</button>
                    </form>
                </div>
                
                <div class="status-container">
                    <div class="status-header">
                        <h2>Current Status</h2>
                        <div id="lastUpdated"></div>
                    </div>
                    <div id="statusCards" class="status-cards"></div>
                </div>
            </div>
            
            <script>
                // All the JavaScript from previous version remains here
                const addSiteForm = document.getElementById('addSiteForm');
                const statusCards = document.getElementById('statusCards');
                const lastUpdated = document.getElementById('lastUpdated');
                
                // Add new site
                addSiteForm.addEventListener('submit', async (e) => {
                    e.preventDefault();
                    
                    const siteName = document.getElementById('siteName').value;
                    const siteUrl = document.getElementById('siteUrl').value;
                    const checkInterval = document.getElementById('checkInterval').value;
                    
                    try {
                        const response = await fetch('/add_site', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({
                                name: siteName,
                                url: siteUrl,
                                interval: checkInterval
                            }),
                        });
                        
                        if (response.ok) {
                            document.getElementById('addSiteForm').reset();
                            fetchStatus();
                        } else {
                            alert('Error adding site');
                        }
                    } catch (error) {
                        console.error('Error:', error);
                        alert('Error adding site');
                    }
                });
                
                // Fetch current status
                async function fetchStatus() {
                    try {
                        const response = await fetch('/status');
                        const data = await response.json();
                        updateStatusUI(data);
                    } catch (error) {
                        console.error('Error fetching status:', error);
                    }
                }
                
                // Update UI with status data
                function updateStatusUI(data) {
                    lastUpdated.textContent = `Last updated: ${new Date().toLocaleTimeString()}`;
                    
                    if (!data.sites || data.sites.length === 0) {
                        statusCards.innerHTML = '<p>No sites being monitored. Add a site to begin.</p>';
                        return;
                    }
                    
                    let html = '';
                    
                    for (const site of data.sites) {
                        const statusInfo = data.status_data[site.url] || {
                            uptime_percent: 0,
                            last_checked: 'Never',
                            response_time: 0,
                            history: []
                        };
                        
                        const lastCheck = statusInfo.history.length > 0 
                            ? statusInfo.history[statusInfo.history.length - 1]
                            : { status: 'unknown', response_time: 0, time: '' };
                        
                        html += `
                            <div class="status-card ${lastCheck.status}">
                                <div class="card-header">
                                    <div class="site-name">${site.name}</div>
                                    <div class="status-badge ${lastCheck.status}">${lastCheck.status.toUpperCase()}</div>
                                </div>
                                <div class="card-details">${site.url}</div>
                                <div class="response-time">Response: ${lastCheck.response_time} ms</div>
                                
                                <div class="progress-container">
                                    <div class="progress-bar">
                                        <div class="progress-fill" style="width: ${statusInfo.uptime_percent}%"></div>
                                    </div>
                                    <div class="uptime-percent">Uptime: ${statusInfo.uptime_percent}%</div>
                                </div>
                                
                                <div class="last-checked">Last checked: ${statusInfo.last_checked || 'Never'}</div>
                                
                                <div class="history-container">
                                    ${statusInfo.history.map(item => `
                                        <div class="history-item">
                                            <span>${item.time}</span>
                                            <span class="history-status ${item.status}">${item.status.toUpperCase()}</span>
                                            <span>${item.response_time} ms</span>
                                        </div>
                                    `).reverse().join('')}
                                </div>
                            </div>
                        `;
                    }
                    
                    statusCards.innerHTML = html;
                }
                
                // Set up EventSource for real-time updates
                function setupEventSource() {
                    const eventSource = new EventSource('/status_updates');
                    
                    eventSource.onmessage = (event) => {
                        const data = JSON.parse(event.data);
                        updateStatusUI(data);
                    };
                    
                    eventSource.onerror = () => {
                        console.log('EventSource error. Reconnecting...');
                        setTimeout(setupEventSource, 5000);
                    };
                }
                
                // Initial fetch and setup
                fetchStatus();
                setupEventSource();
                
                // Refresh every 10 seconds as fallback
                setInterval(fetchStatus, 10000);
            </script>
        </body>
        </html>
        """
        return web.Response(text=html, content_type='text/html')

    async def handle_add_site(self, request):
        data = await request.json()
        self.monitored_sites.append(MonitoredSite(
            name=data['name'],
            url=data['url'],
            interval=int(data['interval'])
        ))
        return web.json_response({'success': True})

    async def handle_status(self, request):
        return web.json_response({
            'sites': [{'name': s.name, 'url': s.url, 'interval': s.interval} for s in self.monitored_sites],
            'status_data': self.status_data
        })

    async def handle_status_updates(self, request):
        response = web.StreamResponse(
            headers={
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
            }
        )
        await response.prepare(request)
        
        try:
            while True:
                data = {
                    'sites': [{'name': s.name, 'url': s.url, 'interval': s.interval} for s in self.monitored_sites],
                    'status_data': self.status_data
                }
                message = f"data: {json.dumps(data)}\n\n"
                await response.write(message.encode('utf-8'))
                await asyncio.sleep(5)
        except (asyncio.CancelledError, ConnectionResetError):
            pass
        
        return response

    async def start(self):
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 8080)
        self.monitor_task = asyncio.create_task(self.monitor_sites())
        await site.start()
        print("Server started at http://0.0.0.0:8080")

async def main():
    monitor = SiteMonitor()
    await monitor.start()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server stopped")
