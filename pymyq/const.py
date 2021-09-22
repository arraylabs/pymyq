"""The myq constants."""

OAUTH_CLIENT_ID = "IOS_CGI_MYQ"
OAUTH_CLIENT_SECRET = "VUQ0RFhuS3lQV3EyNUJTdw=="
OAUTH_BASE_URI = "https://partner-identity.myq-cloud.com"
OAUTH_AUTHORIZE_URI = f"{OAUTH_BASE_URI}/connect/authorize"
OAUTH_REDIRECT_URI = "com.myqops://ios"
OAUTH_TOKEN_URI = f"{OAUTH_BASE_URI}/connect/token"

ACCOUNTS_ENDPOINT = "https://accounts.myq-cloud.com/api/v6.0/accounts"
DEVICES_ENDPOINT = (
    "https://devices.myq-cloud.com/api/v5.2/Accounts/{account_id}/Devices"
)

WAIT_TIMEOUT = 60

DEVICE_TYPE = "device_type"
DEVICE_TYPE_GATE = "gate"
DEVICE_FAMILY = "device_family"
DEVICE_FAMILY_GATEWAY = "gateway"
DEVICE_FAMILY_GARAGEDOOR = "garagedoor"
DEVICE_FAMILY_LAMP = "lamp"
DEVICE_FAMILY_LOCK = "locks"
DEVICE_STATE = "state"
DEVICE_STATE_ONLINE = "online"

MANUFACTURER = "The Chamberlain Group Inc."

KNOWN_MODELS = {
    "00": "Chamberlain Ethernet Gateway",
    "01": "LiftMaster Ethernet Gateway",
    "02": "Craftsman Ethernet Gateway",
    "03": "Chamberlain Wi-Fi hub",
    "04": "LiftMaster Wi-Fi hub",
    "05": "Craftsman Wi-Fi hub",
    "08": "LiftMaster Wi-Fi GDO DC w/Battery Backup",
    "09": "Chamberlain Wi-Fi GDO DC w/Battery Backup",
    "10": "Craftsman Wi-Fi GDO DC 3/4HP",
    "11": "MyQ Replacement Logic Board Wi-Fi GDO DC 3/4HP",
    "12": "Chamberlain Wi-Fi GDO DC 1.25HP",
    "13": "LiftMaster Wi-Fi GDO DC 1.25HP",
    "14": "Craftsman Wi-Fi GDO DC 1.25HP",
    "15": "MyQ Replacement Logic Board Wi-Fi GDO DC 1.25HP",
    "0A": "Chamberlain Wi-Fi GDO or Gate Operator AC",
    "0B": "LiftMaster Wi-Fi GDO or Gate Operator AC",
    "0C": "Craftsman Wi-Fi GDO or Gate Operator AC",
    "0D": "MyQ Replacement Logic Board Wi-Fi GDO or Gate Operator AC",
    "0E": "Chamberlain Wi-Fi GDO DC 3/4HP",
    "0F": "LiftMaster Wi-Fi GDO DC 3/4HP",
    "20": "Chamberlain MyQ Home Bridge",
    "21": "LiftMaster MyQ Home Bridge",
    "23": "Chamberlain Smart Garage Hub",
    "24": "LiftMaster Smart Garage Hub",
    "27": "LiftMaster Wi-Fi Wall Mount opener",
    "28": "LiftMaster Commercial Wi-Fi Wall Mount operator",
    "80": "EU LiftMaster Ethernet Gateway",
    "81": "EU Chamberlain Ethernet Gateway",
}
