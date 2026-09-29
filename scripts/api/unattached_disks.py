#!/usr/bin/env python3

# File: get_all_unattached_disks.py
# Description: Scans ALL hosts defined in sr_pass_config.py for unattached disks.
#              Exports results to a CSV file.
#              Uses Host Name (zabbix_host) from config instead of IP.

import XenAPI
import sys
import ssl
import http.client
import xmlrpc.client
import csv
import time

# Import your specific config file
try:
    from sr_pass_config import get_all_configs
except ImportError:
    print("FATAL: sr_pass_config.py not found. Please ensure it exists.", file=sys.stderr)
    sys.exit(1)

# --- SSL CERTIFICATE BYPASS ---
def setup_ssl_transport():
    """Disables SSL certificate verification for self-signed certs."""
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

# --- CORE LOGIC ---
def get_orphaned_disks_for_host(session, host_id, host_name):
    """
    Scans a single host session for unattached disks.
    Returns a list of rows for the CSV.
    """
    results = []
    
    # Fetch all records
    try:
        all_srs = session.xenapi.SR.get_all_records()
        all_vdis = session.xenapi.VDI.get_all_records()
    except Exception as e:
        print(f"  [!] Error fetching records from {host_name}: {e}")
        return []

    for vdi_ref, vdi_rec in all_vdis.items():
        # 1. Skip snapshots
        if vdi_rec.get('is_a_snapshot', False): continue

        # 2. Check SR validity
        sr_ref = vdi_rec.get('SR')
        if not sr_ref or sr_ref == "OpaqueRef:NULL": continue

        sr_rec = all_srs.get(sr_ref)
        if not sr_rec: continue

        # 3. Skip ISOs and removable media
        if sr_rec.get('type') in ['iso', 'udev']: continue
        if 'iso' in sr_rec.get('name_label', '').lower(): continue

        # 4. Check if Unattached (Empty VBDs list)
        vbds = vdi_rec.get('VBDs', [])

        if len(vbds) == 0:
            # Calculate sizes
            virt_bytes = int(vdi_rec.get('virtual_size', 0))
            phys_bytes = int(vdi_rec.get('physical_utilisation', 0))

            virt_gb = round(virt_bytes / (1024**3), 2)
            phys_gb = round(phys_bytes / (1024**3), 2)

            # Create CSV Row: HostID, Host Name, SR Name, Disk Name, Used GB, Max GB, UUID
            row = [
                host_id,
                host_name,  # Using the name from config
                sr_rec.get('name_label', 'Unknown SR'),
                vdi_rec.get('name_label', 'Unknown Disk'),
                phys_gb,    # Actual Used
                virt_gb,    # Max Size
                vdi_rec.get('uuid', '')
            ]
            results.append(row)

    return results

# --- MAIN EXECUTION ---
def main():
    setup_ssl_transport()
    
    configs = get_all_configs()
    csv_filename = "unattached_disks_report.csv"
    
    print(f"Starting scan of {len(configs)} hosts...")
    print(f"Output will be saved to: {csv_filename}\n")

    # Open CSV file for writing
    with open(csv_filename, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Write Header
        header = ["Host ID", "Host Name", "SR Name", "Disk Name", "Used (GB)", "Max (GB)", "Disk UUID"]
        writer.writerow(header)

        # Loop through all configs
        for host_id, config in configs.items():
            # Get the display name from config (zabbix_host), fallback to IP if missing
            host_display_name = config.get('zabbix_host', config['host'])
            
            print(f"[*] Connecting to: {host_display_name} (ID: {host_id})...")
            
            session = None
            try:
                # Initialize session using the IP address
                url = f"https://{config['host']}"
                session = XenAPI.Session(url)
                session.login_with_password(config['username'], config['password'])
                
                # Scan for disks
                disk_rows = get_orphaned_disks_for_host(session, host_id, host_display_name)
                
                if disk_rows:
                    print(f"    -> Found {len(disk_rows)} unattached disks.")
                    writer.writerows(disk_rows)
                else:
                    print(f"    -> No unattached disks found.")

            except Exception as e:
                print(f"    [!] Connection Failed: {e}")
            
            finally:
                if session:
                    try:
                        session.logout()
                    except:
                        pass

    print("\n" + "="*50)
    print(f"Scan Complete. Data saved to {csv_filename}")
    print("="*50)

if __name__ == "__main__":
    main()
