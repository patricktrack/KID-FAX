#!/usr/bin/env python3
"""Admin web interface for Kid Fax contact management."""
from __future__ import annotations

import logging
import os
import subprocess
from functools import wraps
from pathlib import Path
from typing import Dict, Set, Tuple

from flask import Flask, render_template, request, Response, jsonify, redirect, url_for, send_file

from kidfax.avatar_manager import (
    delete_avatar,
    ensure_avatar_dir,
    get_avatar_path,
    list_avatars,
    process_avatar,
)
from kidfax.config_manager import (
    get_contacts_from_env,
    get_allowlist_from_env,
    save_env_config,
    validate_phone_number,
    validate_contact_name,
    parse_contacts,
    parse_allowlist,
)

# Configure logging
logging.basicConfig(
    level=os.getenv("KIDFAX_LOG_LEVEL", "INFO").upper(),
    format="[%(asctime)s] %(levelname)s: %(message)s",
)
LOG = logging.getLogger("kidfax.admin_web")

# Create Flask app
app = Flask(__name__)
app.secret_key = os.urandom(24)  # For flash messages


def check_auth(password: str) -> bool:
    """
    Check if provided password matches ADMIN_PASSWORD.

    Args:
        password: Password to check

    Returns:
        True if password matches
    """
    admin_password = os.getenv("ADMIN_PASSWORD", "admin")
    return password == admin_password


def authenticate() -> Response:
    """Send 401 response that enables HTTP basic auth."""
    return Response(
        'Login Required\n\n'
        'Please enter the admin password configured in your .env file.\n',
        401,
        {'WWW-Authenticate': 'Basic realm="Kid Fax Admin"'}
    )


def requires_auth(f):
    """Decorator to require HTTP basic authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.password):
            LOG.warning(f"Failed login attempt from {request.remote_addr}")
            return authenticate()

        LOG.info(f"Admin login from {request.remote_addr}")
        return f(*args, **kwargs)

    return decorated


@app.route('/')
def index():
    """Redirect root to /admin."""
    return redirect(url_for('admin_dashboard'))


@app.route('/admin')
@requires_auth
def admin_dashboard():
    """
    Main admin dashboard showing contacts and allowlist.

    Requires HTTP basic authentication.
    """
    try:
        env_path = os.getenv("ENV_FILE_PATH", ".env")

        # Load current configuration
        contacts = get_contacts_from_env(env_path)
        allowlist = get_allowlist_from_env(env_path)

        # Initialize avatar directory
        ensure_avatar_dir()

        # Check which contacts have avatars
        avatars = list_avatars()
        contacts_with_avatars = {name.lower() for name in avatars.keys()}

        # Map contacts to F-keys (F1-F12) with avatar status
        fkey_contacts = []
        # Get custom order if set
        contacts_order = os.getenv('CONTACTS_ORDER', '').split(',')
        contacts_order = [c.strip() for c in contacts_order if c.strip()]

        # Sort contacts by custom order, then alphabetically for unordered
        def sort_key(item):
            name = item[0]
            if name in contacts_order:
                return (0, contacts_order.index(name))
            return (1, name)

        sorted_contacts = sorted(contacts.items(), key=sort_key)

        for i, (name, number) in enumerate(sorted_contacts, start=1):
            if i > 12:  # Max 12 contacts for keyboard mode
                break
            has_avatar = name.lower() in contacts_with_avatars
            fkey_contacts.append((f"F{i}", name, number, has_avatar))

        # Check if avatars are enabled
        avatar_enabled = os.getenv("AVATAR_ENABLED", "true").lower() in {"1", "true", "yes"}

        return render_template(
            'admin.html',
            contacts=fkey_contacts,
            all_contacts=contacts,
            allowlist=sorted(allowlist),
            max_contacts=12,
            contact_count=len(contacts),
            avatar_enabled=avatar_enabled
        )

    except FileNotFoundError as e:
        LOG.error(f".env file not found: {e}")
        return f"Error: .env file not found. Please create it first.", 500

    except Exception as e:
        LOG.error(f"Error loading dashboard: {e}")
        return f"Error loading admin dashboard: {e}", 500


@app.route('/admin/contacts/add', methods=['POST'])
@requires_auth
def add_contact():
    """
    Add a new contact.

    Request JSON:
        {
            "name": "contact_name",
            "number": "+15551234567"
        }

    Returns:
        JSON response with success/error
    """
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        number = data.get('number', '').strip()

        # Validate contact name
        valid, error = validate_contact_name(name)
        if not valid:
            return jsonify({'success': False, 'error': error}), 400

        # Validate phone number
        valid, error = validate_phone_number(number)
        if not valid:
            return jsonify({'success': False, 'error': error}), 400

        # Load current contacts
        env_path = os.getenv("ENV_FILE_PATH", ".env")
        contacts = get_contacts_from_env(env_path)
        allowlist = get_allowlist_from_env(env_path)

        # Check for duplicate name
        if name in contacts:
            return jsonify({
                'success': False,
                'error': f"Contact '{name}' already exists"
            }), 400

        # Check for duplicate number
        if number in contacts.values():
            return jsonify({
                'success': False,
                'error': f"Number {number} already assigned to another contact"
            }), 400

        # Check max contacts limit
        if len(contacts) >= 12:
            return jsonify({
                'success': False,
                'error': "Maximum 12 contacts allowed (F1-F12 keyboard limit)"
            }), 400

        # Add contact
        contacts[name] = number

        # Save to .env
        save_env_config(contacts, allowlist, env_path)

        LOG.info(f"Contact added: {name} -> {number}")
        return jsonify({
            'success': True,
            'message': f"Contact '{name}' added successfully"
        })

    except Exception as e:
        LOG.error(f"Error adding contact: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/contacts/edit', methods=['POST'])
@requires_auth
def edit_contact():
    """
    Edit an existing contact.

    Request JSON:
        {
            "old_name": "current_name",
            "new_name": "new_name",
            "new_number": "+15551234567"
        }

    Returns:
        JSON response with success/error
    """
    try:
        data = request.get_json()
        old_name = data.get('old_name', '').strip()
        new_name = data.get('new_name', '').strip()
        new_number = data.get('new_number', '').strip()

        # Validate new name
        valid, error = validate_contact_name(new_name)
        if not valid:
            return jsonify({'success': False, 'error': error}), 400

        # Validate new phone number
        valid, error = validate_phone_number(new_number)
        if not valid:
            return jsonify({'success': False, 'error': error}), 400

        # Load current contacts
        env_path = os.getenv("ENV_FILE_PATH", ".env")
        contacts = get_contacts_from_env(env_path)
        allowlist = get_allowlist_from_env(env_path)

        # Check old contact exists
        if old_name not in contacts:
            return jsonify({
                'success': False,
                'error': f"Contact '{old_name}' not found"
            }), 404

        # If renaming, check new name not taken (unless same as old)
        if new_name != old_name and new_name in contacts:
            return jsonify({
                'success': False,
                'error': f"Contact '{new_name}' already exists"
            }), 400

        # Remove old contact
        del contacts[old_name]

        # Add with new name/number
        contacts[new_name] = new_number

        # Save to .env
        save_env_config(contacts, allowlist, env_path)

        LOG.info(f"Contact edited: {old_name} -> {new_name} ({new_number})")
        return jsonify({
            'success': True,
            'message': f"Contact updated successfully"
        })

    except Exception as e:
        LOG.error(f"Error editing contact: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/contacts/delete', methods=['POST'])
@requires_auth
def delete_contact():
    """
    Delete a contact.

    Request JSON:
        {
            "name": "contact_name"
        }

    Returns:
        JSON response with success/error
    """
    try:
        data = request.get_json()
        name = data.get('name', '').strip()

        # Load current contacts
        env_path = os.getenv("ENV_FILE_PATH", ".env")
        contacts = get_contacts_from_env(env_path)
        allowlist = get_allowlist_from_env(env_path)

        # Check contact exists
        if name not in contacts:
            return jsonify({
                'success': False,
                'error': f"Contact '{name}' not found"
            }), 404

        # Remove contact
        del contacts[name]

        # Save to .env
        save_env_config(contacts, allowlist, env_path)

        LOG.info(f"Contact deleted: {name}")
        return jsonify({
            'success': True,
            'message': f"Contact '{name}' deleted successfully"
        })

    except Exception as e:
        LOG.error(f"Error deleting contact: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/allowlist/add', methods=['POST'])
@requires_auth
def add_to_allowlist():
    """
    Add a phone number to allowlist.

    Request JSON:
        {
            "number": "+15551234567"
        }

    Returns:
        JSON response with success/error
    """
    try:
        data = request.get_json()
        number = data.get('number', '').strip()

        # Validate phone number
        valid, error = validate_phone_number(number)
        if not valid:
            return jsonify({'success': False, 'error': error}), 400

        # Load current configuration
        env_path = os.getenv("ENV_FILE_PATH", ".env")
        contacts = get_contacts_from_env(env_path)
        allowlist = get_allowlist_from_env(env_path)

        # Check if already in allowlist
        if number in allowlist:
            return jsonify({
                'success': False,
                'error': f"Number {number} already in allowlist"
            }), 400

        # Add to allowlist
        allowlist.add(number)

        # Save to .env
        save_env_config(contacts, allowlist, env_path)

        LOG.info(f"Added to allowlist: {number}")
        return jsonify({
            'success': True,
            'message': f"Number added to allowlist"
        })

    except Exception as e:
        LOG.error(f"Error adding to allowlist: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/allowlist/delete', methods=['POST'])
@requires_auth
def remove_from_allowlist():
    """
    Remove a phone number from allowlist.

    Request JSON:
        {
            "number": "+15551234567"
        }

    Returns:
        JSON response with success/error
    """
    try:
        data = request.get_json()
        number = data.get('number', '').strip()

        # Load current configuration
        env_path = os.getenv("ENV_FILE_PATH", ".env")
        contacts = get_contacts_from_env(env_path)
        allowlist = get_allowlist_from_env(env_path)

        # Check if in allowlist
        if number not in allowlist:
            return jsonify({
                'success': False,
                'error': f"Number {number} not in allowlist"
            }), 404

        # Remove from allowlist
        allowlist.discard(number)

        # Save to .env
        save_env_config(contacts, allowlist, env_path)

        LOG.info(f"Removed from allowlist: {number}")
        return jsonify({
            'success': True,
            'message': f"Number removed from allowlist"
        })

    except Exception as e:
        LOG.error(f"Error removing from allowlist: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/restart', methods=['POST'])
@requires_auth
def restart_service():
    """
    Restart Kid Fax systemd service.

    Requires sudo permissions for pi user:
    Add to /etc/sudoers.d/kidfax:
        pi ALL=(ALL) NOPASSWD: /bin/systemctl restart kidfax

    Returns:
        JSON response with success/error
    """
    try:
        result = subprocess.run(
            ['sudo', 'systemctl', 'restart', 'kidfax'],
            capture_output=True,
            timeout=10,
            text=True
        )

        if result.returncode == 0:
            LOG.info("Kid Fax service restarted successfully")
            return jsonify({
                'success': True,
                'message': "Kid Fax service restarted successfully"
            })
        else:
            error_msg = result.stderr or "Unknown error"
            LOG.error(f"Service restart failed: {error_msg}")
            return jsonify({
                'success': False,
                'error': f"Restart failed: {error_msg}"
            }), 500

    except subprocess.TimeoutExpired:
        LOG.error("Service restart timed out")
        return jsonify({
            'success': False,
            'error': "Restart command timed out"
        }), 500

    except FileNotFoundError:
        LOG.warning("systemctl not found or sudo not configured")
        return jsonify({
            'success': False,
            'error': "Service restart not available. Configure sudo permissions."
        }), 500

    except Exception as e:
        LOG.error(f"Error restarting service: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/avatars/upload', methods=['POST'])
@requires_auth
def upload_avatar():
    """
    Upload avatar image for a contact.

    Request: multipart/form-data
        - contact_name: str (contact name)
        - avatar_file: file (PNG image)

    Returns:
        JSON response with success/error
    """
    try:
        contact_name = request.form.get('contact_name', '').strip()
        avatar_file = request.files.get('avatar_file')

        # Validate contact exists
        env_path = os.getenv("ENV_FILE_PATH", ".env")
        contacts = get_contacts_from_env(env_path)

        if contact_name not in contacts:
            return jsonify({
                'success': False,
                'error': f"Contact '{contact_name}' not found"
            }), 404

        # Validate file uploaded
        if not avatar_file:
            return jsonify({
                'success': False,
                'error': 'No file uploaded'
            }), 400

        # Validate file extension
        if not avatar_file.filename or not avatar_file.filename.lower().endswith('.png'):
            return jsonify({
                'success': False,
                'error': 'Only PNG files allowed'
            }), 400

        # Validate file size (max 5MB)
        avatar_file.seek(0, os.SEEK_END)
        file_size = avatar_file.tell()
        avatar_file.seek(0)

        max_size = int(os.getenv("AVATAR_MAX_FILE_SIZE", "5")) * 1024 * 1024
        if file_size > max_size:
            return jsonify({
                'success': False,
                'error': f'File too large (max {max_size // (1024*1024)}MB)'
            }), 400

        # Process and save avatar
        avatar_path = process_avatar(avatar_file, contact_name)

        LOG.info(f"Avatar uploaded for {contact_name}: {avatar_path}")
        return jsonify({
            'success': True,
            'message': f"Avatar uploaded for '{contact_name}'",
            'avatar_url': f"/admin/avatars/{contact_name}.png"
        })

    except ValueError as e:
        LOG.error(f"Validation error uploading avatar: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400

    except Exception as e:
        LOG.error(f"Error uploading avatar: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/avatars/<contact_name>.png')
@requires_auth
def get_avatar(contact_name):
    """
    Serve avatar image for preview in admin UI.

    Args:
        contact_name: Name of the contact

    Returns:
        PNG image file or 404 if not found
    """
    avatar_path = get_avatar_path(contact_name)

    if not avatar_path or not avatar_path.exists():
        return Response("Avatar not found", 404)

    return send_file(avatar_path, mimetype='image/png')


@app.route('/admin/avatars/delete', methods=['POST'])
@requires_auth
def delete_avatar_route():
    """
    Delete avatar for a contact.

    Request JSON:
        {
            "contact_name": "grandma"
        }

    Returns:
        JSON response with success/error
    """
    try:
        data = request.get_json()
        contact_name = data.get('contact_name', '').strip()

        if not contact_name:
            return jsonify({
                'success': False,
                'error': 'Contact name is required'
            }), 400

        # Delete avatar
        success = delete_avatar(contact_name)

        if not success:
            return jsonify({
                'success': False,
                'error': f"Avatar not found for '{contact_name}'"
            }), 404

        LOG.info(f"Avatar deleted for {contact_name}")
        return jsonify({
            'success': True,
            'message': f"Avatar deleted for '{contact_name}'"
        })

    except Exception as e:
        LOG.error(f"Error deleting avatar: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500





@app.route('/admin/discover', methods=['POST'])
@requires_auth
def discover_chats():
    """Discover Telegram chat IDs and save to local log."""
    try:
        import requests as http_requests
        import subprocess
        import json
        from pathlib import Path

        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            return jsonify({'success': False, 'error': 'TELEGRAM_BOT_TOKEN not configured'}), 500

        # Load existing discovered chats from local log
        discover_log_path = Path.home() / '.kidfax_discovered_chats.json'
        existing_chats = {}
        if discover_log_path.exists():
            try:
                with open(discover_log_path, 'r') as f:
                    existing_chats = json.load(f)
            except:
                existing_chats = {}

        # Stop the poller temporarily
        poller_was_running = False
        try:
            result = subprocess.run(['sudo', 'systemctl', 'is-active', 'kidfax'], capture_output=True, text=True)
            if result.stdout.strip() == 'active':
                subprocess.run(['sudo', 'systemctl', 'stop', 'kidfax'], timeout=5, capture_output=True)
                poller_was_running = True
        except:
            pass

        # Fetch updates from Telegram
        new_chats = {}
        try:
            url = f'https://api.telegram.org/bot{bot_token}/getUpdates'
            params = {'timeout': 5}
            resp = http_requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            updates = resp.json().get('result', [])

            for update in updates:
                if 'message' in update:
                    msg = update['message']
                    chat = msg['chat']
                    chat_id = str(chat['id'])
                    first_name = chat.get('first_name', 'Unknown')
                    last_name = chat.get('last_name', '')
                    username = chat.get('username', '')

                    full_name = f"{first_name} {last_name}".strip()
                    new_chats[chat_id] = {
                        'name': full_name,
                        'username': username,
                        'last_message': msg.get('text', '')[:50] if msg.get('text') else '[media]'
                    }
        except Exception as e:
            LOG.error(f'Telegram API error: {e}')

        # Restart poller if it was running
        if poller_was_running:
            subprocess.run(['sudo', 'systemctl', 'start', 'kidfax'], timeout=5, capture_output=True)

        # Merge new chats into existing
        for chat_id, info in new_chats.items():
            existing_chats[chat_id] = info

        # Save to local log
        try:
            with open(discover_log_path, 'w') as f:
                json.dump(existing_chats, f, indent=2)
        except Exception as e:
            LOG.error(f'Failed to save discover log: {e}')

        # Mark which chats are already in contacts
        env_path = os.getenv('ENV_FILE_PATH', '.env')
        current_contacts = get_contacts_from_env(env_path)
        added_chat_ids = set(str(v) for v in current_contacts.values())

        for chat_id, info in existing_chats.items():
            info['already_added'] = chat_id in added_chat_ids

        return jsonify({
            'success': True,
            'chats': existing_chats,
            'new_count': len(new_chats),
            'total_count': len(existing_chats)
        })

    except Exception as e:
        LOG.error(f'Error discovering chats: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/chat/send', methods=['POST'])
@requires_auth
def send_chat_message():
    """Send a Telegram message to a contact."""
    try:
        import requests as http_requests
        
        data = request.get_json()
        contact_name = data.get('contact_name', '').strip()
        message = data.get('message', '').strip()

        if not contact_name:
            return jsonify({'success': False, 'error': 'Contact name required'}), 400

        if not message:
            return jsonify({'success': False, 'error': 'Message cannot be empty'}), 400

        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            return jsonify({'success': False, 'error': 'TELEGRAM_BOT_TOKEN not configured'}), 500

        env_path = os.getenv('ENV_FILE_PATH', '.env')
        contacts = get_contacts_from_env(env_path)

        if contact_name not in contacts:
            return jsonify({'success': False, 'error': f"Contact '{contact_name}' not found"}), 404

        chat_id = contacts[contact_name]

        url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
        payload = {'chat_id': chat_id, 'text': message}
        
        resp = http_requests.post(url, json=payload, timeout=10)
        resp_data = resp.json()

        if resp_data.get('ok'):
            LOG.info(f"Message sent to {contact_name} ({chat_id})")
            return jsonify({
                'success': True,
                'message': f"Message sent to {contact_name}",
                'message_id': resp_data['result']['message_id']
            })
        else:
            error_desc = resp_data.get('description', 'Unknown error')
            LOG.error(f"Telegram API error: {error_desc}")
            return jsonify({'success': False, 'error': error_desc}), 500

    except Exception as e:
        LOG.error(f"Error sending message: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500



@app.route('/admin/service/status', methods=['GET'])
@requires_auth
def get_service_status():
    """Get the current status of the kidfax poller service."""
    try:
        import subprocess
        result = subprocess.run(
            ['sudo', 'systemctl', 'is-active', 'kidfax'],
            capture_output=True, text=True, timeout=5
        )
        is_running = result.stdout.strip() == 'active'
        return jsonify({
            'success': True,
            'running': is_running,
            'status': 'running' if is_running else 'stopped'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/service/toggle', methods=['POST'])
@requires_auth
def toggle_service():
    """Start or stop the kidfax poller service."""
    try:
        import subprocess

        # Check current status
        result = subprocess.run(
            ['sudo', 'systemctl', 'is-active', 'kidfax'],
            capture_output=True, text=True, timeout=5
        )
        is_running = result.stdout.strip() == 'active'

        # Toggle
        if is_running:
            subprocess.run(['sudo', 'systemctl', 'stop', 'kidfax'], timeout=5)
            new_status = 'stopped'
        else:
            subprocess.run(['sudo', 'systemctl', 'start', 'kidfax'], timeout=5)
            new_status = 'running'

        LOG.info(f"Service toggled to: {new_status}")
        return jsonify({
            'success': True,
            'running': new_status == 'running',
            'status': new_status
        })
    except Exception as e:
        LOG.error(f"Error toggling service: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500




@app.route('/admin/contacts/reorder', methods=['POST'])
@requires_auth
def reorder_contacts():
    """
    Reorder contacts for F-key assignment.
    Saves order to CONTACTS_ORDER in .env
    """
    try:
        data = request.get_json()
        order = data.get('order', [])  # List of contact names in desired order

        if not order:
            return jsonify({'success': False, 'error': 'Order list required'}), 400

        env_path = os.getenv('ENV_FILE_PATH', '.env')

        # Read current .env
        with open(env_path, 'r') as f:
            lines = f.readlines()

        # Update or add CONTACTS_ORDER
        order_line = f"CONTACTS_ORDER={','.join(order)}\n"
        found = False
        for i, line in enumerate(lines):
            if line.startswith('CONTACTS_ORDER='):
                lines[i] = order_line
                found = True
                break

        if not found:
            # Add after CONTACTS line
            for i, line in enumerate(lines):
                if line.startswith('CONTACTS='):
                    lines.insert(i + 1, order_line)
                    found = True
                    break

        if not found:
            lines.append(order_line)

        # Write back
        with open(env_path, 'w') as f:
            f.writelines(lines)

        LOG.info(f"Contacts reordered: {order}")
        return jsonify({'success': True, 'message': 'F-key order updated'})

    except Exception as e:
        LOG.error(f"Error reordering contacts: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500



@app.route('/admin/settings', methods=['GET'])
@requires_auth
def get_settings():
    """Get current settings from .env file."""
    try:
        env_path = os.getenv('ENV_FILE_PATH', '.env')
        settings = {}

        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        settings[key.strip()] = value.strip()

        return jsonify({'success': True, 'settings': settings})
    except Exception as e:
        LOG.error(f"Error loading settings: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/settings', methods=['POST'])
@requires_auth
def save_settings():
    """Save settings to .env file and restart service."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400

        env_path = os.getenv('ENV_FILE_PATH', '.env')

        # Read current .env
        lines = []
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                lines = f.readlines()

        # Update values
        updated_keys = set()
        new_lines = []

        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith('#') and '=' in stripped:
                key = stripped.split('=', 1)[0].strip()
                if key in data:
                    new_lines.append(f"{key}={data[key]}\n")
                    updated_keys.add(key)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)

        # Add any new keys that weren't in the file
        for key, value in data.items():
            if key not in updated_keys:
                new_lines.append(f"{key}={value}\n")

        # Write back
        with open(env_path, 'w') as f:
            f.writelines(new_lines)

        LOG.info(f"Settings updated: {list(data.keys())}")

        # Restart kidfax service
        import subprocess
        subprocess.run(['sudo', 'systemctl', 'restart', 'kidfax'], check=True)

        return jsonify({'success': True, 'message': 'Settings saved and service restarted'})
    except Exception as e:
        LOG.error(f"Error saving settings: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


def main():
    """Entry point for admin web interface."""
    if not os.getenv('ADMIN_PASSWORD'):
        LOG.warning('ADMIN_PASSWORD not set in .env file. Using default admin.')
        LOG.warning('Please set ADMIN_PASSWORD in .env for security!')

    env_path = os.getenv('ENV_FILE_PATH', '.env')
    if not os.path.exists(env_path):
        LOG.error(f'.env file not found at {env_path}')
        print(f'Error: .env file not found at {env_path}')
        print('Please create .env file with CONTACTS and ALLOWLIST configuration.')
        return

    host = os.getenv('ADMIN_HOST', '0.0.0.0')
    port = int(os.getenv('ADMIN_PORT', '5000'))

    print('=' * 60)
    print('Kid Fax Admin Web Interface')
    print('=' * 60)
    print(f'Running on: http://{host}:{port}/admin')
    if host == '127.0.0.1':
        print('Access from this machine only (localhost)')
    else:
        print(f'Access from local network: http://raspberrypi.local:{port}/admin')
    print()
    print('Press Ctrl+C to stop')
    print('=' * 60)

    app.run(host=host, port=port, debug=False)


if __name__ == '__main__':
    main()
