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
        for i, (name, number) in enumerate(sorted(contacts.items()), start=1):
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


def main():
    """Entry point for admin web interface."""
    # Check if ADMIN_PASSWORD is set
    if not os.getenv("ADMIN_PASSWORD"):
        LOG.warning("ADMIN_PASSWORD not set in .env file. Using default 'admin'.")
        LOG.warning("Please set ADMIN_PASSWORD in .env for security!")

    # Check if .env file exists
    env_path = os.getenv("ENV_FILE_PATH", ".env")
    if not os.path.exists(env_path):
        LOG.error(f".env file not found at {env_path}")
        print(f"Error: .env file not found at {env_path}")
        print("Please create .env file with CONTACTS and ALLOWLIST configuration.")
        return

    # Determine host and port
    host = os.getenv("ADMIN_HOST", "127.0.0.1")  # Default: localhost only
    port = int(os.getenv("ADMIN_PORT", "5000"))

    print("=" * 60)
    print("Kid Fax Admin Web Interface")
    print("=" * 60)
    print(f"Running on: http://{host}:{port}/admin")
    if host == "127.0.0.1":
        print("Access from this machine only (localhost)")
    else:
        print(f"Access from local network: http://raspberrypi.local:{port}/admin")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 60)

    # Run Flask app
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
