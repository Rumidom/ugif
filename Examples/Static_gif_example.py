import math
import st7789 as st7789
import framebuf
from machine import Pin, SPI
from ugif import gif
import micropython

# set landscape screen
screen_width = 240
screen_height = 240
screen_rotation = 3

spi = SPI(1,
          baudrate=31250000,
          polarity=1,
          phase=1,
          bits=8,
          firstbit=SPI.MSB,
          sck=Pin(4),
          mosi=Pin(5))

display = st7789.ST7789(
    spi,
    screen_width,
    screen_height,
    reset=Pin(9, Pin.OUT),
    #cs=Pin(9, Pin.OUT),
    dc=Pin(8, Pin.OUT),
    backlight=Pin(7, Pin.OUT),
    rotation=screen_rotation)

buffer_width = 240
buffer_height = 1
line_buffer = bytearray(screen_width*buffer_height*2)
line_buffer = bytearray()
def drawToScreen_LinebyLine(x,y,color):
    global line_buffer 
    line_buffer.extend(color.to_bytes(2,'big'))
    if x == buffer_width-1 and y%buffer_height == 0 and y!=0:
        display.blit_buffer(line_buffer, 0, y, buffer_width, buffer_height)
        line_buffer = bytearray()
        
def drawToScreen_PixelbyPixel(x,y,color):
    display.pixel(x,y,color)

# drawToScreen_LinebyLine is faster
display.fill(0)
gif_obj = gif('jake.gif')
gif_obj.BlitFrameToScreen(0,drawToScreen_LinebyLine)