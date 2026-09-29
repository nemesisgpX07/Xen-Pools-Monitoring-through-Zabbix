#!/usr/bin/env python3

# File: fetch_nfs_sr.py
# Description: Connects to all Xen pools defined in pass_config.py.
#              Fetches ONLY SRs with type='nfs'.
#              Saves output to 'sr_nfs_details.json'.

import XenAPI
import json
import sys
import ssl
import http.client
import xmlrpc.client

try:
    # Import the global dictionary we created in Step 1
    from sr_pass_config import ALL_CONFIGS
except ImportError:
    print("FATAL: Could not import ALL_CONFIGS from pass_config.py. Please update pass_config.py.", file=sys.stderr)
    sys.exit(1)

# --- SSL Setup (Ignore self-signed certs) ---
def setup_ssl_transport():
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    class CustomHTTPSConnection(http.client.HTTPSConnection):
        def __init__(self, host, **kwargs):
            super().__init__(host, context=ssl_context, **kwargs)

    def custom_https_connection(self, host):
        if hasattr(self, '_connection') and self._connection and self._connection[0] == host:
            return self._connection[1]
        self._connection = host, CustomHTTPSConnection(host)
        return self._connection[1]
    xmlrpc.client.SafeTransport.make_connection = custom_https_connection

def get_nfs_srs(session):
    """
    Fetches SRs where type is NFS.
    """
    try:
        # Get all SRs and PBDs (Physical Block Devices)
        all_srs = session.xenapi.SR.get_all_records()
        all_pbds = session.xenapi.PBD.get_all_records()
    except Exception as e:
        return {"error": str(e)}

    nfs_list = []

    for sr_ref, sr_rec in all_srs.items():
        # --- FILTER: ONLY NFS ---
        if sr_rec['type'] != 'nfs':
            continue

        # Check if the SR is actually attached to a host via a PBD
        attached_pbds = [pbd for pbd in all_pbds.values() if pbd['SR'] == sr_ref and pbd['currently_attached']]
        
        # If no PBDs are attached, the SR is detached/broken
        if not attached_pbds:
            continue

        # Calculate Usage
        physical_size = int(sr_rec['physical_size'])
        physical_util = int(sr_rec['physical_utilisation'])
        
        if physical_size > 0:
            usage_percent = round((physical_util / physical_size) * 100, 2)
        else:
            usage_percent = 0.0

        sr_data = {
            "name": sr_rec['name_label'],
            "uuid": sr_rec['uuid'],
            "type": sr_rec['type'],
            "description": sr_rec['name_description'],
            "physical_size_bytes": physical_size,
            "physical_used_bytes": physical_util,
            "physical_free_bytes": physical_size - physical_util,
            "usage_percent": usage_percent,
            "content_type": sr_rec.get('content_type', 'unknown')
        }
        nfs_list.append(sr_data)

    return nfs_list

def main():
    setup_ssl_transport()
    
    final_output = {}
    print(f"--- Starting NFS SR Collection for {len(ALL_CONFIGS)} pools ---", file=sys.stderr)

    for host_id, config in ALL_CONFIGS.items():
        pool_name = config.get('zabbix_host', f"Pool_{host_id}")
        target_host = config['host']
        
        print(f"Processing Pool: {pool_name} ({target_host})...", end=" ", file=sys.stderr)
        sys.stderr.flush()

        session = None
        try:
            # Connect to the Master
            session = XenAPI.Session(f"https://{target_host}")
            session.login_with_password(config['username'], config['password'])
            
            # Fetch Data
            srs = get_nfs_srs(session)
            
            # Store in final dictionary
            final_output[pool_name] = {
                "pool_master_ip": target_host,
                "nfs_storage": srs
            }
            
            print(f"Done. Found {len(srs)} NFS SRs.", file=sys.stderr)
            session.logout()

        except Exception as e:
            print(f"FAILED. Error: {e}", file=sys.stderr)
            final_output[pool_name] = {
                "pool_master_ip": target_host,
                "error": str(e)
            }

    # Save to JSON File
    output_file = "sr_nfs_details.json"
    try:
        with open(output_file, 'w') as f:
            json.dump(final_output, f, indent=4)
        print(f"\nSuccessfully saved data to {output_file}", file=sys.stderr)
    except IOError as e:
        print(f"Error saving file: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
