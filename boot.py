import network
import utime

WIFI_SSID     = "wifi kalian "
WIFI_PASSWORD = "12345678"

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    
    # Reset interface
    wlan.active(False)
    utime.sleep_ms(500)
    wlan.active(True)
    utime.sleep_ms(500)

    if wlan.isconnected():
        print("Wi-Fi sudah terhubung:", wlan.ifconfig()[0])
        return True

    print("Menghubungkan ke Wi-Fi:", WIFI_SSID)
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)

    timeout = 15
    for i in range(timeout * 10):
        if wlan.isconnected():
            print("Wi-Fi terhubung! IP:", wlan.ifconfig()[0])
            return True
        utime.sleep_ms(100)

    print("GAGAL terhubung ke Wi-Fi!")
    return False
