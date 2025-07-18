# 🚀 Deployment Strategy: VPS Infrastructure & Production Release

## 📋 Overview

This document outlines the deployment strategy for CoachNTT.ai's backend services to the Ubuntu 24.04 VPS, supporting both Phase 1 completion and Phase 2 VSCode extension integration.

## 🖥️ VPS Infrastructure

### Server Specifications
- **Provider**: HostSlinger VPS
- **OS**: Ubuntu 24.04 LTS
- **CPU**: 2 vCPU cores
- **RAM**: 8 GB
- **Storage**: 100 GB NVMe SSD
- **Bandwidth**: 8 TB monthly
- **Access**: SSH root@145.79.0.118
- **Docker**: Pre-installed

### Resource Allocation Plan
```
Total Resources:
├── System & Docker (1GB RAM, 0.5 CPU)
├── PostgreSQL (1-2GB RAM, 0.5 CPU)
├── API Server (1-2GB RAM, 0.5 CPU)
├── Monitoring Stack (1GB RAM, 0.5 CPU)
└── Buffer/Cache (2-3GB RAM)
```

## 🔒 Security Configuration

### Initial Setup (Priority 1)
```bash
# 1. Create non-root user
adduser coachntt
usermod -aG sudo,docker coachntt

# 2. Configure SSH security
sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config

# 3. Setup firewall
ufw allow 22/tcp  # SSH
ufw allow 80/tcp  # HTTP
ufw allow 443/tcp # HTTPS
ufw enable

# 4. Automatic security updates
apt install unattended-upgrades
dpkg-reconfigure -plow unattended-upgrades
```

### Docker Security
- Use non-root containers
- Implement resource limits
- Enable AppArmor profiles
- Regular image updates

## 🏗️ Deployment Architecture

### Network Architecture
```
Internet
    ↓
Cloudflare (optional CDN)
    ↓
Nginx (Reverse Proxy + SSL)
    ↓
Docker Network (172.20.0.0/16)
    ├── API Container (:8000)
    ├── PostgreSQL (:5432)
    ├── PgBouncer (:6432)
    └── Monitoring Stack
```

### Domain Configuration
- **Primary**: api.coachntt.ai (to be configured)
- **Monitoring**: metrics.coachntt.ai
- **SSL**: Let's Encrypt via Certbot

## 📦 Deployment Stages

### Stage 1: Infrastructure Setup (Session 2.3.x)
1. **Secure VPS**
   - Non-root user creation
   - SSH key authentication
   - Firewall configuration
   - Fail2ban installation

2. **Install Dependencies**
   ```bash
   # System packages
   apt update && apt upgrade -y
   apt install -y nginx certbot python3-certbot-nginx
   
   # Docker Compose
   curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" -o /usr/local/bin/docker-compose
   chmod +x /usr/local/bin/docker-compose
   ```

3. **Configure Nginx**
   ```nginx
   server {
       listen 80;
       server_name api.coachntt.ai;
       
       location / {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
       
       location /ws {
           proxy_pass http://localhost:8000;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
       }
   }
   ```

### Stage 2: Backend Deployment (Session 2.4.x)
1. **Repository Setup**
   ```bash
   # Clone repository
   cd /opt
   git clone https://github.com/user/coachntt.git
   cd coachntt
   
   # Create environment file
   cp .env.example .env.production
   # Edit with production values
   ```

2. **Database Migration**
   ```bash
   # Start PostgreSQL first
   docker-compose -f docker-compose.prod.yml up -d postgres
   
   # Run migrations
   docker-compose -f docker-compose.prod.yml run --rm api python -m scripts.migrate
   ```

3. **Launch Services**
   ```bash
   # Start all services
   docker-compose -f docker-compose.prod.yml up -d
   
   # Verify health
   docker-compose ps
   curl http://localhost:8000/health
   ```

### Stage 3: SSL & Security (Session 2.4.x)
1. **SSL Certificate**
   ```bash
   certbot --nginx -d api.coachntt.ai -d metrics.coachntt.ai
   ```

2. **Security Headers**
   ```nginx
   # In Nginx config
   add_header X-Frame-Options "SAMEORIGIN" always;
   add_header X-Content-Type-Options "nosniff" always;
   add_header X-XSS-Protection "1; mode=block" always;
   add_header Strict-Transport-Security "max-age=31536000" always;
   ```

3. **Rate Limiting**
   ```nginx
   limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
   limit_req zone=api burst=20 nodelay;
   ```

### Stage 4: Monitoring Setup (Optional)
1. **Prometheus & Grafana**
   ```yaml
   # docker-compose.monitoring.yml
   services:
     prometheus:
       image: prom/prometheus:latest
       volumes:
         - ./prometheus.yml:/etc/prometheus/prometheus.yml
       ports:
         - "9090:9090"
   
     grafana:
       image: grafana/grafana:latest
       ports:
         - "3000:3000"
       environment:
         - GF_SECURITY_ADMIN_PASSWORD=secure_password
   ```

2. **Application Metrics**
   - API response times
   - Database query performance
   - Safety validation rates
   - Memory usage patterns

## 🔄 Continuous Deployment

### GitHub Actions Workflow
```yaml
name: Deploy to VPS
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Deploy to VPS
        uses: appleboy/ssh-action@v0.1.5
        with:
          host: ${{ secrets.VPS_HOST }}
          username: ${{ secrets.VPS_USER }}
          key: ${{ secrets.VPS_SSH_KEY }}
          script: |
            cd /opt/coachntt
            git pull origin main
            docker-compose -f docker-compose.prod.yml pull
            docker-compose -f docker-compose.prod.yml up -d
            docker system prune -f
```

### Deployment Checklist
- [ ] Backup database before deployment
- [ ] Test in staging environment
- [ ] Run migrations if needed
- [ ] Verify health checks pass
- [ ] Monitor error rates post-deployment
- [ ] Keep rollback plan ready

## 🔧 Production Configuration

### Environment Variables
```bash
# .env.production
NODE_ENV=production
DATABASE_URL=postgresql://coachntt:secure_pass@postgres:5432/coachntt_prod
JWT_SECRET=<generated-secret>
API_KEY=<generated-api-key>
CORS_ORIGINS=https://app.coachntt.ai
```

### Docker Compose Production
```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  api:
    image: coachntt/api:latest
    restart: always
    environment:
      - NODE_ENV=production
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - coachntt
```

## 📊 Monitoring & Maintenance

### Health Checks
- **API Health**: GET /health
- **Database**: pg_isready
- **Disk Space**: >20% free
- **Memory**: <80% usage
- **CPU**: <70% sustained

### Backup Strategy
```bash
# Daily database backup
0 2 * * * docker exec ccp_postgres pg_dump -U coachntt coachntt_prod | gzip > /backups/db_$(date +\%Y\%m\%d).sql.gz

# Weekly full backup
0 3 * * 0 tar -czf /backups/full_$(date +\%Y\%m\%d).tar.gz /opt/coachntt/data
```

### Maintenance Windows
- **Scheduled**: Sundays 2-4 AM UTC
- **Updates**: Security patches monthly
- **Scaling**: Monitor and adjust resources

## 🚨 Incident Response

### Rollback Procedure
```bash
# Quick rollback
cd /opt/coachntt
git checkout <previous-commit>
docker-compose -f docker-compose.prod.yml up -d --force-recreate
```

### Common Issues
1. **High Memory Usage**
   - Restart API container
   - Check for memory leaks
   - Scale horizontally if needed

2. **Database Connection Issues**
   - Check PgBouncer logs
   - Verify connection limits
   - Restart database if needed

3. **SSL Certificate Expiry**
   - Auto-renewal via Certbot
   - Manual: `certbot renew`

## 📈 Scaling Strategy

### Vertical Scaling
- Current VPS can handle 100+ concurrent users
- Upgrade to 4 vCPU, 16GB RAM if needed
- Database can scale to 10,000+ memories

### Horizontal Scaling
- Add read replicas for database
- Load balancer for multiple API instances
- Consider Kubernetes for orchestration

## 🎯 Phase 2 Integration

### VSCode Extension Connection
```typescript
// Extension configuration
const config = {
  apiUrl: 'https://api.coachntt.ai',
  wsUrl: 'wss://api.coachntt.ai/ws',
  apiKey: await context.secrets.get('coachntt.apiKey')
};
```

### Development vs Production
- Local development: localhost:8000
- Staging: staging.api.coachntt.ai
- Production: api.coachntt.ai

---

This deployment strategy ensures secure, scalable, and maintainable infrastructure for CoachNTT.ai, supporting both current functionality and future growth.