#!/usr/bin/env python3
"""
HTTP Server for Stock Analysis Report with Data Refresh Capability
Serves the stock analysis HTML report and handles data refresh requests
with real-time progress tracking
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

PORT = 5000
SERVER_DIRECTORY = Path(__file__).resolve().parent
PROGRESS_FILE = SERVER_DIRECTORY / 'progress.json'

class StockReportHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler for stock report server"""
    
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
        report_file = SERVER_DIRECTORY / 'stock_analysis_table_report.html'
        
        if not report_file.exists():
            self.send_error(404, "Report file not found")
            return
        
        try:
            with open(report_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(content.encode('utf-8'))
        except Exception as e:
            self.send_error(500, f"Error reading report: {str(e)}")
    
    def get_progress(self):
        """Return current progress status"""
        try:
            if PROGRESS_FILE.exists():
                with open(PROGRESS_FILE, 'r') as f:
                    progress = json.load(f)
            else:
                progress = {"percentage": 0, "status": "idle", "message": "No update in progress"}
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(progress).encode('utf-8'))
        except Exception as e:
            self.send_json_response(500, "error", f"Error reading progress: {str(e)}")
    
    def refresh_data(self):
        """Execute update_data.py and regenerate report in background thread"""
        try:
            # Start update in a background thread
            thread = threading.Thread(target=self._run_update)
            thread.daemon = True
            thread.start()
            
            self.send_json_response(200, "success", "Update started. Check /progress for status.")
        
        except Exception as e:
            error_msg = f"Failed to start update: {str(e)}"
            print(f"[SERVER] {error_msg}")
            self.send_json_response(500, "error", error_msg)
    
    def _run_update(self):
        """Background thread function to run update and report generation"""
        print("\n[SERVER] Refresh data request received. Starting update_data.py...")
        
        try:
            # Step 1: Run update_data.py
            update_script = SERVER_DIRECTORY / 'update_data.py'
            if not update_script.exists():
                self._write_progress(100, "error", "update_data.py not found")
                return
            
            result = subprocess.run(
                [sys.executable, str(update_script)],
                capture_output=True,
                text=True,
                timeout=1200,  # 20 minutes timeout
                cwd=str(SERVER_DIRECTORY)
            )
            
            if result.returncode != 0:
                error_msg = f"update_data.py failed: {result.stderr}"
                print(f"[SERVER] {error_msg}")
                self._write_progress(0, "error", error_msg)
                return
            
            print("[SERVER] update_data.py completed successfully. Regenerating report...")
            self._write_progress(95, "generating_report", "Regenerating analysis report...")
            
            # Step 2: Run bullish_bearish_table_report.py
            report_script = SERVER_DIRECTORY / 'bullish_bearish_table_report.py'
            if not report_script.exists():
                self._write_progress(0, "error", "bullish_bearish_table_report.py not found")
                return
            
            result = subprocess.run(
                [sys.executable, str(report_script)],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes timeout
                cwd=str(SERVER_DIRECTORY)
            )
            
            if result.returncode != 0:
                error_msg = f"Report generation failed: {result.stderr}"
                print(f"[SERVER] {error_msg}")
                self._write_progress(0, "error", error_msg)
                return
            
            print("[SERVER] Report regenerated successfully.")
            self._write_progress(100, "completed", "Update and report generation completed successfully!")
        
        except subprocess.TimeoutExpired:
            error_msg = "Data refresh timed out (exceeded 20 minutes)"
            print(f"[SERVER] {error_msg}")
            self._write_progress(0, "error", error_msg)
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            print(f"[SERVER] {error_msg}")
            self._write_progress(0, "error", error_msg)
    
    def _write_progress(self, percentage, status, message):
        """Write progress to JSON file"""
        try:
            progress_data = {
                "percentage": min(100, max(0, percentage)),
                "status": status,
                "message": message,
                "timestamp": time.time()
            }
            with open(PROGRESS_FILE, 'w') as f:
                json.dump(progress_data, f)
        except Exception as e:
            print(f"[SERVER] Error writing progress: {e}")
    
    def send_json_response(self, status_code, status, message):
        """Send JSON response to client"""
        response = {
            "status": status,
            "message": message
        }
        
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def log_message(self, format, *args):
        """Override to customize log messages"""
        print(f"[{self.client_address[0]}] {format % args}")


def run_server(port=PORT):
    """Start the HTTP server"""
    handler = StockReportHandler
    
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"\n{'='*60}")
        print(f"Stock Analysis Report Server")
        print(f"{'='*60}")
        print(f"Server running at: http://localhost:{port}")
        print(f"Open this URL in your browser to view the report")
        print(f"Click 'Refresh Data' button to update market data")
        print(f"\nPress Ctrl+C to stop the server")
        print(f"{'='*60}\n")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n[SERVER] Shutting down...")
            httpd.shutdown()


if __name__ == '__main__':
    run_server(PORT)
