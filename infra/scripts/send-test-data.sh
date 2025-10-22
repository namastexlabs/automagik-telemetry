#!/bin/bash
# Script to send test telemetry data to local infrastructure

set -e

ENDPOINT="${AUTOMAGIK_TELEMETRY_ENDPOINT:-http://localhost:4318/v1/traces}"
PROJECT_NAME="${PROJECT_NAME:-test-project}"
NUM_EVENTS="${NUM_EVENTS:-10}"

echo "Sending ${NUM_EVENTS} test events to ${ENDPOINT}..."

for i in $(seq 1 ${NUM_EVENTS}); do
  TRACE_ID=$(openssl rand -hex 16)
  SPAN_ID=$(openssl rand -hex 8)
  TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%S.%3NZ")

  # Generate random event types
  EVENT_TYPES=("user.login" "user.signup" "api.request" "feature.used" "error.occurred")
  EVENT_TYPE=${EVENT_TYPES[$((RANDOM % ${#EVENT_TYPES[@]}))]}

  # Generate random status
  STATUS_CODES=("OK" "OK" "OK" "OK" "ERROR")  # 80% OK, 20% ERROR
  STATUS_CODE=${STATUS_CODES[$((RANDOM % ${#STATUS_CODES[@]}))]}

  # Random duration between 10-500ms
  DURATION=$((10 + RANDOM % 490))

  PAYLOAD=$(cat <<EOF
{
  "resourceSpans": [{
    "resource": {
      "attributes": [
        {"key": "service.name", "value": {"stringValue": "${PROJECT_NAME}"}},
        {"key": "service.version", "value": {"stringValue": "1.0.0"}},
        {"key": "deployment.environment", "value": {"stringValue": "production"}},
        {"key": "host.name", "value": {"stringValue": "test-host-$(hostname)"}}
      ]
    },
    "scopeSpans": [{
      "scope": {
        "name": "automagik-telemetry-test",
        "version": "1.0.0"
      },
      "spans": [{
        "traceId": "${TRACE_ID}",
        "spanId": "${SPAN_ID}",
        "name": "${EVENT_TYPE}",
        "kind": 1,
        "startTimeUnixNano": "$(($(date +%s%N)))",
        "endTimeUnixNano": "$(($(date +%s%N) + DURATION * 1000000))",
        "attributes": [
          {"key": "event.type", "value": {"stringValue": "${EVENT_TYPE}"}},
          {"key": "test.iteration", "value": {"intValue": ${i}}},
          {"key": "random.value", "value": {"intValue": ${RANDOM}}}
        ],
        "status": {
          "code": "$([[ ${STATUS_CODE} == "OK" ]] && echo 1 || echo 2)",
          "message": "${STATUS_CODE}"
        }
      }]
    }]
  }]
}
EOF
)

  # Send to collector
  RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${ENDPOINT}" \
    -H "Content-Type: application/json" \
    -d "${PAYLOAD}")

  HTTP_CODE=$(echo "${RESPONSE}" | tail -n1)

  if [ "${HTTP_CODE}" -eq 200 ] || [ "${HTTP_CODE}" -eq 202 ]; then
    echo "✓ Event ${i}/${NUM_EVENTS}: ${EVENT_TYPE} (${STATUS_CODE}) - ${DURATION}ms"
  else
    echo "✗ Event ${i}/${NUM_EVENTS}: Failed with HTTP ${HTTP_CODE}"
  fi

  # Small delay between events
  sleep 0.1
done

echo ""
echo "✓ Test data sent successfully!"
echo "  Total events: ${NUM_EVENTS}"
echo "  Project: ${PROJECT_NAME}"
echo ""
echo "View data in Grafana: http://localhost:3000"
