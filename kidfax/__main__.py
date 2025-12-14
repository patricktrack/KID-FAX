"""Make kidfax modules runnable with python -m kidfax.module_name."""
import sys

if __name__ == "__main__":
    # This file is intentionally minimal
    # Use: python -m kidfax.admin_web
    # Use: python -m kidfax.interactive_keyboard
    # Use: python -m kidfax.sms_poller
    # Use: python -m kidfax.send_sms
    print("Usage:")
    print("  python -m kidfax.admin_web          # Admin web interface")
    print("  python -m kidfax.interactive_keyboard  # Interactive keyboard mode")
    print("  python -m kidfax.sms_poller         # SMS polling service")
    print("  python -m kidfax.send_sms <contact> <message>  # Send SMS")
    sys.exit(1)
