#!/usr/bin/env python3
import XenAPI
import sys
import ssl

# --- Configuration ---
XEN_HOST = "198.19.55.126"
XEN_USER = "CTRL4C\\MG-SCRIPT-CTRL4C"
XEN_PASS = "Pod3ASMzVpqhv1KVN3nx"
TARGET_LUN = "XEN_TEJASXEN2_F2750_10_L09"
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
        print(f"Successfully connected to {XEN_HOST}")
        print(f"Scanning ONLY inside LUN: '{TARGET_LUN}' for 100/300 GiB disks...\n")
        
        all_srs = session.xenapi.SR.get_all_records()
        all_vdis = session.xenapi.VDI.get_all_records()
        all_vbds = session.xenapi.VBD.get_all_records()
        all_vms = session.xenapi.VM.get_all_records()

        # Build map of VDI -> VM
        vdi_to_vm = {}
        for vbd_ref, vbd_rec in all_vbds.items():
            if vbd_rec.get('VDI') != 'OpaqueRef:NULL':
                vm_ref = vbd_rec.get('VM')
                if vm_ref in all_vms:
                    vdi_to_vm[vbd_rec['VDI']] = all_vms[vm_ref].get('name_label', 'Unknown VM')

        # Find the specific SR
        target_sr_ref = None
        for sr_ref, sr_rec in all_srs.items():
            if sr_rec.get('name_label') == TARGET_LUN:
                target_sr_ref = sr_ref
                break
                
        if not target_sr_ref:
            print(f"❌ ERROR: LUN '{TARGET_LUN}' was not found in this pool.")
            return

        # Check disks in this SR only
        vdi_refs = all_srs[target_sr_ref].get('VDIs', [])
        found_count = 0
        
        for vdi_ref in vdi_refs:
            vdi_rec = all_vdis.get(vdi_ref)
            if not vdi_rec or vdi_rec.get('is_a_snapshot', False):
                continue
                
            size_gb = round(int(vdi_rec.get('virtual_size', 0)) / (1024**3))
            
            # Filter for 100 and 300 GB
            if size_gb in [100, 300]:
                found_count += 1
                name_label = vdi_rec.get('name_label', 'No Name')
                real_uuid = vdi_rec.get('uuid')
                attached_vm = vdi_to_vm.get(vdi_ref, "NONE (Unattached/Orphaned) <-- LIKELY MIGRATED DISK")
                
                print(f"✅ Found {size_gb} GiB Disk in {TARGET_LUN}:")
                print(f"   Name:        {name_label}")
                print(f"   Xen UUID:    {real_uuid}")
                print(f"   Attached To: {attached_vm}")
                print("-" * 50)
                
        if found_count == 0:
            print(f"❌ No 100 GiB or 300 GiB disks exist in '{TARGET_LUN}'.")
            print("   (This means the migration tool either failed to put them here, or put them in a different LUN)")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        if session.is_logged_in():
            session.logout()

if __name__ == "__main__":
    main()
