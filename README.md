# ugif
This is a simple micropython library for decoding gifs with low resources. Modern microcontrollers have a lot more ram than they used to have but it is still barely enough to handle images. A single 240x240 compressed gif frame takes about 35kb of memory, which is quite significant. This library loads the compressed image to ram and dynamically decodes it directly to screen via a callback function. Currently there is no support for animation 

```python
def drawToScreen_PixelbyPixel(x,y,color):
    display.pixel(x,y,color)

# Draws frame 0 to Screen pixel by pixel
gif_obj = gif('jake.gif')
gif_obj.BlitToScreen(0,drawToScreen_LinebyLine)
```
this approach works but its very slow



https://github.com/user-attachments/assets/f57805bc-e20f-4f8e-8c96-0629b0321fab



# TODO
- [ ] Add option to hold the decompressed image in memory
- [ ] Add animation support

# LICENSE:
this project is [MIT licensed](https://github.com/Rumidom/micropython_fontlib/blob/main/LICENSE)

# Support
[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/M4M41NQV7I)
