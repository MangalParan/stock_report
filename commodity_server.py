#!/usr/bin/env python3
"""
Commodity Analysis Web Server
Serves the commodity analysis report with refresh and progress tracking
"""

import http.server
import socketserver
import json
import subprocess
import sys
import os
import threading
import time
from urllib.parse import urlparse
from pathlib import Path

PORT = 5001
SERVER_DIRECTORY = Path(__file__).resolve().parent
PROGRESS_FILE = SERVER_DIRECTORY / 'progress.json'

class CommodityReportHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler for commodity report server"""
    
    def do_GET(self):
        """Handle GET requests - serve the HTML report or progress"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/':
            self.serve_report()
        elif parsed_path.path == '/progress':
            self.get_progress()
        else:
            self.send_error(404, "Not found")
    
    def do_POST(self):
        """Handle POST requests - refresh data"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/refresh-data':
            self.refresh_data()
        else:
            self.send_error(404, "Not found")
    
    def serve_report(self):
        """Serve the HTML report file"""
        report_file = SERVER_DIRECTORY / 'commodity_analysis_table_report.html'
        
        if not report_file.exists():
            self.send_error(404, "Report not found. Run analysis first.")
            return
        
        try:
            with open(report_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', len(content.encode('utf-8')))
            self.end_headers()
            self.wfile.write(content.encode('utf-8'))
        except Exception as e:
            self.send_error(500, f"Error serving report: {str(e)}")
    
    def get_progress(self):
        """Send current progress as JSON"""
        if PROGRESS_FILE.exists():
            try:
                with open(PROGRESS_FILE, 'r') as f:
                    progress_data = json.load(f)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps(progress_data).encode('utf-8'))
            except Exception as e:
                self.send_error(500, f"Error reading progress: {str(e)}")
        else:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            default_progress = {
                "percentage": 100,
                "status": "idle",
                "message": "No refresh in progress",
                "timestamp": time.time()
            }
            self.wfile.write(json.dumps(default_progress).encode('utf-8'))
    
    def refresh_data(self):
        """Start data refresh in background thread"""
        def run_refresh():
            try:
                print("\n[*] Starting commodity data refresh...")
                subprocess.run([sys.executable, 'update_data.py'], 
                             cwd=SERVER_DIRECTORY, check=True)
                print("[*] Data update complete, generating report...")
                subprocess.run([sys.executable, 'commodity_bullish_bearish_table_report.py'],
                             cwd=SERVER_DIRECTORY, check=True)
                print("[*] Refresh complete!")
            except subprocess.CalledProcessError as e:
                print(f"[-] Refresh error: {e}")
        
        # Run in background thread
        refresh_thread = threading.Thread(target=run_refresh, daemon=True)
        refresh_thread.start()
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        response = {"status": "refresh_started", "message": "Data refresh in progress"}
        self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        pass

def main():
    """Start the web server"""
    server_address = ('', PORT)
    
    with socketserver.TCPServer(server_address, CommodityReportHandler) as httpd:
        print("="*70)
        print(f"Commodity Analysis Server")
        print("="*70)
        print(f"Serving at: http://localhost:{PORT}")
        print(f"Commands:")
        print(f"  - View Report: http://localhost:{PORT}")
        print(f"  - Refresh Data: POST to http://localhost:{PORT}/refresh-data (via UI button)")
        print(f"  - Check Progress: http://localhost:{PORT}/progress")
        print("="*70)
        print("Press Ctrl+C to stop server\n")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[*] Server stopped")

if __name__ == '__main__':
    main()
