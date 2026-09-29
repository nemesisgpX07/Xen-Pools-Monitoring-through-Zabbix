#!/usr/bin/env python3

# File: vdi_naming_report.py
# Description: Detects VDIs with irregular name-labels (paths, brackets, special characters) 
#              and flags disks that mix both hyphens (-) and underscores (_) together.
# Usage: python3 vdi_naming_report.py <host_id_1> <host_id_2> ... <host_id_N>

import XenAPI
import sys
import ssl
import re
import http.client
import xmlrpc.client
from datetime import datetime

try:
    import openpyxl
    from openpyxl.styles import Font
except ImportError:
    print("FATAL: 'openpyxl' module is required. Run: pip3 install openpyxl", file=sys.stderr)
    sys.exit(1)

try:
    from pass_config import get_xen_config
except ImportError:
    print("FATAL: pass_config.py not found.", file=sys.stderr)
    sys.exit(1)

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

def find_irregular_vdis(session):
    """Retrieves all VDIs and flags those matching the irregular naming regex."""
    pools = session.xenapi.pool.get_all_records()
    hosts = session.xenapi.host.get_all_records()
    vms = session.xenapi.VM.get_all_records()
    vbds = session.xenapi.VBD.get_all_records()
    vdis = session.xenapi.VDI.get_all_records()

    pool_rec = list(pools.values())[0]
    pool_name = pool_rec['name_label']
    master_host_name = hosts[pool_rec['master']]['name_label']

    # 1. Pre-map VDIs to VMs for speed
    vdi_to_vms = {}
    for vbd_rec in vbds.values():
        if vbd_rec['type'] == 'Disk' and vbd_rec['VDI'] != 'OpaqueRef:NULL':
            vdi_uuid = vdis.get(vbd_rec['VDI'], {}).get('uuid')
            vm_rec = vms.get(vbd_rec['VM'])
            
            if vdi_uuid and vm_rec:
                if vdi_uuid not in vdi_to_vms:
                    vdi_to_vms[vdi_uuid] = []
                vdi_to_vms[vdi_uuid].append(vm_rec['name_label'])

    irregular_data = []

    # 3. Evaluate all VDIs
    for vdi_ref, vdi_rec in vdis.items():
        vdi_uuid = vdi_rec['uuid']
        name_label = vdi_rec.get('name_label', '')

        # Skip "Update:" system VDIs completely
        if name_label.startswith("Update:"):
            continue
            
        # RULE 1: Is it purely alphanumeric, spaces, dots, and ONLY underscores?
        valid_underscore_only = bool(re.fullmatch(r'[a-zA-Z0-9\.\s_]+', name_label))
        
        # RULE 2: Is it purely alphanumeric, spaces, dots, and ONLY hyphens?
        valid_hyphen_only = bool(re.fullmatch(r'[a-zA-Z0-9\.\s\-]+', name_label))
        
        # IF IT FAILS BOTH RULES (meaning it has BOTH '-' and '_', or it has '()', '\', etc.)
        # Then it is irregular and must be flagged.
        if not (valid_underscore_only or valid_hyphen_only):
            
            # Get attached VMs (comma separated if attached to multiple)
            attached_vms = vdi_to_vms.get(vdi_uuid, [])
            vm_name_str = ", ".join(attached_vms) if attached_vms else "Not Attached"

            irregular_data.append({
                "Poolname": pool_name,
                "Masterhost": master_host_name,
                "VM_Name": vm_name_str,
                "VDI_UUID": vdi_uuid,
                "Disk_Name_Length": len(name_label),
                "Disk_Name_Label": name_label
            })

    return irregular_data

def write_excel(filename, data):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Irregular VDI Names"

    headers = ["Poolname", "Masterhost", "VM_Name", "VDI_UUID", "Disk_Name_Length", "Disk_Name_Label"]
    ws.append(headers)
    
    # Bold headers
    for cell in ws[1]:
        cell.font = Font(bold=True)

    # Append data
    for row in data:
        ws.append([row.get(h, "") for h in headers])

    # Auto-adjust column widths
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 100) 
        ws.column_dimensions[column].width = adjusted_width

    wb.save(filename)
    print(f"\nExcel Report successfully saved to: {filename}", file=sys.stderr)

def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <host_id_1> <host_id_2> ... <host_id_N>", file=sys.stderr)
        sys.exit(1)

    host_ids = sys.argv[1:]
    master_irregular_vdis = []

    setup_ssl_transport()

    for host_id in host_ids:
        config = get_xen_config(host_id)
        if not config:
            print(f"Skipping '{host_id}': No config found in pass_config.py", file=sys.stderr)
            continue

        print(f"\n--- Processing Host/Pool: {config['host']} ---", file=sys.stderr)
        session = None
        try:
            session = XenAPI.Session(f"https://{config['host']}")
            session.login_with_password(config['username'], config['password'])

            pool_irregular_data = find_irregular_vdis(session)
            print(f"Found {len(pool_irregular_data)} irregularly named VDIs in this pool.")
            
            master_irregular_vdis.extend(pool_irregular_data)

        except Exception as exc:
            print(f"Error processing {host_id}: {exc}", file=sys.stderr)
        finally:
            if session and session.is_logged_in():
                session.logout()

    if master_irregular_vdis:
        # Sort master list by Pool name, then by Disk Name Length (longest first)
        master_irregular_vdis.sort(key=lambda x: (x["Poolname"], -x["Disk_Name_Length"]))
        
        filename = f"VDI_Naming_Compliance_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        write_excel(filename, master_irregular_vdis)
    else:
        print("\nNo irregular VDIs found. Excel file was not generated.")

if __name__ == "__main__":
    main()
