ZABBIX_SERVER = "172.23.245.50"
ZABBIX_PORT = 10051

# Common credentials
COMMON_USERNAME = "CTRL4C\\MG-SCRIPT-CTRL4C"
COMMON_PASSWORD = "Pod3ASMzVpqhv1KVN3nx"

# Helper to create config
def make_config(host, zabbix_host, username=COMMON_USERNAME, password=COMMON_PASSWORD):
    return {
        "host": host,
        "username": username,
        "password": password,
        "zabbix_host": zabbix_host
    }

def get_xen_config(host_id):
    configs = {
        "1": make_config(
            "198.19.23.219", "MUM4C-MGMT-POOL_192.168.230.55_198.19.23.219_XENMASTER",
            username="MG-SCRIPT-CTRL4C",
            password="Pod3ASMzVpqhv1KVN3nx"

        ),
        "2": make_config(
            "198.18.252.239",
            "HydXen2.ctrl4c.com_192.168.214.150_198.18.252.239_XENMASTER"
        ),
        "3": make_config(
            "198.19.17.128", "4C-MUM-XEN_mumctr4c-ctx229_192.168.230.229_198.19.17.128_XENMASTER",
            #username="cloud-mon",
            #password="mon@123"
        ),
        "4": make_config(
            "198.19.17.135", "4C-MUM-XEN2_mumctr4c-ctx127_192.168.230.127_198.19.17.135_XENMASTER",
            username="MG-SCRIPT-CTRL4C",
            password="Pod3ASMzVpqhv1KVN3nx"
        ),
        "5": make_config(
            "198.19.17.142", "4C-MUM-XEN4_mumctr4c-ctx110_192.168.230.110_198.19.17.142_XENMASTER",
        ),
        "6": make_config(
            "198.19.17.152", "4C-MUM_XEN3_POD1-POD2_mumctr4c-ctx117_192.168.230.117_198.19.17.152_XENMASTER",
            #username="MG-SCRIPT-CTRL4C",
            #password="Pod3ASMzVpqhv1KVN3nx"
        ),
        "7": make_config(
            "198.19.17.154", "clmu4c-xenprod_clmu4c-ctx169_192.168.230.169_198.19.17.154_XENMASTER",
             username="MG-SCRIPT-CTRL4C",
             password="Pod3ASMzVpqhv1KVN3nx"
        ),
        "8": make_config(
            "198.19.17.192", "clmuvn-prod_clmuvn-ctx172_192.168.217.172_198.19.17.193_XENMASTER"
        ),
        "9": make_config(
            "198.18.252.174", "Atlas-hydctrat-ctx-pool2_p-hydctrat-ctx-37_172.27.255.37_198.18.252.174_XENMASTER"
        ),
        "10": make_config(
            "198.18.93.68", "HYDCYGCTX-POOL-hydcygctx131_172.27.255.131_198.18.252.165_XENMASTER"
        ),
        "11": make_config(
            "198.19.254.139", "MUM-GLXY-Pool_p-mumctrgx-ctx-12_172.16.44.12_198.19.254.139_XENMASTER"
        ),
        "12": make_config(
            "198.19.7.202", "MUMAGSCTXPool1_mumagsctx33_172.16.45.33_198.19.7.202_XENMASTER"
        ),
        "13": make_config(
            "198.18.130.72", "HydXen.ctrl4c.com_clhy4c-ctx72_192.168.214.72_198.18.130.72_XENMASTER"
        ),
        "14": make_config(
            "198.19.253.91", "mumctrp-xen-pool2_p-mumctrp-ctx138_192.168.101.138_198.19.253.91_XENMASTER"
        ),
        "15": make_config(
            "198.18.252.38", "MercuryXen.ctrl4c.com_clmercury-ctx113_192.168.99.113_198.18.252.36_XENMASTER"
        ),
        "16": make_config(
            "198.18.47.186", "CygHydXen8-Pool2_cyghydxen186_172.27.255.186_198.18.47.186_XENMASTER"
            #username="root",
        ),
        "17": make_config(
            "198.19.53.196", "MUMAGSCTXPOOL2_mumags-ctx187_172.16.45.187_198.19.42.157_XENMASTER"
        ),
        "18": make_config(
            "198.19.17.147", "4C-MUM-HYBRID_Pool_MUM4CHYBRID-CTX94_192.168.230.94_198.19.17.147_XENMASTER",
             username="MG-SCRIPT-CTRL4C",
             password="Pod3ASMzVpqhv1KVN3nx"
        ),
        "19": make_config(
            "198.19.55.76", "MUM-TEJAS-XEN_mumtejas-ctx76_198.19.55.76_172.28.48.76_XENMASTER"
        ),
        "20": make_config(
            "198.18.252.248", "HydXen3.ctrl4c.com_clhy4c-ctx158_192.168.214.158_198.18.252.248_XENMASTER"
        ),
        "21": make_config(
            "198.19.55.126", "MUM-TEJAS-XEN2_mumtejas-ctx79_172.28.48.79_198.19.55.126_XENMASTER"
        ),
        "22": make_config(
            "198.18.252.99", "HYDMARS-XEN_192.168.218.30_198.18.252.99_XENMASTER"
        ),
        "23": make_config(
            "198.18.48.244", "MERCURY-HYD-XEN_192.168.99.112_198.18.48.244_XENMASTER"
        ),
        "24": make_config(
            "198.18.130.134", "4CHYD-XEN8-POOL_hyd4c-ctx28_192.168.214.28_198.18.130.134_XENMASTER"
        ),
        "25": make_config(
            "198.18.44.107", "Jupiter-xen1_192.168.92.103_198.18.44.107_XENMASTER",
            username="MG-SCRIPT-CTRL4C",
            password="Pod3ASMzVpqhv1KVN3nx"
        ),
        "26": make_config(
            "198.19.17.186", "Dubai XEN 8_DUBAI-xen-ctx24_10.168.227.24_198.19.17.186_XENMASTER"
        ),
        "27": make_config(
            "198.19.47.205", "VENUS_BHARUWA-XEN8_venusmum-ctx95_192.168.217.95_198.19.47.205_XENMASTER"
        ),
        "28": make_config(
            "198.19.254.234", "mumctratm-xen-zbx_mumctratm-xen36_172.16.60.36_198.19.254.234_XENMASTER"
        ),
        "29": make_config(
            "198.19.254.231", "mumctratm-xen-prod_mumctratm-xen32_172.16.60.32_198.19.254.231_XENMASTER"
        ),
        "30": make_config(
            "198.18.60.155", "HYDTEJAS-XEN2_CTX16_172.28.28.16_198.18.60.155_XENMASTER"
        ),
        "31": make_config(
            "198.19.253.91", "PLUTO-MUM-XEN8_pluto-mum-ctx139_192.168.101.139_198.19.46.36_XENMASTER"
        ),
        "32": make_config(
            "198.18.252.114", "MARS-MGMT-CTX23_192.168.218.23_198.18.252.114_XENMASTER"
        ),
        "33": make_config(
            "198.19.50.30", "galaxymum-ctx45_172.16.44.45_198.19.50.30_XENMASTER"
        ),
        "34": make_config(
            "198.19.16.230", "MUAGSCTXMGMT_mumagsctx21_172.16.45.21_198.19.16.230_XENMASTER"
        ),
        "35": make_config(
            "198.19.254.131", "Galaxy-MGMT-POOL_CTX110_172.16.44.110_198.19.254.131_XENMASTER",
            #username="cloud-mon",
            #password="mon@123"
        ),
        "36": make_config(
            "198.19.47.211", "VENUS-MGMT-CTX115_192.168.217.115_198.19.47.204_XENMASTER"
        ),
        "37": make_config(
            "198.19.46.29", "Pluto-MGMT-Pool_ctx109_192.168.101.109_198.19.46.29_XENMASTER"
        ),
        "38": make_config(
            "198.19.253.89", "mumctrp-xen-prod_p-mumctrp-ctx59_198.19.253.62_192.168.101.59_XENMASTER"
        ),
        "39": make_config(
            "198.18.252.230", "HYD4C-MGMT-CTX198_192.168.214.198_198.18.252.230_XENMASTER"
        ),
        "40": make_config(
            "198.18.252.230", "HYD4C-MGMT-CTX198_192.168.214.198_198.18.252.230_XENMASTER-test"
        ),
        "41": make_config(
            "198.18.60.151", "HYDTEJAS-XEN_172.28.28.15_198.18.60.151_XENMASTER"
        ),
        "42": make_config(
            "198.18.2.251", "Atlas-hydctrat-ctx-pool1_p-hydctrat-ctx-17_172.27.255.17_198.18.2.251_XENMASTER"
        ),
        "43": make_config(
            "198.19.56.197", "MUM-INFINIA-XEN_198.19.56.197_172.16.142.25_XENMASTER",
            username="cloudmonitoring",
            password="CTRLS.!@#$@4c$"
        ),
        "44": make_config(
            "192.168.217.29", "VENUS_BHARUWA-XEN8-POOL2_198.19.254.183_192.168.217.29_XENMASTER"
        ),
        "45": make_config(
            "198.18.7.19", "HYDATLMGMT.ctrl4c.com_198.18.7.19_172.27.255.136_XENMASTER"
        ),
        "46": make_config(
            "198.18.252.42", "MERCURY-MGMT-POOL_198.18.252.42_192.168.99.201_XENMASTER"
        ),
        "47": make_config(
            "198.18.130.134", "4CHYD-XEN8-POOL_192.168.214.27_198.18.130.109_XENMASTER"
        ),
        "48": make_config(
            "198.18.130.121", "HYD4C-CSINFO-CTX195_198.18.130.121_192.168.214.195_XENMASTER"
        ),
        "49": make_config(
            "198.18.20.52", "hydctratm-xen-prod_172.17.60.11_198.18.49.80_XENMASTER"
        ),
        "50": make_config(
            "198.19.76.154", "csinfo-mgmtctx-100_172.23.33.101_198.19.76.154_XENMASTER",
            #username="cloud-mon",
            #password="Information@123456"
        ),
        "51": make_config(
            "198.18.49.77", "hydctratm-xen-prod_172.17.60.11_198.18.49.77_XENMASTER"
        ),
        "52": make_config(
            "198.19.254.224", "MUM-Automation-Pool2_172.16.60.13_198.19.254.224__XENMASTER"
        ),
        "53": make_config(
            "198.19.254.238", "MUM-Automation-MGMT__172.16.60.23_198.19.254.238__XENMASTER"
        ),
        "54": make_config(
            "198.19.20.113", "MumCtrPrudence-Cluster1_198.19.20.113_172.16.50.28_XENMASTER",
            username="cloudmon",
            password="Inf0rmati0n@123456"
        ),
        "55": make_config(
            "198.19.253.77", "PLUTO-MUM_POOL3_plutomum-ctx151_192.168.101.151_198.19.46.51_XENMASTER"
        ),
        "56": make_config(
            "198.18.44.212", "jupiter-xen2_ctx126_192.168.92.126_198.18.44.212_XENMASTER"
        ),

    }

    return configs.get(host_id)


