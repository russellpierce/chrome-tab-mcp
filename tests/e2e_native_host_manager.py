#!/usr/bin/env python3
"""
Native Messaging Host Manager for E2E Tests

Safely manages native messaging host configuration for E2E tests without
clobbering the user's existing setup.

Features:
- Backs up existing manifest before tests
- Adds test extension ID to allowed_origins
- Restores original manifest after tests
"""

import json
import shutil
import sys
from pathlib import Path
import platform


def get_manifest_path():
    """Get the native messaging host manifest path for the current platform"""
    system = platform.system()

    if system == "Darwin":  # macOS
        base_path = Path.home() / "Library" / "Application Support" / "Google" / "Chrome"
    elif system == "Linux":
        base_path = Path.home() / ".config" / "google-chrome"
    elif system == "Windows":
        # On Windows, it's in the registry, but we'll skip for now
        raise NotImplementedError("Windows native messaging host management not yet implemented for E2E tests")
    else:
        raise NotImplementedError(f"Unsupported platform: {system}")

    manifest_dir = base_path / "NativeMessagingHosts"
    manifest_path = manifest_dir / "com.chrome_tab_reader.json"

    return manifest_path


def backup_manifest():
    """Backup existing native messaging host manifest"""
    manifest_path = get_manifest_path()

    if not manifest_path.exists():
        print(f"No existing manifest found at {manifest_path}")
        return None

    backup_path = manifest_path.with_suffix('.json.e2e-backup')
    shutil.copy(manifest_path, backup_path)
    print(f"✓ Backed up manifest to {backup_path}")

    return backup_path


def restore_manifest():
    """Restore original native messaging host manifest from backup"""
    manifest_path = get_manifest_path()
    backup_path = manifest_path.with_suffix('.json.e2e-backup')

    if not backup_path.exists():
        print("No backup found to restore")
        return False

    shutil.copy(backup_path, manifest_path)
    backup_path.unlink()
    print(f"✓ Restored original manifest from backup")

    return True


def add_test_extension_id(extension_id):
    """Add test extension ID to native messaging host manifest"""
    manifest_path = get_manifest_path()

    if not manifest_path.exists():
        print(f"Error: Native messaging host not installed at {manifest_path}")
        print("Please run: python chrome_tab_native_host.py --install")
        return False

    # Read current manifest
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)

    # Get current allowed origins
    allowed_origins = manifest.get('allowed_origins', [])
    test_origin = f"chrome-extension://{extension_id}/"

    # Check if already present
    if test_origin in allowed_origins:
        print(f"✓ Test extension ID {extension_id} already in manifest")
        return True

    # Add test extension ID
    allowed_origins.append(test_origin)
    manifest['allowed_origins'] = allowed_origins

    # Write updated manifest
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)

    print(f"✓ Added test extension ID {extension_id} to manifest")
    print(f"  Allowed origins: {len(allowed_origins)}")

    return True


def remove_test_extension_id(extension_id):
    """Remove test extension ID from native messaging host manifest"""
    manifest_path = get_manifest_path()

    if not manifest_path.exists():
        return False

    # Read current manifest
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)

    # Get current allowed origins
    allowed_origins = manifest.get('allowed_origins', [])
    test_origin = f"chrome-extension://{extension_id}/"

    # Remove test extension ID if present
    if test_origin in allowed_origins:
        allowed_origins.remove(test_origin)
        manifest['allowed_origins'] = allowed_origins

        # Write updated manifest
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)

        print(f"✓ Removed test extension ID {extension_id} from manifest")
        return True

    return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Manage native messaging host for E2E tests")
    parser.add_argument("action", choices=["backup", "restore", "add", "remove"],
                       help="Action to perform")
    parser.add_argument("--extension-id", help="Extension ID for add/remove actions")

    args = parser.parse_args()

    try:
        if args.action == "backup":
            backup_manifest()
        elif args.action == "restore":
            restore_manifest()
        elif args.action == "add":
            if not args.extension_id:
                print("Error: --extension-id required for add action")
                sys.exit(1)
            add_test_extension_id(args.extension_id)
        elif args.action == "remove":
            if not args.extension_id:
                print("Error: --extension-id required for remove action")
                sys.exit(1)
            remove_test_extension_id(args.extension_id)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
