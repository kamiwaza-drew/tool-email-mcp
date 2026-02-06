#!/bin/bash
# Package Setup Script for Kamiwaza Extensions Registry
# This script configures the local environment for using the packaged registry

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory (which is the package root when extracted)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PACKAGE_ROOT="$SCRIPT_DIR"

echo "Kamiwaza Extensions Registry Setup"
echo "==================================="
echo ""

# Function to print colored output
print_success() { echo -e "${GREEN}✓${NC} $1"; }
print_error() { echo -e "${RED}✗${NC} $1"; }
print_warning() { echo -e "${YELLOW}⚠${NC} $1"; }
print_info() { echo -e "  $1"; }

# Check Docker availability
check_docker() {
    echo "Checking Docker installation..."
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed or not in PATH"
        echo "Please install Docker from https://www.docker.com/get-started"
        exit 1
    fi
    print_success "Docker is installed"

    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running"
        echo "Please start Docker and try again"
        exit 1
    fi
    print_success "Docker daemon is running"
    echo ""
}

# Load Docker images
load_docker_images() {
    local images_dir="$PACKAGE_ROOT/garden/default/docker-images"

    if [ ! -d "$images_dir" ]; then
        print_error "Docker images directory not found: $images_dir"
        echo "This package may not contain Docker images."
        return 1
    fi

    # Count tar files
    local tar_count=$(ls -1 "$images_dir"/*.tar 2>/dev/null | wc -l)

    if [ "$tar_count" -eq 0 ]; then
        print_warning "No Docker image tar files found"
        echo "Images may need to be pulled from registry when extensions are deployed."
        return 0
    fi

    echo "Found $tar_count Docker image tar files"
    echo ""

    # Ask for confirmation
    read -p "Load all Docker images locally? This may take several minutes. (y/n): " -n 1 -r
    echo ""

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Skipping Docker image loading"
        return 0
    fi

    echo ""
    echo "Loading Docker images..."

    local success=0
    local failed=0

    for tar_file in "$images_dir"/*.tar; do
        local filename=$(basename "$tar_file")
        echo -n "  Loading $filename... "

        if docker load -i "$tar_file" &> /dev/null; then
            print_success "done"
            success=$((success + 1))
        else
            print_error "failed"
            failed=$((failed + 1))
        fi
    done

    echo ""
    print_info "Images loaded: $success successful, $failed failed"
    echo ""
}

# Configure environment
configure_environment() {
    echo "Environment Configuration"
    echo "-------------------------"
    echo ""
    echo "To use this registry with Kamiwaza, set the following environment variables:"
    echo ""

    echo "Option 1: Serve registry via HTTPS (recommended for team sharing)"
    echo "  export KAMIWAZA_EXTENSION_STAGE=LOCAL"
    echo "  export KAMIWAZA_EXTENSION_LOCAL_STAGE_URL=https://your-server:58888"
    echo ""
    echo "  Then serve the registry (see 'Start HTTPS server' option below)"
    echo ""

    echo "Option 2: Use local file system (single machine)"
    echo "  export KAMIWAZA_EXTENSION_STAGE=LOCAL"
    echo "  export KAMIWAZA_EXTENSION_LOCAL_STAGE_URL=file://$PACKAGE_ROOT"
    echo ""

    # Create env file
    local env_file="$PACKAGE_ROOT/kamiwaza-registry.env"
    cat > "$env_file" << EOF
# Kamiwaza Extensions Registry Environment Configuration
# Source this file to configure your environment:
#   source kamiwaza-registry.env

# Enable local extension stage
export KAMIWAZA_EXTENSION_STAGE=LOCAL

# Option 1: HTTPS server (change to your server URL)
# export KAMIWAZA_EXTENSION_LOCAL_STAGE_URL=https://localhost:58888

# Option 2: Local file system
export KAMIWAZA_EXTENSION_LOCAL_STAGE_URL=file://$PACKAGE_ROOT

# Registry paths (automatically configured)
export KAMIWAZA_REGISTRY_APPS=$PACKAGE_ROOT/garden/default/apps.json
export KAMIWAZA_REGISTRY_TOOLS=$PACKAGE_ROOT/garden/default/tools.json
EOF

    print_success "Created environment file: kamiwaza-registry.env"
    echo ""
}

# Create self-signed certificate
create_self_signed_cert() {
    local cert_dir="$PACKAGE_ROOT/.certs"
    local cert_file="$cert_dir/server.pem"
    local key_file="$cert_dir/server.key"

    # Check if cert already exists
    if [ -f "$cert_file" ] && [ -f "$key_file" ]; then
        print_info "Using existing self-signed certificate"
        return 0
    fi

    echo "Creating self-signed certificate..."
    mkdir -p "$cert_dir"

    # Generate self-signed certificate
    openssl req -new -x509 -keyout "$key_file" -out "$cert_file" -days 365 -nodes \
        -subj "/C=US/ST=State/L=City/O=Kamiwaza/CN=localhost" &> /dev/null

    if [ $? -eq 0 ]; then
        print_success "Created self-signed certificate in $cert_dir"
    else
        print_error "Failed to create self-signed certificate"
        return 1
    fi
}

# Create HTTPS server script
create_https_server() {
    local server_script="$PACKAGE_ROOT/serve-registry.py"

    cat > "$server_script" << 'EOF'
#!/usr/bin/env python3
"""
HTTPS server for Kamiwaza Extensions Registry
Serves registry files over HTTPS with self-signed certificate
"""

import ssl
import os
import sys
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
import argparse

class CORSRequestHandler(SimpleHTTPRequestHandler):
    """HTTP request handler with CORS headers."""

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

def create_ssl_context(cert_dir):
    """Create SSL context with self-signed certificate."""
    cert_file = cert_dir / "server.pem"
    key_file = cert_dir / "server.key"

    if not cert_file.exists() or not key_file.exists():
        print(f"Certificate files not found in {cert_dir}")
        print("Run the package-setup.sh script to generate certificates")
        sys.exit(1)

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_file, key_file)

    return context

def main():
    parser = argparse.ArgumentParser(description='Serve Kamiwaza Extensions Registry over HTTPS')
    parser.add_argument('--port', type=int, default=58888, help='Port to serve on (default: 58888)')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to (default: 0.0.0.0)')
    args = parser.parse_args()

    # Get package root directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    # Create SSL context
    cert_dir = script_dir / ".certs"
    ssl_context = create_ssl_context(cert_dir)

    # Create and configure server
    server_address = (args.host, args.port)
    httpd = HTTPServer(server_address, CORSRequestHandler)
    httpd.socket = ssl_context.wrap_socket(httpd.socket, server_side=True)

    print(f"Serving Kamiwaza Extensions Registry over HTTPS")
    print(f"Server running at https://localhost:{args.port}")
    print("")
    print("Registry URLs:")
    print(f"  Apps:  https://localhost:{args.port}/garden/default/apps.json")
    print(f"  Tools: https://localhost:{args.port}/garden/default/tools.json")
    print("")
    print("Note: This uses a self-signed certificate. Clients may need to accept it.")
    print("Press Ctrl+C to stop the server")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.shutdown()

if __name__ == '__main__':
    main()
EOF

    chmod +x "$server_script"
    print_success "Created HTTPS server script: serve-registry.py"
}

# Verify registry integrity
verify_registry() {
    echo "Verifying registry integrity..."

    local apps_json="$PACKAGE_ROOT/garden/default/apps.json"
    local tools_json="$PACKAGE_ROOT/garden/default/tools.json"
    local manifest="$PACKAGE_ROOT/garden/default/docker-images/manifest.json"

    # Check registry files
    if [ -f "$apps_json" ]; then
        local app_count=$(jq '. | length' "$apps_json" 2>/dev/null || echo "0")
        print_success "Found $app_count apps in registry"
    else
        print_warning "apps.json not found"
    fi

    if [ -f "$tools_json" ]; then
        local tool_count=$(jq '. | length' "$tools_json" 2>/dev/null || echo "0")
        print_success "Found $tool_count tools in registry"
    else
        print_warning "tools.json not found"
    fi

    # Check manifest if exists
    if [ -f "$manifest" ]; then
        local image_count=$(jq '.total_images' "$manifest" 2>/dev/null || echo "unknown")
        local total_size=$(jq '.total_size' "$manifest" 2>/dev/null || echo "0")

        if [ "$total_size" != "0" ] && [ "$total_size" != "unknown" ]; then
            local human_size=$(numfmt --to=iec-i --suffix=B "$total_size" 2>/dev/null || echo "unknown size")
            print_success "Manifest reports $image_count images ($human_size)"
        else
            print_success "Manifest reports $image_count images"
        fi
    else
        print_info "No manifest file found (images may not be included)"
    fi

    echo ""
}

# Start HTTPS server
start_https_server() {
    echo "HTTPS Server Options"
    echo "--------------------"
    echo ""
    read -p "Start HTTPS server to serve registry? (y/n): " -n 1 -r
    echo ""

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        return 0
    fi

    # Create self-signed certificate if needed
    create_self_signed_cert

    # Create HTTPS server script
    create_https_server

    local port=58888
    read -p "Port number (default: 58888): " user_port
    if [ ! -z "$user_port" ]; then
        port=$user_port
    fi

    echo ""
    echo "Starting HTTPS server on port $port..."
    echo ""

    # Run the HTTPS server
    python3 "$PACKAGE_ROOT/serve-registry.py" --port "$port"
}

# Main execution
main() {
    echo "Package location: $PACKAGE_ROOT"
    echo ""

    # Check Docker
    check_docker

    # Verify registry
    verify_registry

    # Load Docker images
    load_docker_images

    # Configure environment
    configure_environment

    # Optionally start HTTPS server
    start_https_server
}

# Run main function
main "$@"