import machine
import sh1106_lt
import fontlib
import framebuf
import math
from ugif import gif
from machine import Pin

screen_width = 128
screen_height = 64

i2c = machine.I2C(1,sda=machine.Pin(14), scl=machine.Pin(15))
oled = sh1106_lt.SH1106_I2C(screen_width, screen_height, i2c,flip=True)
oled.fill(0)
oled.show()
fbuf = framebuf.FrameBuffer(oled.buffer, screen_width, screen_height, framebuf.MONO_VLSB)
fbuf.fill(0)

def drawToScreen_PixelbyPixel(x,y,color):
    oled.pixel(x, y,color)

gif_obj = gif('Bongo_Cat_64x64.gif',useram = True)
gif_obj.setPosition(32,0)

while True:
    gif_obj.BlitAnimationToScreen(drawToScreen_PixelbyPixel)
    oled.show()
    