# Kid Fax Quick Start Guide

Get your Kid Fax SMS mailbox up and running in 15 minutes!

## Prerequisites

- Raspberry Pi (any model with GPIO, tested on Pi 400)
- 58mm Thermal Printer (USB or Serial)
- Twilio account (free trial available)
- Internet connection

## Step 1: Hardware Setup (5 minutes)

### USB Printer
1. Connect thermal printer to Raspberry Pi USB port
2. Power on the printer

### Serial Printer (Adafruit Mini TTL)
1. Connect printer to Pi GPIO:
   - Printer TX → Pi RX (GPIO 15)
   - Printer RX → Pi TX (GPIO 14)
   - Printer GND → Pi GND
2. Connect printer to separate 5-9V power supply
3. Enable serial port:
   ```bash
   sudo raspi-config
   # Navigate to: Interface Options → Serial Port → Enable
   ```

## Step 2: Twilio Setup (3 minutes)

1. **Create Twilio Account**
   - Go to [twilio.com](https://www.twilio.com)
   - Sign up for free account ($15 credit)

2. **Get Phone Number**
   - Console → Phone Numbers → Buy a number
   - Choose number with SMS capability
   - Note your phone number

3. **Get API Credentials**
   - Console → Account → API credentials
   - Copy Account SID (starts with `AC...`)
   - Copy Auth Token (click to reveal)

## Step 3: Software Installation (5 minutes)

1. **Install Dependencies**
   ```bash
   sudo apt-get update
   sudo apt-get install -y python3-pip python3-dev libusb-1.0-0-dev
   ```

2. **Clone Repository**
   ```bash
   cd ~
   git clone https://github.com/yourusername/KID-FAX.git
   cd KID-FAX
   ```

3. **Install Python Packages**
   ```bash
   pip3 install -r requirements.txt
   ```

4. **Configure Environment**
   ```bash
   cp .env.example .env
   nano .env
   ```

5. **Edit `.env` with Your Settings**

   **Required:**
   ```bash
   TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   TWILIO_AUTH_TOKEN=your_auth_token_here
   TWILIO_NUMBER=+15551234567
   ALLOWLIST=+15551112222,+15553334444
   CONTACTS=grandma:+15551112222,uncle:+15553334444
   ```

   **USB Printer:**
   ```bash
   PRINTER_TYPE=usb
   USB_VENDOR=0x0416
   USB_PRODUCT=0x5011
   ```

   Find your printer IDs with `lsusb`

   **Serial Printer:**
   ```bash
   PRINTER_TYPE=serial
   SERIAL_PORT=/dev/serial0
   SERIAL_BAUD=19200
   ```

6. **Set Permissions (USB Printer)**
   ```bash
   sudo usermod -a -G lp,dialout $USER
   # Log out and log back in
   ```

## Step 4: Test Run (2 minutes)

1. **Start Kid Fax**
   ```bash
   python -m kidfax.sms_poller
   ```

   You should see:
   ```
   [2025-12-14 10:00:00] INFO: Starting Kid Fax SMS poller...
   [2025-12-14 10:00:00] INFO: Connecting to USB printer (vendor=0x416, product=0x5011)
   [2025-12-14 10:00:00] INFO: Printer connected successfully
   [2025-12-14 10:00:01] INFO: Polling Twilio for new messages...
   ```

2. **Send Test Message**
   - From a phone number in your ALLOWLIST
   - Text your Twilio number: "Hello Kid Fax!"
   - Within 15 seconds, it should print!

3. **Test Reply**
   ```bash
   # In another terminal (or press Ctrl+C first)
   python -m kidfax.send_sms grandma "Got your message!"
   ```

## Step 5: Auto-Start on Boot (Optional)

See [SYSTEMD_SETUP.md](SYSTEMD_SETUP.md) for complete systemd service configuration.

**Quick version:**
```bash
sudo nano /etc/systemd/system/kidfax.service
```

Paste this:
```ini
[Unit]
Description=Kid Fax SMS Poller
After=network-online.target

[Service]
User=pi
EnvironmentFile=/home/pi/KID-FAX/.env
WorkingDirectory=/home/pi/KID-FAX
ExecStart=/usr/bin/python3 -m kidfax.sms_poller
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable kidfax
sudo systemctl start kidfax
sudo systemctl status kidfax
```

## Troubleshooting

### Printer Not Found

**USB Printer:**
```bash
# Check if detected
lsusb

# Should see something like: ID 0416:5011
# Update .env with these IDs
```

**Serial Printer:**
```bash
# Check serial port exists
ls /dev/serial*

# Enable if needed
sudo raspi-config
```

### No Messages Printing

1. **Check ALLOWLIST**: Sender must be in the allowlist
   ```bash
   # In .env:
   ALLOWLIST=+15551112222,+15553334444
   ```

2. **Check Twilio Credentials**: Test sending
   ```bash
   python -m kidfax.send_sms +15551234567 "Test"
   ```

3. **Check Logs**
   ```bash
   # If running manually
   # Look at terminal output

   # If running as service
   sudo journalctl -u kidfax -f
   ```

### Test Without Printer

```bash
export ALLOW_DUMMY_PRINTER=true
python -m kidfax.sms_poller
```

This prints to console instead of hardware.

## Next Steps

- **Set up contacts**: Add family members to `.env` CONTACTS
- **Adjust polling**: Change POLL_SECONDS (default 15)
- **Add e-ink display**: See README for e-ink setup
- **Learn more**: Read [DEPLOYMENT.md](DEPLOYMENT.md) for advanced configuration

## Quick Reference

### Start Kid Fax
```bash
python -m kidfax.sms_poller
```

### Send Reply
```bash
python -m kidfax.send_sms grandma "Hi!"
```

### View Logs (if running as service)
```bash
sudo journalctl -u kidfax -f
```

### Restart Service
```bash
sudo systemctl restart kidfax
```

### Edit Configuration
```bash
nano ~/KID-FAX/.env
sudo systemctl restart kidfax  # If running as service
```

## Need Help?

- **Full Documentation**: [README.md](README.md)
- **Systemd Setup**: [SYSTEMD_SETUP.md](SYSTEMD_SETUP.md)
- **Twilio Details**: [TWILIO_SETUP.md](TWILIO_SETUP.md)
- **Troubleshooting**: [DEPLOYMENT.md](DEPLOYMENT.md)
- **Issues**: [GitHub Issues](https://github.com/yourusername/KID-FAX/issues)

---

**You're done!** 🎉 Your Kid Fax SMS mailbox is ready to receive family messages!
