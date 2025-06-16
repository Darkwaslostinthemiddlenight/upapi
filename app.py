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

class UptimeMonitor:
    def __init__(self):
        self.monitored_sites: List[MonitoredSite] = []
        self.status_data: Dict[str, Dict] = {}
        self.app = web.Application()
        self.app.add_routes([
            web.get('/', self.handle_index),
            web.post('/add_site', self.handle_add_site),
            web.get('/status', self.handle_status),
            web.get('/status_updates', self.handle_status_updates),
            web.get('/site_details/{url}', self.handle_site_details)
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
                'name': site.name,
                'history': [],
                'uptime_percent': 0,
                'last_checked': None,
                'response_time': 0,
                'total_checks': 0,
                'up_count': 0,
                'down_count': 0,
                'avg_response_time': 0,
                'last_status': status
            }
        
        record = self.status_data[site.url]
        record['history'].append({
            'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'status': status,
            'response_time': response_time
        })
        
        # Keep last 100 checks
        if len(record['history']) > 100:
            record['history'].pop(0)
        
        # Update statistics
        record['total_checks'] += 1
        if status == 'up':
            record['up_count'] += 1
        else:
            record['down_count'] += 1
        
        record['uptime_percent'] = round((record['up_count'] / record['total_checks']) * 100, 2)
        record['last_checked'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        record['response_time'] = response_time
        record['last_status'] = status
        
        # Calculate average response time (only for successful requests)
        successful_responses = [r['response_time'] for r in record['history'] if r['status'] == 'up']
        record['avg_response_time'] = round(sum(successful_responses) / len(successful_responses), 2) if successful_responses else 0

    async def handle_index(self, request):
        html = """
        <!DOCTYPE html>
        <html lang="en" data-theme="light">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Storm X Up</title>
            <style>
                :root {
                    --primary: #4361ee;
                    --secondary: #3a0ca3;
                    --success: #4cc9f0;
                    --danger: #f72585;
                    --warning: #f8961e;
                    --info: #4895ef;
                    --light: #f8f9fa;
                    --dark: #212529;
                    --gray: #6c757d;
                    --bg: #ffffff;
                    --text: #212529;
                    --card-bg: #ffffff;
                    --border: #dee2e6;
                }
                
                [data-theme="dark"] {
                    --primary: #3a86ff;
                    --secondary: #8338ec;
                    --success: #06d6a0;
                    --danger: #ef476f;
                    --warning: #ffd166;
                    --info: #118ab2;
                    --light: #343a40;
                    --dark: #f8f9fa;
                    --gray: #adb5bd;
                    --bg: #121212;
                    --text: #f8f9fa;
                    --card-bg: #1e1e1e;
                    --border: #343a40;
                }
                
                * {
                    box-sizing: border-box;
                    margin: 0;
                    padding: 0;
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    transition: background-color 0.3s, color 0.3s, border-color 0.3s;
                }
                
                body {
                    background-color: var(--bg);
                    color: var(--text);
                    min-height: 100vh;
                }
                
                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                }
                
                header {
                    background: linear-gradient(135deg, var(--primary), var(--secondary));
                    color: white;
                    padding: 20px 0;
                    text-align: center;
                    position: sticky;
                    top: 0;
                    z-index: 100;
                    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
                }
                
                h1 {
                    font-size: 2.5rem;
                    font-weight: 700;
                    letter-spacing: 1px;
                }
                
                .menu-bar {
                    display: flex;
                    justify-content: center;
                    gap: 20px;
                    margin: 20px 0;
                    flex-wrap: wrap;
                }
                
                .menu-btn {
                    padding: 10px 20px;
                    border-radius: 50px;
                    background-color: var(--primary);
                    color: white;
                    border: none;
                    cursor: pointer;
                    font-weight: 500;
                    transition: transform 0.2s, box-shadow 0.2s;
                    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
                }
                
                .menu-btn:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
                }
                
                .menu-btn.active {
                    background-color: var(--secondary);
                }
                
                .add-btn {
                    width: 50px;
                    height: 50px;
                    border-radius: 50%;
                    background-color: var(--primary);
                    color: white;
                    border: none;
                    font-size: 1.5rem;
                    cursor: pointer;
                    position: fixed;
                    bottom: 30px;
                    right: 30px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);
                    transition: transform 0.3s, background-color 0.3s;
                    z-index: 90;
                }
                
                .add-btn:hover {
                    transform: scale(1.1) rotate(90deg);
                    background-color: var(--secondary);
                }
                
                .modal {
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background-color: rgba(0, 0, 0, 0.5);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 1000;
                    opacity: 0;
                    pointer-events: none;
                    transition: opacity 0.3s;
                }
                
                .modal.active {
                    opacity: 1;
                    pointer-events: all;
                }
                
                .modal-content {
                    background-color: var(--card-bg);
                    padding: 30px;
                    border-radius: 10px;
                    width: 90%;
                    max-width: 500px;
                    transform: translateY(-50px);
                    transition: transform 0.3s;
                    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
                }
                
                .modal.active .modal-content {
                    transform: translateY(0);
                }
                
                .form-group {
                    margin-bottom: 20px;
                }
                
                label {
                    display: block;
                    margin-bottom: 8px;
                    font-weight: 500;
                    color: var(--text);
                }
                
                input, select {
                    width: 100%;
                    padding: 12px 15px;
                    border: 1px solid var(--border);
                    border-radius: 6px;
                    font-size: 16px;
                    background-color: var(--card-bg);
                    color: var(--text);
                }
                
                .form-actions {
                    display: flex;
                    justify-content: flex-end;
                    gap: 10px;
                    margin-top: 20px;
                }
                
                .btn {
                    padding: 10px 20px;
                    border-radius: 6px;
                    border: none;
                    cursor: pointer;
                    font-weight: 500;
                    transition: background-color 0.3s;
                }
                
                .btn-primary {
                    background-color: var(--primary);
                    color: white;
                }
                
                .btn-secondary {
                    background-color: var(--gray);
                    color: white;
                }
                
                .status-container {
                    margin-top: 30px;
                }
                
                .status-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                    gap: 20px;
                }
                
                .status-card {
                    background-color: var(--card-bg);
                    border-radius: 10px;
                    padding: 20px;
                    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
                    transition: transform 0.3s, box-shadow 0.3s;
                    border-left: 4px solid var(--primary);
                    cursor: pointer;
                }
                
                .status-card:hover {
                    transform: translateY(-5px);
                    box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
                }
                
                .status-card.up {
                    border-left-color: var(--success);
                }
                
                .status-card.down {
                    border-left-color: var(--danger);
                }
                
                .status-card.warning {
                    border-left-color: var(--warning);
                }
                
                .card-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 15px;
                }
                
                .site-name {
                    font-weight: 600;
                    font-size: 18px;
                    color: var(--text);
                }
                
                .status-badge {
                    padding: 5px 12px;
                    border-radius: 20px;
                    font-size: 14px;
                    font-weight: 500;
                }
                
                .status-badge.up {
                    background-color: rgba(76, 201, 240, 0.1);
                    color: var(--success);
                }
                
                .status-badge.down {
                    background-color: rgba(247, 37, 133, 0.1);
                    color: var(--danger);
                }
                
                .status-badge.warning {
                    background-color: rgba(248, 150, 30, 0.1);
                    color: var(--warning);
                }
                
                .card-stats {
                    display: grid;
                    grid-template-columns: repeat(2, 1fr);
                    gap: 15px;
                    margin-top: 15px;
                }
                
                .stat-item {
                    display: flex;
                    flex-direction: column;
                }
                
                .stat-label {
                    font-size: 12px;
                    color: var(--gray);
                    margin-bottom: 5px;
                }
                
                .stat-value {
                    font-weight: 600;
                    font-size: 16px;
                    color: var(--text);
                }
                
                .theme-toggle {
                    position: fixed;
                    bottom: 30px;
                    left: 30px;
                    width: 50px;
                    height: 50px;
                    border-radius: 50%;
                    background-color: var(--primary);
                    color: white;
                    border: none;
                    font-size: 1.2rem;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);
                    z-index: 90;
                }
                
                .details-modal {
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background-color: rgba(0, 0, 0, 0.5);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 1000;
                    opacity: 0;
                    pointer-events: none;
                    transition: opacity 0.3s;
                }
                
                .details-modal.active {
                    opacity: 1;
                    pointer-events: all;
                }
                
                .details-content {
                    background-color: var(--card-bg);
                    padding: 30px;
                    border-radius: 10px;
                    width: 90%;
                    max-width: 800px;
                    max-height: 80vh;
                    overflow-y: auto;
                    transform: translateY(-50px);
                    transition: transform 0.3s;
                    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
                }
                
                .details-modal.active .details-content {
                    transform: translateY(0);
                }
                
                .details-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 20px;
                }
                
                .close-btn {
                    background: none;
                    border: none;
                    font-size: 1.5rem;
                    cursor: pointer;
                    color: var(--gray);
                }
                
                .chart-container {
                    height: 200px;
                    margin: 20px 0;
                    position: relative;
                }
                
                .history-table {
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                }
                
                .history-table th, .history-table td {
                    padding: 10px;
                    text-align: left;
                    border-bottom: 1px solid var(--border);
                }
                
                .history-table th {
                    font-weight: 500;
                    color: var(--gray);
                }
                
                .status-cell {
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 12px;
                    text-align: center;
                }
                
                .status-cell.up {
                    background-color: rgba(76, 201, 240, 0.1);
                    color: var(--success);
                }
                
                .status-cell.down {
                    background-color: rgba(247, 37, 133, 0.1);
                    color: var(--danger);
                }
                
                @media (max-width: 768px) {
                    .status-grid {
                        grid-template-columns: 1fr;
                    }
                    
                    .card-stats {
                        grid-template-columns: 1fr;
                    }
                    
                    h1 {
                        font-size: 2rem;
                    }
                }
                
                /* Animations */
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(20px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                
                .fade-in {
                    animation: fadeIn 0.5s ease-out forwards;
                }
                
                .delay-1 { animation-delay: 0.1s; }
                .delay-2 { animation-delay: 0.2s; }
                .delay-3 { animation-delay: 0.3s; }
            </style>
        </head>
        <body>
            <header>
                <h1>Storm X Up</h1>
            </header>
            
            <div class="container">
                <div class="menu-bar">
                    <button class="menu-btn active" data-view="status">Status</button>
                    <button class="menu-btn" data-view="add">Add Monitor</button>
                    <button class="menu-btn" data-view="settings">Settings</button>
                </div>
                
                <div class="status-container" id="statusView">
                    <h2>Monitor Status</h2>
                    <div class="status-grid" id="statusGrid">
                        <!-- Status cards will be added here dynamically -->
                    </div>
                </div>
                
                <div class="add-container" id="addView" style="display: none;">
                    <div class="form-container fade-in">
                        <h2>Add New Monitor</h2>
                        <form id="addMonitorForm">
                            <div class="form-group">
                                <label for="monitorName">Monitor Name</label>
                                <input type="text" id="monitorName" placeholder="e.g. My API" required>
                            </div>
                            <div class="form-group">
                                <label for="monitorUrl">Website URL</label>
                                <input type="url" id="monitorUrl" placeholder="https://example.com" required>
                            </div>
                            <div class="form-group">
                                <label for="monitorInterval">Check Interval</label>
                                <select id="monitorInterval">
                                    <option value="30">30 seconds</option>
                                    <option value="60" selected>1 minute</option>
                                    <option value="300">5 minutes</option>
                                    <option value="600">10 minutes</option>
                                    <option value="1800">30 minutes</option>
                                    <option value="3600">1 hour</option>
                                </select>
                            </div>
                            <div class="form-actions">
                                <button type="button" class="btn btn-secondary" id="cancelAdd">Cancel</button>
                                <button type="submit" class="btn btn-primary">Add Monitor</button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
            
            <button class="add-btn" id="floatingAddBtn">+</button>
            <button class="theme-toggle" id="themeToggle">🌓</button>
            
            <div class="modal" id="addModal">
                <div class="modal-content">
                    <h2>Add New Monitor</h2>
                    <form id="modalAddForm">
                        <div class="form-group">
                            <label for="modalMonitorName">Monitor Name</label>
                            <input type="text" id="modalMonitorName" placeholder="e.g. My API" required>
                        </div>
                        <div class="form-group">
                            <label for="modalMonitorUrl">Website URL</label>
                            <input type="url" id="modalMonitorUrl" placeholder="https://example.com" required>
                        </div>
                        <div class="form-group">
                            <label for="modalMonitorInterval">Check Interval</label>
                            <select id="modalMonitorInterval">
                                <option value="30">30 seconds</option>
                                <option value="60" selected>1 minute</option>
                                <option value="300">5 minutes</option>
                                <option value="600">10 minutes</option>
                                <option value="1800">30 minutes</option>
                                <option value="3600">1 hour</option>
                            </select>
                        </div>
                        <div class="form-actions">
                            <button type="button" class="btn btn-secondary" id="modalCancel">Cancel</button>
                            <button type="submit" class="btn btn-primary">Add Monitor</button>
                        </div>
                    </form>
                </div>
            </div>
            
            <div class="details-modal" id="detailsModal">
                <div class="details-content">
                    <div class="details-header">
                        <h2 id="detailsTitle">Monitor Details</h2>
                        <button class="close-btn" id="closeDetails">&times;</button>
                    </div>
                    <div id="detailsContent">
                        <!-- Details content will be added here dynamically -->
                    </div>
                </div>
            </div>
            
            <script>
                // DOM Elements
                const statusView = document.getElementById('statusView');
                const addView = document.getElementById('addView');
                const statusGrid = document.getElementById('statusGrid');
                const addModal = document.getElementById('addModal');
                const floatingAddBtn = document.getElementById('floatingAddBtn');
                const themeToggle = document.getElementById('themeToggle');
                const detailsModal = document.getElementById('detailsModal');
                const menuBtns = document.querySelectorAll('.menu-btn');
                
                // Theme management
                themeToggle.addEventListener('click', () => {
                    const html = document.documentElement;
                    const currentTheme = html.getAttribute('data-theme');
                    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
                    html.setAttribute('data-theme', newTheme);
                    localStorage.setItem('theme', newTheme);
                });
                
                // Set initial theme
                const savedTheme = localStorage.getItem('theme') || 'light';
                document.documentElement.setAttribute('data-theme', savedTheme);
                
                // Menu navigation
                menuBtns.forEach(btn => {
                    btn.addEventListener('click', () => {
                        const view = btn.dataset.view;
                        menuBtns.forEach(b => b.classList.remove('active'));
                        btn.classList.add('active');
                        
                        if (view === 'status') {
                            statusView.style.display = 'block';
                            addView.style.display = 'none';
                        } else if (view === 'add') {
                            statusView.style.display = 'none';
                            addView.style.display = 'block';
                        }
                    });
                });
                
                // Floating add button
                floatingAddBtn.addEventListener('click', () => {
                    addModal.classList.add('active');
                });
                
                // Modal handling
                document.getElementById('modalCancel').addEventListener('click', () => {
                    addModal.classList.remove('active');
                });
                
                document.getElementById('cancelAdd').addEventListener('click', () => {
                    document.querySelector('.menu-btn[data-view="status"]').click();
                });
                
                // Add monitor form
                document.getElementById('modalAddForm').addEventListener('submit', async (e) => {
                    e.preventDefault();
                    
                    const name = document.getElementById('modalMonitorName').value;
                    const url = document.getElementById('modalMonitorUrl').value;
                    const interval = document.getElementById('modalMonitorInterval').value;
                    
                    try {
                        const response = await fetch('/add_site', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({
                                name: name,
                                url: url,
                                interval: interval
                            }),
                        });
                        
                        if (response.ok) {
                            addModal.classList.remove('active');
                            document.getElementById('modalAddForm').reset();
                            fetchStatus();
                        } else {
                            alert('Error adding monitor');
                        }
                    } catch (error) {
                        console.error('Error:', error);
                        alert('Error adding monitor');
                    }
                });
                
                // Close details modal
                document.getElementById('closeDetails').addEventListener('click', () => {
                    detailsModal.classList.remove('active');
                });
                
                // Fetch and display status
                async function fetchStatus() {
                    try {
                        const response = await fetch('/status');
                        const data = await response.json();
                        updateStatusGrid(data);
                    } catch (error) {
                        console.error('Error fetching status:', error);
                    }
                }
                
                // Update status grid
                function updateStatusGrid(data) {
                    if (!data.sites || data.sites.length === 0) {
                        statusGrid.innerHTML = '<p class="no-monitors">No monitors added yet. Click the + button to add one.</p>';
                        return;
                    }
                    
                    let html = '';
                    let delay = 0;
                    
                    for (const site of data.sites) {
                        const statusInfo = data.status_data[site.url] || {
                            uptime_percent: 0,
                            last_checked: 'Never',
                            response_time: 0,
                            last_status: 'unknown',
                            avg_response_time: 0,
                            total_checks: 0,
                            up_count: 0,
                            down_count: 0
                        };
                        
                        // Determine status class
                        let statusClass = statusInfo.last_status;
                        if (statusInfo.last_status === 'up' && statusInfo.avg_response_time > 1000) {
                            statusClass = 'warning';
                        }
                        
                        html += `
                            <div class="status-card ${statusClass} fade-in delay-${delay % 3}" data-url="${site.url}">
                                <div class="card-header">
                                    <div class="site-name">${site.name}</div>
                                    <div class="status-badge ${statusClass}">${statusClass.toUpperCase()}</div>
                                </div>
                                <div class="card-details">${site.url}</div>
                                
                                <div class="card-stats">
                                    <div class="stat-item">
                                        <span class="stat-label">Uptime</span>
                                        <span class="stat-value">${statusInfo.uptime_percent}%</span>
                                    </div>
                                    <div class="stat-item">
                                        <span class="stat-label">Avg Response</span>
                                        <span class="stat-value">${statusInfo.avg_response_time} ms</span>
                                    </div>
                                    <div class="stat-item">
                                        <span class="stat-label">Last Response</span>
                                        <span class="stat-value">${statusInfo.response_time} ms</span>
                                    </div>
                                    <div class="stat-item">
                                        <span class="stat-label">Last Checked</span>
                                        <span class="stat-value">${statusInfo.last_checked || 'Never'}</span>
                                    </div>
                                </div>
                            </div>
                        `;
                        delay++;
                    }
                    
                    statusGrid.innerHTML = html;
                    
                    // Add click event to status cards
                    document.querySelectorAll('.status-card').forEach(card => {
                        card.addEventListener('click', () => {
                            const url = card.dataset.url;
                            showSiteDetails(url);
                        });
                    });
                }
                
                // Show site details
                async function showSiteDetails(url) {
                    try {
                        const response = await fetch(`/site_details/${encodeURIComponent(url)}`);
                        const data = await response.json();
                        
                        const detailsTitle = document.getElementById('detailsTitle');
                        const detailsContent = document.getElementById('detailsContent');
                        
                        detailsTitle.textContent = data.name;
                        
                        let html = `
                            <div class="card-stats">
                                <div class="stat-item">
                                    <span class="stat-label">Current Status</span>
                                    <span class="stat-value">
                                        <span class="status-badge ${data.last_status}">${data.last_status.toUpperCase()}</span>
                                    </span>
                                </div>
                                <div class="stat-item">
                                    <span class="stat-label">Uptime Percentage</span>
                                    <span class="stat-value">${data.uptime_percent}%</span>
                                </div>
                                <div class="stat-item">
                                    <span class="stat-label">Average Response Time</span>
                                    <span class="stat-value">${data.avg_response_time} ms</span>
                                </div>
                                <div class="stat-item">
                                    <span class="stat-label">Total Checks</span>
                                    <span class="stat-value">${data.total_checks}</span>
                                </div>
                                <div class="stat-item">
                                    <span class="stat-label">Successful Checks</span>
                                    <span class="stat-value">${data.up_count}</span>
                                </div>
                                <div class="stat-item">
                                    <span class="stat-label">Failed Checks</span>
                                    <span class="stat-value">${data.down_count}</span>
                                </div>
                                <div class="stat-item">
                                    <span class="stat-label">Last Checked</span>
                                    <span class="stat-value">${data.last_checked}</span>
                                </div>
                                <div class="stat-item">
                                    <span class="stat-label">Check URL</span>
                                    <span class="stat-value">${url}</span>
                                </div>
                            </div>
                            
                            <h3 style="margin-top: 30px;">Response Time History</h3>
                            <div class="chart-container">
                                <canvas id="responseChart"></canvas>
                            </div>
                            
                            <h3>Recent Checks</h3>
                            <table class="history-table">
                                <thead>
                                    <tr>
                                        <th>Time</th>
                                        <th>Status</th>
                                        <th>Response Time</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${data.history.map(item => `
                                        <tr>
                                            <td>${item.time}</td>
                                            <td class="status-cell ${item.status}">${item.status.toUpperCase()}</td>
                                            <td>${item.response_time} ms</td>
                                        </tr>
                                    `).reverse().join('')}
                                </tbody>
                            </table>
                        `;
                        
                        detailsContent.innerHTML = html;
                        
                        // Initialize chart
                        initializeChart(data.history);
                        
                        detailsModal.classList.add('active');
                    } catch (error) {
                        console.error('Error fetching details:', error);
                    }
                }
                
                // Initialize response time chart
                function initializeChart(history) {
                    const ctx = document.getElementById('responseChart').getContext('2d');
                    const labels = history.map(item => item.time).reverse();
                    const data = history.map(item => item.response_time).reverse();
                    const statuses = history.map(item => item.status).reverse();
                    
                    const backgroundColors = statuses.map(status => 
                        status === 'up' ? 'rgba(76, 201, 240, 0.5)' : 'rgba(247, 37, 133, 0.5)'
                    );
                    
                    const borderColors = statuses.map(status => 
                        status === 'up' ? 'rgba(76, 201, 240, 1)' : 'rgba(247, 37, 133, 1)'
                    );
                    
                    new Chart(ctx, {
                        type: 'line',
                        data: {
                            labels: labels,
                            datasets: [{
                                label: 'Response Time (ms)',
                                data: data,
                                backgroundColor: backgroundColors,
                                borderColor: borderColors,
                                borderWidth: 1,
                                pointRadius: 3,
                                pointHoverRadius: 5,
                                tension: 0.1
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            scales: {
                                y: {
                                    beginAtZero: true
                                }
                            }
                        }
                    });
                }
                
                // Set up EventSource for real-time updates
                function setupEventSource() {
                    const eventSource = new EventSource('/status_updates');
                    
                    eventSource.onmessage = (event) => {
                        const data = JSON.parse(event.data);
                        updateStatusGrid(data);
                    };
                    
                    eventSource.onerror = () => {
                        console.log('EventSource error. Reconnecting...');
                        setTimeout(setupEventSource, 5000);
                    };
                }
                
                // Initialize
                fetchStatus();
                setupEventSource();
                
                // Load Chart.js
                const script = document.createElement('script');
                script.src = 'https://cdn.jsdelivr.net/npm/chart.js';
                script.onload = () => console.log('Chart.js loaded');
                document.head.appendChild(script);
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
                await asyncio.sleep(5)  # Send updates every 5 seconds
        except (asyncio.CancelledError, ConnectionResetError):
            pass
        
        return response

    async def handle_site_details(self, request):
        url = request.match_info['url']
        details = self.status_data.get(url, {})
        return web.json_response({
            'name': details.get('name', url),
            'url': url,
            'last_status': details.get('last_status', 'unknown'),
            'uptime_percent': details.get('uptime_percent', 0),
            'avg_response_time': details.get('avg_response_time', 0),
            'total_checks': details.get('total_checks', 0),
            'up_count': details.get('up_count', 0),
            'down_count': details.get('down_count', 0),
            'last_checked': details.get('last_checked', 'Never'),
            'history': details.get('history', [])
        })

    async def start(self):
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 8080)
        self.monitor_task = asyncio.create_task(self.monitor_sites())
        await site.start()
        print("Server started at http://0.0.0.0:8080")

async def start(self):
    runner = web.AppRunner(self.app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 5000)  # Changed to port 5000
    self.monitor_task = asyncio.create_task(self.monitor_sites())
    await site.start()
    print("Server started at http://0.0.0.0:5000")

if __name__ == '__main__':
    try:
        # This is the aiohttp equivalent of app.run()
        monitor = UptimeMonitor()
        web.run_app(monitor.app, port=5000)
    except KeyboardInterrupt:
        print("Server stopped")
