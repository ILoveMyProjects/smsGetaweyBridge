"""Constants for smsGetaweyBridge."""

DOMAIN = "smsgetaweybridge"
NAME = "smsGetaweyBridge"
DEFAULT_PORT = 8080
DEFAULT_SCAN_INTERVAL = 30
CONF_HOST = "host"
CONF_PORT = "port"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_SSL = "use_ssl"
EVENT_SMS_RECEIVED = f"{DOMAIN}_sms_received"
EVENT_SMS_STATUS = f"{DOMAIN}_sms_status"
EVENT_SMS_QUEUED = f"{DOMAIN}_sms_queued"
SERVICE_SEND_SMS = "send_sms"
MAX_SEEN = 2000
