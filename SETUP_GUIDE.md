# Kid Fax Setup Guide - Complete Walkthrough

**For Non-Technical Users**

This guide will walk you through setting up Kid Fax from scratch. No prior technical experience required!

⏱️ **Total time**: 30-45 minutes
🛠️ **Difficulty**: Easy (just follow the steps!)

---

## What You'll Need

### Required Hardware

- [ ] **Raspberry Pi** (any model with WiFi)
  - Raspberry Pi 400 Computer Kit is ideal (has keyboard built-in)
  - Or: Raspberry Pi 4 + keyboard + monitor + mouse
- [ ] **Power supply** for Raspberry Pi (usually included with Pi)
- [ ] **MicroSD card** (32GB or larger, with Raspberry Pi OS installed)
- [ ] **Thermal receipt printer** (58mm, USB connection)
  - Recommended: Netum 58mm USB printer
- [ ] **Thermal printer paper** (58mm rolls)
- [ ] **Internet connection** (WiFi or Ethernet)

### Optional Hardware

- [ ] **E-ink display** (2.9" Waveshare HAT) - shows message counter
- [ ] **Keyboard** (if not using Pi 400)
- [ ] **Monitor with HDMI** (for setup)

### Required Accounts

- [ ] **Twilio account** (for SMS) - Sign up at [twilio.com](https://www.twilio.com)
  - You'll need a credit/debit card (pay-as-you-go, very cheap)
  - Costs about $1/month for a phone number + $0.0075 per SMS

---

## Step 1: Assemble the Hardware (5 minutes)

### Connect the Printer

1. **Unbox your thermal printer**
2. **Plug the USB cable** into the printer
3. **Plug the other end of USB cable** into your Raspberry Pi
4. **Plug in the printer's power adapter** (if it has one)
5. **Turn on the printer** - you should see a light come on
6. **Load paper**:
   - Open the printer cover
   - Insert a roll of thermal paper (shiny side down)
   - Close the cover - it should feed the paper out a bit

✅ **Success check**: Printer light is on and paper feeds smoothly

### Connect the Raspberry Pi

1. **Insert the microSD card** into the Raspberry Pi
2. **Connect keyboard** (USB port)
3. **Connect mouse** (USB port)
4. **Connect monitor** (HDMI port)
5. **Connect to power** - Pi will turn on automatically

✅ **Success check**: You see Raspberry Pi logo on screen

### Optional: E-ink Display

1. **Carefully attach** the e-ink HAT to the GPIO pins on top of the Pi
2. Make sure all pins are aligned
3. Press down gently until fully seated

---

## Step 2: First-Time Raspberry Pi Setup (10 minutes)

*Skip this if your Raspberry Pi is already set up*

When Raspberry Pi boots for the first time:

1. **Choose your language and timezone**
2. **Set a password** (write it down!)
3. **Connect to WiFi**:
   - Click WiFi icon in top-right corner
   - Select your network
   - Enter WiFi password
4. **Update software** (click "Next" when prompted - this takes 5-10 minutes)
5. **Restart** when prompted

✅ **Success check**: You see the desktop with icons

---

## Step 3: Get a Twilio Phone Number (5 minutes)

Twilio provides the SMS service for Kid Fax.

### Create Twilio Account

1. **Go to** [twilio.com](https://www.twilio.com)
2. **Click "Sign Up"**
3. **Fill out the form**:
   - Email address
   - Create a password
   - Phone number (for verification)
4. **Verify your email** (check inbox)
5. **Verify your phone** (enter code they text you)

### Get Your First Phone Number

1. **Log into Twilio Console**
2. **Click "Get a Trial Number"** (or "Buy a Number" if you've upgraded)
3. **Accept the number** Twilio suggests (or search for a specific area code)
4. **Write down this number** - this is the number family will text!

### Get Your Credentials

You need 3 pieces of information from Twilio:

1. **Go to Twilio Console** (console.twilio.com)
2. **Look for "Account Info"** section on the dashboard
3. **Write down**:
   - **Account SID** (starts with "AC...")
   - **Auth Token** (click to reveal, then copy)
   - **Phone Number** (the one you just got, format: +15551234567)

⚠️ **Important**: Keep these secret! They're like your password.

✅ **Success check**: You have 3 items written down

---

## Step 4: Install Kid Fax Software (10 minutes)

### Open Terminal

1. **Click** the black terminal icon in the top menu bar
2. A black window will appear - this is where you type commands

### Install Kid Fax

**Copy and paste** these commands one at a time. After each command, press **Enter** and wait for it to finish.

```bash
# 1. Update your system
sudo apt-get update
```
*(Takes 1-2 minutes)*

```bash
# 2. Install required software
sudo apt-get install -y python3-pip python3-dev libusb-1.0-0-dev git
```
*(Takes 2-3 minutes)*

```bash
# 3. Download Kid Fax
cd ~
git clone https://github.com/yourusername/KID-FAX.git
cd KID-FAX
```

```bash
# 4. Install Python packages
pip3 install -r requirements.txt
```
*(Takes 3-5 minutes)*

✅ **Success check**: No red error messages (yellow warnings are OK)

---

## Step 5: Configure Kid Fax (5 minutes)

### Create Configuration File

```bash
# Copy the example file
cp .env.example .env
```

### Edit Configuration File

```bash
# Open the file for editing
nano .env
```

You'll see a text file open. **Use arrow keys** to move around.

### Fill In Your Information

Find these lines and **replace** the placeholder text with your real information:

```bash
# Twilio Settings
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_NUMBER=+15551234567
```

**Replace with YOUR values** from Step 3:
- `ACxxxxxxxx...` → Your actual Account SID
- `your_auth_token_here` → Your actual Auth Token
- `+15551234567` → Your actual Twilio phone number

### Add Your Family's Phone Numbers

Find this line:
```bash
ALLOWLIST=+15551112222,+15553334444
```

**Replace** with your family's phone numbers (must start with `+1` for US):
```bash
ALLOWLIST=+15551234567,+15559876543
```

*Separate multiple numbers with commas, no spaces*

Find this line:
```bash
CONTACTS=grandma:+15551112222,uncle:+15553334444
```

**Replace** with your family's names and numbers:
```bash
CONTACTS=grandma:+15551234567,dad:+15559876543
```

*Format: name:number,name:number*

### Set Admin Password

Find this line:
```bash
ADMIN_PASSWORD=your_secure_password_here
```

**Replace** with a password you'll remember:
```bash
ADMIN_PASSWORD=KidFax2024!
```

### Save the File

1. Press **Ctrl + X** to exit
2. Press **Y** to save
3. Press **Enter** to confirm

✅ **Success check**: You're back at the command prompt

---

## Step 6: Find Your Printer (5 minutes)

### Test Printer Connection

```bash
lsusb
```

You should see a line that says something like:
```
Bus 001 Device 004: ID 0416:5011 Random Printer Company
```

The important part is the two numbers: `0416:5011`

### Update Printer Settings

```bash
nano .env
```

Find these lines:
```bash
USB_VENDOR=0x0416
USB_PRODUCT=0x5011
```

**Replace** with YOUR printer's numbers (add `0x` at the start):
- If your printer showed `0416:5011`
- Then use: `USB_VENDOR=0x0416` and `USB_PRODUCT=0x5011`

**Save**: Ctrl + X, then Y, then Enter

✅ **Success check**: Numbers match what you saw in lsusb

---

## Step 7: Test Everything! (5 minutes)

### Test the Printer

```bash
python3 -c "
from kidfax.printer import get_printer
p = get_printer(allow_dummy=False)
if p:
    p.text('Hello from Kid Fax!\n\n\n')
    p.cut()
    print('✓ Printer test successful!')
else:
    print('✗ Printer not found')
"
```

✅ **Success check**: A receipt prints with "Hello from Kid Fax!"

⚠️ **If it doesn't print**:
- Check printer is turned on
- Check USB cable is connected
- Check paper is loaded
- Try a different USB port

### Start Kid Fax SMS Service

```bash
python -m kidfax.sms_poller
```

You should see:
```
Kid Fax SMS poller started (polling every 15s)
```

**Leave this running!** *(Don't close this window)*

### Send Your First Message!

1. **Grab your phone**
2. **Send a text to your Twilio number** (the one you got in Step 3)
3. **Type**: "Hello Kid Fax!"
4. **Send it**

⏱️ **Wait 15 seconds** (Kid Fax checks for new messages every 15 seconds)

✅ **Success check**: The receipt printer comes to life and prints your message!

🎉 **IT WORKS!** You've successfully set up Kid Fax!

---

## Step 8: Make It Start Automatically (Optional)

Right now, Kid Fax stops when you close the terminal. Let's make it run automatically!

### Stop the Current Process

In the terminal window, press **Ctrl + C**

### Create Auto-Start Service

```bash
sudo nano /etc/systemd/system/kidfax.service
```

**Copy and paste** this entire block:

```ini
[Unit]
Description=Kid Fax SMS Poller
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/KID-FAX
EnvironmentFile=/home/pi/KID-FAX/.env
ExecStart=/usr/bin/python3 -m kidfax.sms_poller
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Save**: Ctrl + X, then Y, then Enter

### Enable Auto-Start

```bash
# Enable the service
sudo systemctl enable kidfax

# Start the service now
sudo systemctl start kidfax

# Check it's running
sudo systemctl status kidfax
```

You should see **"active (running)"** in green.

**Press Q** to exit the status view.

✅ **Success check**: Kid Fax is now running in the background!

### Useful Commands

```bash
# Stop Kid Fax
sudo systemctl stop kidfax

# Start Kid Fax
sudo systemctl start kidfax

# Restart Kid Fax (after changing settings)
sudo systemctl restart kidfax

# View recent messages/errors
sudo journalctl -u kidfax -f
```

*(Press Ctrl + C to stop viewing logs)*

---

## Step 9: Set Up Contact Avatars (Optional - Fun!)

Add pixel art portraits that print with each message!

### Start the Admin Interface

```bash
python -m kidfax.admin_web
```

You'll see:
```
Running on: http://127.0.0.1:5000/admin
```

### Open in Browser

1. **Open the web browser** on your Raspberry Pi (usually Firefox or Chromium)
2. **Type in the address bar**: `http://localhost:5000/admin`
3. **Login**:
   - Username: *(leave blank or type anything)*
   - Password: *(the ADMIN_PASSWORD you set in Step 5)*

### Upload Avatars

1. **Find a contact** in the table
2. **Click "+ Add Avatar"**
3. **Click "Select PNG Image"**
4. **Choose a photo**:
   - Square photos work best (like profile pictures)
   - Any size is fine - it'll be resized automatically
   - Must be PNG format
5. **Click "Upload Avatar"**
6. **Wait** - the image will be converted to pixel art
7. **Success!** You'll see a thumbnail in the Avatar column

### Test It

1. **Send a text from that contact's phone**
2. **Watch the printer** - their pixel art portrait prints above the message!

---

## Troubleshooting

### "Printer not found"

**Try**:
1. Unplug printer USB, wait 5 seconds, plug back in
2. Try a different USB port
3. Check printer is turned on
4. Run `lsusb` and verify your printer appears
5. Check `USB_VENDOR` and `USB_PRODUCT` in `.env` match your printer

### "No messages printing"

**Check**:
1. Is the sender's number in `ALLOWLIST`?
2. Did you send to the correct Twilio number?
3. Is Kid Fax running? (`sudo systemctl status kidfax`)
4. Check logs: `sudo journalctl -u kidfax -n 50`

### "Invalid Twilio credentials"

**Fix**:
1. Double-check `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN` in `.env`
2. Make sure you copied them exactly (no extra spaces)
3. Try generating a new Auth Token in Twilio console

### "Out of paper" or "Paper jam"

1. Open printer cover
2. Remove any jammed paper
3. Load new roll (shiny side down)
4. Close cover firmly

### Kid Fax stopped working after restart

**Check**:
1. Did you enable the systemd service? (`sudo systemctl enable kidfax`)
2. Check if it's running: `sudo systemctl status kidfax`
3. If not running: `sudo systemctl start kidfax`

### Can't access admin interface

1. Make sure admin web is running: `python -m kidfax.admin_web`
2. Try: `http://localhost:5000/admin` (not `127.0.0.1`)
3. Check your admin password in `.env`

---

## Kids Can Reply! (Keyboard Mode)

If you have a keyboard connected (or using Pi 400):

### Start Interactive Mode

```bash
python -m kidfax.interactive_keyboard
```

### How Kids Use It

1. **Press F1** - Send to first contact (e.g., Grandma)
2. **Press F2** - Send to second contact (e.g., Dad)
3. **Type the message** using the keyboard
4. **Press Enter** to send

### Add Stickers

Print or write contact names on stickers and place above F1-F12 keys so kids know who each key sends to!

---

## Daily Use

### For Kids

1. **Wait for printer** to print when a message arrives
2. **Read the message**
3. **To reply**:
   - Press the F-key for that person (F1 = Grandma, etc.)
   - Type your message
   - Press Enter

### For Parents (Managing Contacts)

1. **Start admin**: `python -m kidfax.admin_web`
2. **Open**: `http://localhost:5000/admin`
3. **Add/remove contacts** and phone numbers
4. **Upload avatars** for family members
5. **Add to allowlist** if grandma gets a new phone number

### For Family Members

**Just text the Kid Fax phone number!**
(The Twilio number you got in Step 3)

Example:
```
To: +15551234567
"Hi sweetie! How was school today? Love, Grandma 💕"
```

15 seconds later → Receipt prints with Grandma's pixel art face!

---

## Cost Breakdown

- **Raspberry Pi 400 Kit**: ~$100 (one-time)
- **Thermal Printer**: ~$40 (one-time)
- **Thermal Paper (5 rolls)**: ~$15 (lasts months)
- **Twilio Phone Number**: ~$1/month
- **SMS Messages**: ~$0.0075 per message
  - 100 messages/month = $0.75
  - 500 messages/month = $3.75

**Total first month**: ~$165
**Ongoing monthly**: ~$2-5 depending on usage

---

## Tips for Success

### For Kids
- 📸 **Use avatars!** Kids love seeing faces on receipts
- 🎨 **Let kids decorate** the printer area
- 🏷️ **Label F-keys** with stickers so they know who's who
- 💌 **Keep receipts** in a special box - they're keepsakes!

### For Parents
- 🔋 **Leave it running 24/7** so messages arrive anytime
- 📱 **Add grandparents to allowlist** first
- ⚡ **Start with one roll of paper** to test
- 🛡️ **Don't share Twilio number publicly** (only family)

### For Grandparents
- ✅ **Save the Kid Fax number** as a contact
- 💬 **Keep messages short** (receipts are small!)
- 😊 **Use emojis** - they print as cute symbols
- ⏰ **Messages arrive in ~15 seconds** after sending

---

## Getting Help

### Documentation
- **Full README**: See `README.md` in the KID-FAX folder
- **Admin Guide**: See `ADMIN_WEB.md` for web interface help
- **Keyboard Mode**: See `KEYBOARD_MODE.md` for reply setup

### Check Logs
```bash
# See what Kid Fax is doing
sudo journalctl -u kidfax -f
```

### Need More Help?
- 📖 Check the README files in the KID-FAX folder
- 🐛 Report issues: [GitHub Issues](https://github.com/yourusername/KID-FAX/issues)

---

## You Did It! 🎉

Kid Fax is now running! Family members can send texts that magically print out, and kids can reply using the keyboard.

**Enjoy staying connected!** 💌🖨️

---

*Made with ❤️ for families who love staying connected*
