#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Installing AWS CLI..."
bash "$SCRIPT_DIR/install-awscli.sh"

echo "Installing Terraform..."
bash "$SCRIPT_DIR/install-terraform.sh"

echo "Setup completed successfully!"
