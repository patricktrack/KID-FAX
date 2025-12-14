# Twilio Setup Guide for Kid Fax

Complete guide to setting up Twilio for your Kid Fax SMS mailbox.

## What You'll Need

- Credit card (for Twilio verification, even for free tier)
- Phone number for account verification
- ~$5-10 for initial phone number purchase and testing

## Step 1: Create Twilio Account

1. **Go to Twilio**
   - Visit [www.twilio.com](https://www.twilio.com)
   - Click "Sign up"

2. **Sign Up**
   - Enter your email
   - Create password
   - Verify email address

3. **Verify Phone Number**
   - Twilio will send verification code
   - Enter code to verify your identity

4. **Free Trial Credit**
   - New accounts get $15 free credit
   - Enough for testing and initial setup

## Step 2: Purchase Phone Number

1. **Go to Phone Numbers Console**
   - Dashboard → Phone Numbers → Manage → Buy a number

2. **Select Country**
   - Choose your country (e.g., United States)

3. **Filter Capabilities**
   - Check "SMS" (required)
   - Check "MMS" (optional, for future image support)
   - Uncheck "Voice" (not needed, saves money)

4. **Search for Number**
   - Click "Search"
   - Browse available numbers
   - Look for local numbers in your area code (easier for family to remember)

5. **Purchase**
   - Click "Buy" next to chosen number
   - Confirm purchase (~$1-2/month)
   - Note: Some numbers are more expensive (toll-free, vanity numbers)

6. **Save Your Number**
   - Copy the number in E.164 format: `+15551234567`
   - You'll need this for `.env` file

## Step 3: Get API Credentials

1. **Go to Console Dashboard**
   - [console.twilio.com](https://console.twilio.com)

2. **Find Account Info**
   - Look for "Account Info" section
   - You'll see:
     - **Account SID**: Starts with `AC...`
     - **Auth Token**: Click eye icon to reveal

3. **Copy Credentials**
   - Account SID: `ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` (34 characters)
   - Auth Token: `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` (32 characters)

4. **Keep Credentials Secure**
   - Never share these publicly
   - Never commit to git
   - Store only in `.env` file

## Step 4: Configure Kid Fax

Edit your `.env` file:

```bash
cd ~/KID-FAX
nano .env
```

Add these values:

```bash
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_32_character_auth_token
TWILIO_NUMBER=+15551234567
```

## Step 5: Configure Allowlist and Contacts

### Allowlist (Required for Safety)

Only numbers in the allowlist can send messages to Kid Fax:

```bash
ALLOWLIST=+15551112222,+15553334444,+15559998888
```

- **Format**: E.164 (international format with + prefix)
- **Multiple numbers**: Comma-separated, no spaces
- **Recommended**: Keep this list small for kid safety

### Contacts (Optional but Helpful)

Map names to numbers for easy replies:

```bash
CONTACTS=grandma:+15551112222,uncle:+15553334444,mom:+15559998888
```

Then you can send replies with:

```bash
python -m kidfax.send_sms grandma "Thanks for the message!"
```

Instead of:

```bash
python -m kidfax.send_sms +15551112222 "Thanks for the message!"
```

## Step 6: Test Configuration

### Test Sending SMS

```bash
python -m kidfax.send_sms +15551234567 "Test message"
```

If successful, you should see:

```
Message sent successfully. SID: SMxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Test Receiving SMS

1. Start Kid Fax poller:
   ```bash
   python -m kidfax.sms_poller
   ```

2. From a phone in your ALLOWLIST, text your Twilio number:
   ```
   Hello Kid Fax!
   ```

3. Within 15 seconds, it should print!

## Twilio Pricing

### Phone Number
- **US Local Number**: ~$1.00-$2.00/month
- **US Toll-Free**: ~$2.00/month
- **International**: Varies by country

### SMS Messaging
- **Outbound SMS (US)**: $0.0079/message
- **Inbound SMS (US)**: $0.0079/message
- **International**: Higher rates, check pricing page

### Example Monthly Cost

For a family sending 20 messages/day:

- Phone number: $1.50/month
- Inbound SMS: 20 msg × 30 days × $0.0079 = $4.74/month
- Outbound SMS: 10 msg × 30 days × $0.0079 = $2.37/month
- **Total**: ~$8.61/month

### Free Trial Limits

- $15 credit for new accounts
- Can only send to verified phone numbers
- Messages show "Sent from a Twilio trial account"

### Upgrading Account

To send to non-verified numbers and remove trial message:

1. Dashboard → Billing → Upgrade account
2. Add payment method
3. Make initial payment (~$20 minimum)

## A2P 10DLC Registration (US Only)

If sending to US phone numbers, you may need to register for A2P 10DLC:

### What is A2P 10DLC?
- Application-to-Person messaging over 10-digit long codes
- Required by US carriers for business messaging
- Reduces spam, improves deliverability

### When You Need It
- **Personal use**: Low volume (< 100 msg/day) may not require
- **Multiple recipients**: Higher volume requires registration
- **Carrier filtering**: If messages aren't delivering, register

### How to Register

1. **Create Brand**
   - Go to Messaging → Regulatory Compliance → Brands
   - Click "Create a brand"
   - Fill in business information (or personal use)

2. **Create Campaign**
   - After brand approval, create campaign
   - Select use case: "2FA" or "Notifications"
   - Describe: "Family messaging for kids"

3. **Register Phone Number**
   - Messaging → Phone Numbers → Select number
   - Attach to campaign

4. **Cost**
   - Brand registration: One-time $4 fee
   - Campaign registration: ~$10/month
   - **Note**: Only needed if experiencing delivery issues

## Troubleshooting

### Messages Not Sending

1. **Check credentials**:
   ```bash
   python -m kidfax.send_sms +1234 "test"
   # Look for error message
   ```

2. **Common errors**:
   - `Unauthorized`: Wrong Account SID or Auth Token
   - `Invalid To number`: Wrong phone number format
   - `From number not purchased`: Wrong Twilio number in .env

### Messages Not Receiving

1. **Check allowlist**:
   - Sender must be in `ALLOWLIST`
   - Format must be E.164: `+15551234567`

2. **Check Twilio console**:
   - Go to Monitor → Logs → Messages
   - See if messages are arriving at Twilio
   - Check for delivery errors

3. **Test with Twilio console**:
   - Phone Numbers → Active Numbers → Select number
   - Send test message from Twilio website

### Free Trial Limitations

If on free trial:

1. **Verify recipient numbers**:
   - Console → Phone Numbers → Verified Caller IDs
   - Add and verify each family member's number

2. **Trial message prefix**:
   - All messages show: "Sent from a Twilio trial account"
   - Upgrade account to remove

### International Numbers

For non-US numbers:

1. **Check Twilio coverage**:
   - [www.twilio.com/international](https://www.twilio.com/international)
   - Some countries require additional verification

2. **Geographic Permissions**:
   - Console → Messaging → Settings → Geo Permissions
   - Enable countries you need

## Security Best Practices

### Protect Credentials

```bash
# Secure .env file
chmod 600 ~/KID-FAX/.env

# Never commit .env
echo ".env" >> ~/.gitignore
```

### Rotate Auth Token

If credentials are compromised:

1. Console → Account → API keys & tokens
2. Click "View" next to Auth Token
3. Click "Refresh" to generate new token
4. Update `.env` file

### Monitor Usage

- Console → Monitor → Usage
- Set up usage alerts:
  - Console → Account → Notifications
  - Alert if usage > $X per day

### Enable Two-Factor Authentication

- Console → Account → Security
- Enable 2FA for account protection

## Next Steps

- **Test thoroughly**: Send/receive several messages
- **Set up auto-start**: See [SYSTEMD_SETUP.md](SYSTEMD_SETUP.md)
- **Monitor costs**: Check Twilio console monthly
- **Add family numbers**: Update ALLOWLIST and CONTACTS

Your Twilio setup is complete! 🎉
