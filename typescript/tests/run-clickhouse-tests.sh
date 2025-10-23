#!/bin/bash
# Script to run ClickHouse integration tests with proper environment setup

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}ClickHouse Integration Test Runner${NC}"
echo "===================================="
echo ""

# Check if ClickHouse is running
echo -n "Checking ClickHouse availability... "
if curl -s http://localhost:8123 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Running${NC}"
else
    echo -e "${RED}✗ Not running${NC}"
    echo ""
    echo "Please start ClickHouse first:"
    echo "  cd ../infra && docker compose up -d clickhouse"
    exit 1
fi

# Check if database exists
echo -n "Checking telemetry database... "
if curl -s "http://localhost:8123/?query=SHOW%20DATABASES" | grep -q "telemetry"; then
    echo -e "${GREEN}✓ Exists${NC}"
else
    echo -e "${RED}✗ Not found${NC}"
    echo ""
    echo "Database not initialized. Reinitializing..."
    cd ../infra && docker compose restart clickhouse
    sleep 5
fi

# Check if table exists
echo -n "Checking traces table... "
if curl -s "http://localhost:8123/?query=SHOW%20TABLES%20FROM%20telemetry" | grep -q "traces"; then
    echo -e "${GREEN}✓ Exists${NC}"
else
    echo -e "${RED}✗ Not found${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}Running tests...${NC}"
echo ""

# Run the tests
cd "$(dirname "$0")/.."
RUN_INTEGRATION_TESTS=true npm test -- clickhouse.integration.test.ts "$@"

TEST_EXIT_CODE=$?

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ All tests passed!${NC}"
else
    echo ""
    echo -e "${RED}✗ Some tests failed${NC}"
fi

exit $TEST_EXIT_CODE
