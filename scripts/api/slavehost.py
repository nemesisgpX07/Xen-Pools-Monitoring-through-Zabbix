#!/usr/bin/env python3

# File: slavehost.py
# Description: Gathers metrics for Xen/XCP-ng hosts.
#              Fixed: Passes 5 arguments to slave login (User, Pass, Version, Originator, UserAgent).
# Usage: python3 slavehost.py <host_id>

import XenAPI
import json
import socket
import struct
import time
import sys
import ssl
import http.client
import xmlrpc.client
from datetime import datetime
from collections import defaultdict

try:
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

def recv_exact(sock, size):
    """Receive exactly size bytes or raise IOError."""
    buf = b''
    while len(buf) < size:
        chunk = sock.recv(size - len(buf))
        if not chunk:
            raise IOError("Connection closed prematurely")
        buf += chunk
    return buf

def get_xen_host_data(session):
    """Gathers metrics using an efficient pre-fetch method."""
    print("Pre-fetching all records (Local DB view)...", file=sys.stderr)
    all_records = {}
    record_types = ["pool", "host", "host_metrics", "SR", "PBD", "PIF", "PIF_metrics", "network", "Bond"]
    
    for r_type in record_types:
        try:
            all_records[r_type] = getattr(session.xenapi, r_type).get_all_records()
        except Exception as e:
            all_records[r_type] = {}

    print("Processing collected records...", file=sys.stderr)
    all_data = {"pool": {}, "hosts": [], "srs": [], "pifs": []}
    processed_pifs = set()

    # Handle Pool record
    if all_records.get("pool"):
        pool_record = list(all_records["pool"].values())[0]
        all_data["pool"] = { "name": pool_record["name_label"], "num_hosts": len(all_records.get("host", [])) }
    else:
        all_data["pool"] = { "name": "Unknown (Slave View)", "num_hosts": 0 }
        pool_record = {"master": "Unknown"}

    # --- Reconstruct bond information ---
    bonds_by_host_ref = defaultdict(list)
    bond_to_master_pif = {b_ref: b_rec.get('master') for b_ref, b_rec in all_records.get("Bond", {}).items()}
    slaves_by_bond_ref = defaultdict(list)
    
    for pif_ref, pif_rec in all_records.get("PIF", {}).items():
        bond_ref = pif_rec.get('bond_slave_of')
        if bond_ref and bond_ref != 'OpaqueRef:NULL':
            slaves_by_bond_ref[bond_ref].append(pif_rec.get('device'))

    for bond_ref, member_nics in slaves_by_bond_ref.items():
        master_pif_ref = bond_to_master_pif.get(bond_ref)
        if not master_pif_ref: continue
        master_pif_rec = all_records["PIF"].get(master_pif_ref)
        if not master_pif_rec: continue
        network_rec = all_records["network"].get(master_pif_rec.get('network'), {})
        host_ref = master_pif_rec.get('host')
        if host_ref:
            bond_info = {
                "bond_device": master_pif_rec.get('device', 'N/A'),
                "description": f"{master_pif_rec.get('device', 'N/A')}-{network_rec.get('name_label', 'N/A')}-{','.join(sorted(member_nics))}"
            }
            bonds_by_host_ref[host_ref].append(bond_info)

    # --- Process all PIFs ---
    for pif_ref, pif_rec in all_records.get("PIF", {}).items():
        host_ref = pif_rec.get('host')
        if not host_ref or host_ref not in all_records.get("host", {}): continue
        if not (pif_rec.get('physical') or pif_rec.get('bond_master_of', 'OpaqueRef:NULL') != 'OpaqueRef:NULL'): continue

        host_rec = all_records["host"][host_ref]
        device = pif_rec.get('device')
        host_name = host_rec["name_label"]
        
        pif_identifier = (host_name, device)
        if pif_identifier in processed_pifs: continue
        processed_pifs.add(pif_identifier)

        pif_metrics_rec = all_records.get('PIF_metrics', {}).get(pif_rec.get('metrics'), {})
        host_bonds = {bond['bond_device']: bond['description'] for bond in bonds_by_host_ref.get(host_ref, [])}

        pif_data = {
            "host_name": host_name, "device": device,
            "description": host_bonds.get(device, device),
            "status": 1 if pif_metrics_rec.get('carrier') else 0
        }
        all_data["pifs"].append(pif_data)

    # --- Process all Hosts ---
    for host_ref, host_rec in all_records.get("host", {}).items():
        metrics_rec = all_records.get("host_metrics", {}).get(host_rec.get('metrics'), {})
        try:
            if metrics_rec.get('live', False):
                cpu_usage = float(session.xenapi.host.query_data_source(host_ref, "cpu_avg")) * 100
            else:
                cpu_usage = 0.0
        except (XenAPI.Failure, ValueError):
            cpu_usage = 0.0

        is_enabled = host_rec.get('enabled', False)
        is_live = metrics_rec.get('live', False)

        if not is_enabled and not is_live:
            host_state_live = "hidden"
        elif not is_enabled and is_live:
            host_state_live = "maintenance"
        else:
            host_state_live = "unknown"

        host_role = "slave"
        if pool_record.get('master') == host_ref:
            host_role = "master"

        all_data["hosts"].append({
            "name": host_rec["name_label"], "uuid": host_rec["uuid"],
            "host_ip": host_rec.get('address', 'N/A'),
            "host_role": host_role,
            "host_status": "running", 
            "host_live_state": host_state_live,
            "cpu_cores": int(host_rec.get('cpu_info', {}).get('cpu_count', 0)),
            "cpu_usage_percent": cpu_usage,
            "memory_total": int(metrics_rec.get("memory_total", 0)),
            "memory_used": int(metrics_rec.get("memory_total", 0)) - int(metrics_rec.get("memory_free", 0)),
            "uptime_seconds": int(time.time() - float(host_rec.get('other_config', {}).get('boot_time', 0))),
            "bond_details": ",".join([bond['description'] for bond in bonds_by_host_ref.get(host_ref, [])])
        })

    # --- Process SRs ---
    all_srs = all_records.get("SR", {})
    all_pbds = all_records.get("PBD", {})
    for sr_ref, sr_rec in all_srs.items():
        if sr_rec.get('type') != 'lvmohba':
            continue
        attached_pbds = [pbd for pbd in all_pbds.values() if pbd.get('SR') == sr_ref and pbd.get('currently_attached')]
        if not attached_pbds: continue

        size = int(sr_rec.get('physical_size', 0))
        util = int(sr_rec.get('physical_utilisation', 0))
        usage_percent = (util / size * 100) if size > 0 else 0
        sr_name = sr_rec.get('name_label', 'Unknown')
        
        is_shared = sr_rec.get('shared', False)
        if not is_shared and attached_pbds:
            host_ref = attached_pbds[0].get('host')
            host_name = all_records.get('host', {}).get(host_ref, {}).get('name_label')
            if host_name and host_name not in sr_name:
                sr_name = f"{sr_name} ({host_name})"

        all_data["srs"].append({
            "name": sr_name, "uuid": sr_rec['uuid'],
            "sr_type": sr_rec['type'],
            "physical_size": size,
            "physical_utilisation": util,
            "virtual_allocation_bytes": int(sr_rec.get('virtual_allocation', 0)),
            "usage_percent": usage_percent,
        })

    return all_data

def format_discovery_data(items):
    return json.dumps({"data": items})

def send_to_zabbix(data, zabbix_host_name):
    """Sends collected data to the Zabbix server."""
    metrics = []
    ts = int(time.time())

    metrics.append({"host": zabbix_host_name, "key": "xen.poller.status", "value": "1", "clock": ts})

    # Discovery
    metrics.append({"host": zabbix_host_name, "key": "xen.host.discovery", "value": format_discovery_data([{"{#HOSTNAME}": h["name"].replace(" ", "_"), "{#HOSTUUID}": h["uuid"],"{#POOLNAME}": data["pool"]["name"],"{#HOSTROLE}": h["host_role"], "{#HOSTIP}": h["host_ip"]} for h in data["hosts"]])})
    metrics.append({"host": zabbix_host_name, "key": "xen.sr.discovery", "value": format_discovery_data([{"{#SRNAME}": s["name"].replace(" ", "_"), "{#SRUUID}": s["uuid"]} for s in data["srs"]])})

    # Pool metrics
    metrics.extend([
        {"host": zabbix_host_name, "key": "xen.pool.name", "value": data["pool"]["name"], "clock": ts},
        {"host": zabbix_host_name, "key": "xen.pool.num_hosts", "value": str(data["pool"]["num_hosts"]), "clock": ts},
    ])

    # PIF Discovery
    pif_discovery_data = []
    for pif in data.get('pifs', []):
        pif_discovery_data.append({
            "{#HOSTNAME}": pif["host_name"].replace(" ", "_"),
            "{#PIFDEVICE}": pif["device"],
            "{#PIFDESC}": pif["description"]
        })
    metrics.append({"host": zabbix_host_name, "key": "xen.pif.discovery", "value": format_discovery_data(pif_discovery_data), "clock": ts})

    # Items
    for host in data["hosts"]:
        h_name = host["name"].replace(" ", "_")
        for pif in data.get('pifs', []):
            if pif["host_name"] == host["name"]:
                device = pif['device']
                metrics.append({"host": zabbix_host_name, "key": f"xen.pif.status[{h_name},{device}]", "value": str(pif["status"]), "clock": ts})

        for k, v in host.items():
            if k in ("name", "uuid", "pif_stats"): continue
            if not isinstance(v, (int, float, str)):
                v = json.dumps(v)
            metrics.append({"host": zabbix_host_name, "key": f"xen.host[{h_name},{k}]", "value": str(v), "clock": ts})

    for sr in data["srs"]:
        sr_name = sr["name"].replace(" ", "_")
        for k, v in sr.items():
            if k in ("name", "uuid"): continue
            metrics.append({"host": zabbix_host_name, "key": f"xen.sr[{sr_name},{k}]", "value": str(v), "clock": ts})

    print(f"Prepared {len(metrics)} metric items to send to Zabbix.", file=sys.stderr)
    json_data = json.dumps({"request": "sender data", "data": metrics})
    packet = b'ZBXD\x01' + struct.pack('<Q', len(json_data)) + json_data.encode('utf-8')
    try:
        with socket.socket() as sock:
            sock.settimeout(30)
            sock.connect((ZABBIX_SERVER, ZABBIX_PORT))
            sock.sendall(packet)
            response_header = recv_exact(sock, 5)
            if response_header != b'ZBXD\x01': raise IOError(f"Invalid response header: {response_header}")
            response_len = struct.unpack('<Q', recv_exact(sock, 8))[0]
            response_raw = recv_exact(sock, response_len)
            response = json.loads(response_raw.decode('utf-8'))
            print(f"Response from Zabbix: {response}")
    except Exception as e:
        print(f"Error sending data to Zabbix: {e}", file=sys.stderr)

def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <host_id>", file=sys.stderr)
        sys.exit(1)
    host_id = sys.argv[1]
    config = get_xen_config(host_id)
    if not config:
        print(f"FATAL: No config for host_id '{host_id}' in xen_config.py", file=sys.stderr)
        sys.exit(1)

    print(f"--- Starting Host data collection for '{config['zabbix_host']}' ---", file=sys.stderr)
    session = None
    try:
        setup_ssl_transport()
        session = XenAPI.Session(f"https://{config['host']}")
        
        # --- FIXED LOGIN LOGIC (5 Arguments) ---
        try:
            print(f"Attempting standard login to {config['host']}...", file=sys.stderr)
            session.login_with_password(config['username'], config['password'])
            print(f"Standard login successful.", file=sys.stderr)
        except XenAPI.Failure as e:
            if e.details[0] == 'HOST_IS_SLAVE':
                print(f"Host {config['host']} is a SLAVE. Attempting Slave-Local Login...", file=sys.stderr)
                try:
                    # FIX: We now provide the 5 arguments.
                    # 1. Username
                    # 2. Password
                    # 3. Version ('1.3')
                    # 4. Originator ('host.py')
                    # 5. User-Agent/Label ('' - empty string)
                    
                    login_result = session.xenapi.session.slave_local_login_with_password(
                        config['username'], 
                        config['password'], 
                        '1.3', 
                        'host.py',
                        '' 
                    )
                    
                    session.handle = login_result
                    
                    print("Slave-Local login successful. Fetching local DB view.", file=sys.stderr)
                except Exception as ex_slave:
                    print(f"FATAL: Could not establish even a slave-local session: {ex_slave}", file=sys.stderr)
                    sys.exit(1)
            else:
                raise e
        # ---------------------------------------

        xen_data = get_xen_host_data(session)

        print("\n--- Sending data to Zabbix ---", file=sys.stderr)
        send_to_zabbix(xen_data, config['zabbix_host'])

        print(f"\n--- Script finished successfully at {datetime.now()} ---", file=sys.stderr)
    finally:
        if session:
            try:
                session.logout()
            except Exception:
                pass

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\nFATAL ERROR during script execution: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
