#!/usr/bin/env python3
"""
Mock BFD9010 scanner service for local development.

Implements the FHIR Device endpoints used by the bfd9000 scan page:
  GET  /Device/{id}          - device info
  POST /Device/{id}/$scan    - returns a sample PNG as a FHIR Binary
  POST /Device/{id}/$calibrate
  POST /Device/{id}/$eject

Usage:
    python dev_tools/mock_bfd9010/mock_bfd9010.py
    python dev_tools/mock_bfd9010/mock_bfd9010.py --port 5001

Set SCANNER_API_BASE=http://localhost:5000 (default) in your .env
and SCANNER_DEVICE_ID=scanner-001 (default) in Django settings.
"""

import argparse
import base64
import http.server
import json
import random
import socketserver
from pathlib import Path
from urllib.parse import unquote, urlparse

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "http://localhost:9000",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Accept",
    "Content-Type": "application/fhir+json",
}

SAMPLE_DEVICE: dict = {
    "resourceType": "Device",
    "manufacturer": "Planmeca",
    "modelNumber": "ProMax 3D Mid",
    "serialNumber": "PM-MOCK-00042",
    "deviceName": [
        {"name": "ProMax 3D Mid", "type": "manufacturer-name"}
    ],
    "version": [
        {"type": {"text": "Firmware"}, "value": "1.0.0-mock"}
    ],
    "property": [
        {
            "type": {"text": "Resolution"},
            "valueQuantity": {"value": 300, "unit": "DPI"},
        }
    ],
}

SAMPLE_OPERATION_OUTCOME: dict = {
    "resourceType": "OperationOutcome",
    "issue": [
        {
            "severity": "information",
            "code": "informational",
            "details": {"text": "Operation completed successfully (mock)"},
        }
    ],
}

# 1x1 white PNG as fallback when sample image is not found
FALLBACK_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwADhQGAWjR9awAAAABJRU5ErkJggg=="
)

# Directory of sample PNG images.  When running inside Docker the images are
# extracted here by the Dockerfile; when running locally they can be placed in
# the same directory or the fallback 1x1 PNG is used instead.
SAMPLE_IMAGES_DIR = Path(__file__).parent / "sample_images"

_NOT_FOUND_BODY = json.dumps({
    "resourceType": "OperationOutcome",
    "issue": [{"severity": "error", "code": "not-found"}],
}).encode("utf-8")


class MockBFD9010RequestHandler(http.server.BaseHTTPRequestHandler):

    def _send_json(self, body: dict, status: int = 200) -> None:
        payload = json.dumps(body).encode("utf-8")
        self.send_response(status)
        for key, value in CORS_HEADERS.items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_not_found(self) -> None:
        self.send_response(404)
        for key, value in CORS_HEADERS.items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(_NOT_FOUND_BODY)))
        self.end_headers()
        self.wfile.write(_NOT_FOUND_BODY)

    def do_OPTIONS(self) -> None:  # CORS preflight
        self.send_response(200)
        for key, value in CORS_HEADERS.items():
            self.send_header(key, value)
        self.end_headers()

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        parts = path.strip("/").split("/")
        # GET /Device/{id}
        if len(parts) == 2 and parts[0] == "Device":
            device_id: str = unquote(parts[1])
            body = {**SAMPLE_DEVICE, "id": device_id}
            self._send_json(body)
        else:
            self._send_not_found()

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        parts = path.strip("/").split("/")
        # POST /Device/{id}/$action
        if len(parts) == 3 and parts[0] == "Device":
            action: str = parts[2]
            if action == "$scan":
                self._send_json(self._build_scan_bundle())
            elif action in ("$calibrate", "$eject"):
                self._send_json(SAMPLE_OPERATION_OUTCOME)
            else:
                self._send_not_found()
        else:
            self._send_not_found()

    def _build_scan_bundle(self) -> dict:
        image_b64 = self._load_sample_image_b64()
        return {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [
                {
                    "resource": {
                        "resourceType": "Binary",
                        "contentType": "image/png",
                        "data": image_b64,
                    }
                }
            ],
        }

    def _load_sample_image_b64(self) -> str:
        images: list[Path] = sorted(SAMPLE_IMAGES_DIR.glob("*.png"))
        if images:
            try:
                return base64.b64encode(random.choice(images).read_bytes()).decode("ascii")
            except Exception:
                pass
        return FALLBACK_PNG_B64

    def log_message(self, fmt: str, *args: object) -> None:  # type: ignore[override]
        print(f"  {self.address_string()} - {fmt % args}")


class _ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mock BFD9010 FHIR scanner service for local development."
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host address to bind (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port to listen on (default: 5000)",
    )
    args = parser.parse_args()

    images: list[Path] = sorted(SAMPLE_IMAGES_DIR.glob("*.png"))
    print(
        f"Mock BFD9010 scanner running at http://{args.host}:{args.port}\n"
        f"Device ID: scanner-001  (matches SCANNER_DEVICE_ID default in Django settings)\n"
        f"Sample images dir: {SAMPLE_IMAGES_DIR} "
        f"({len(images)} PNG(s) found{' — using fallback 1x1 PNG' if not images else ''})\n"
        f"Press Ctrl+C to stop."
    )

    with _ReusableTCPServer((args.host, args.port), MockBFD9010RequestHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")


if __name__ == "__main__":
    main()
