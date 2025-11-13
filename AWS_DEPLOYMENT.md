# AWS EC2 Deployment Guide - CI2D3 Ice Island Explorer

Complete guide to deploy the CI2D3 Ice Island Explorer on AWS EC2 with public IP access.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [AWS EC2 Setup](#aws-ec2-setup)
3. [Configure Security Groups](#configure-security-groups)
4. [Install Dependencies](#install-dependencies)
5. [Deploy Application](#deploy-application)
6. [Configure for Public Access](#configure-for-public-access)
7. [Verify CORS](#verify-cors)
8. [Testing](#testing)
9. [Troubleshooting](#troubleshooting)
10. [Security Best Practices](#security-best-practices)

---

## Prerequisites

- AWS Account with EC2 access
- Basic knowledge of SSH and Linux commands
- Domain name (optional, but recommended for production)

### Minimum EC2 Instance Requirements

- **Instance Type**: t3.medium or larger (2 vCPU, 4 GB RAM)
- **Storage**: 20 GB minimum, 50 GB recommended
- **OS**: Ubuntu 22.04 LTS (or Amazon Linux 2023)

---

## AWS EC2 Setup

### Step 1: Launch EC2 Instance

1. **Log in to AWS Console** → Navigate to EC2

2. **Click "Launch Instance"**

3. **Configure Instance:**
   - **Name**: `ci2d3-ice-island-explorer`
   - **AMI**: Ubuntu Server 22.04 LTS (Free tier eligible)
   - **Instance type**: `t3.medium` (minimum)
   - **Key pair**: Create new or select existing SSH key pair
   - **Storage**: 20 GB gp3 (minimum)

4. **Click "Launch Instance"**

5. **Wait for instance to start** (State: Running)

6. **Note your Public IP address** from EC2 Dashboard
   - Example: `54.123.45.67`
   - You'll need this for configuration

### Step 2: Connect to EC2 Instance

```bash
# Replace with your key file and public IP
ssh -i "your-key.pem" ubuntu@54.123.45.67
```

---

## Configure Security Groups

### Required Ports

Configure your EC2 Security Group to allow these inbound ports:

| Port | Protocol | Source | Purpose |
|------|----------|--------|---------|
| 22 | TCP | Your IP | SSH access |
| 8080 | TCP | 0.0.0.0/0 | GeoServer & Frontend |
| 5000 | TCP | 0.0.0.0/0 | Flask API |

### Configure in AWS Console

1. **Go to EC2 Dashboard** → Select your instance

2. **Click "Security" tab** → Click on Security Group link

3. **Click "Edit inbound rules"**

4. **Add the following rules:**

   ```
   Type: SSH
   Protocol: TCP
   Port: 22
   Source: My IP (or your specific IP)

   Type: Custom TCP
   Protocol: TCP
   Port: 8080
   Source: 0.0.0.0/0 (or specific IPs for better security)
   Description: GeoServer and Frontend

   Type: Custom TCP
   Protocol: TCP
   Port: 5000
   Source: 0.0.0.0/0
   Description: Flask API
   ```

5. **Click "Save rules"**

**Security Note:** For production, restrict `0.0.0.0/0` to specific IP ranges or use a Load Balancer.

---

## Install Dependencies

SSH into your EC2 instance and run:

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add ubuntu user to docker group
sudo usermod -aG docker ubuntu

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install Git
sudo apt install git -y

# Verify installations
docker --version
docker-compose --version
git --version

# Log out and log back in for docker group changes to take effect
exit
```

**Re-connect via SSH:**
```bash
ssh -i "your-key.pem" ubuntu@54.123.45.67
```

---

## Deploy Application

### Step 1: Clone Repository

```bash
# Clone your repository
git clone https://github.com/sm-pawar/ci2d3_web.git
cd ci2d3_web

# Checkout your branch
git checkout claude/setup-docker-geoserver-postgis-011CV5rqjtAgSAMsjfmx2Uzy
```

### Step 2: Configure Environment

```bash
# Copy production environment file
cp .env.production .env

# Edit with your EC2 public IP
nano .env

# Replace <YOUR_EC2_PUBLIC_IP> with your actual IP
# Example: PUBLIC_IP=54.123.45.67

# Save and exit (Ctrl+X, Y, Enter)
```

**Important Configuration in `.env`:**

```bash
# Replace this line
PUBLIC_IP=<YOUR_EC2_PUBLIC_IP>

# With your actual IP (example)
PUBLIC_IP=54.123.45.67

# Also change passwords for production!
GEOSERVER_PASSWORD=YOUR_SECURE_PASSWORD
DB_PASSWORD=YOUR_SECURE_DB_PASSWORD
SECRET_KEY=YOUR-RANDOM-SECRET-KEY
```

### Step 3: Build and Start Services

```bash
# Build Docker images (this may take 10-15 minutes)
docker-compose build

# Start all services
docker-compose up -d

# Monitor logs
docker-compose logs -f
```

Watch for these success messages:
- PostGIS: `database system is ready to accept connections`
- GeoServer: `Server startup in [xxxx] milliseconds`
- Flask: `Running on http://0.0.0.0:5000`

Press `Ctrl+C` to exit log view.

### Step 4: Load Ice Island Data

```bash
# Load shapefile into PostGIS
docker-compose exec postgis bash /home/user/ci2d3_web/scripts/load_data.sh

# Verify data loaded
docker-compose exec postgis psql -U geoserver -d ci2d3_db -c "SELECT COUNT(*) FROM iceislands;"
```

### Step 5: Configure GeoServer

```bash
# Run GeoServer configuration script
docker-compose exec geoserver bash /opt/scripts/configure_geoserver.sh
```

---

## Configure for Public Access

### Verify CORS is Enabled

Check `docker-compose.yml` has:

```yaml
environment:
  CORS_ENABLED: "true"
  CORS_ALLOWED_ORIGINS: "*"
```

✅ **CORS is already enabled** in your configuration!

### Frontend Configuration

The frontend now **automatically detects** the host and uses the correct URLs:

- **Local development**: Uses `http://localhost:8080` and `http://localhost:5000`
- **AWS EC2**: Uses `http://YOUR_PUBLIC_IP:8080` and `http://YOUR_PUBLIC_IP:5000`

This is handled by the new `frontend/js/config.js` file.

### Check Container Status

```bash
docker-compose ps
```

All three services should show "Up" status.

---

## Testing

### Test from Your Local Machine

**1. Test GeoServer:**

Open in browser:
```
http://54.123.45.67:8080/geoserver
```

**Login credentials:**
- Username: `admin`
- Password: `geoserver` (or your changed password)

**2. Test Flask API:**

```bash
curl http://54.123.45.67:5000/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "ci2d3-api",
  "version": "1.0.0"
}
```

**3. Test Frontend Application:**

Open in browser:
```
http://54.123.45.67:8080/
```

You should see:
- ✅ Map loads correctly
- ✅ Ice islands are visible
- ✅ Click on ice island shows details
- ✅ Filter panel works

**4. Test WMS Layer:**

```
http://54.123.45.67:8080/geoserver/ci2d3/wms?service=WMS&request=GetCapabilities
```

Should return XML with layer information.

**5. Test API Endpoints:**

```bash
# Get attributes
curl http://54.123.45.67:5000/api/inspect/attributes

# Filter by location
curl -X POST http://54.123.45.67:5000/api/filter/ \
  -H "Content-Type: application/json" \
  -d '{"field": "calvingloc", "operator": "=", "value": "PG"}'
```

---

## Troubleshooting

### Services Not Starting

**Check logs:**
```bash
docker-compose logs geoserver
docker-compose logs flask-api
docker-compose logs postgis
```

**Restart services:**
```bash
docker-compose restart
```

### Can't Access from Browser

**1. Verify Security Group rules are correct**

**2. Check if services are listening:**
```bash
sudo netstat -tulpn | grep -E '8080|5000|5432'
```

**3. Test locally on EC2:**
```bash
curl http://localhost:8080/geoserver/web/
curl http://localhost:5000/health
```

### CORS Errors

**Check CORS configuration:**
```bash
docker-compose exec geoserver env | grep CORS
```

Should show:
```
CORS_ENABLED=true
CORS_ALLOWED_ORIGINS=*
```

**Restart GeoServer if needed:**
```bash
docker-compose restart geoserver
```

### Map Not Loading

**1. Open browser console (F12)**

Check for errors related to:
- Network requests
- CORS errors
- 404 errors

**2. Verify config.js is loaded:**

In browser console:
```javascript
console.log(CONFIG);
```

Should show your public IP in URLs.

### Data Not Loading

**Check if data is in database:**
```bash
docker-compose exec postgis psql -U geoserver -d ci2d3_db -c "SELECT COUNT(*) FROM iceislands;"
```

**Reload data if needed:**
```bash
docker-compose exec postgis bash /home/user/ci2d3_web/scripts/load_data.sh
```

---

## Security Best Practices

### 1. Change Default Passwords

Edit `.env`:
```bash
# Use strong passwords
GEOSERVER_PASSWORD=YourStr0ngP@ssw0rd!
DB_PASSWORD=An0therStr0ngP@ssw0rd!
SECRET_KEY=$(openssl rand -hex 32)
```

Restart services:
```bash
docker-compose down
docker-compose up -d
```

### 2. Restrict CORS Origins

For production, edit `.env`:
```bash
# Instead of *
CORS_ORIGINS=http://54.123.45.67:8080,http://54.123.45.67:5000
```

### 3. Use HTTPS

Install and configure:
- **Nginx** as reverse proxy
- **Let's Encrypt** for SSL certificates

### 4. Restrict Database Access

Remove PostgreSQL port from Security Group (port 5432) unless needed for external access.

### 5. Set Up Domain Name

Use Route 53 or your DNS provider to point a domain to your EC2 public IP:
```
iceislands.yourdomain.com → 54.123.45.67
```

Then use domain in configuration instead of IP.

### 6. Regular Updates

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Update Docker images
docker-compose pull
docker-compose up -d
```

### 7. Backups

**Backup PostgreSQL data:**
```bash
# Create backup
docker-compose exec postgis pg_dump -U geoserver ci2d3_db > backup_$(date +%Y%m%d).sql

# Copy to S3 (optional)
aws s3 cp backup_$(date +%Y%m%d).sql s3://your-bucket/backups/
```

**Backup GeoServer configuration:**
```bash
docker-compose exec geoserver tar czf /tmp/geoserver_backup.tar.gz /opt/geoserver_data
docker cp ci2d3_geoserver:/tmp/geoserver_backup.tar.gz ./
```

---

## Monitoring

### Check Service Health

```bash
# Overall status
docker-compose ps

# CPU and Memory usage
docker stats

# Disk usage
df -h
```

### View Logs

```bash
# All services
docker-compose logs --tail=100 -f

# Specific service
docker-compose logs -f geoserver
docker-compose logs -f flask-api
docker-compose logs -f postgis
```

### Application Health Checks

```bash
# Create monitoring script
nano monitor.sh
```

Add:
```bash
#!/bin/bash
echo "Checking GeoServer..."
curl -s http://localhost:8080/geoserver/web/ > /dev/null && echo "✓ GeoServer OK" || echo "✗ GeoServer DOWN"

echo "Checking Flask API..."
curl -s http://localhost:5000/health > /dev/null && echo "✓ Flask API OK" || echo "✗ Flask API DOWN"

echo "Checking PostGIS..."
docker-compose exec -T postgis psql -U geoserver -d ci2d3_db -c '\q' > /dev/null 2>&1 && echo "✓ PostGIS OK" || echo "✗ PostGIS DOWN"
```

Make executable and run:
```bash
chmod +x monitor.sh
./monitor.sh
```

---

## Cost Optimization

### AWS EC2 Cost Estimates (us-east-1)

| Instance Type | Monthly Cost | Use Case |
|---------------|--------------|----------|
| t3.medium | ~$30 | Development/Testing |
| t3.large | ~$60 | Small production |
| t3.xlarge | ~$121 | Medium production |

### Cost Saving Tips

1. **Use Reserved Instances** for production (up to 72% savings)
2. **Stop instance** when not in use (Development)
3. **Use Elastic IP** to maintain IP when stopping/starting
4. **Enable CloudWatch** for monitoring and auto-scaling

---

## Next Steps

1. ✅ Application deployed and accessible
2. ⬜ Configure custom domain
3. ⬜ Set up HTTPS with Let's Encrypt
4. ⬜ Configure backups to S3
5. ⬜ Set up CloudWatch monitoring
6. ⬜ Implement auto-scaling (if needed)

---

## Support

**Common Issues:**
- See [SETUP.md](SETUP.md) for detailed troubleshooting
- Check [README.md](README.md) for application documentation

**AWS Resources:**
- [EC2 Documentation](https://docs.aws.amazon.com/ec2/)
- [Security Groups](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_SecurityGroups.html)

---

## Summary

Your CI2D3 Ice Island Explorer is now:

✅ **Deployed on AWS EC2**
✅ **Accessible via public IP**
✅ **CORS enabled for cross-origin requests**
✅ **Frontend automatically configured**
✅ **Ready for public use**

**Access your application:**
```
http://YOUR_EC2_PUBLIC_IP:8080/
```

**GeoServer Admin:**
```
http://YOUR_EC2_PUBLIC_IP:8080/geoserver
```

**API Endpoint:**
```
http://YOUR_EC2_PUBLIC_IP:5000/api/
```

Enjoy your deployed Ice Island Explorer! 🧊🗺️
