# CI2D3 Deployment Guide for AWS Free Tier

This guide explains how to deploy the CI2D3 Ice Island Explorer on AWS Free Tier (t2.micro instance with 1GB RAM).

## Optimizations for Free Tier

The production configuration (`docker-compose.prod.yml`) has been optimized for minimal resource usage:

| Service | Memory Limit | CPU Limit | Optimizations |
|---------|-------------|-----------|---------------|
| PostgreSQL | 300MB | 0.5 CPU | Reduced connections (20), smaller buffers |
| GeoServer | 450MB | 0.5 CPU | Java heap 128-400MB, G1GC, no extensions |
| Flask API | 150MB | 0.3 CPU | Gunicorn with 2 workers |
| **Total** | **~900MB** | **1.3 CPU** | Leaves 100MB for OS |

## Prerequisites

- AWS Free Tier account
- t2.micro EC2 instance (1 vCPU, 1GB RAM)
- Ubuntu 22.04 LTS AMI
- At least 10GB storage (Free Tier: 30GB)

## Step 1: Launch EC2 Instance

1. **Launch t2.micro instance**:
   ```
   AMI: Ubuntu 22.04 LTS
   Instance Type: t2.micro (1 vCPU, 1GB RAM)
   Storage: 15GB GP3 (or GP2)
   ```

2. **Security Group** - Allow inbound traffic:
   ```
   Port 22 (SSH): Your IP
   Port 8080 (GeoServer/Frontend): 0.0.0.0/0
   Port 5000 (Flask API): 0.0.0.0/0
   ```

3. **Download key pair** and connect:
   ```bash
   chmod 400 your-key.pem
   ssh -i your-key.pem ubuntu@<EC2-PUBLIC-IP>
   ```

## Step 2: Install Docker

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker ubuntu

# Install Docker Compose
sudo apt install -y docker-compose

# Log out and back in for group changes to take effect
exit
# SSH back in
```

## Step 3: Enable Swap (Critical for 1GB RAM!)

Without swap, the instance will run out of memory:

```bash
# Create 2GB swap file
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Make swap permanent
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Optimize swappiness for low-memory systems
sudo sysctl vm.swappiness=10
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf

# Verify swap
free -h
```

## Step 4: Clone Repository

```bash
cd ~
git clone https://github.com/YOUR_USERNAME/ci2d3_web.git
cd ci2d3_web
```

## Step 5: Configure Environment

Create production environment file:

```bash
cat > .env.prod << EOF
# Database
DB_PASSWORD=CHANGE_THIS_PASSWORD

# GeoServer
GEOSERVER_PASSWORD=CHANGE_THIS_PASSWORD

# Public access
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
CORS_ORIGINS=*
EOF
```

## Step 6: Deploy Application

```bash
# Build and start services (takes 5-10 minutes on t2.micro)
docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d --build

# Monitor startup (GeoServer takes 2-3 minutes)
docker-compose -f docker-compose.prod.yml logs -f
```

**Expected startup times**:
- PostgreSQL: ~10 seconds
- Flask API: ~5 seconds
- GeoServer: **2-5 minutes** (be patient!)

## Step 7: Load Data

```bash
# Wait for all services to be healthy
docker-compose -f docker-compose.prod.yml ps

# Load ice island data
docker-compose -f docker-compose.prod.yml exec postgis bash /scripts/load_data.sh

# Configure GeoServer layer
docker-compose -f docker-compose.prod.yml exec geoserver bash /opt/scripts/configure_geoserver.sh
```

## Step 8: Access Application

Open in browser:
```
http://<EC2-PUBLIC-IP>:8080/
```

## Performance Tips for Free Tier

### 1. Monitor Memory Usage

```bash
# Check memory usage
free -h

# Check Docker container stats
docker stats

# If memory is high, restart containers one by one
docker-compose -f docker-compose.prod.yml restart flask-api
docker-compose -f docker-compose.prod.yml restart postgis
docker-compose -f docker-compose.prod.yml restart geoserver
```

### 2. Reduce Memory Pressure

If you experience slowness or Out Of Memory (OOM) errors:

**Option A: Further reduce GeoServer memory**:
```bash
# Edit docker-compose.prod.yml
# Change EXTRA_JAVA_OPTS:
-Xms96m -Xmx350m
```

**Option B: Stop services when not in use**:
```bash
# Stop all services
docker-compose -f docker-compose.prod.yml stop

# Start only when needed
docker-compose -f docker-compose.prod.yml start
```

### 3. Optimize PostgreSQL

```bash
# Connect to PostgreSQL
docker-compose -f docker-compose.prod.yml exec postgis psql -U geoserver -d ci2d3_db

# Add indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_iceislands_area ON iceislands(area);
CREATE INDEX IF NOT EXISTS idx_iceislands_calvingloc ON iceislands(calvingloc);
CREATE INDEX IF NOT EXISTS idx_iceislands_calvingyr ON iceislands(calvingyr);
CREATE INDEX IF NOT EXISTS idx_iceislands_geom_gist ON iceislands USING GIST(geom);

# Exit
\q
```

### 4. Enable GeoServer Disk Caching

This reduces memory usage by caching tiles to disk:

```bash
# Access GeoServer web interface
# http://<EC2-IP>:8080/geoserver/web
# Login: admin / <your-password>

# Navigate to: Settings > Tile Caching > Disk Quota
# Enable disk quota: 500MB
# Configure cleanup frequency: Daily
```

## Monitoring & Maintenance

### Check Service Health

```bash
# View all containers
docker-compose -f docker-compose.prod.yml ps

# Check logs
docker-compose -f docker-compose.prod.yml logs --tail=100

# Check specific service
docker-compose -f docker-compose.prod.yml logs geoserver
```

### Restart if Needed

```bash
# Restart all services
docker-compose -f docker-compose.prod.yml restart

# Restart specific service
docker-compose -f docker-compose.prod.yml restart geoserver
```

### Update Application

```bash
cd ~/ci2d3_web
git pull origin main
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build
```

## Cost Optimization

### Free Tier Limits

AWS Free Tier includes:
- ✅ 750 hours/month of t2.micro (enough for 24/7)
- ✅ 30GB EBS storage
- ✅ 15GB data transfer out per month

### Staying Within Free Tier

1. **Use only t2.micro** (don't upgrade!)
2. **Monitor data transfer**:
   ```bash
   # Check AWS CloudWatch for data transfer metrics
   ```
3. **Stop when not demoing**:
   ```bash
   # Stop EC2 instance when not in use (via AWS Console)
   ```

## Troubleshooting

### GeoServer Won't Start / Very Slow

**Symptom**: GeoServer logs show "OutOfMemoryError" or takes >10 minutes to start

**Solution**:
```bash
# Increase swap
sudo swapoff -a
sudo dd if=/dev/zero of=/swapfile bs=1M count=4096
sudo mkswap /swapfile
sudo swapon /swapfile

# Restart GeoServer alone
docker-compose -f docker-compose.prod.yml restart geoserver
```

### Application Crashes / Container Dies

**Symptom**: Containers randomly stop

**Solution**:
```bash
# Check kernel logs for OOM killer
dmesg | grep -i "out of memory"

# If OOM killer is active, reduce memory limits further or add more swap
```

### Map Tiles Load Slowly

**Symptom**: Map takes long time to load ice island data

**Solutions**:
1. Enable GeoServer tile caching (see above)
2. Reduce data complexity:
   ```sql
   -- Simplify geometries for web display
   ALTER TABLE iceislands ADD COLUMN geom_simple geometry;
   UPDATE iceislands SET geom_simple = ST_SimplifyPreserveTopology(geom, 0.001);
   CREATE INDEX idx_iceislands_geom_simple ON iceislands USING GIST(geom_simple);
   ```

### Port Already in Use

**Symptom**: "port is already allocated" error

**Solution**:
```bash
# Find process using the port
sudo lsof -i :8080

# Kill the process or change ports in docker-compose.prod.yml
```

## Security Hardening (Recommended)

After deployment, secure your instance:

1. **Change default passwords** in `.env.prod`
2. **Restrict Security Group**: Only allow your IP for admin access
3. **Enable AWS CloudWatch** for monitoring
4. **Regular updates**:
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

## Alternative: Further Cost Reduction

If still experiencing issues on t2.micro:

### Option 1: Use RDS Free Tier for PostgreSQL

- Move PostgreSQL to AWS RDS Free Tier (db.t2.micro)
- Reduces memory pressure on EC2 instance
- Allows GeoServer more memory

### Option 2: Use S3 + CloudFront

- Serve static frontend from S3
- Reduces GeoServer memory usage
- Better performance

## Support & Issues

For issues specific to this deployment:
1. Check logs: `docker-compose -f docker-compose.prod.yml logs`
2. Check system resources: `free -h` and `docker stats`
3. Review this guide's troubleshooting section

For application issues:
- Open issue on GitHub repository
