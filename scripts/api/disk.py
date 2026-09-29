#!/usr/bin/env python3
import XenAPI
import sys
import ssl

# --- Configuration ---
XEN_HOST = "198.19.55.76"
XEN_USER = "CTRL4C\\MG-SCRIPT-CTRL4C"
XEN_PASS = "Pod3ASMzVpqhv1KVN3nx"
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
        print(f"Successfully connected to {XEN_HOST}")
        print(f"Searching ENTIRE POOL for disks matching name: '{SEARCH_NAME}'...\n")
        
        all_vdis = session.xenapi.VDI.get_all_records()
        all_srs = session.xenapi.SR.get_all_records()

        found_count = 0
        
        # 1. Search across all LUNs by Name
        for vdi_ref, vdi_rec in all_vdis.items():
            name_label = vdi_rec.get('name_label', '')
            name_desc = vdi_rec.get('name_description', '')
            
            # Check if search term is in name or description
            if SEARCH_NAME.lower() in name_label.lower() or SEARCH_NAME.lower() in name_desc.lower():
                found_count += 1
                
                sr_ref = vdi_rec.get('SR')
                sr_name = all_srs.get(sr_ref, {}).get('name_label', 'Unknown SR (Orphaned)')
                size_gb = int(vdi_rec.get('virtual_size', 0)) / (1024**3)
                real_uuid = vdi_rec.get('uuid')
                
                print(f"✅ Disk #{found_count} Found:")
                print(f"   Name:     {name_label}")
                print(f"   Xen UUID: {real_uuid}")
                print(f"   Size:     {size_gb:.2f} GiB")
                print(f"   Location: {sr_name} (This is the LUN it is in)")
                print("-" * 50)

        # 2. Fallback: If no name matches, search by exact Size (100GB and 300GB)
        if found_count == 0:
            print(f"❌ Could not find any disks containing '{SEARCH_NAME}' anywhere in the pool.\n")
            print("--- FALLBACK: Searching entire pool for ANY 100 GiB or 300 GiB disks... ---")
            
            size_matches = 0
            for vdi_ref, vdi_rec in all_vdis.items():
                if vdi_rec.get('is_a_snapshot', False):
                    continue # Skip snapshots
                
                size_gb = round(int(vdi_rec.get('virtual_size', 0)) / (1024**3))
                
                if size_gb in [100, 300]:
                    size_matches += 1
                    sr_ref = vdi_rec.get('SR')
                    sr_name = all_srs.get(sr_ref, {}).get('name_label', 'Unknown SR')
                    vdi_uuid = vdi_rec.get('uuid')
                    vdi_name = vdi_rec.get('name_label')
                    
                    print(f"   Found {size_gb} GiB Disk -> Name: '{vdi_name}' | Location: '{sr_name}' | UUID: {vdi_uuid}")
            
            if size_matches == 0:
                print("   No 100 GiB or 300 GiB disks found in the pool either.")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        if session.is_logged_in():
            session.logout()

if __name__ == "__main__":
    main()
