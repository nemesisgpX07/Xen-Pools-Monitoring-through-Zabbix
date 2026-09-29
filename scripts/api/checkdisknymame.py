#!/usr/bin/env python3
import XenAPI
import sys
import ssl

# --- Configuration ---
XEN_HOST = "198.19.55.126"
XEN_USER = "CTRL4C\\MG-SCRIPT-CTRL4C"
XEN_PASS = "Pod3ASMzVpqhv1KVN3nx"
TARGET_LUN = "XEN_TEJASXEN2_F2750_10_L09"
SEARCH_NAME = "BiotechP2C26818"
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
        
        all_vdis = session.xenapi.VDI.get_all_records()
        all_srs = session.xenapi.SR.get_all_records()

        # 1. Search by Name
        print(f"--- Searching for any disks containing the name: '{SEARCH_NAME}' ---")
        found_by_name = False
        
        for vdi_ref, vdi_rec in all_vdis.items():
            name_label = vdi_rec.get('name_label', '')
            name_desc = vdi_rec.get('name_description', '')
            
            # Check if our target name is in the VDI name or description
            if SEARCH_NAME.lower() in name_label.lower() or SEARCH_NAME.lower() in name_desc.lower():
                found_by_name = True
                sr_ref = vdi_rec.get('SR')
                sr_name = all_srs.get(sr_ref, {}).get('name_label', 'Unknown SR')
                size_gb = int(vdi_rec.get('virtual_size', 0)) / (1024**3)
                real_uuid = vdi_rec.get('uuid')
                
                print(f"✅ FOUND DISK: '{name_label}'")
                print(f"   Real Xen UUID: {real_uuid}")
                print(f"   Size:          {size_gb:.2f} GiB")
                print(f"   Location (SR): {sr_name}")
                
                if sr_name == TARGET_LUN:
                    print("   -> Status: Correct LUN! ✔️\n")
                else:
                    print(f"   -> Status: WRONG LUN! (Expected {TARGET_LUN}) ❌\n")

        if not found_by_name:
            print(f"❌ No disks found containing the name '{SEARCH_NAME}'.\n")


        # 2. List contents of the target LUN
        print(f"--- Listing all disks currently in LUN: '{TARGET_LUN}' ---")
        lun_found = False
        for sr_ref, sr_rec in all_srs.items():
            if sr_rec.get('name_label') == TARGET_LUN:
                lun_found = True
                vdi_refs = sr_rec.get('VDIs', [])
                
                if not vdi_refs:
                    print(f"⚠️ SR '{TARGET_LUN}' is completely empty (no disks inside).")
                else:
                    count = 0
                    for v_ref in vdi_refs:
                        v_rec = all_vdis.get(v_ref)
                        if v_rec and not v_rec.get('is_a_snapshot', False): # hide snapshots to keep it clean
                            size_g = int(v_rec.get('virtual_size', 0)) / (1024**3)
                            print(f" - {v_rec.get('name_label')} | UUID: {v_rec.get('uuid')} | {size_g:.0f} GiB")
                            count += 1
                    if count == 0:
                        print("   (Only snapshots/hidden volumes exist in this LUN)")
                break
                
        if not lun_found:
            print(f"❌ SR (LUN) '{TARGET_LUN}' does not exist on this Xen Pool.")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        if session.is_logged_in():
            session.logout()

if __name__ == "__main__":
    main()
