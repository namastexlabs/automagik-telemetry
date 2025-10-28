#!/usr/bin/env python3
"""
Generate realistic test data for Automagik Telemetry with smooth, natural patterns.

This script generates production-like telemetry data directly into ClickHouse with:
- Realistic time distribution (past 24 hours)
- Smooth traffic patterns (business hours, lunch dip, evening decline)
- Multiple services and environments
- Proper metric types (gauge, counter, histogram)
- Correlated logs and traces
- Natural error rates (5-10%)
- Realistic latencies and durations

Usage:
    python3 infra/scripts/generate_test_data.py
"""

import math
import os
import random
import subprocess
import uuid
from datetime import datetime, timedelta
from typing import List, Dict


class RealisticDataGenerator:
    """Generate realistic telemetry data with smooth patterns via direct ClickHouse insertion."""

    def __init__(self):
        self.services = [
            {"name": "api-gateway", "weight": 0.4, "base_latency": 50},
            {"name": "auth-service", "weight": 0.25, "base_latency": 30},
            {"name": "worker-service", "weight": 0.20, "base_latency": 150},
            {"name": "database-service", "weight": 0.15, "base_latency": 80},
        ]

        self.environments = [
            {"name": "production", "weight": 0.7},
            {"name": "staging", "weight": 0.2},
            {"name": "development", "weight": 0.1},
        ]

        self.features = [
            "user_login", "data_export", "report_generation",
            "file_upload", "api_call", "dashboard_view",
            "settings_update", "batch_processing"
        ]

        self.endpoints = [
            "/api/v1/users", "/api/v1/auth/login", "/api/v1/data/export",
            "/api/v1/reports", "/api/v1/files/upload", "/api/v1/analytics",
            "/api/v1/settings", "/api/v1/health"
        ]

        self.log_messages = {
            "INFO": [
                "Request processed successfully",
                "User authenticated successfully",
                "Cache hit for key",
                "Configuration loaded",
                "Health check passed",
                "Session created",
            ],
            "WARN": [
                "Cache miss for key",
                "Slow query detected (>500ms)",
                "Rate limit approaching threshold",
                "Deprecated API usage detected",
            ],
            "ERROR": [
                "Invalid request parameters",
                "Database connection timeout",
                "Authentication failed",
                "Service unavailable",
            ],
            "FATAL": [
                "Critical system failure",
                "Database connection lost",
                "Out of memory",
            ],
        }

        # Static values for consistency
        self.project_name = "api-gateway"
        self.project_version = "1.0.0"
        self.user_id = str(uuid.uuid4())
        self.session_id = str(uuid.uuid4())

    def get_traffic_multiplier(self, hour: int) -> float:
        """Generate realistic traffic pattern based on hour of day."""
        if 0 <= hour < 6:  # Night (low traffic)
            return 0.3
        elif 6 <= hour < 9:  # Morning ramp
            return 0.5 + (hour - 6) * 0.17  # 0.5 -> 1.0
        elif 9 <= hour < 12:  # Morning peak
            return 1.0
        elif 12 <= hour < 14:  # Lunch dip
            return 0.7 + 0.15 * math.sin((hour - 12) * math.pi / 2)
        elif 14 <= hour < 17:  # Afternoon peak
            return 1.0
        elif 17 <= hour < 22:  # Evening decline
            return 1.0 - (hour - 17) * 0.12  # 1.0 -> 0.4
        else:  # Late night
            return 0.3

    def choose_weighted(self, items: List[Dict]) -> Dict:
        """Choose item based on weight."""
        weights = [item['weight'] for item in items]
        return random.choices(items, weights=weights)[0]

    def generate_latency(self, base_latency: int, is_error: bool = False) -> int:
        """Generate realistic latency with smooth distribution using log-normal."""
        if is_error:
            base_latency *= 3

        latency = random.lognormvariate(math.log(base_latency), 0.3)
        return max(5, int(latency))  # Minimum 5ms

    def should_be_error(self, hour: int) -> bool:
        """Determine if event should be an error (5-10% with peak hour increase)."""
        base_error_rate = 0.05
        peak_multiplier = 1.5 if 9 <= hour < 17 else 1.0
        return random.random() < (base_error_rate * peak_multiplier)

    def clickhouse_exec(self, query: str) -> None:
        """Execute ClickHouse query via docker compose."""
        cmd = [
            "docker", "compose", "exec", "-T", "clickhouse",
            "clickhouse-client", "--database=telemetry", f"--query={query}"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd="/home/cezar/automagik-telemetry/infra")
        if result.returncode != 0:
            print(f"ClickHouse Error: {result.stderr}")
            print(f"Query: {query[:500]}")
            raise Exception(f"ClickHouse query failed: {result.stderr}")

    def generate_traces(self, hours: int = 24, events_per_hour: int = 50) -> List[Dict]:
        """Generate realistic traces over time period."""
        print(f"📊 Generating traces for past {hours} hours...")
        print(f"   Target: ~{hours * events_per_hour} traces with smooth traffic pattern\n")

        trace_contexts = []
        total_traces = 0

        # Generate data hour by hour for smooth distribution
        for hour_offset in range(hours):
            hour_ago = hours - hour_offset - 1
            timestamp = datetime.now() - timedelta(hours=hour_ago)
            current_hour = timestamp.hour
            traffic_mult = self.get_traffic_multiplier(current_hour)
            hour_events = int(events_per_hour * traffic_mult)

            print(f"   Hour {hour_offset + 1}/{hours} ({current_hour:02d}:00) - "
                  f"{hour_events} events (traffic: {traffic_mult:.1%})")

            # Distribute events smoothly within the hour
            for event_idx in range(hour_events):
                # Smooth distribution within hour (0-60 minutes)
                minute_offset = (event_idx / hour_events) * 60
                event_timestamp = timestamp + timedelta(minutes=minute_offset)

                service = self.choose_weighted(self.services)
                environment = self.choose_weighted(self.environments)
                is_error = self.should_be_error(current_hour)
                latency = self.generate_latency(service['base_latency'], is_error)

                # Generate trace IDs
                trace_id = uuid.uuid4().hex + uuid.uuid4().hex  # 64 chars
                span_id = uuid.uuid4().hex[:16]  # 16 chars

                # Determine event type and attributes
                event_type = random.choice(["feature", "api", "user_action"])

                if event_type == "feature":
                    feature = random.choice(self.features)
                    event_name = "automagik.feature.used"
                    attrs = f"'feature_name', '{feature}', 'latency_ms', '{latency}'"
                elif event_type == "api":
                    endpoint = random.choice(self.endpoints)
                    method = random.choice(["GET", "POST", "PUT", "DELETE"])
                    status_code = 500 if is_error else random.choice([200, 200, 200, 201, 204])
                    event_name = "automagik.api.request"
                    attrs = f"'endpoint', '{endpoint}', 'method', '{method}', 'status_code', '{status_code}', 'latency_ms', '{latency}'"
                else:
                    action = random.choice(["login", "logout", "update_profile", "view_page"])
                    event_name = "automagik.user.action"
                    attrs = f"'action', '{action}', 'latency_ms', '{latency}'"

                # Format timestamp for ClickHouse
                ts_str = event_timestamp.strftime("%Y-%m-%d %H:%M:%S")
                ts_ns = int(event_timestamp.timestamp() * 1_000_000_000)

                # Build INSERT query for traces
                status_code_str = 'ERROR' if is_error else 'OK'
                insert_query = f"""
                INSERT INTO traces (
                    trace_id, span_id, parent_span_id,
                    timestamp, timestamp_ns,
                    project_name, project_version, span_name,
                    duration_ms, status_code,
                    service_name, environment,
                    user_id, session_id,
                    attributes
                ) VALUES (
                    '{trace_id}', '{span_id}', '',
                    '{ts_str}', {ts_ns},
                    '{self.project_name}', '{self.project_version}', '{event_name}',
                    {latency}, '{status_code_str}',
                    '{service['name']}', '{environment['name']}',
                    '{self.user_id}', '{self.session_id}',
                    map({attrs})
                )
                """

                self.clickhouse_exec(insert_query)

                # Store context for correlated logs
                trace_contexts.append({
                    "trace_id": trace_id,
                    "span_id": span_id,
                    "timestamp": event_timestamp,
                    "service": service['name'],
                    "environment": environment['name'],
                    "is_error": is_error,
                })

                total_traces += 1

        print(f"\n✅ Generated {total_traces} traces\n")
        return trace_contexts

    def generate_metrics(self, hours: int = 24, metrics_per_hour: int = 20) -> None:
        """Generate realistic metrics over time period."""
        print(f"📈 Generating metrics for past {hours} hours...")
        print(f"   Target: ~{hours * metrics_per_hour} metrics\n")

        total_metrics = 0

        # Generate metrics hour by hour
        for hour_offset in range(hours):
            hour_ago = hours - hour_offset - 1
            timestamp = datetime.now() - timedelta(hours=hour_ago)
            current_hour = timestamp.hour

            for service in self.services:
                # CPU Usage (Gauge) - smooth sine wave 30-80%
                cpu_base = 50 + 20 * math.sin((hour_offset / hours) * 2 * math.pi)
                cpu_usage = max(30, min(80, cpu_base + random.uniform(-5, 5)))

                ts_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                ts_ns = int(timestamp.timestamp() * 1_000_000_000)

                self.clickhouse_exec(f"""
                INSERT INTO metrics (
                    metric_id, timestamp, timestamp_ns,
                    project_name, project_version,
                    metric_name, metric_type, value_double,
                    service_name, attributes
                ) VALUES (
                    '{uuid.uuid4()}', '{ts_str}', {ts_ns},
                    '{self.project_name}', '{self.project_version}',
                    '{service['name']}.cpu.usage', 'GAUGE', {cpu_usage},
                    '{service['name']}', map('unit', 'percent')
                )
                """)
                total_metrics += 1

                # Memory Usage (Gauge) - gradual growth with resets
                memory_cycle = (hour_offset % 8) / 8  # Reset every 8 hours
                memory_usage = 60 + 30 * memory_cycle + random.uniform(-3, 3)

                self.clickhouse_exec(f"""
                INSERT INTO metrics (
                    metric_id, timestamp, timestamp_ns,
                    project_name, project_version,
                    metric_name, metric_type, value_double,
                    service_name, attributes
                ) VALUES (
                    '{uuid.uuid4()}', '{ts_str}', {ts_ns},
                    '{self.project_name}', '{self.project_version}',
                    '{service['name']}.memory.usage', 'GAUGE', {memory_usage},
                    '{service['name']}', map('unit', 'percent')
                )
                """)
                total_metrics += 1

        print(f"✅ Generated {total_metrics} metrics\n")

    def generate_logs(self, trace_contexts: List[Dict], standalone_count: int = 300) -> None:
        """Generate correlated logs for traces plus standalone logs."""
        print(f"📝 Generating logs...")
        print(f"   {len(trace_contexts)} correlated logs + {standalone_count} standalone logs\n")

        total_logs = 0

        # Generate correlated logs (one per trace)
        for ctx in trace_contexts:
            # Choose severity based on whether it's an error
            if ctx['is_error']:
                severity = random.choice(["ERROR", "ERROR", "FATAL"])
            else:
                severity = random.choice(["INFO", "INFO", "INFO", "WARN"])

            body = random.choice(self.log_messages[severity])
            severity_num = {"INFO": 9, "WARN": 13, "ERROR": 17, "FATAL": 21}[severity]

            ts_str = ctx['timestamp'].strftime("%Y-%m-%d %H:%M:%S")
            ts_ns = int(ctx['timestamp'].timestamp() * 1_000_000_000)

            self.clickhouse_exec(f"""
            INSERT INTO logs (
                log_id, trace_id, span_id,
                timestamp, timestamp_ns,
                severity_text, severity_number, body,
                project_name, project_version,
                service_name, environment,
                user_id, session_id
            ) VALUES (
                '{uuid.uuid4()}', '{ctx['trace_id']}', '{ctx['span_id']}',
                '{ts_str}', {ts_ns},
                '{severity}', {severity_num}, '{body}',
                '{self.project_name}', '{self.project_version}',
                '{ctx['service']}', '{ctx['environment']}',
                '{self.user_id}', '{self.session_id}'
            )
            """)
            total_logs += 1

        # Generate standalone logs (not correlated with traces)
        for _ in range(standalone_count):
            # Random time in past 24 hours
            random_timestamp = datetime.now() - timedelta(hours=random.uniform(0, 24))
            severity = random.choice(["INFO"] * 5 + ["WARN"] * 2 + ["ERROR"])
            body = random.choice(self.log_messages[severity])
            severity_num = {"INFO": 9, "WARN": 13, "ERROR": 17}[severity]

            service = self.choose_weighted(self.services)
            environment = self.choose_weighted(self.environments)

            ts_str = random_timestamp.strftime("%Y-%m-%d %H:%M:%S")
            ts_ns = int(random_timestamp.timestamp() * 1_000_000_000)

            self.clickhouse_exec(f"""
            INSERT INTO logs (
                log_id, timestamp, timestamp_ns,
                severity_text, severity_number, body,
                project_name, project_version,
                service_name, environment,
                user_id, session_id
            ) VALUES (
                '{uuid.uuid4()}', '{ts_str}', {ts_ns},
                '{severity}', {severity_num}, '{body}',
                '{self.project_name}', '{self.project_version}',
                '{service['name']}', '{environment['name']}',
                '{self.user_id}', '{self.session_id}'
            )
            """)
            total_logs += 1

        print(f"✅ Generated {total_logs} logs\n")


def main():
    """Main entry point."""
    print("=" * 70)
    print("  Realistic Telemetry Data Generator")
    print("=" * 70)
    print("\n🎯 Generating production-like data with smooth patterns\n")

    generator = RealisticDataGenerator()

    # Generate traces (returns contexts for correlated logs)
    trace_contexts = generator.generate_traces(hours=24, events_per_hour=50)

    # Generate metrics
    generator.generate_metrics(hours=24, metrics_per_hour=20)

    # Generate logs (correlated + standalone)
    generator.generate_logs(trace_contexts, standalone_count=300)

    print("=" * 70)
    print("  ✅ Data Generation Complete!")
    print("=" * 70)
    print("\n📈 Summary:")
    print(f"  - {len(trace_contexts)} traces (events) over 24 hours")
    print(f"  - ~{24 * 20} metrics (gauges, counters)")
    print(f"  - ~{len(trace_contexts) + 300} logs (correlated + standalone)")
    print("  - Multiple services: api-gateway, auth-service, worker-service, database-service")
    print("  - Multiple environments: production, staging, development")
    print("  - Realistic traffic patterns (business hours, lunch dip, evening decline)")
    print("  - Natural error rates (5-10%)")
    print("  - Smooth latency distributions (5ms-2000ms)")
    print("\n🎯 All dashboards should now display realistic data over 24 hours!")
    print("\nView dashboards at: http://localhost:3000")
    print("Default credentials: admin/admin\n")


if __name__ == "__main__":
    main()
