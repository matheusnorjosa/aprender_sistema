# 🔧 Troubleshooting Guide - Sistema Aprender

This comprehensive troubleshooting guide helps diagnose and resolve common issues in the Sistema Aprender application.

## 🚨 Emergency Response

### System Down - Complete Outage
```bash
# 1. Quick health check
curl -f http://localhost:8000/health/ || echo "System completely down"

# 2. Check all services
make system-status

# 3. Review recent changes
git log --oneline -10

# 4. Check system resources
make resource-check

# 5. Emergency restart
make emergency-restart
```

### Critical Performance Degradation
```bash
# 1. Check system load
top
htop

# 2. Check database connections
python manage.py dbshell -c "\l"

# 3. Check memory usage
free -h
ps aux --sort=-%mem | head

# 4. Check disk space
df -h
```

### Data Corruption Detected
```bash
# 1. STOP all write operations immediately
make stop-all-writes

# 2. Create emergency backup
make emergency-backup

# 3. Assess damage
make data-integrity-check

# 4. Contact database administrator
echo "Critical: Data corruption detected" | mail -s "CRITICAL ALERT" dba@yourdomain.com
```

---

## 🔍 Diagnostic Tools

### Health Check Commands
```bash
# Comprehensive system health
python manage.py health_check --verbose

# Database connectivity
python manage.py health_check --check-db

# Cache connectivity
python manage.py health_check --check-cache

# External services
python manage.py health_check --check-external

# Generate health report
python manage.py health_check --format=json > health_report.json
```

### System Monitoring
```bash
# Real-time system stats
make system-monitor

# Database performance
make db-performance-stats

# Application metrics
make app-metrics

# Network connectivity
make network-diagnostics
```

### Log Analysis
```bash
# View recent application logs
make logs-recent

# Search for errors
make logs-errors

# Filter by timestamp
make logs-since timestamp="2025-09-11 10:00:00"

# Export logs for analysis
make export-logs
```

---

## 🐛 Common Issues & Solutions

### 1. Application Won't Start

#### Symptoms
- Server fails to start
- Port binding errors
- Import errors
- Configuration errors

#### Diagnosis
```bash
# Check Python environment
python --version
which python

# Verify virtual environment
echo $VIRTUAL_ENV

# Check dependencies
pip check

# Validate settings
python manage.py check

# Check for syntax errors
python -m py_compile manage.py
```

#### Solutions

**Port Already in Use**
```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use different port
python manage.py runserver 8001
```

**Missing Dependencies**
```bash
# Install requirements
pip install -r requirements.txt

# Check for conflicting versions
pip list --outdated

# Clean install
pip uninstall -y -r requirements.txt
pip install -r requirements.txt
```

**Environment Variables**
```bash
# Check environment variables
env | grep DJANGO

# Validate .env file
make validate-env

# Load environment manually
source .env
export $(grep -v '^#' .env | xargs)
```

### 2. Database Connection Issues

#### Symptoms
- "Connection refused" errors
- Timeout errors
- "Too many connections" errors
- Authentication failures

#### Diagnosis
```bash
# Test database connection
python manage.py dbshell

# Check PostgreSQL status
sudo systemctl status postgresql

# Check connection limits
psql -c "SELECT * FROM pg_stat_activity;"

# Verify credentials
psql -h localhost -U postgres -d aprender_sistema
```

#### Solutions

**PostgreSQL Not Running**
```bash
# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Check logs
sudo journalctl -u postgresql -f
```

**Connection Pool Exhausted**
```bash
# Check active connections
python manage.py shell -c "
from django.db import connections
print(len(connections.all()))
"

# Reset connection pool
make reset-db-connections

# Increase connection limits in settings
# DATABASES['default']['OPTIONS']['MAX_CONNS'] = 50
```

**Authentication Issues**
```bash
# Verify pg_hba.conf
sudo cat /etc/postgresql/15/main/pg_hba.conf

# Reset PostgreSQL password
sudo -u postgres psql
postgres=# ALTER USER postgres PASSWORD 'newpassword';

# Update .env file with new credentials
```

### 3. Performance Issues

#### Symptoms
- Slow page loading
- High CPU/memory usage
- Database query timeouts
- Unresponsive interface

#### Diagnosis
```bash
# Check system resources
htop
iotop

# Profile Django application
python manage.py runserver --profile

# Analyze slow queries
python manage.py slow_queries --limit 10

# Check database locks
psql -c "SELECT * FROM pg_locks WHERE NOT granted;"
```

#### Solutions

**High Database Load**
```bash
# Analyze query performance
python manage.py shell
>>> from django.db import connection
>>> print(connection.queries)

# Add database indexes
python manage.py dbshell
postgres=# CREATE INDEX CONCURRENTLY idx_solicitation_status ON core_solicitacao(status);

# Optimize queries with select_related/prefetch_related
# Review models and views for N+1 query issues
```

**Memory Issues**
```bash
# Check Django memory usage
python manage.py shell -c "
import psutil
process = psutil.Process()
print(f'Memory: {process.memory_info().rss / 1024 / 1024:.2f} MB')
"

# Clear Django cache
python manage.py clear_cache

# Restart with memory limit
ulimit -v 2097152  # 2GB limit
python manage.py runserver
```

**High CPU Usage**
```bash
# Profile CPU usage
python -m cProfile manage.py runserver

# Check for infinite loops or heavy computation
# Review recent code changes
git diff HEAD~5 --stat
```

### 4. Authentication & Permission Issues

#### Symptoms
- Users can't login
- Permission denied errors
- Session expired frequently
- OAuth failures

#### Diagnosis
```bash
# Check user status
python manage.py shell -c "
from django.contrib.auth.models import User
print(User.objects.filter(is_active=True).count())
"

# Verify groups and permissions
python manage.py shell -c "
from django.contrib.auth.models import Group
for group in Group.objects.all():
    print(f'{group.name}: {group.permissions.count()} permissions')
"

# Check session configuration
python manage.py check --tag=sessions
```

#### Solutions

**User Authentication Issues**
```bash
# Reset user password
python manage.py changepassword username

# Check user status
python manage.py shell -c "
user = User.objects.get(username='testuser')
print(f'Active: {user.is_active}, Staff: {user.is_staff}')
"

# Clear sessions
python manage.py clearsessions
```

**Permission Problems**
```bash
# Recreate permissions
python manage.py migrate --run-syncdb

# Check group assignments
python manage.py shell -c "
from django.contrib.auth.models import User, Group
user = User.objects.get(username='testuser')
print([g.name for g in user.groups.all()])
"

# Assign user to correct groups
python manage.py assign_user_groups
```

### 5. Google Calendar Integration Issues

#### Symptoms
- Events not syncing
- OAuth authentication failures
- API quota exceeded
- Permission errors

#### Diagnosis
```bash
# Test Google API credentials
python manage.py test_google_api

# Check OAuth token status
python manage.py shell -c "
from core.services.google_calendar import GoogleCalendarService
service = GoogleCalendarService()
print(service.test_connection())
"

# Verify API quotas
# Check Google Cloud Console for quota usage
```

#### Solutions

**OAuth Token Expired**
```bash
# Refresh OAuth tokens
python manage.py refresh_google_tokens

# Re-authenticate
python manage.py setup_google_oauth

# Update credentials in .env
```

**API Quota Exceeded**
```bash
# Check current quota usage
python manage.py google_quota_status

# Implement rate limiting
# Add delays between API calls
# Consider caching strategies
```

### 6. Static Files & Media Issues

#### Symptoms
- CSS/JS not loading
- Images not displaying
- 404 errors for static files
- Broken admin interface styling

#### Diagnosis
```bash
# Check static files configuration
python manage.py check --tag=staticfiles

# Verify STATIC_ROOT and STATIC_URL
python manage.py shell -c "
from django.conf import settings
print(f'STATIC_ROOT: {settings.STATIC_ROOT}')
print(f'STATIC_URL: {settings.STATIC_URL}')
"

# Test static file serving
curl -I http://localhost:8000/static/admin/css/base.css
```

#### Solutions

**Missing Static Files**
```bash
# Collect static files
python manage.py collectstatic --noinput

# Clear static files cache
rm -rf staticfiles/*
python manage.py collectstatic --clear

# Check permissions
ls -la staticfiles/
```

**Development vs Production Settings**
```bash
# For development
# Ensure DEBUG = True
# Add 'django.contrib.staticfiles' to INSTALLED_APPS

# For production
# Configure web server to serve static files
# Set proper STATIC_ROOT path
```

---

## 📊 Performance Monitoring

### Key Metrics to Monitor

#### System Metrics
- **CPU Usage**: Target < 70% average
- **Memory Usage**: Target < 80% of available RAM
- **Disk Usage**: Target < 85% of available space
- **Network I/O**: Monitor for unusual spikes

#### Application Metrics
- **Response Time**: Target < 500ms for 95% of requests
- **Error Rate**: Target < 0.1% of all requests
- **Database Connections**: Monitor pool utilization
- **Cache Hit Rate**: Target > 80% for Redis cache

#### Database Metrics
- **Query Performance**: Identify slow queries (>100ms)
- **Connection Count**: Monitor active connections
- **Lock Waits**: Identify blocking queries
- **Index Usage**: Ensure proper index utilization

### Performance Monitoring Tools
```bash
# Real-time monitoring
make monitor-performance

# Generate performance report
make performance-report

# Database performance analysis
make analyze-db-performance

# Application profiling
make profile-application
```

---

## 🔧 Advanced Troubleshooting

### Database Issues

#### Deadlock Detection
```sql
-- Check for deadlocks
SELECT 
    blocked_locks.pid AS blocked_pid,
    blocked_activity.usename AS blocked_user,
    blocking_locks.pid AS blocking_pid,
    blocking_activity.usename AS blocking_user,
    blocked_activity.query AS blocked_statement,
    blocking_activity.query AS current_statement_in_blocking_process
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;
```

#### Index Analysis
```sql
-- Check for unused indexes
SELECT 
    schemaname, 
    tablename, 
    indexname, 
    idx_scan 
FROM pg_stat_user_indexes 
WHERE idx_scan = 0;

-- Check for duplicate indexes
SELECT 
    pg_size_pretty(sum(pg_relation_size(idx))::bigint) as size,
    (array_agg(idx))[1] as idx1, 
    (array_agg(idx))[2] as idx2
FROM (
    SELECT indexrelid::regclass as idx, (indrelid::text ||E'\n'|| indclass::text ||E'\n'|| indkey::text ||E'\n'|| coalesce(indexprs::text,'')||E'\n' || coalesce(indpred::text,'')) as KEY 
    FROM pg_index
) sub 
GROUP BY KEY HAVING count(*)>1
ORDER BY sum(pg_relation_size(idx)) DESC;
```

### Memory Analysis

#### Django Memory Profiling
```python
# Add to views for memory debugging
import tracemalloc

def debug_view(request):
    tracemalloc.start()
    
    # Your view logic here
    
    current, peak = tracemalloc.get_traced_memory()
    print(f"Current memory usage: {current / 1024 / 1024:.2f} MB")
    print(f"Peak memory usage: {peak / 1024 / 1024:.2f} MB")
    tracemalloc.stop()
```

#### System Memory Analysis
```bash
# Check memory usage by process
ps aux --sort=-%mem | head -20

# Check for memory leaks
valgrind --tool=memcheck --leak-check=full python manage.py runserver

# Monitor memory over time
while true; do
    date
    free -h
    ps -eo pid,ppid,cmd,%mem,%cpu --sort=-%mem | head -10
    sleep 60
done > memory_monitor.log
```

### Network Troubleshooting

#### Connection Testing
```bash
# Test database connectivity
nc -zv localhost 5432

# Test Redis connectivity
redis-cli ping

# Test external API connectivity
curl -I https://www.googleapis.com/calendar/v3/users/me/settings

# Check DNS resolution
nslookup yourdomain.com
dig yourdomain.com
```

#### SSL/TLS Issues
```bash
# Test SSL certificate
openssl s_client -connect yourdomain.com:443 -servername yourdomain.com

# Check certificate expiry
echo | openssl s_client -connect yourdomain.com:443 -servername yourdomain.com 2>/dev/null | openssl x509 -noout -dates

# Verify SSL configuration
ssl-checker yourdomain.com
```

---

## 🚨 Incident Response

### Severity Levels

#### P0 - Critical (15 minutes response)
- System completely down
- Data corruption or loss
- Security breach
- Critical functionality unavailable

#### P1 - High (1 hour response)
- Significant performance degradation
- Important features unavailable
- High error rates
- Partial system outage

#### P2 - Medium (4 hours response)
- Minor performance issues
- Non-critical features affected
- Workaround available
- Low error rates

#### P3 - Low (24 hours response)
- Cosmetic issues
- Enhancement requests
- Documentation updates
- Optimization opportunities

### Incident Response Process

#### 1. Detection & Alert
```bash
# Automated monitoring alerts
# Manual issue reports
# Health check failures

# Initial response
make incident-response priority=P0
```

#### 2. Assessment & Triage
```bash
# Assess severity and impact
make assess-incident

# Gather initial information
make collect-incident-data

# Notify stakeholders
make notify-stakeholders level=P0
```

#### 3. Investigation & Resolution
```bash
# Start investigation
make investigate-incident

# Implement fix
make apply-incident-fix

# Verify resolution
make verify-incident-fix
```

#### 4. Recovery & Monitoring
```bash
# Monitor system stability
make monitor-post-incident

# Verify full functionality
make full-system-test

# Update documentation
make update-incident-docs
```

### Communication Templates

#### Initial Alert (P0/P1)
```
INCIDENT ALERT - [P0/P1] - Sistema Aprender

Status: INVESTIGATING
Impact: [Brief description of impact]
Start Time: [Timestamp]
Estimated Resolution: [If known]

We are investigating [issue description]. Updates will be provided every 15 minutes.

Next Update: [Timestamp]
Incident Commander: [Name]
```

#### Resolution Notice
```
INCIDENT RESOLVED - Sistema Aprender

Status: RESOLVED
Resolution Time: [Timestamp]
Duration: [Total duration]

Issue: [Brief description]
Root Cause: [Brief root cause]
Resolution: [Brief resolution summary]

Full post-mortem will be available within 24 hours.
```

---

## 📚 Troubleshooting Reference

### Log Locations
- **Application Logs**: `logs/django.log`
- **Database Logs**: `/var/log/postgresql/postgresql-15-main.log`
- **Nginx Logs**: `/var/log/nginx/access.log`, `/var/log/nginx/error.log`
- **System Logs**: `/var/log/syslog`
- **Docker Logs**: `docker-compose logs`

### Configuration Files
- **Django Settings**: `aprender_sistema/settings.py`
- **Environment Variables**: `.env`
- **Database Config**: `postgresql.conf`
- **Nginx Config**: `/etc/nginx/sites-available/aprender_sistema`
- **Docker Config**: `docker-compose.yml`

### Useful Commands
```bash
# System information
uname -a
lsb_release -a
free -h
df -h
lscpu

# Network information
ip addr show
netstat -tlnp
ss -tlnp

# Process information
ps aux | grep python
pgrep -f "manage.py runserver"
lsof -p <PID>

# File permissions
ls -la
stat filename
chmod 644 filename
chown user:group filename
```

### Emergency Contacts
- **System Administrator**: admin@yourdomain.com, +55 85 9999-0001
- **Database Administrator**: dba@yourdomain.com, +55 85 9999-0002
- **Security Team**: security@yourdomain.com, +55 85 9999-0003
- **Development Lead**: dev@yourdomain.com, +55 85 9999-0004

---

## 🔄 Preventive Measures

### Regular Maintenance
- **Weekly**: Log rotation, system updates
- **Monthly**: Database maintenance, performance review
- **Quarterly**: Security audit, capacity planning
- **Annually**: Disaster recovery testing

### Monitoring Setup
```bash
# Set up comprehensive monitoring
make setup-monitoring

# Configure alerts
make configure-alerts

# Test alert system
make test-alerts
```

### Backup Strategy
```bash
# Automated daily backups
0 2 * * * /path/to/backup-script.sh

# Weekly full system backup
0 3 * * 0 /path/to/full-backup-script.sh

# Test backup restoration monthly
make test-backup-restoration
```

---

*Troubleshooting guide created during repository cleanup - Phase 4*  
*Date: 2025-09-11*  
*Version: 1.0*