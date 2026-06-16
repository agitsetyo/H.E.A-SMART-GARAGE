from machine import Pin, PWM, I2C
from mfrc522 import MFRC522
from i2c_lcd import I2cLcd
import dht
import utime

# ─── PIN CONFIG ─────────────────────────────────
PIN_DHT    = 4
PIN_SERVO  = 13
PIN_SDA    = 21
PIN_SCL    = 22
PIN_LED_H  = 26   # Hijau
PIN_LED_M  = 25   # Merah
PIN_LED_P1 = 32   # Putih 1 - lampu garasi
PIN_LED_P2 = 33   # Putih 2 - lampu rumah
PIN_TTP1   = 34   # Sensor sentuh lampu garasi
PIN_TTP2   = 35   # Sensor sentuh lampu rumah

# ─── UID WHITELIST ──────────────────────────────
WHITELIST = {
    "0A:83:F6:05": "Gabungan",
    "88:05:83:5B": "Ergi",
    "88:05:8B:E1": "Agit",
    "D0:38:CE:5F": "Haeda",
}


# ════════════════════════════════════════════════
# CLASS: SensorDHT  (sensor suhu & kelembapan)
# ════════════════════════════════════════════════
class SensorDHT:
    def __init__(self, pin):
        self.sensor = dht.DHT11(Pin(pin))

    def baca(self):
        """Kembalikan (suhu, kelembapan) atau (None, None) jika gagal."""
        try:
            self.sensor.measure()
            return self.sensor.temperature(), self.sensor.humidity()
        except:
            return None, None


# ════════════════════════════════════════════════
# CLASS: SensorTTP  (sensor sentuh kapasitif)
# ════════════════════════════════════════════════
class SensorTTP:
    def __init__(self, pin):
        self.pin  = Pin(pin, Pin.IN)
        self.last = 0

    def ditekan(self):
        """Kembalikan True sekali saat tombol baru ditekan (rising edge)."""
        val = self.pin.value()
        tekan = (val == 1 and self.last == 0)
        self.last = val
        return tekan


# ════════════════════════════════════════════════
# CLASS: Servo
# ════════════════════════════════════════════════
class Servo:
    def __init__(self, pin):
        self.pwm = PWM(Pin(pin), freq=50)

    def set_derajat(self, derajat):
        duty = int(40 + (derajat / 180) * 75)
        self.pwm.duty(duty)


# ════════════════════════════════════════════════
# CLASS: LED
# ════════════════════════════════════════════════
class LED:
    def __init__(self, pin):
        self.pin = Pin(pin, Pin.OUT)
        self.pin.value(0)

    def nyala(self):
        self.pin.value(1)

    def mati(self):
        self.pin.value(0)

    def kedip(self, kali=3, delay_ms=100):
        for _ in range(kali):
            self.pin.value(1)
            utime.sleep_ms(delay_ms)
            self.pin.value(0)
            utime.sleep_ms(delay_ms)


# ════════════════════════════════════════════════
# CLASS: LCD  (wrapper I2cLcd)
# ════════════════════════════════════════════════
class LCD:
    def __init__(self, sda, scl, addr=0x27, baris=2, kolom=16):
        i2c = I2C(0, sda=Pin(sda), scl=Pin(scl), freq=100000)
        self.lcd = I2cLcd(i2c, addr, baris, kolom)
        self.kolom = kolom

    def tulis(self, baris0="", baris1=""):
        self.lcd.clear()
        utime.sleep_ms(50)
        self.lcd.move_to(0, 0)
        self.lcd.putstr("{:<{w}}".format(baris0[:self.kolom], w=self.kolom))
        self.lcd.move_to(0, 1)
        self.lcd.putstr("{:<{w}}".format(baris1[:self.kolom], w=self.kolom))


# ════════════════════════════════════════════════
# CLASS: SensorRFID
# ════════════════════════════════════════════════
class SensorRFID:
    def __init__(self, sck, mosi, miso, rst, cs):
        self.rfid = MFRC522(sck=sck, mosi=mosi, miso=miso, rst=rst, cs=cs)

    def scan(self):
        """Kembalikan string UID (misal '0A:83:F6:05') atau None."""
        stat, _ = self.rfid.request(MFRC522.REQIDL)
        if stat == MFRC522.OK:
            stat, uid = self.rfid.anticoll()
            if stat == MFRC522.OK and uid:
                self.rfid.halt()
                return ":".join("{:02X}".format(x) for x in uid[:4])
        return None


# ════════════════════════════════════════════════
# CLASS: GarasiController  (logika kendali utama)
# ════════════════════════════════════════════════
class GarasiController:
    def __init__(self):
        self.dht    = SensorDHT(PIN_DHT)
        self.servo  = Servo(PIN_SERVO)
        self.lcd    = LCD(PIN_SDA, PIN_SCL)
        self.led_h  = LED(PIN_LED_H)
        self.led_m  = LED(PIN_LED_M)
        self.led_p1 = LED(PIN_LED_P1)
        self.led_p2 = LED(PIN_LED_P2)
        self.ttp1   = SensorTTP(PIN_TTP1)
        self.ttp2   = SensorTTP(PIN_TTP2)
        self.rfid   = SensorRFID(sck=18, mosi=23, miso=19, rst=27, cs=5)

        self.pintu_terbuka = False
        self.lampu1_on     = False
        self.lampu2_on     = False

        self._startup()

    def _startup(self):
        self.servo.set_derajat(0)
        self.lcd.tulis("Garasi Ready", "Tap kartu...")
        print("=== Sistem Garasi Siap ===")
        utime.sleep_ms(2000)
        self.tampil_suhu()

    # ── Suhu ─────────────────────────────────────
    def baca_suhu(self):
        return self.dht.baca()

    def tampil_suhu(self):
        suhu, lembab = self.baca_suhu()
        if suhu is not None:
            self.lcd.tulis("Suhu: {}C".format(suhu), "Lembab: {}%".format(lembab))
        else:
            self.lcd.tulis("Sensor Error", "")

    # ── Lampu sentuh ─────────────────────────────
    def cek_ttp(self):
        """Cek sensor sentuh, toggle lampu jika ditekan. Kembalikan True jika ada perubahan."""
        berubah = False

        if self.ttp1.ditekan():
            self.lampu1_on = not self.lampu1_on
            self.led_p1.nyala() if self.lampu1_on else self.led_p1.mati()
            print("Lampu garasi:", "ON" if self.lampu1_on else "OFF")
            utime.sleep_ms(300)
            berubah = True

        if self.ttp2.ditekan():
            self.lampu2_on = not self.lampu2_on
            self.led_p2.nyala() if self.lampu2_on else self.led_p2.mati()
            print("Lampu rumah:", "ON" if self.lampu2_on else "OFF")
            utime.sleep_ms(300)
            berubah = True

        return berubah

    # ── Pintu ─────────────────────────────────────
    def buka_pintu(self, nama):
        self.lcd.tulis("Selamat datang", nama)
        print("Membuka pintu untuk:", nama)

        self.servo.set_derajat(0)
        utime.sleep_ms(300)

        for derajat in range(0, 142, 3):
            self.servo.set_derajat(derajat)
            self.led_h.nyala()
            utime.sleep_ms(30)
            self.led_h.mati()
            utime.sleep_ms(30)

        self.led_h.nyala()
        self.led_p1.nyala()
        self.led_p2.nyala()
        self.lampu1_on = True
        self.lampu2_on = True
        self.pintu_terbuka = True
        print("Pintu terbuka.")

        start = utime.ticks_ms()
        while utime.ticks_diff(utime.ticks_ms(), start) < 10000:
            self.cek_ttp()
            utime.sleep_ms(100)

        self.tampil_suhu()

    def tutup_pintu(self):
        print("Menutup pintu...")
        self.lcd.tulis("Menutup pintu..", "")
        self.led_h.mati()

        for derajat in range(141, -1, -3):
            self.servo.set_derajat(derajat)
            self.led_m.nyala()
            utime.sleep_ms(30)
            self.led_m.mati()
            utime.sleep_ms(30)

        self.pintu_terbuka = False
        self.led_m.nyala()
        self.lcd.tulis("Pintu Tertutup", "")
        print("Pintu tertutup.")
        utime.sleep_ms(10000)
        self.led_m.mati()

        self.tampil_suhu()

    # ── RFID ──────────────────────────────────────
    def scan_rfid(self):
        return self.rfid.scan()

    def proses_rfid(self, uid_str):
        """Proses UID, kembalikan dict status untuk MQTT atau None jika tidak ada kartu."""
        print("UID scan:", uid_str)
        if uid_str in WHITELIST:
            nama = WHITELIST[uid_str]
            print("Akses diterima:", nama)
            if not self.pintu_terbuka:
                self.buka_pintu(nama)
            else:
                self.tutup_pintu()
            return {"akses": "diterima", "nama": nama, "uid": uid_str}
        else:
            print("Akses ditolak!")
            self.lcd.tulis("Akses Ditolak!", uid_str[:16])
            utime.sleep_ms(2000)
            self.tampil_suhu()
            return {"akses": "ditolak", "nama": "unknown", "uid": uid_str}
