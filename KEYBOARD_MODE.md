# Kid Fax Interactive Keyboard Mode

**Send SMS messages using function keys (F1-F12) and your keyboard - designed for kids!**

## Overview

Interactive Keyboard Mode transforms Kid Fax from CLI-based replies into a tactile, kid-friendly messaging experience. Kids can reply to family messages using physical keyboard shortcuts.

### How It Works

1. **Press F1-F12** to select a recipient (each key mapped to a family member)
2. **Type your message** and see it appear on the e-ink display
3. **Press Enter** to send the SMS
4. **Optional receipt** prints on thermal printer as confirmation

### Hardware Requirements

- **Raspberry Pi 400 Computer Kit** (built-in keyboard with F1-F12 function keys)
  - Or any keyboard with F1-F12 keys connected to Raspberry Pi
- **Waveshare 2.9" e-Paper HAT** (optional but recommended for visual feedback)
- **Thermal printer** (58mm ESC/POS compatible)

## Quick Start

### 1. Configure Contacts

Edit your `.env` file to map contacts to function keys:

```bash
# First 12 contacts map to F1-F12
CONTACTS=grandma:+15551112222,uncle:+15553334444,mom:+15559998888,dad:+15554445555
```

**F-key mapping:**
- F1 = first contact (grandma)
- F2 = second contact (uncle)
- F3 = third contact (mom)
- F4 = fourth contact (dad)
- Maximum 12 contacts (F1-F12 limit)

### 2. Enable E-ink Display (Optional)

```bash
EINK_STATUS_ENABLED=true
EINK_DRIVER_MODULE=epd2in9d
```

### 3. Start Interactive Mode

```bash
python -m kidfax.interactive_keyboard
```

### 4. Send a Message

```
Kid Fax - Interactive Keyboard Mode
==================================================
Press F1-F12 to select a recipient:
  F1: Grandma
  F2: Uncle
  F3: Mom
  F4: Dad

Press ESC to exit
==================================================
```

**Workflow:**
1. Press **F1** (Grandma)
2. Type: `Thanks for the cookies! They were delicious!`
3. Press **Enter**
4. ✓ Message sent!

## Physical Sticker Setup

Add stickers above each function key on your keyboard to help kids remember who each key represents.

### DIY Sticker Template

**Materials:**
- Masking tape or label maker
- Permanent marker
- Clear tape (optional - to protect labels)

**Placement:**
```
┌─────┬─────┬─────┬─────┐
│ F1  │ F2  │ F3  │ F4  │  ← Function keys on keyboard
└─────┴─────┴─────┴─────┘
   ↑     ↑     ↑     ↑
Grandma Uncle Mom  Dad    ← Add stickers here with names
```

**Tips:**
- Use different colored stickers for each person
- Draw small pictures/emojis to help younger kids
- Laminate stickers for durability
- Update stickers if you change CONTACTS configuration

### Printable Labels

You can create printable labels sized for keyboard keys:
- **Size**: ~14mm x 14mm squares
- **Font**: Large, bold, easy-to-read
- **Colors**: Bright colors for each contact
- **Material**: Use adhesive paper or label sheets

## E-ink Display Layouts

### Contact Selection Screen

```
┌─────────────────────────┐
│ Kid Fax - Reply Mode    │
│ ─────────────────────   │
│ F1  Grandma             │
│ F2  Uncle               │
│ F3  Mom                 │
│ F4  Dad                 │
│                         │
│ Press F-key to reply    │
└─────────────────────────┘
```

### Message Composition Screen

```
┌─────────────────────────┐
│ To: Grandma             │  ← Selected recipient (bold)
│ ─────────────────────   │
│ Thanks for the cookies! │  ← Message text (live updates)
│ They were delicious. Lo │
│ ve you! See you soon!   │
│                         │
│ [64/160]          ENTER │  ← Character count + hint
└─────────────────────────┘
```

### Send Confirmation

```
┌─────────────────────────┐
│                         │
│                         │
│         ✓               │  ← Success icon
│       Sent!             │
│   To: Grandma           │
│                         │
│                         │
└─────────────────────────┘
```

## Configuration Options

### SMS Character Limit

```bash
# Single SMS segment (default)
SMS_CHAR_LIMIT=160

# Multi-segment SMS (allows longer messages, costs more)
SMS_CHAR_LIMIT=320
```

**Character count guide:**
- 1 segment = 160 chars ($0.0079 per SMS)
- 2 segments = 306 chars ($0.0158)
- 3 segments = 459 chars ($0.0237)

### Receipt Printing

Enable optional receipt printing for send confirmation:

```bash
PRINT_SEND_RECEIPTS=true
```

**Receipt format:**
```
================================
MESSAGE SENT
--------------------------------
To: Grandma
Time: 2025-12-14 16:30
--------------------------------
Thanks for the cookies!
They were delicious. Love you!
See you soon!
--------------------------------
✓ Delivered via SMS
================================
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| **F1-F12** | Select recipient (mapped to first 12 contacts) |
| **A-Z, 0-9, Space, Punctuation** | Type message |
| **Backspace** | Delete last character |
| **Enter** | Send message |
| **ESC** | Exit interactive mode |

**Not yet supported** (future enhancements):
- Shift+Enter: New line within message
- Ctrl+F1-F12: Quick emoji shortcuts
- Ctrl+C: Cancel current message

## Troubleshooting

### Function Keys Not Working

**Problem**: Pressing F1-F12 doesn't select recipient

**Solutions:**

1. **Check if keys are captured by terminal/OS:**
   ```bash
   # Test keyboard input
   python3 -c "from pynput import keyboard; keyboard.Listener(on_press=print).start().join()"
   # Press F1 - should show: Key.f1
   ```

2. **Disable terminal function key shortcuts:**
   - In LXTerminal: Edit → Preferences → Disable shortcuts
   - In SSH session: May not work - use physical keyboard on Pi

3. **Run with elevated permissions (if needed):**
   ```bash
   sudo python -m kidfax.interactive_keyboard
   ```

### No Recipient Selected Message

**Problem**: Typing without selecting recipient shows error

**Solution**: Press F1-F12 first to select a recipient before typing

### Character Limit Reached

**Problem**: Can't type more characters

**Solution**:
- Check `SMS_CHAR_LIMIT` in `.env` (default 160)
- Delete characters with Backspace
- Send current message and compose a second one

### E-ink Display Not Updating

**Problem**: Screen shows old content or stays blank

**Solutions:**

1. **Check e-ink is enabled:**
   ```bash
   EINK_STATUS_ENABLED=true
   ```

2. **Verify driver module:**
   ```bash
   # Check e-Paper library is installed
   ls e-Paper/RaspberryPi_JetsonNano/python/lib/waveshare_epd/
   # Should show: epd2in9d.py (or your model)
   ```

3. **Check logs for errors:**
   ```bash
   # Enable debug logging
   KIDFAX_LOG_LEVEL=DEBUG python -m kidfax.interactive_keyboard
   ```

4. **Power cycle e-ink display:**
   ```bash
   # Reboot Raspberry Pi
   sudo reboot
   ```

### Message Not Sending

**Problem**: Message shows "Error!" after pressing Enter

**Solutions:**

1. **Check Twilio credentials:**
   ```bash
   # Test sending manually
   python -m kidfax.send_sms +15551234567 "test"
   ```

2. **Verify recipient phone number format:**
   - Must be E.164 format: `+15551234567`
   - Not `1-555-123-4567` or `(555) 123-4567`

3. **Check Twilio account balance:**
   - Login to console.twilio.com
   - Verify you have credit

### Keyboard Listener Doesn't Start

**Problem**: Error on startup: "Permission denied" or "No module named pynput"

**Solutions:**

1. **Install pynput:**
   ```bash
   pip install pynput==1.7.6
   ```

2. **Check dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run with sudo (if permission error):**
   ```bash
   sudo python3 -m kidfax.interactive_keyboard
   ```

## Advanced Configuration

### Contact Ordering

Contacts are mapped to F-keys in the order they appear in `CONTACTS`:

```bash
# This order determines F-key mapping
CONTACTS=alice:+1555...,bob:+1555...,carol:+1555...
# F1 = alice, F2 = bob, F3 = carol
```

To reorder, just rearrange the CONTACTS string:

```bash
# Change F1 to bob instead of alice
CONTACTS=bob:+1555...,alice:+1555...,carol:+1555...
# F1 = bob, F2 = alice, F3 = carol
```

### Running Alongside SMS Poller

You can run both polling mode and keyboard mode simultaneously:

**Terminal 1** (SMS poller):
```bash
python -m kidfax.sms_poller
```

**Terminal 2** (Keyboard mode):
```bash
python -m kidfax.interactive_keyboard
```

**Note**: Only one process can update the e-ink display at a time. If running both:
- Turn off e-ink in poller: `EINK_STATUS_ENABLED=false` for sms_poller
- Enable e-ink in keyboard mode: `EINK_STATUS_ENABLED=true` for interactive_keyboard

### Auto-Start on Boot

Create a systemd service to auto-start keyboard mode on boot:

```bash
sudo nano /etc/systemd/system/kidfax-keyboard.service
```

**Service file:**
```ini
[Unit]
Description=Kid Fax Interactive Keyboard
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/KID-FAX
Environment="DISPLAY=:0"
EnvironmentFile=/home/pi/KID-FAX/.env
ExecStart=/usr/bin/python3 -m kidfax.interactive_keyboard
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

**Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable kidfax-keyboard
sudo systemctl start kidfax-keyboard
```

## Safety & Privacy

### Allowlist Protection

Even though kids can send to anyone in CONTACTS, you control who's in that list.

**Best practices:**
- Only add trusted family members to CONTACTS
- Keep ALLOWLIST updated (who can send TO Kid Fax)
- Review CONTACTS periodically
- Remove contacts if needed

### Message Logging

Interactive keyboard mode:
- **Does NOT** log message content to files
- **Does** log metadata (timestamp, recipient name, success/failure)
- **Never** commits messages to git

**Log location**: Console output only (not saved to disk)

### Parental Controls

Suggestions for keeping keyboard mode safe:
1. **Supervise**: Keep Raspberry Pi in common area
2. **Review**: Check CONTACTS list regularly
3. **Limit**: Use SMS_CHAR_LIMIT to prevent long messages
4. **Receipt printing**: Enable `PRINT_SEND_RECEIPTS=true` to track what was sent
5. **Twilio usage**: Monitor Twilio console for message history

## Future Enhancements

Planned features for future releases:

- [ ] **Multi-line messages**: Shift+Enter for line breaks
- [ ] **Emoji shortcuts**: Ctrl+F1-F12 for common emojis (❤️, 😊, 👍)
- [ ] **Quick replies**: Shift+F1-F12 for pre-written messages ("Thanks!", "Love you!")
- [ ] **Message templates**: Save frequently used messages
- [ ] **Group messages**: Send to multiple recipients at once
- [ ] **Voice input**: Microphone support for voice-to-text
- [ ] **MMS support**: Attach photos from USB camera
- [ ] **Message history**: View recent sent messages on e-ink
- [ ] **Contact pagination**: F11/F12 for next/previous page (support 24+ contacts)

## Credits

Interactive Keyboard Mode designed for **Raspberry Pi 400 Computer Kit** - the perfect kid-friendly messaging device!

**Made with ❤️ for families**

For questions or issues, see [CONTRIBUTING.md](CONTRIBUTING.md) or open an issue on GitHub.
