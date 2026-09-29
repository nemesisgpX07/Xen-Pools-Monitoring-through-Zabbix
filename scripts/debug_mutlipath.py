#!/usr/bin/env python3
"""
File: multipath_debug.py
Description: Dumps ALL multipath-related keys from PBD.other_config,
             host.other_config and SR.sm_config for every lvmohba SR.
             Run this once to find exactly where the path data lives.
Usage: python3 multipath_debug.py <host_id>
"""
import XenAPI, sys, ssl, json, http.client, xmlrpc.client, pprint

try:
    from pass_config import get_xen_config
except ImportError:
    print("FATAL: pass_config.py not found.", file=sys.stderr); sys.exit(1)

def setup_ssl():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    class Conn(http.client.HTTPSConnection):
        def __init__(self, host, **kw): super().__init__(host, context=ctx, **kw)
    def make_conn(self, host):
        if hasattr(self,'_connection') and self._connection and self._connection[0]==host:
            return self._connection[1]
        self._connection = host, Conn(host); return self._connection[1]
    xmlrpc.client.SafeTransport.make_connection = make_conn

def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <host_id>"); sys.exit(1)
    setup_ssl()
    cfg = get_xen_config(sys.argv[1])
    session = XenAPI.Session(f"https://{cfg['host']}")
    session.login_with_password(cfg['username'], cfg['password'])

    hosts   = session.xenapi.host.get_all_records()
    srs     = session.xenapi.SR.get_all_records()
    pbds    = session.xenapi.PBD.get_all_records()

    lvmohba = {r:v for r,v in srs.items() if v.get('type','').lower()=='lvmohba'}
    print(f"\n=== Found {len(lvmohba)} lvmohba SR(s) ===\n")

    for sr_ref, sr_rec in lvmohba.items():
        print(f"\n{'='*70}")
        print(f"SR : {sr_rec['name_label']}  [{sr_rec['uuid']}]")
        print(f"sm_config  : {pprint.pformat(sr_rec.get('sm_config',{}))}")

        sr_pbds = [v for v in pbds.values() if v['SR']==sr_ref]
        for pbd in sr_pbds:
            hname = hosts.get(pbd['host'],{}).get('name_label', str(pbd['host']))
            print(f"\n  --- PBD for host: {hname} ---")
            print(f"  currently_attached : {pbd.get('currently_attached')}")
            print(f"  device_config      : {pprint.pformat(pbd.get('device_config',{}))}")
            oc = pbd.get('other_config', {})
            mpath_keys = {k:v for k,v in oc.items() if 'mpath' in k.lower() or 'multi' in k.lower() or 'path' in k.lower()}
            print(f"  other_config (path-related) : {pprint.pformat(mpath_keys) if mpath_keys else '(none)'}")
            print(f"  other_config (ALL)          : {pprint.pformat(oc)}")

    print(f"\n\n{'='*70}")
    print("=== host.other_config (path/mpath-related keys only) ===")
    for h_ref, h_rec in hosts.items():
        hoc = h_rec.get('other_config', {})
        mkeys = {k:v for k,v in hoc.items() if 'mpath' in k.lower() or 'multi' in k.lower() or 'path' in k.lower()}
        if mkeys:
            print(f"\n  Host: {h_rec['name_label']}")
            for k,v in mkeys.items():
                print(f"    [{k}] = {v}")

    session.logout()

if __name__ == "__main__":
    main()
