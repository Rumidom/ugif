# ugif
This is a micropython library for decoding gifs on low resources. Modern microcontrollers have a lot more ram than they used to have but it is still barely enough to handle images. A single 240x240 compressed gif frame takes about 35kb of memory, which is quite significant. This library loads the compressed frames dynamically directly to the screen via a callback function. (this approach works but its very slow.)

https://github.com/user-attachments/assets/f57805bc-e20f-4f8e-8c96-0629b0321fab

## Displaying static Gifs
```python
def drawToScreen_PixelbyPixel(x,y,color):
    display.pixel(x,y,color)

# Draws frame 0 to Screen pixel by pixel
gif_obj = gif('jake.gif')
gif_obj.BlitToScreen(0,drawToScreen_LinebyLine)
```

## Displaying Animated Gif from flash
By default ugif will load each frame from the gif file decompress it and display it to screen. The decompression will happend every time a frame is needed.
```python
def drawToScreen_PixelbyPixel(x,y,color):
    oled.pixel(x, y,color)

gif_obj = gif('Bongo_Cat_64x64.gif')
gif_obj.setPosition(32,0)

while True:
    gif_obj.BlitAnimationToScreen(drawToScreen_PixelbyPixel)
    oled.show()
```

## Displaying Animated Gif from ram
If 'useram' is enabled ugif will load the gif file decompress it and save the decompressed frame data on the gif object,
the decompression will happen once and after the gif is loaded the frames will be displayed from ram.
```python
def drawToScreen_PixelbyPixel(x,y,color):
    oled.pixel(x, y,color)

gif_obj = gif('Bongo_Cat_64x64.gif',useram = True)
gif_obj.setPosition(32,0)

while True:
    gif_obj.BlitAnimationToScreen(drawToScreen_PixelbyPixel)
    oled.show()
```


https://github.com/user-attachments/assets/bd1c00c3-2735-452e-a132-a9631fec73a7


# TODO
- [x] Add support for monocrome gifs
- [x] Add option to hold the decompressed image in memory
- [x] Add animation support
- [x] Use 1 bit per color to save ram on monocrome mode
- [ ] Implement all disposal methods for compatibility
- [ ] Optimize with native/viper decorators
  
# LICENSE:
this project is [MIT licensed](https://github.com/Rumidom/micropython_fontlib/blob/main/LICENSE)

# Support
[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/M4M41NQV7I)
