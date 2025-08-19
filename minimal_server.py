#!/usr/bin/env python3
"""
Minimal server for Conversational State Engine
Runs with built-in Python modules only
"""
import json
import sqlite3
import uuid
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import sys

# Add server directory to path
sys.path.append('/home/mikewong/Projects/conversational-state-engine/server')

# Simple in-memory database simulation
class SimpleDB:
    def __init__(self):
        self.sessions = {}
        self.states = {}
        self.init_db()
    
    def init_db(self):
        # Create a sample session
        session_id = "sess_demo123"
        self.sessions[session_id] = {
            "session_id": session_id,
            "current_version": "v1",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Initial state
        self.states[session_id] = {
            "version": "v1",
            "schema_version": "1.0.0",
            "data": {
                "stories": [],
                "glossary": []
            }
        }
    
    def create_session(self):
        session_id = f"sess_{uuid.uuid4().hex[:8]}"
        self.sessions[session_id] = {
            "session_id": session_id,
            "current_version": "v1",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        self.states[session_id] = {
            "version": "v1",
            "schema_version": "1.0.0",
            "data": {
                "stories": [],
                "glossary": []
            }
        }
        
        return {
            "session_id": session_id,
            "version": "v1"
        }
    
    def get_state(self, session_id):
        if session_id not in self.states:
            return None
        return self.states[session_id]
    
    def submit_intent(self, session_id, message):
        if session_id not in self.sessions:
            return None
        
        # Simple mock response based on message content
        patches = []
        impact = {
            "affected_paths": [],
            "risk_level": "low",
            "semantic_conflicts": []
        }
        
        # Simple rule-based parsing
        if "add" in message.lower() or "添加" in message.lower():
            patches.append({
                "op": "add",
                "path": "/stories/-",
                "value": {
                    "key": f"STORY-{uuid.uuid4().hex[:3]}",
                    "title": "New Story",
                    "priority": "P2",
                    "acceptance_criteria": []
                }
            })
            impact["affected_paths"].append("/stories")
            impact["risk_level"] = "medium"
        
        return {
            "intentions": [{"action": "add", "target_path": "/stories/-"}],
            "patches": patches,
            "impact": impact
        }
    
    def confirm_patches(self, session_id, patch_indices):
        if session_id not in self.states:
            return None
        
        # Apply patches (simplified)
        state = self.states[session_id]
        new_state = state["data"].copy()
        
        # Simple mock - add a story
        if "stories" not in new_state:
            new_state["stories"] = []
        
        new_state["stories"].append({
            "key": f"STORY-{uuid.uuid4().hex[:3]}",
            "title": "Added Story",
            "priority": "P2",
            "acceptance_criteria": ["Sample criterion"]
        })
        
        return {
            "success": True,
            "new_state": new_state,
            "applied_patches": [{"op": "add", "path": "/stories/-"}]
        }

# Global database instance
db = SimpleDB()

class CSEHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path == '/':
            self.send_json_response({
                "name": "Conversational State Engine (Minimal)",
                "version": "0.1.0-minimal",
                "gaps": "Running with identified gaps - no auth, mock LLM, simplified workflow"
            })
        elif path == '/health':
            self.send_json_response({"status": "healthy", "mode": "minimal"})
        elif path.startswith('/sessions/'):
            parts = path.split('/')
            if len(parts) >= 4 and parts[3] == 'state':
                session_id = parts[2]
                state = db.get_state(session_id)
                if state:
                    self.send_json_response(state)
                else:
                    self.send_error_response(404, "Session not found")
            else:
                self.send_error_response(404, "Not found")
        else:
            self.send_error_response(404, "Not found")
    
    def do_POST(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path == '/sessions':
            result = db.create_session()
            self.send_json_response(result)
        elif path.startswith('/sessions/'):
            parts = path.split('/')
            session_id = parts[2]
            
            if len(parts) >= 4 and parts[3] == 'intents':
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                
                result = db.submit_intent(session_id, data.get('message', ''))
                if result:
                    self.send_json_response(result)
                else:
                    self.send_error_response(404, "Session not found")
            
            elif len(parts) >= 4 and parts[3] == 'confirm':
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                
                result = db.confirm_patches(session_id, data.get('patch_indices', []))
                if result:
                    self.send_json_response(result)
                else:
                    self.send_error_response(404, "Session not found")
            
            elif len(parts) >= 4 and parts[3] == 'commit':
                # Mock commit response
                self.send_json_response({
                    "success": True,
                    "artifacts": [
                        {"id": "art_md123", "type": "markdown", "url": "/artifacts/art_md123"},
                        {"id": "art_csv123", "type": "csv", "url": "/artifacts/art_csv123"}
                    ]
                })
            
            else:
                self.send_error_response(404, "Not found")
        else:
            self.send_error_response(404, "Not found")
    
    def send_json_response(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def send_error_response(self, code, message):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({"error": message}).encode('utf-8'))

def run_server():
    server_address = ('', 8000)
    httpd = HTTPServer(server_address, CSEHandler)
    print("Minimal Conversational State Engine Server running on http://localhost:8000")
    print(" gaps identified:")
    print("  🔴 No authentication (security risk)")
    print("  🔴 Mock LLM analysis (no AI processing)")
    print("  🟡 Simplified workflow (single-stage confirmation)")
    print("  🟡 No conflict detection")
    print("  🟡 No ContextSlicer integration")
    print("  🟡 Basic functionality only")
    print("\nAPI endpoints available:")
    print("  GET  /                 - Server info")
    print("  GET  /health          - Health check")
    print("  POST /sessions        - Create session")
    print("  GET  /sessions/{id}/state - Get state")
    print("  POST /sessions/{id}/intents - Submit intent")
    print("  POST /sessions/{id}/confirm - Confirm patches")
    print("  POST /sessions/{id}/commit - Commit changes")
    print("\nPress Ctrl+C to stop the server")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped")

if __name__ == "__main__":
    run_server()