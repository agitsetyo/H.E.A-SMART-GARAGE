import time
from lcd_api import LcdApi
from machine import I2C
 
MASK_RS = 0x01
MASK_RW = 0x02
MASK_E  = 0x04
SHIFT_BACKLIGHT = 3
SHIFT_DATA = 4
 
class I2cLcd(LcdApi):
    def __init__(self, i2c, i2c_addr, num_lines, num_columns):
        self.i2c = i2c
        self.i2c_addr = i2c_addr
        self.i2c_buf = bytearray(1)
        self.backlight = True
        time.sleep_ms(20)
        self.hal_write_init_nibble(0x30)
        time.sleep_ms(5)
        self.hal_write_init_nibble(0x30)
        time.sleep_us(100)
        self.hal_write_init_nibble(0x30)
        time.sleep_us(100)
        self.hal_write_init_nibble(0x20)  # Switch to 4-bit mode
        time.sleep_us(100)
        LcdApi.__init__(self, num_lines, num_columns)
        cmd = LcdApi.LCD_FUNCTION
        if num_lines > 1:
            cmd |= LcdApi.LCD_FUNCTION_2LINES
        self.hal_write_command(cmd)
 
    def hal_backlight_on(self):
        self.i2c_buf[0] = (1 << SHIFT_BACKLIGHT)
        self.i2c.writeto(self.i2c_addr, self.i2c_buf)
 
    def hal_backlight_off(self):
        self.i2c_buf[0] = 0
        self.i2c.writeto(self.i2c_addr, self.i2c_buf)
 
    def hal_write_init_nibble(self, nibble):
        byte = ((nibble >> 4) & 0x0f) << SHIFT_DATA
        self.i2c_buf[0] = byte | MASK_E
        self.i2c.writeto(self.i2c_addr, self.i2c_buf)
        self.i2c_buf[0] = byte
        self.i2c.writeto(self.i2c_addr, self.i2c_buf)
 
    def hal_write_command(self, cmd):
        byte = ((self.backlight << SHIFT_BACKLIGHT) |
                (((cmd >> 4) & 0x0f) << SHIFT_DATA))
        self.i2c_buf[0] = byte | MASK_E
        self.i2c.writeto(self.i2c_addr, self.i2c_buf)
        self.i2c_buf[0] = byte
        self.i2c.writeto(self.i2c_addr, self.i2c_buf)
        byte = ((self.backlight << SHIFT_BACKLIGHT) |
                ((cmd & 0x0f) << SHIFT_DATA))
        self.i2c_buf[0] = byte | MASK_E
        self.i2c.writeto(self.i2c_addr, self.i2c_buf)
        self.i2c_buf[0] = byte
        self.i2c.writeto(self.i2c_addr, self.i2c_buf)
        if cmd <= 3:
            time.sleep_ms(5)
 
    def hal_write_data(self, data):
        byte = (MASK_RS |
                (self.backlight << SHIFT_BACKLIGHT) |
                (((data >> 4) & 0x0f) << SHIFT_DATA))
        self.i2c_buf[0] = byte | MASK_E
        self.i2c.writeto(self.i2c_addr, self.i2c_buf)
        self.i2c_buf[0] = byte
        self.i2c.writeto(self.i2c_addr, self.i2c_buf)
        byte = (MASK_RS |
                (self.backlight << SHIFT_BACKLIGHT) |
                ((data & 0x0f) << SHIFT_DATA))
        self.i2c_buf[0] = byte | MASK_E
        self.i2c.writeto(self.i2c_addr, self.i2c_buf)
        self.i2c_buf[0] = byte
        self.i2c.writeto(self.i2c_addr, self.i2c_buf)
