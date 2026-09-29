#!/usr/bin/env python3
import XenAPI
import sys
import ssl

# --- Configuration ---
XEN_HOST = "198.19.55.76"
XEN_USER = "CTRL4C\\MG-SCRIPT-CTRL4C"
XEN_PASS = "Pod3ASMzVpqhv1KVN3nx"

TARGET_LUN = "XEN_TEJASXEN2_F2750_10_L09"
DISKS_TO_CHECK = [
    "aa62d56f-67eb-427d-b588-cfccaefc3abe",  # 100 GiB Disk
    "688729e5-c3e8-410e-8173-8579e95b84cb"   # 300 GiB Disk
]
# ---------------------

def disable_ssl():
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    return ssl_context

def main():
    import xmlrpc.client
    class CustomTransport(xmlrpc.client.SafeTransport):
        def make_connection(self, host):
            import http.client
            return http.client.HTTPSConnection(host, context=disable_ssl())
            
    session = XenAPI.Session(f"https://{XEN_HOST}", transport=CustomTransport())
    
    try:
        session.login_with_password(XEN_USER, XEN_PASS)
        print(f"Successfully connected to {XEN_HOST}\n")
        
        for disk_uuid in DISKS_TO_CHECK:
            try:
                # 1. Try to find the VDI by its UUID
                vdi_ref = session.xenapi.VDI.get_by_uuid(disk_uuid)
                vdi_rec = session.xenapi.VDI.get_record(vdi_ref)
                
                # 2. Find which SR (LUN) it belongs to
                sr_ref = vdi_rec['SR']
                sr_rec = session.xenapi.SR.get_record(sr_ref)
                sr_name = sr_rec['name_label']
                size_gb = int(vdi_rec['virtual_size']) / (1024**3)
                
                # 3. Check if it matches the expected target LUN
                if sr_name == TARGET_LUN:
                    print(f"✅ FOUND: Disk {disk_uuid} ({size_gb:.0f} GiB) is correctly located in LUN '{TARGET_LUN}'.")
                else:
                    print(f"⚠️ MISMATCH: Disk {disk_uuid} exists, but it is in SR '{sr_name}' instead of '{TARGET_LUN}'.")
                    
            except XenAPI.Failure as e:
                if e.details[0] == 'UUID_INVALID':
                    print(f"❌ NOT FOUND: Disk UUID {disk_uuid} does not exist in this Xen Pool.")
                else:
                    print(f"Error checking disk {disk_uuid}: {e}")

    finally:
        if session.is_logged_in():
            session.logout()

if __name__ == "__main__":
    main()
