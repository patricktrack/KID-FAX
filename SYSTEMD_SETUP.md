# Systemd Service Setup for Kid Fax

This guide shows you how to set up Kid Fax to run automatically on boot using systemd.

## Why Use Systemd?

- **Auto-start on boot**: Kid Fax starts automatically when Pi powers on
- **Auto-restart on failure**: If the process crashes, systemd restarts it
- **Log management**: Centralized logging via journald
- **Easy control**: Start/stop/restart with simple commands

## Step 1: Create Service File

Create the systemd service file:

```bash
sudo nano /etc/systemd/system/kidfax.service
```

## Step 2: Configure Service

Paste this configuration (adjust paths for your installation):

```ini
[Unit]
Description=Kid Fax SMS Poller
Documentation=https://github.com/yourusername/KID-FAX
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
Group=pi

# Environment file containing Twilio credentials and configuration
EnvironmentFile=/home/pi/KID-FAX/.env

# Working directory
WorkingDirectory=/home/pi/KID-FAX

# Command to run
ExecStart=/usr/bin/python3 -m kidfax.sms_poller

# Restart behavior
Restart=on-failure
RestartSec=10

# Security settings
NoNewPrivileges=true
PrivateTmp=true

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=kidfax

[Install]
WantedBy=multi-user.target
```

Save and exit (Ctrl+X, then Y, then Enter).

## Step 3: Update Paths

Adjust these paths in the service file to match your installation:

- **User/Group**: Change `pi` if using different user
- **EnvironmentFile**: Full path to your `.env` file
- **WorkingDirectory**: Full path to KID-FAX directory
- **ExecStart**: Should point to your Python 3 installation

### Find Your Python Path

```bash
which python3
# Use this path in ExecStart
```

### Verify Environment File Path

```bash
ls -la ~/KID-FAX/.env
# Should show: /home/pi/KID-FAX/.env
```

## Step 4: Enable and Start Service

```bash
# Reload systemd to recognize new service
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable kidfax

# Start service now
sudo systemctl start kidfax

# Check status
sudo systemctl status kidfax
```

You should see:

```
● kidfax.service - Kid Fax SMS Poller
     Loaded: loaded (/etc/systemd/system/kidfax.service; enabled; vendor preset: enabled)
     Active: active (running) since Sat 2025-12-14 10:00:00 UTC; 5s ago
   Main PID: 1234 (python3)
      Tasks: 2 (limit: 4915)
        CPU: 100ms
     CGroup: /system.slice/kidfax.service
             └─1234 /usr/bin/python3 -m kidfax.sms_poller
```

## Service Management Commands

### View Status
```bash
sudo systemctl status kidfax
```

### Start Service
```bash
sudo systemctl start kidfax
```

### Stop Service
```bash
sudo systemctl stop kidfax
```

### Restart Service
```bash
sudo systemctl restart kidfax
```

### Disable Auto-Start
```bash
sudo systemctl disable kidfax
```

### Enable Auto-Start
```bash
sudo systemctl enable kidfax
```

## View Logs

### Real-time Logs (Follow Mode)
```bash
sudo journalctl -u kidfax -f
```

Press Ctrl+C to exit.

### Last 50 Lines
```bash
sudo journalctl -u kidfax -n 50
```

### Last Hour
```bash
sudo journalctl -u kidfax --since "1 hour ago"
```

### Today's Logs
```bash
sudo journalctl -u kidfax --since today
```

### Yesterday's Logs
```bash
sudo journalctl -u kidfax --since yesterday --until today
```

### With Timestamps
```bash
sudo journalctl -u kidfax -o short-iso
```

## Troubleshooting

### Service Won't Start

1. **Check service status**:
   ```bash
   sudo systemctl status kidfax
   ```

2. **Check for syntax errors**:
   ```bash
   sudo systemd-analyze verify /etc/systemd/system/kidfax.service
   ```

3. **Check permissions**:
   ```bash
   ls -la /home/pi/KID-FAX/.env
   # Should be readable by pi user
   ```

4. **Test manually**:
   ```bash
   cd ~/KID-FAX
   source .env
   python3 -m kidfax.sms_poller
   # Does it work? If yes, issue is in service file
   ```

### Service Starts But Crashes

1. **View logs**:
   ```bash
   sudo journalctl -u kidfax -n 100
   ```

2. **Common issues**:
   - Missing environment variables in `.env`
   - Incorrect paths in service file
   - Permission issues with printer
   - Twilio credentials invalid

### Logs Not Showing

If `journalctl` shows no logs:

1. **Check syslog identifier**:
   ```bash
   sudo journalctl -t kidfax
   ```

2. **Check all journal entries**:
   ```bash
   sudo journalctl -xe
   ```

### Printer Permission Issues

If running as service but printer doesn't work:

```bash
# Add user to required groups
sudo usermod -a -G lp,dialout pi

# Restart service
sudo systemctl restart kidfax
```

## Advanced Configuration

### Custom User

If running as different user (not `pi`):

```ini
[Service]
User=yourusername
Group=yourusername
EnvironmentFile=/home/yourusername/KID-FAX/.env
WorkingDirectory=/home/yourusername/KID-FAX
```

Then set permissions:

```bash
sudo usermod -a -G lp,dialout yourusername
```

### Virtual Environment

If using Python venv:

```ini
[Service]
ExecStart=/home/pi/KID-FAX/venv/bin/python -m kidfax.sms_poller
```

### Email Alerts on Failure

Install mail utilities:

```bash
sudo apt-get install -y mailutils
```

Add to service file:

```ini
[Service]
OnFailure=status-email@%n.service
```

### Resource Limits

Limit CPU and memory:

```ini
[Service]
CPUQuota=50%
MemoryLimit=512M
```

### Multiple Instances

Run multiple Kid Fax instances (different Twilio numbers):

```bash
sudo cp /etc/systemd/system/kidfax.service /etc/systemd/system/kidfax-alt.service
```

Edit `kidfax-alt.service` with different environment file:

```ini
EnvironmentFile=/home/pi/KID-FAX/.env.alt
```

## Environment File Best Practices

### Secure Permissions

```bash
chmod 600 ~/KID-FAX/.env
```

Only owner can read the file (contains Twilio credentials).

### Validate Before Starting

```bash
# Test environment loads correctly
set -a
source ~/KID-FAX/.env
set +a
echo $TWILIO_ACCOUNT_SID
# Should print your Account SID
```

### Backup Environment

```bash
cp ~/KID-FAX/.env ~/KID-FAX/.env.backup
chmod 600 ~/KID-FAX/.env.backup
```

## Monitoring and Maintenance

### Check Service Health

Create monitoring script:

```bash
#!/bin/bash
STATUS=$(systemctl is-active kidfax)
if [ "$STATUS" != "active" ]; then
    echo "Kid Fax is not running!"
    # Send alert (email, SMS, etc.)
fi
```

### Auto-Restart on Network Issues

Service already has `Restart=on-failure`, but you can add:

```ini
[Service]
RestartSec=10
StartLimitInterval=200
StartLimitBurst=5
```

### Log Rotation

systemd journal handles rotation automatically, but you can configure:

```bash
sudo nano /etc/systemd/journald.conf
```

Set:

```ini
[Journal]
SystemMaxUse=500M
MaxFileSec=7day
```

## Uninstalling Service

To remove Kid Fax systemd service:

```bash
# Stop service
sudo systemctl stop kidfax

# Disable auto-start
sudo systemctl disable kidfax

# Remove service file
sudo rm /etc/systemd/system/kidfax.service

# Reload systemd
sudo systemctl daemon-reload
```

## Next Steps

- **Monitor logs**: `sudo journalctl -u kidfax -f`
- **Send test message**: Text your Twilio number
- **Verify auto-start**: `sudo reboot` and check if service starts

Your Kid Fax mailbox is now running as a reliable system service!
