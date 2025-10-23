#!/bin/bash
# Version sync check for automagik-telemetry
# Ensures Python and TypeScript packages have matching versions

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🔍 Checking version sync between Python and TypeScript..."

# Extract Python version from pyproject.toml
PYTHON_VERSION=$(grep '^version = ' python/pyproject.toml | cut -d'"' -f2)

# Extract TypeScript version from package.json
TS_VERSION=$(grep '"version":' typescript/package.json | head -1 | cut -d'"' -f4)

echo "  Python version:     ${PYTHON_VERSION}"
echo "  TypeScript version: ${TS_VERSION}"

# Check if versions match
if [ "$PYTHON_VERSION" != "$TS_VERSION" ]; then
    echo ""
    echo -e "${RED}❌ VERSION MISMATCH DETECTED!${NC}"
    echo ""
    echo "Python and TypeScript versions MUST be identical."
    echo ""
    echo "  Python (pyproject.toml):     ${PYTHON_VERSION}"
    echo "  TypeScript (package.json):   ${TS_VERSION}"
    echo ""
    echo "Please update one of the following files to match:"
    echo "  - python/pyproject.toml"
    echo "  - typescript/package.json"
    echo ""
    exit 1
fi

echo -e "${GREEN}✅ Versions are in sync!${NC}"
exit 0
