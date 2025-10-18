#!/usr/bin/env python3
# discovery_hardcoded.py

import json
import paho.mqtt.client as mqtt

# ==== ハードコード設定 ====
MQTT_HOST = "psv.internal"
MQTT_PORT = 1883
MQTT_USER = None  # 例: "username"
MQTT_PASS = None  # 例: "password"
CLIENT_ID  = "amedas_discovery_once"

CONFIG_TOPIC = "homeassistant/sensor/amedas/config"  # Discovery用
TOPIC_PREFIX = "weather/amedas"                       # state/attr/availability を出す想定先

# Discoveryペイロード（固定）
DISCOVERY = {
    "name": "JMA AMEDAS Raw",
    "uniq_id": "jma_amedas_raw_1",
    "stat_t": f"{TOPIC_PREFIX}/state",
    "json_attr_t": f"{TOPIC_PREFIX}/attr",
    "avty_t": f"{TOPIC_PREFIX}/availability",
    "pl_avail": "online",
    "pl_not_avail": "offline",
    "dev": {
        "ids": ["amedas"],
        "name": "AMEDAS Feed",
        "mf": "fjworks",
        "mdl": "JMA MQTT bridge"
    }
}
# ==========================

def main():
    client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311)
    if MQTT_USER:
        client.username_pw_set(MQTT_USER, MQTT_PASS)

    client.connect(MQTT_HOST, MQTT_PORT, keepalive=30)
    client.loop_start()

    # retain=True, QoS=1（PUBACK待ち）
    info1 = client.publish(CONFIG_TOPIC, json.dumps(DISCOVERY, ensure_ascii=False), qos=1, retain=True)
    info2 = client.publish(DISCOVERY['avty_t'], 'online', qos=1, retain=True)
    info1.wait_for_publish()
    info2.wait_for_publish()

    client.disconnect()
    client.loop_stop()

if __name__ == "__main__":
    main()
