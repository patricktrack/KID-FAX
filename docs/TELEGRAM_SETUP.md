# Telegram Bot Setup for Kid Fax

Complete guide to setting up your Kid Fax Telegram bot from scratch.

## Step 1: Create Your Telegram Bot

1. **Open Telegram** on your phone or computer
2. **Search for @BotFather** (the official Telegram bot creator)
3. **Start a chat** with @BotFather
4. **Send `/newbot`** command
5. **Choose a display name** for your bot
   - Example: `Kid Fax Family Bot`
   - This is what family members will see
6. **Choose a username** for your bot (must end in `bot`)
   - Example: `kidfax_family_bot`
   - Must be unique across all of Telegram
   - Can only contain letters, numbers, and underscores
7. **Save your bot token** - you'll need this later!
   - Looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz1234567890`
   - ⚠️ **Keep this secret!** Anyone with this token can control your bot

### Optional: Customize Your Bot

While still chatting with @BotFather:

```
/setdescription - Add a description (e.g., "Family messaging bot for Kid Fax")
/setabouttext - Add an about message (e.g., "Send messages to print on Kid Fax!")
/setuserpic - Upload a profile picture for your bot
```

---

## Step 2: Configure Environment

1. **Navigate to your Kid Fax directory:**
   ```bash
   cd /path/to/KID-FAX
   ```

2. **Edit your `.env` file:**
   ```bash
   nano .env
   ```

3. **Add your bot token:**
   ```bash
   TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz1234567890
   ```
   Replace with your actual token from Step 1

4. **Save and exit** (Ctrl+X, then Y, then Enter)

---

## Step 3: Discover Chat IDs

Telegram uses numeric chat IDs instead of phone numbers. You need to discover these IDs for your family members.

### 3.1 Have Family Send Test Messages

1. **Share your bot** with family members
   - Send them the username (e.g., `@kidfax_family_bot`)
   - Or share the link: `https://t.me/kidfax_family_bot`

2. **Ask each family member to:**
   - Open Telegram
   - Search for your bot by username
   - Start a chat
   - Send "hello" or any message

### 3.2 Run Discovery Script

```bash
python -m kidfax.discover_chats
```

### 3.3 Copy Output to .env

The script will output something like:

```
============================================================
TELEGRAM CHAT IDS DISCOVERED
============================================================

Chat ID: 123456789
  Name: Jane Smith
  Username: @janesmith
  Last message: hello

Chat ID: 987654321
  Name: Bob Johnson
  Username: @bobjohnson
  Last message: Hi from grandpa!

============================================================
ADD TO YOUR .env FILE:
============================================================
CONTACTS=jane:123456789,bob:987654321
ALLOWLIST=123456789,987654321
```

**Copy those two lines** and add them to your `.env` file:

```bash
nano .env
```

Add:
```bash
CONTACTS=jane:123456789,bob:987654321
ALLOWLIST=123456789,987654321
```

**Customize contact names** if desired:
```bash
CONTACTS=grandma:123456789,grandpa:987654321
```

Save and exit.

---

## Step 4: Test Your Setup

### 4.1 Start the Telegram Poller

```bash
python -m kidfax.telegram_poller
```

You should see:
```
[2025-01-15 10:30:00] INFO: Kid Fax Telegram poller started (long polling, timeout=30s)
```

### 4.2 Send a Test Message

From a family member's phone (or your own Telegram account):
1. Send a message to your bot
2. Watch your Raspberry Pi terminal - you should see:
   ```
   [2025-01-15 10:30:15] INFO: Printed message from grandma (123456789)
   ```
3. Check your thermal printer - the message should print!

### 4.3 Send a Test Photo

1. Send a photo to your bot (with or without a caption)
2. The photo will be:
   - Downloaded
   - Converted to black & white
   - Dithered (creates pixel art effect)
   - Printed below the message

### 4.4 Test Replies

From the Raspberry Pi terminal (Ctrl+C to stop the poller first):

```bash
# Send a reply to grandma
python -m kidfax.send_telegram grandma "Thank you for the message!"
```

Or using chat ID directly:
```bash
python -m kidfax.send_telegram 123456789 "Hello!"
```

---

## Step 5: Set Up as System Service (Optional)

To make Kid Fax start automatically on boot:

### 5.1 Create Service File

```bash
sudo nano /etc/systemd/system/kidfax.service
```

### 5.2 Add Service Configuration

```ini
[Unit]
Description=Kid Fax Telegram Bot
After=network-online.target

[Service]
User=pi
WorkingDirectory=/home/pi/KID-FAX
EnvironmentFile=/home/pi/KID-FAX/.env
ExecStart=/usr/bin/python3 -m kidfax.telegram_poller
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Update paths** if your installation is in a different location.

### 5.3 Enable and Start Service

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

### 5.4 View Logs

```bash
# Follow logs in real-time
sudo journalctl -u kidfax -f

# View recent logs
sudo journalctl -u kidfax -n 50
```

---

## Sending Replies (For Kids)

### Method 1: Command Line (Simple)

```bash
# Template
python -m kidfax.send_telegram <contact_name> "Your message here"

# Examples
python -m kidfax.send_telegram grandma "I love you!"
python -m kidfax.send_telegram uncle "Thanks for the birthday card"
```

### Method 2: Interactive Keyboard Mode (Advanced)

See `kidfax/interactive_keyboard.py` for F-key based messaging interface.

---

## Photo Support

### Sending Photos to Kid Fax

Family members can send photos to the bot:
- With or without captions
- Any common image format (JPEG, PNG, etc.)
- Maximum size: 5 MB (configurable)

### How Photos Are Printed

1. **Download** - Photo fetched from Telegram servers
2. **Resize** - Scaled to fit thermal printer (default: 96 pixels)
3. **Dither** - Converted to black & white using Floyd-Steinberg dithering
4. **Print** - Creates a retro "pixel art" aesthetic perfect for thermal printers!

### Disable Photo Printing

Edit `.env`:
```bash
TELEGRAM_DOWNLOAD_PHOTOS=false
```

### Adjust Photo Size

Edit `.env`:
```bash
AVATAR_SIZE=128  # Larger = more detail, but slower and more paper
# Options: 64, 96 (default), 128
```

---

## Troubleshooting

### Bot Not Receiving Messages

1. **Check bot token:**
   ```bash
   grep TELEGRAM_BOT_TOKEN .env
   ```
   Make sure it matches the token from @BotFather

2. **Test token manually:**
   ```bash
   python -m kidfax.send_telegram <chat_id> "Test"
   ```

3. **Check logs:**
   ```bash
   sudo journalctl -u kidfax -n 50
   ```

### Messages Not Printing

1. **Check allowlist:**
   - Make sure sender's chat ID is in `ALLOWLIST` in `.env`
   - Run `python -m kidfax.discover_chats` to verify chat IDs

2. **Check printer:**
   ```bash
   python3 << EOF
   from kidfax.printer import get_printer
   p = get_printer(allow_dummy=True)
   p.text("Test print\n")
   p.cut()
   EOF
   ```

3. **Test with dummy printer:**
   ```bash
   export ALLOW_DUMMY_PRINTER=true
   python -m kidfax.telegram_poller
   ```
   Send a message - you should see output in terminal even without printer

### Photos Not Printing

1. **Check photo setting:**
   ```bash
   grep TELEGRAM_DOWNLOAD_PHOTOS .env
   ```
   Should be `true`

2. **Check photo size limit:**
   ```bash
   grep TELEGRAM_MAX_PHOTO_SIZE .env
   ```
   Increase if needed (in MB)

3. **Check logs for download errors:**
   ```bash
   sudo journalctl -u kidfax -n 50 | grep photo
   ```

### Duplicate Prints

This should not happen (state tracking prevents it). If it does:

1. **Check state file:**
   ```bash
   cat ~/.kidfax_state.json
   ```

2. **Clear state** (will re-print recent messages):
   ```bash
   rm ~/.kidfax_state.json
   ```

3. **Restart service:**
   ```bash
   sudo systemctl restart kidfax
   ```

---

## Adding New Family Members

1. **Have them message the bot** (any message)
2. **Run discovery script:**
   ```bash
   python -m kidfax.discover_chats
   ```
3. **Update `.env`** with new chat ID:
   ```bash
   nano .env
   ```
   Add to CONTACTS and ALLOWLIST:
   ```bash
   CONTACTS=grandma:123456789,uncle:987654321,aunt:555666777
   ALLOWLIST=123456789,987654321,555666777
   ```
4. **Restart service:**
   ```bash
   sudo systemctl restart kidfax
   ```

---

## Security & Privacy

### Bot Token Security

- **Never share** your bot token publicly
- **Don't commit** `.env` to git (it's in `.gitignore`)
- **If compromised:** Revoke token via @BotFather and create a new bot

### Allowlist (Kid Safety)

The `ALLOWLIST` setting is **critical for kid safety**:
- Only chat IDs in the allowlist can send messages that print
- Unknown senders are ignored (logged but not printed)
- Prevents spam and unwanted messages

**Always use an allowlist** unless you have a specific reason not to.

### Message Privacy

- Messages are sent over Telegram (end-to-end encrypted)
- Bot API sees message content (required for printing)
- Messages are not stored permanently (only update IDs in state file)
- No cloud database - everything stays on your Raspberry Pi

---

## Advanced Configuration

### Change Polling Timeout

Edit `.env`:
```bash
TELEGRAM_POLL_TIMEOUT=60  # Increase timeout (more efficient but slightly higher latency)
```

### Multiple Bots (Different Families)

Create separate bots for different families:

1. Create multiple bots via @BotFather
2. Use different `.env` files
3. Run multiple instances with different config files
4. Use different systemd service names

---

## Cost Comparison

### SMS (Twilio) - Old Method
- **Cost:** ~$0.0079 per message
- **Annual (50 msgs/week):** ~$205/year
- **Photos:** Requires MMS (~$0.02/message)

### Telegram - New Method
- **Cost:** $0 (FREE!)
- **Annual:** $0
- **Photos:** Included, unlimited

**Savings:** ~$205/year + unlimited photos!

---

## Need Help?

1. **Check logs:** `sudo journalctl -u kidfax -f`
2. **Read troubleshooting** section above
3. **Test components** individually (bot token, printer, chat IDs)
4. **Ask for help:** [GitHub Issues](https://github.com/yourusername/KID-FAX/issues)

---

## What's Next?

- ✅ Bot is running and printing messages
- ✅ Family can send photos that print as pixel art
- ✅ Kids can send replies

**Optional Enhancements:**
- Add avatars for family members (see `kidfax/avatar_manager.py`)
- Set up E-ink display for message counter
- Configure interactive keyboard mode for easier replies
- Customize message formatting and printer settings
