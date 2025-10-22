#!/usr/bin/env python3
"""
Local telemetry testing script.
Tests both traces and metrics against OpenTelemetry Collector.

Usage:
    python test_telemetry_local.py                           # Test production
    python test_telemetry_local.py http://localhost:4318     # Test local collector
"""

import json
import sys
import time
import uuid
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


class TelemetryTester:
    def __init__(self, endpoint="https://telemetry.namastex.ai"):
        self.endpoint = endpoint.rstrip('/')

    def test_trace(self):
        """Test sending a trace."""
        trace_id = uuid.uuid4().hex[:32]
        span_id = uuid.uuid4().hex[:16]

        timestamp_now = int(time.time() * 1_000_000_000)

        payload = {
            "resourceSpans": [{
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "telemetry-tester"}},
                        {"key": "service.version", "value": {"stringValue": "1.0.0"}},
                        {"key": "service.namespace", "value": {"stringValue": "namastex"}},
                        {"key": "telemetry.sdk.name", "value": {"stringValue": "python-test"}},
                        {"key": "telemetry.sdk.version", "value": {"stringValue": "1.0.0"}}
                    ]
                },
                "scopeSpans": [{
                    "scope": {
                        "name": "telemetry-tester.tracer",
                        "version": "1.0.0"
                    },
                    "spans": [{
                        "traceId": trace_id,
                        "spanId": span_id,
                        "name": "test.operation",
                        "kind": "SPAN_KIND_INTERNAL",
                        "startTimeUnixNano": str(timestamp_now),
                        "endTimeUnixNano": str(timestamp_now + 100_000_000),
                        "attributes": [
                            {"key": "test.type", "value": {"stringValue": "development"}},
                            {"key": "test.timestamp", "value": {"stringValue": time.strftime("%Y-%m-%d %H:%M:%S")}},
                            {"key": "test.trace_id", "value": {"stringValue": trace_id}}
                        ],
                        "status": {"code": "STATUS_CODE_OK"}
                    }]
                }]
            }]
        }

        return self._send_otlp("/v1/traces", payload)

    def test_counter_metric(self):
        """Test sending a counter metric."""
        timestamp_now = int(time.time() * 1_000_000_000)

        payload = {
            "resourceMetrics": [{
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "telemetry-tester"}},
                        {"key": "service.version", "value": {"stringValue": "1.0.0"}},
                        {"key": "service.namespace", "value": {"stringValue": "namastex"}},
                        {"key": "telemetry.sdk.name", "value": {"stringValue": "python-test"}},
                        {"key": "telemetry.sdk.version", "value": {"stringValue": "1.0.0"}}
                    ]
                },
                "scopeMetrics": [{
                    "scope": {
                        "name": "telemetry-tester.meter",
                        "version": "1.0.0"
                    },
                    "metrics": [{
                        "name": "test_api_requests_total",
                        "description": "Total test API requests",
                        "unit": "1",
                        "sum": {
                            "dataPoints": [{
                                "attributes": [
                                    {"key": "endpoint", "value": {"stringValue": "/api/v1/test"}},
                                    {"key": "method", "value": {"stringValue": "POST"}},
                                    {"key": "status", "value": {"stringValue": "200"}}
                                ],
                                "startTimeUnixNano": str(timestamp_now),
                                "timeUnixNano": str(timestamp_now),
                                "asInt": "42"
                            }],
                            "aggregationTemporality": "AGGREGATION_TEMPORALITY_CUMULATIVE",
                            "isMonotonic": True
                        }
                    }]
                }]
            }]
        }

        return self._send_otlp("/v1/metrics", payload)

    def test_gauge_metric(self):
        """Test sending a gauge metric."""
        timestamp_now = int(time.time() * 1_000_000_000)

        payload = {
            "resourceMetrics": [{
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "telemetry-tester"}},
                        {"key": "service.version", "value": {"stringValue": "1.0.0"}},
                        {"key": "service.namespace", "value": {"stringValue": "namastex"}},
                        {"key": "telemetry.sdk.name", "value": {"stringValue": "python-test"}},
                        {"key": "telemetry.sdk.version", "value": {"stringValue": "1.0.0"}}
                    ]
                },
                "scopeMetrics": [{
                    "scope": {
                        "name": "telemetry-tester.meter",
                        "version": "1.0.0"
                    },
                    "metrics": [{
                        "name": "test_memory_usage_mb",
                        "description": "Test memory usage in megabytes",
                        "unit": "MB",
                        "gauge": {
                            "dataPoints": [{
                                "attributes": [
                                    {"key": "host", "value": {"stringValue": "test-host"}},
                                    {"key": "process", "value": {"stringValue": "python"}}
                                ],
                                "timeUnixNano": str(timestamp_now),
                                "asDouble": 512.75
                            }]
                        }
                    }]
                }]
            }]
        }

        return self._send_otlp("/v1/metrics", payload)

    def test_histogram_metric(self):
        """Test sending a histogram metric."""
        timestamp_now = int(time.time() * 1_000_000_000)

        payload = {
            "resourceMetrics": [{
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "telemetry-tester"}},
                        {"key": "service.version", "value": {"stringValue": "1.0.0"}},
                        {"key": "service.namespace", "value": {"stringValue": "namastex"}},
                        {"key": "telemetry.sdk.name", "value": {"stringValue": "python-test"}},
                        {"key": "telemetry.sdk.version", "value": {"stringValue": "1.0.0"}}
                    ]
                },
                "scopeMetrics": [{
                    "scope": {
                        "name": "telemetry-tester.meter",
                        "version": "1.0.0"
                    },
                    "metrics": [{
                        "name": "test_response_time_ms",
                        "description": "Test API response time distribution",
                        "unit": "ms",
                        "histogram": {
                            "dataPoints": [{
                                "attributes": [
                                    {"key": "endpoint", "value": {"stringValue": "/api/v1/test"}},
                                    {"key": "method", "value": {"stringValue": "GET"}}
                                ],
                                "startTimeUnixNano": str(timestamp_now - 60_000_000_000),
                                "timeUnixNano": str(timestamp_now),
                                "count": "100",
                                "sum": 15432.5,
                                "bucketCounts": ["10", "25", "40", "20", "5"],
                                "explicitBounds": [50.0, 100.0, 200.0, 500.0, 1000.0]
                            }],
                            "aggregationTemporality": "AGGREGATION_TEMPORALITY_CUMULATIVE"
                        }
                    }]
                }]
            }]
        }

        return self._send_otlp("/v1/metrics", payload)

    def _send_otlp(self, path, payload):
        """Send OTLP payload."""
        url = f"{self.endpoint}{path}"
        data = json.dumps(payload).encode('utf-8')

        request = Request(
            url,
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )

        try:
            with urlopen(request, timeout=10) as response:
                status = response.status
                body = response.read().decode('utf-8')
                return {
                    'success': True,
                    'status': status,
                    'body': body or '(empty response)'
                }
        except HTTPError as e:
            return {
                'success': False,
                'status': e.code,
                'error': e.read().decode('utf-8')
            }
        except URLError as e:
            return {
                'success': False,
                'error': str(e.reason)
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


def main():
    endpoint = sys.argv[1] if len(sys.argv) > 1 else "https://telemetry.namastex.ai"

    print("🧪 OpenTelemetry Endpoint Tester")
    print("=" * 60)
    print(f"📡 Testing endpoint: {endpoint}")
    print("=" * 60)

    tester = TelemetryTester(endpoint)

    tests = [
        ("Trace", tester.test_trace),
        ("Counter Metric", tester.test_counter_metric),
        ("Gauge Metric", tester.test_gauge_metric),
        ("Histogram Metric", tester.test_histogram_metric),
    ]

    results = []

    for i, (name, test_func) in enumerate(tests, 1):
        print(f"\n{i}️⃣  Testing {name}...")
        result = test_func()

        if result['success']:
            print(f"   ✅ {name} sent successfully (HTTP {result['status']})")
            if result.get('body') and result['body'] != '(empty response)':
                print(f"   📄 Response: {result['body'][:100]}")
        else:
            error_msg = result.get('error', 'Unknown error')
            status = result.get('status', 'N/A')
            print(f"   ❌ {name} failed (HTTP {status}): {error_msg}")

        results.append((name, result['success']))
        time.sleep(0.5)  # Small delay between tests

    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    print("=" * 60)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {status}  {name}")

    print("-" * 60)
    print(f"   Results: {passed}/{total} tests passed")

    if passed == total:
        print("   🎉 All tests passed!")
    elif passed > 0:
        print("   ⚠️  Some tests failed")
    else:
        print("   ❌ All tests failed")

    print("\n" + "=" * 60)
    print("💡 Next Steps:")
    print("=" * 60)
    print("1. Check collector logs:")
    print("   ssh root@dl380-g10")
    print("   pct exec 155 -- journalctl -u otelcol-contrib -n 50 --no-pager")
    print()
    print("2. Query Prometheus (after ~30s):")
    print("   curl -s 'http://192.168.112.122:9090/api/v1/label/__name__/values' | jq")
    print()
    print("3. Search for your test metrics:")
    print('   curl -s "http://192.168.112.122:9090/api/v1/query?query=test_api_requests_total" | jq')
    print("=" * 60)

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
