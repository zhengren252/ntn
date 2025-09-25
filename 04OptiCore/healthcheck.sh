#!/bin/bash

# OptiCore Health Check Script
# This script checks if the OptiCore service is running and healthy

set -e

# Check if the service is responding on port 8000
if curl -f -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "OptiCore service is healthy"
    exit 0
else
    echo "OptiCore service health check failed"
    exit 1
fi