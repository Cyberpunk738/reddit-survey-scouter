"""
Reddit Survey Scout - Health Check Server
Runs a lightweight HTTP server on a daemon thread to keep cloud platforms like Render
healthy and awake via ping monitoring.
"""

import json
import logging
import os
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional

logger = logging.getLogger(__name__)

# Track startup timestamp for uptime reporting
_START_TIME = time.time()


class HealthCheckHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler responding to health and ping checks."""

    def do_GET(self):
        if self.path in ("/", "/health", "/status", "/ping"):
            uptime_seconds = int(time.time() - _START_TIME)
            response_data = {
                "status": "healthy",
                "service": "Reddit Survey Scout",
                "uptime_seconds": uptime_seconds
            }
            body = json.dumps(response_data).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        """Suppress noisy request logs, forwarding only to debug."""
        logger.debug("HealthCheck HTTP: %s", format % args)


def start_health_server(port: int = 10000) -> Optional[HTTPServer]:
    """Start the health server on a background daemon thread."""
    try:
        server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        logger.info("Health check web server running on http://0.0.0.0:%d", port)
        return server
    except Exception as e:
        logger.warning("Failed to start health check server on port %d: %s", port, e)
        return None
