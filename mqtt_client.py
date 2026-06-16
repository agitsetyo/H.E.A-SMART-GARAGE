from umqtt.simple import MQTTClient
import utime

# ─── KONFIGURASI HiveMQ ─────────────────────────
MQTT_HOST      = "url"
MQTT_PORT      = port
MQTT_USER      = "user"
MQTT_PASSWORD  = "pw"
MQTT_CLIENT_ID = "client id"

# ─── TOPIC PUBLISH (ESP32 → App) ────────────────
TOPIC_SUHU   = b"garasi/suhu"
TOPIC_LEMBAB = b"garasi/kelembapan"
TOPIC_PINTU  = b"garasi/pintu"
TOPIC_LAMPU1 = b"garasi/lampu/garasi"
TOPIC_LAMPU2 = b"garasi/lampu/rumah"
TOPIC_AKSES  = b"garasi/akses"

# ─── TOPIC SUBSCRIBE (App → ESP32) ──────────────
TOPIC_CMD_PINTU  = b"garasi/cmd/pintu"
TOPIC_CMD_LAMPU1 = b"garasi/cmd/lampu1"
TOPIC_CMD_LAMPU2 = b"garasi/cmd/lampu2"


class MQTTGarasi:
    def __init__(self, on_command=None):
        self.client     = None
        self.on_command = on_command
        self.terhubung  = False

    # ── Koneksi ──────────────────────────────────
    def connect(self):
        print("MQTT: mencoba connect ke", MQTT_HOST)
        try:
            self.client = MQTTClient(
                MQTT_CLIENT_ID,
                MQTT_HOST,
                port=MQTT_PORT,
                user=MQTT_USER,
                password=MQTT_PASSWORD,
                ssl=True,
                ssl_params={"server_hostname": MQTT_HOST},
                keepalive=60
            )

            if self.on_command:
                self.client.set_callback(self.on_command)

            print("MQTT: menghubungkan...")
            self.client.connect()
            self.terhubung = True
            print("MQTT: TERHUBUNG ke HiveMQ!")

            self.client.subscribe(TOPIC_CMD_PINTU)
            self.client.subscribe(TOPIC_CMD_LAMPU1)
            self.client.subscribe(TOPIC_CMD_LAMPU2)
            print("MQTT: subscribe OK")
            return True

        except OSError as e:
            print("MQTT ERROR (OSError):", e)
            self.terhubung = False
            return False
        except Exception as e:
            print("MQTT ERROR:", type(e).__name__, e)
            self.terhubung = False
            return False

    def disconnect(self):
        if self.client and self.terhubung:
            try:
                self.client.disconnect()
            except:
                pass
            self.terhubung = False

    # ── Cek pesan masuk (non-blocking, toleran error -1) ──
    def cek_pesan(self):
        if not self.terhubung:
            return
        try:
            self.client.check_msg()
        except OSError as e:
            # error -1 = tidak ada pesan, bukan koneksi putus → abaikan
            if e.args[0] == -1:
                pass
            else:
                # error lain (misal 104, 110) = koneksi benar-benar putus
                print("MQTT koneksi putus (OSError {})".format(e.args[0]))
                self.terhubung = False
        except Exception as e:
            print("MQTT cek_pesan error:", e)
            self.terhubung = False

    # ── Publish helper (plain text) ──────────────
    def _publish(self, topic, pesan):
        if not self.terhubung:
            return
        try:
            self.client.publish(topic, str(pesan))
            print("MQTT publish", topic, "->", pesan)
        except Exception as e:
            print("MQTT publish error:", e)
            self.terhubung = False

    # ── Publish spesifik ─────────────────────────
    def publish_sensor(self, suhu, lembab):
        self._publish(TOPIC_SUHU,   "{}".format(suhu))
        self._publish(TOPIC_LEMBAB, "{}".format(lembab))

    def publish_pintu(self, terbuka):
        self._publish(TOPIC_PINTU, "buka" if terbuka else "tutup")

    def publish_lampu(self, lampu1, lampu2):
        self._publish(TOPIC_LAMPU1, "on" if lampu1 else "off")
        self._publish(TOPIC_LAMPU2, "on" if lampu2 else "off")

    def publish_akses(self, akses_dict):
        nama  = akses_dict.get("nama", "unknown")
        akses = akses_dict.get("akses", "ditolak")
        uid   = akses_dict.get("uid", "??:??:??:??")
        if akses == "diterima":
            pesan = "Diterima: {}".format(nama)
        else:
            pesan = "Ditolak: {}".format(uid)
        self._publish(TOPIC_AKSES, pesan)
