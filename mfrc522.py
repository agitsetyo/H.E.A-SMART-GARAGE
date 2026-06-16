from machine import Pin, SPI
import utime
 
class MFRC522:
    OK     = 0
    ERR    = 2
    REQIDL = 0x26
 
    def __init__(self, sck, mosi, miso, rst, cs):
        self.cs  = Pin(cs, Pin.OUT)
        self.rst = Pin(rst, Pin.OUT)
        self.cs.value(1)
        self.rst.value(1)
        self.spi = SPI(1, baudrate=1000000, polarity=0, phase=0,
                       sck=Pin(sck), mosi=Pin(mosi), miso=Pin(miso))
        self._init()
 
    def _init(self):
        self.rst.value(0)
        utime.sleep_ms(50)
        self.rst.value(1)
        self._write(0x2A, 0x8D)
        self._write(0x2B, 0x3E)
        self._write(0x2D, 30)
        self._write(0x2C, 0)
        self._write(0x15, 0x40)
        self._write(0x11, 0x3D)
        self._write(0x14, self._read(0x14) | 0x03)
 
    def _write(self, reg, val):
        self.cs.value(0)
        self.spi.write(bytes([(reg << 1) & 0x7E, val]))
        self.cs.value(1)
 
    def _read(self, reg):
        self.cs.value(0)
        self.spi.write(bytes([((reg << 1) & 0x7E) | 0x80]))
        val = self.spi.read(1)
        self.cs.value(1)
        return val[0]
 
    def _set(self, reg, mask):
        self._write(reg, self._read(reg) | mask)
 
    def _clr(self, reg, mask):
        self._write(reg, self._read(reg) & (~mask))
 
    def _transceive(self, data):
        self._write(0x02, 0x77)
        self._clr(0x04, 0x80)
        self._set(0x0A, 0x80)
        self._write(0x01, 0x00)
        for b in data:
            self._write(0x09, b)
        self._write(0x01, 0x0C)
        self._set(0x0D, 0x80)
 
        i = 2000
        while i > 0:
            n = self._read(0x04)
            if n & 0x30:
                break
            i -= 1
 
        self._clr(0x0D, 0x80)
        if i == 0:
            return self.ERR, []
        if self._read(0x06) & 0x1B:
            return self.ERR, []
 
        n    = self._read(0x0A)
        recv = [self._read(0x09) for _ in range(n)]
        return self.OK, recv
 
    def request(self, mode):
        self._write(0x0D, 0x07)
        stat, recv = self._transceive([mode])
        if stat != self.OK or len(recv) < 2:
            return self.ERR, None
        return self.OK, recv
 
    def anticoll(self):
        self._write(0x0D, 0x00)
        stat, recv = self._transceive([0x93, 0x20])
        if stat == self.OK and len(recv) == 5:
            if recv[0] ^ recv[1] ^ recv[2] ^ recv[3] == recv[4]:
                return self.OK, recv
        return self.ERR, None
 
    def halt(self):
        self._transceive([0x50, 0x00])
