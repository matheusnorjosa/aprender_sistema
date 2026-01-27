# Redis Exporter Healthcheck Analysis

## Current Status (2025-11-25)

**Decision**: Healthcheck removed from `redis_exporter` service in docker-compose.yml.

**Reason**: Image `oliver006/redis_exporter:v1.62.0` is scratch-based (no shell, no utilities).

## Alternatives Considered

### Option 1: Remove Healthcheck (CHOSEN ✅)

**Implementation**: Already applied in PR #204

```yaml
redis_exporter:
  image: oliver006/redis_exporter:v1.62.0
  # ...
  # Note: Healthcheck removed - scratch-based image has no shell/wget.
  # Service health monitored by Prometheus scrape (http://localhost:9121/metrics)
```

**Pros**:
- ✅ No false "unhealthy" status
- ✅ Prometheus already monitors exporter health via scrape
- ✅ Simpler configuration

**Cons**:
- ⚠️ Docker Compose doesn't report health status

**Monitoring**: Prometheus scrape success/failure indicates health.

### Option 2: Use Alpine-based Image

**Implementation**:
```yaml
redis_exporter:
  image: oliver006/redis_exporter:alpine  # If available
  healthcheck:
    test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:9121/metrics"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 10s
```

**Pros**:
- ✅ Would have shell/wget for healthcheck

**Cons**:
- ❌ No official alpine-based image for redis_exporter
- ❌ Larger image size
- ❌ Unnecessary complexity

**Status**: Not recommended (no official alpine variant)

### Option 3: Custom Healthcheck with curl/wget Container

**Implementation**:
```yaml
redis_exporter:
  image: oliver006/redis_exporter:v1.62.0
  healthcheck:
    test: ["CMD-SHELL", "timeout 5 nc -z localhost 9121"]
    interval: 30s
    timeout: 10s
    retries: 3
```

**Pros**:
- ✅ Would check if port is listening

**Cons**:
- ❌ `nc` (netcat) also not available in scratch image
- ❌ Only checks TCP, not actual HTTP endpoint

**Status**: Not feasible (scratch image has no utilities)

### Option 4: Sidecar Container for Healthcheck

**Implementation**:
```yaml
redis_exporter_healthcheck:
  image: busybox:latest
  depends_on:
    - redis_exporter
  command: |
    sh -c 'while true; do
      wget -q --spider http://redis_exporter:9121/metrics || exit 1;
      sleep 30;
    done'
  restart: unless-stopped
```

**Pros**:
- ✅ Would provide health monitoring

**Cons**:
- ❌ Adds unnecessary container
- ❌ Overly complex for simple monitoring
- ❌ Prometheus already does this job

**Status**: Not recommended (unnecessary complexity)

### Option 5: Docker Compose Depends_on with Healthcheck in Prometheus

**Implementation**:
```yaml
prometheus:
  # ...
  healthcheck:
    test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://redis_exporter:9121/metrics"]
    interval: 30s
    timeout: 10s
    retries: 3
  depends_on:
    redis_exporter:
      condition: service_started  # Not service_healthy

redis_exporter:
  # No healthcheck needed
```

**Pros**:
- ✅ Prometheus validates exporter availability during startup

**Cons**:
- ❌ Couples Prometheus healthcheck with redis_exporter availability
- ❌ Prometheus image may not have wget either

**Status**: Not recommended (tight coupling)

## Monitoring Strategy (CHOSEN)

### Prometheus Scrape Monitoring

**How it works**:
1. Prometheus scrapes `http://redis_exporter:9121/metrics` every 15-30s
2. If scrape fails, Prometheus marks target as DOWN
3. Grafana dashboards show target availability

**Query to check exporter health**:
```promql
up{job="redis_exporter"}
```

**Alert rule example**:
```yaml
groups:
  - name: redis_exporter
    rules:
      - alert: RedisExporterDown
        expr: up{job="redis_exporter"} == 0
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Redis Exporter is down"
          description: "Redis Exporter has been down for more than 2 minutes"
```

### Manual Health Verification

```bash
# Check if exporter is running
docker compose ps redis_exporter
# Expected: Up (not unhealthy)

# Check if metrics endpoint responds
curl http://localhost:9121/metrics
# Expected: HTTP 200 with Prometheus metrics

# Check specific metric
curl -s http://localhost:9121/metrics | grep redis_up
# Expected: redis_up 1
```

## Conclusion

**Best approach**: Remove Docker healthcheck, rely on Prometheus scrape monitoring.

**Rationale**:
- Prometheus is the proper monitoring tool for this use case
- Docker healthcheck with scratch image is impossible without workarounds
- Adding complexity (sidecar, alpine image) provides minimal benefit
- Current solution is industry-standard for Prometheus exporters

## References

- Issue identified: Audit 2025-11-25
- Solution applied: PR #204 (d40f968)
- Image documentation: https://hub.docker.com/r/oliver006/redis_exporter
- Scratch image limitations: https://docs.docker.com/develop/develop-images/baseimages/#create-a-simple-parent-image-using-scratch

## Related Documentation

- `v2/infra/docker-compose.yml` - Redis exporter configuration
- `v2/infra/prometheus.yml` - Prometheus scrape config
- `v2/docs/OBSERVABILITY.md` - MP1 monitoring setup
