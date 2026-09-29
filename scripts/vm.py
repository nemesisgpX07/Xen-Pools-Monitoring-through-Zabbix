#!/usr/bin/env python3

# File: vm.py
# Description: Gathers metrics for Xen/XCP-ng virtual machines and sends them to Zabbix.
#              Logic based on a highly efficient, user-provided script.
# Usage: python3 vm.py <host_id>

import XenAPI
import json
import socket
import struct
import time
import sys
import ssl
import http.client
import xmlrpc.client
from datetime import datetime, timezone

try:
    # NOTE: Ensure your config file is named 'xen_config.py'
    from pass_config import get_xen_config, ZABBIX_SERVER, ZABBIX_PORT
except ImportError:
    print("FATAL: xen_config.py not found. Please create it.", file=sys.stderr)
    sys.exit(1)

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

def parse_xen_time(xen_time_obj):
    """Robustly parses Xen's DateTime object into a Unix timestamp."""
    if not xen_time_obj:
        return 0
    try:
        # The object is often a subclass of datetime, so .timestamp() works
        return int(xen_time_obj.timestamp())
    except (AttributeError, TypeError, ValueError):
        # Fallback for string-based time formats
        try:
            dt_obj = datetime.strptime(str(xen_time_obj), "%Y%m%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            return int(dt_obj.timestamp())
        except (ValueError, TypeError):
            return 0

def recv_exact(sock, size):
    """Receive exactly size bytes or raise IOError."""
    buf = b''
    while len(buf) < size:
        chunk = sock.recv(size - len(buf))
        if not chunk:
            raise IOError("Connection closed prematurely while waiting for Zabbix response")
        buf += chunk
    return buf

def get_vm_metrics(session):
    """Connects to Xen and retrieves VM metrics using an efficient pre-fetch method."""
    print(f"Pre-fetching all records for efficiency...", file=sys.stderr)
    all_records = {}
    record_types = ["pool", "host", "VM", "VM_metrics", "VM_guest_metrics","VBD", "VDI","VIF"]
    for r_type in record_types:
        try:
            all_records[r_type] = getattr(session.xenapi, r_type).get_all_records()
        except Exception:
            all_records[r_type] = {}
    all_vbds = all_records.get("VBD", {})
    all_vdis = all_records.get("VDI", {})
    all_hosts = all_records.get("host", {})
    all_vms = all_records.get("VM", {})
    all_vifs = all_records.get("VIF", {})

    if not all_records.get("pool"):
        raise RuntimeError("No pool record found")
    pool_record = list(all_records["pool"].values())[0]
    pool_name = pool_record['name_label']

    print(f"Gathering detailed VM statistics...", file=sys.stderr)
    vm_data = []
    for vm_ref, vm_rec in all_vms.items():
        if vm_rec.get("is_a_template") or vm_rec.get("is_control_domain"):
            continue

        metrics_rec = all_records["VM_metrics"].get(vm_rec['metrics'], {})
        guest_rec = all_records["VM_guest_metrics"].get(vm_rec.get('guest_metrics', 'OpaqueRef:NULL'), {})
        resident_host_rec = all_hosts.get(vm_rec.get('resident_on'))
        total_disk_size_bytes = 0
        for vbd_ref in vm_rec.get('VBDs', []):
            vbd_rec = all_vbds.get(vbd_ref)
            # Ensure VBD is a disk and has a VDI
            if vbd_rec and vbd_rec.get('type') == 'Disk' and vbd_rec.get('VDI'):
                vdi_ref = vbd_rec['VDI']
                vdi_rec = all_vdis.get(vdi_ref)
                if vdi_rec:
                    total_disk_size_bytes += int(vdi_rec.get('virtual_size', 0))
        vm_mac_addresses = []
        for vif_ref in vm_rec.get('VIFs', []):
            vif_rec = all_vifs.get(vif_ref)
            if vif_rec and 'MAC' in vif_rec:
                vm_mac_addresses.append(vif_rec['MAC'])
        vm_mac_address = ", ".join(vm_mac_addresses)
        # --- Collect data based on Zabbix Template ---
        status = vm_rec['power_state']
        start_time = parse_xen_time(metrics_rec.get('start_time'))

        vm_ips, os_type, primary_ip = "N/A", "N/A", "N/A"
        if guest_rec:
            networks = guest_rec.get('networks', {})
            all_ips = [ip.split('/')[0] for net in networks.values() for ip in net.split(',') if ip]
            if all_ips:
                vm_ips = ", ".join(all_ips)
                primary_ip = all_ips[0]
            os_info = guest_rec.get('os_version', {})
            if os_info:
                os_type = os_info.get('name', 'Unknown OS')

        snapshots = vm_rec.get('snapshots', [])
        snapshot_name, snapshot_time = "N/A", 0
        if snapshots:
            snap_rec = all_vms.get(snapshots[-1])
            if snap_rec:
                snapshot_name = snap_rec.get('name_label', 'N/A')
                snapshot_time = parse_xen_time(snap_rec.get('snapshot_time'))

        vm_data.append({
            # --- Data for Zabbix Items ---
            "name": vm_rec["name_label"],
            "uuid": vm_rec["uuid"],
            "pool_name": pool_name,
            "has_snapshot": "1" if snapshots else "0",
            "host_name": resident_host_rec['name_label'] if resident_host_rec else "N/A",
#            "host_ip": resident_host_rec['address'] if resident_host_rec else "N/A",
            "number_of_snapshots": len(snapshots),
            "os_type": os_type,
            "snapshot_name": snapshot_name,
            "snapshot_taken_time": snapshot_time,
            "total_cpu": int(vm_rec.get('VCPUs_max', 0)),
            "total_disk_size_gb": total_disk_size_bytes // (1024*1024*1024),
            "total_memory_mb": int(vm_rec.get('memory_static_max', 0)) // (1024*1024),
            "uptime_seconds": int(time.time()) - start_time if status == 'Running' and start_time > 0 else 0,
            "vm_ips": " ".join(sorted(list(set(v for k, v in guest_rec.get('networks', {}).items() if '/ip' in k and 'ipv6' not in k)))),
            "vm_status": status,
            "vm_mac_address": vm_mac_address,
            # --- Data for Discovery Rule ---
            #"primary_ip": primary_ip
        })
    return {"vms": vm_data}

def send_to_zabbix(data, zabbix_host_name):
    """Formats and sends VM data to Zabbix server."""
    metrics = []
    ts = int(time.time())

    # 1. VM Discovery item
    discovery_data = {"data": [
        {"{#VMNAME}": vm["name"].replace(" ", "_"), "{#POOLNAME}": vm["pool_name"], "{#VMIP}": vm["vm_ips"]}
        for vm in data["vms"]
    ]}
    metrics.append({
        "host": zabbix_host_name,
        "key": "xen.poller.vmstatus",
        "value": 1,  # A simple '1' indicates a successful run
        "clock": ts
    })
    metrics.append({
        "host": zabbix_host_name, "key": "xen.vm.discovery",
        "value": json.dumps(discovery_data), "clock": ts
    })

    # 2. VM metrics from prototypes
    for vm in data["vms"]:
        vm_name_key = vm["name"].replace(" ", "_")
        for key, value in vm.items():
            if key in ("name", "uuid", "pool_name", "primary_ip"): # These are identifiers, not metrics
                continue

            # Sanitize value for Zabbix
            if isinstance(value, bool):
                value = 1 if value else 0

            metrics.append({
                "host": zabbix_host_name,
                "key": f"xen.vm[{vm_name_key},{key}]",
                "value": str(value),
                "clock": ts,
            })

    print(f"Prepared {len(metrics)} metric items to send to Zabbix.", file=sys.stderr)
    json_data = json.dumps({"request": "sender data", "data": metrics})
    packet = b'ZBXD\x01' + struct.pack('<Q', len(json_data)) + json_data.encode('utf-8')

    try:
        with socket.socket() as sock:
            sock.settimeout(30)
            sock.connect((ZABBIX_SERVER, ZABBIX_PORT))
            sock.sendall(packet)
            response_header = recv_exact(sock, 5)
            if response_header != b'ZBXD\x01':
                raise IOError(f"Invalid response header from Zabbix: {response_header}")
            response_len = struct.unpack('<Q', recv_exact(sock, 8))[0]
            response_raw = recv_exact(sock, response_len)
            response = json.loads(response_raw.decode('utf-8'))
            print(f"Response from Zabbix: {response}")
            if 'failed: 0;' not in response.get('info', ''):
                print("Warning: Some items may have failed. Check Zabbix UI.", file=sys.stderr)
    except Exception as e:
        print(f"Error sending data to Zabbix: {e}", file=sys.stderr)

def main():
    """Main execution function."""
    # --- Argument Parsing and Configuration ---
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <host_id>", file=sys.stderr)
        sys.exit(1)
    host_id = sys.argv[1]
    config = get_xen_config(host_id)
    if not config:
        print(f"FATAL: No config for host_id '{host_id}' in xen_config.py", file=sys.stderr)
        sys.exit(1)

    print(f"--- Starting VM data collection for '{config['zabbix_host']}' ---", file=sys.stderr)

    session = None
    try:
        setup_ssl_transport()
        session = XenAPI.Session(f"https://{config['host']}")
        print(f"Connecting to Xen pool master: {config['host']}...", file=sys.stderr)
        session.login_with_password(config['username'], config['password'])
        print(f"Login successful.", file=sys.stderr)

        xen_data = get_vm_metrics(session)

        if xen_data and xen_data.get("vms"):
            # Clean up internal-only fields before printing
            for vm in xen_data.get("vms", []):
                if "primary_ip" in vm:
                    del vm["primary_ip"]

#            print("\n--- Collected VM Data (JSON OUTPUT) ---", file=sys.stderr)
#            print(json.dumps(xen_data, indent=2))

            print("\n--- Sending data to Zabbix ---", file=sys.stderr)
            send_to_zabbix(xen_data, config['zabbix_host'])

            print(f"\n--- Script finished successfully at {datetime.now()} ---", file=sys.stderr)
        else:
            print(f"--- No VM data was collected. Script finished. ---", file=sys.stderr)

    finally:
        if session and session.is_logged_in():
            print(f"Logging out.", file=sys.stderr)
            session.logout()

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\nFATAL ERROR during script execution: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)




