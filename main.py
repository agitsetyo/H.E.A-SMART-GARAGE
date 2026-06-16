import utime
from boot import connect_wifi
from hardware import GarasiController
from mqtt_client import MQTTGarasi

# ─── INISIALISASI ───────────────────────────────
garasi = GarasiController()
mqtt   = None

# ─── CALLBACK PERINTAH DARI APP ─────────────────
def on_command(topic, msg):
    print("Perintah masuk | topic:", topic, "| pesan:", msg)

    if topic == b"garasi/cmd/pintu":
        perintah = msg.decode().strip().lower()
        if perintah == "buka" and not garasi.pintu_terbuka:
            garasi.buka_pintu("Remote")
            mqtt.publish_pintu(garasi.pintu_terbuka)
        elif perintah == "tutup" and garasi.pintu_terbuka:
            garasi.tutup_pintu()
            mqtt.publish_pintu(garasi.pintu_terbuka)

    elif topic == b"garasi/cmd/lampu1":
        perintah = msg.decode().strip().lower()
        if perintah == "on":
            garasi.led_p1.nyala()
            garasi.lampu1_on = True
        elif perintah == "off":
            garasi.led_p1.mati()
            garasi.lampu1_on = False
        mqtt.publish_lampu(garasi.lampu1_on, garasi.lampu2_on)

    elif topic == b"garasi/cmd/lampu2":
        perintah = msg.decode().strip().lower()
        if perintah == "on":
            garasi.led_p2.nyala()
            garasi.lampu2_on = True
        elif perintah == "off":
            garasi.led_p2.mati()
            garasi.lampu2_on = False
        mqtt.publish_lampu(garasi.lampu1_on, garasi.lampu2_on)


# ─── SETUP KONEKSI ──────────────────────────────
def setup():
    global mqtt

    wifi_ok = connect_wifi()
    if not wifi_ok:
        print("WiFi Gagal!")
        utime.sleep_ms(3000)
        return

    mqtt = MQTTGarasi(on_command=on_command)
    mqtt_ok = mqtt.connect()
    if mqtt_ok:
        print("WiFi + MQTT OK!")
        suhu, lembab = garasi.baca_suhu()
        if suhu is not None:
            mqtt.publish_sensor(suhu, lembab)
        mqtt.publish_pintu(garasi.pintu_terbuka)
        mqtt.publish_lampu(garasi.lampu1_on, garasi.lampu2_on)
    else:
        print("MQTT Gagal! Mode offline")
    utime.sleep_ms(2000)
    garasi.tampil_suhu()


# ─── AUTO RECONNECT ─────────────────────────────
def reconnect():
    global mqtt
    print("MQTT: reconnect 10 detik lagi...")
    utime.sleep_ms(10000)
    try:
        mqtt.disconnect()
    except:
        pass
    mqtt = MQTTGarasi(on_command=on_command)
    ok = mqtt.connect()
    if ok:
        print("MQTT: reconnect berhasil!")
        mqtt.publish_pintu(garasi.pintu_terbuka)
        mqtt.publish_lampu(garasi.lampu1_on, garasi.lampu2_on)
    else:
        print("MQTT: reconnect gagal")


# ─── MAIN LOOP ──────────────────────────────────
def loop():
    suhu_timer      = utime.ticks_ms()
    keepalive_timer = utime.ticks_ms()
    INTERVAL_SENSOR    = 10000   # kirim sensor tiap 10 detik
    INTERVAL_KEEPALIVE = 20000   # ping tiap 20 detik

    while True:

        # ── 1. Cek pesan masuk (error -1 sudah diabaikan di mqtt_client) ──
        if mqtt and mqtt.terhubung:
            mqtt.cek_pesan()

        # ── 2. Reconnect kalau benar-benar putus ──
        if mqtt and not mqtt.terhubung:
            reconnect()

        # ── 3. Keepalive ping tiap 20 detik ───────
        if mqtt and mqtt.terhubung:
            if utime.ticks_diff(utime.ticks_ms(), keepalive_timer) > INTERVAL_KEEPALIVE:
                try:
                    mqtt.client.ping()
                    print("MQTT: ping OK")
                except:
                    print("MQTT: ping gagal")
                    mqtt.terhubung = False
                keepalive_timer = utime.ticks_ms()

        # ── 4. Cek sensor sentuh TTP ─────────────
        lampu_berubah = garasi.cek_ttp()
        if lampu_berubah and mqtt and mqtt.terhubung:
            mqtt.publish_lampu(garasi.lampu1_on, garasi.lampu2_on)

        # ── 5. Scan RFID ─────────────────────────
        uid_str = garasi.scan_rfid()
        if uid_str:
            hasil = garasi.proses_rfid(uid_str)
            if mqtt and mqtt.terhubung:
                mqtt.publish_akses(hasil)
                mqtt.publish_pintu(garasi.pintu_terbuka)
                mqtt.publish_lampu(garasi.lampu1_on, garasi.lampu2_on)

        # ── 6. Kirim data sensor berkala ──────────
        if not garasi.pintu_terbuka:
            if utime.ticks_diff(utime.ticks_ms(), suhu_timer) > INTERVAL_SENSOR:
                suhu, lembab = garasi.baca_suhu()
                garasi.tampil_suhu()
                if suhu is not None and mqtt and mqtt.terhubung:
                    mqtt.publish_sensor(suhu, lembab)
                suhu_timer = utime.ticks_ms()
        utime.sleep_ms(100)


# ─── ENTRY POINT ────────────────────────────────
setup()
loop()
