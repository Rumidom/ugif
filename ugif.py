import struct
import gc
import os
import time
#import micropython

def ByteArrayReverse(Barr):
    l = list(Barr)
    l = l[::-1]
    return bytearray(l)

def color565(red, green=0, blue=0):
    """
    Convert red, green and blue values (0-255) into a 16-bit 565 encoding.
    """
    if isinstance(red, (tuple, list)):
        red, green, blue = red[:3]
    return (red & 0xF8) << 8 | (green & 0xFC) << 3 | blue >> 3

class gif():
    def __init__(self,path,x=0,y=0,useram=False,verbose = False):
        src = open(path, "rb")
        Header = self.getHeader(src)
        dummybuffer = bytearray(os.stat(path)[6])
        self.path = path
        self.x = x
        self.y = y
        self.useram = useram
        self.ID_tag = Header[0]
        self.Version = Header[1]
        self.Width = Header[2]
        self.Height = Header[3]
        self.Field = Header[4][0]
        self.Background_ci = Header[5][0]
        self.Pixel_AR = Header[6][0]
        
        self.ColorTable = []
        self.ColorTable565 = []
        self.monocrome = False
        self.AnimTime = 0
        self.currentFrameIndex = 0
        ColorTableLen = 0
        if (self.Field >> 7) & 1:
            ColorTableLen = 2**((self.Field & 0b111)+1)
            self.getColorTable(src,ColorTableLen)
            if ColorTableLen == 2: 
                self.getColorTable = [False,True]
                self.monocrome = True
            else:
                self.getColorTable565()
        else:
            raise Exception("Only gifs with global color table are supported")
        

        self.Frames = []
        self.decoded = []
        self.n_frames = 0
        self.loopcount = 0
        self.getData(src)
        if verbose:
            print(path)
            print("Colors: ",ColorTableLen)
            print("Size: ",self.Width,",",self.Height)
            print("Loop count: ",self.loopcount)
            print("Frames: ",self.n_frames)
    
    def setPosition(self,x,y):
        self.x = x
        self.y = y
        
    def getColorTable565(self):
        for color in self.ColorTable:
            self.ColorTable565.append(color565(color[0],color[1],color[2]))
    
    def blit(self,arr,callback,startPos,frameSize):
        scr_y = startPos[1]
        count = 0
        for i,byte in enumerate(arr):
            if self.monocrome:
                for bit_i in range(8):
                    bit = (byte >> bit_i) & 1
                    scr_x = count%frameSize[0] + startPos[0]
                    if scr_x == startPos[0] and count != 0:
                        scr_y+= 1
                    callback(scr_x,scr_y,bit)
                    count += 1

            else:
                scr_x = i%frameSize[0] + startPos[0]
                if scr_x == startPos[0] and i != 0:
                     scr_y+= 1
                else:
                    if useColor565:
                        callback(scr_x,scr_y,self.ColorTable565[byte])
                    else:
                        callback(scr_x,scr_y,self.ColorTable[byte])

    def lzw_DecodeToScreen(self,data,callback,startPos,frameSize,palBits,useColor565=True):
        # code from: https://github.com/qalle2/pygif/blob/main/gifdec.py
        # decode Lempel-Ziv-Welch (LZW) data (bytes)
        # palBits: palette bit depth in LZW encoding (2-8)
        # return: indexed image data (bytes)
        #outSrc    = open(OutputFilePath, "wb")
        pos       = 0                 # byte position in LZW data
        bitPos    = 0                 # bit position within LZW data byte (0-7)
        codeLen   = palBits + 1       # current length of LZW codes, in bits (3-12)
        code      = 0                 # current LZW code (0-4095)
        prevCode  = None              # previous code for dictionary entry or None
        clearCode = 2 ** palBits      # LZW clear code
        endCode   = 2 ** palBits + 1  # LZW end code
        entry     = bytearray()       # reconstructed dictionary entry
        codeCount = 0                 # number of LZW codes read (statistics only)
        bitCount  = 0                 # number of LZW bits read (statistics only)
        decoded_data = bytearray()
        outbyte = 0b00000000
        bit_index = 0
        # LZW dictionary: index = code, value = entry (reference to another code,
        # final byte)
        lzwDict = [(None, i) for i in range(2 ** palBits + 2)]
        imageDataLen = 0
        scr_x = startPos[0]
        scr_y = startPos[1]
        while True:
            # get current LZW code (0-4095) from remaining data:
            # 1) get the 1-3 bytes that contain the code; equivalent to:
            # codeByteCnt = ceil((bitPos + codeLen) / 8)
            codeByteCnt = (bitPos + codeLen + 7) // 8
            if pos + codeByteCnt > len(data):
                sys.exit("Unexpected end of file.")
            codeBytes = data[pos:pos+codeByteCnt]
            # 2) convert the bytes into an integer (first byte = least significant)
            code = sum(b << (i * 8) for (i, b) in enumerate(codeBytes))
            # 3) delete previously-read bits from the end and unnecessary bits
            # from the beginning; equivalent to:
            # code = (code >> bitPos) % 2 ** codeLen
            code = (code >> bitPos) & ((1 << codeLen) - 1)

            # advance byte/bit position so the next code can be read correctly
            bitPos += codeLen
            pos += bitPos >> 3  # pos += bitPos // 8
            bitPos &= 0b111     # bitPos %= 8

            # update statistics
            codeCount += 1
            bitCount += codeLen
            if code == clearCode:
                # LZW clear code:
                # reset dict. & code length; don't add dict. entry with next code
                lzwDict = lzwDict[:2**palBits+2]
                codeLen = palBits + 1
                prevCode = None
            elif code == endCode:
                break
            elif code > len(lzwDict):
                sys.exit("Invalid LZW code.")
            else:
                # dictionary entry
                if prevCode is not None:
                    # add new entry (previous code, first byte of current/previous
                    # entry)
                    suffixCode = code if code < len(lzwDict) else prevCode
                    while suffixCode is not None:
                        (suffixCode, suffixByte) = lzwDict[suffixCode]
                    lzwDict.append((prevCode, suffixByte))
                    prevCode = None
                # reconstruct and store entry
                entry =  bytearray(b'')
                referredCode = code
                while referredCode is not None:
                    (referredCode, byte) = lzwDict[referredCode]
                    entry.append(byte)
                entry = ByteArrayReverse(entry)
                
                for i,byte in enumerate(entry):
                    count = i+imageDataLen
                    scr_x = count%frameSize[0] + startPos[0]
                    if scr_x == startPos[0] and count != 0:
                         scr_y+= 1
                    if self.monocrome:
                        callback(scr_x,scr_y,byte)
                        outbyte =  outbyte | (byte << bit_index)
                        bit_index += 1
                        if bit_index > 7:
                            bit_index = 0 
                            decoded_data.append(outbyte)
                            outbyte = 0b00000000
                    else:
                        if useColor565:
                            callback(scr_x,scr_y,self.ColorTable565[byte])
                        else:
                            callback(scr_x,scr_y,self.ColorTable[byte])
                    
                imageDataLen += len(entry)
                # prepare to add a dictionary entry
                if len(lzwDict) < 2 ** 12:
                    prevCode = code
                if len(lzwDict) == 2 ** codeLen and codeLen < 12:
                    codeLen += 1
                if self.useram and not self.monocrome:
                    decoded_data += entry

            gc.collect()
        if (len(decoded_data)>0):
            #print(len(decoded_data))
            self.decoded.append(decoded_data)
            #print(f"LZW data: {codeCount} codes, {bitCount} bits, {imageDataLen} pixels")
    
    def getColorTable(self,src,ColorTableLen):
        for i in range(ColorTableLen):
            self.ColorTable.append((src.read(1)[0],src.read(1)[0],src.read(1)[0]))
    
    def getHeader(self,src):
        ID_tag = src.read(3)
        Version = src.read(3)
        Width = int.from_bytes(src.read(2), 'little')
        Height = int.from_bytes(src.read(2), 'little')
        Field = src.read(1)
        Background_ci = src.read(1)
        Pixel_AR = src.read(1)
        Header = ID_tag,Version,Width,Height,Field,Background_ci,Pixel_AR
        #print(Header)
        return Header
    
    def ReadSubBlocks(self,src):
        subBlocksList = []
        while True:
            subBlockLenght = src.read(1)[0]
            if subBlockLenght == 0:
                break
            subBlockData = src.read(subBlockLenght)
            subBlocksList.append(subBlockData)
        return subBlocksList    
    
    def ReadFrameData(self,src):
        gc.collect()
        frameData = bytearray()
        while True:
            subBlockLenght = src.read(1)[0]
            if subBlockLenght == 0:
                break
            subBlockData = src.read(subBlockLenght)
            frameData.extend(subBlockData)
        return frameData
    
    def ReadBlock(self,src):
        Block_Dict = {'SubBlocks':[]}
        BlockLenght = src.read(1)[0]
        Block_Dict['BlockData'] = src.read(BlockLenght)
        Block_Dict['SubBlocks'] = self.ReadSubBlocks(src)
        return Block_Dict
        
    def ReadGraphicsControlBlock(self,src):
        #print('GraphicsControlBlock')
        blockDict = self.ReadBlock(src)
        packField = blockDict['BlockData'][0]
        dispMethod = (packField&0b11100) >> 2
        # 0 - disposal method not specified
        # 1 - leave the image in place and draw the next image on top of it
        # 2 - the canvas should be restored to the background color
        # 3 - restore the canvas to its previous state before the current image was drawn
        TranspFlag = packField&1
        delay = int.from_bytes(blockDict['BlockData'][1:2],'big')*10
        AnimData = {'anim':[dispMethod,TranspFlag,delay]}
        self.Frames.append(AnimData)
        #disposalMethod = 2**((self.Field & 0b111)+1)
        
    def ReadApplicationBlock(self,src):
        #print('ApplicationBlock')
        blockdict = self.ReadBlock(src)
        if blockdict['BlockData'] == b'NETSCAPE2.0':
            self.loopcount = int.from_bytes(blockdict['SubBlocks'][0][1:], 'little')
    
    def ReadPlainTextBlock(self,src):
        #print('PlainTextBlock')
        self.ReadBlock(src)
        
    def ReadCommentBlock(self,src):
        #print('CommentBlock')
        self.ReadBlock(src)
    
    def ReadFrame(self,src):
        #print('Frame')
        #print('FreeMem:',gc.mem_free())
        frameMetaData = src.read(9)
        #print('frameMetaData: ',frameMetaData)
        imageLeft = int.from_bytes(frameMetaData[0:1], 'little') 
        imageTop = int.from_bytes(frameMetaData[2:3], 'little')
        frameWidth = int.from_bytes(frameMetaData[4:6], 'little') 
        frameHeight = int.from_bytes(frameMetaData[6:8], 'little')
        localTableFlag = frameMetaData[8] >> 7
        interlaceFlag = frameMetaData[8] >> 6
        BytesToData = src.tell()
        frameLZW_min = src.read(1)[0]
        # imgdata : [imlft,imtop,Width,Height,locc,intlc]
        FrameDict = {'img':[imageLeft,imageTop,frameWidth,frameHeight,localTableFlag,interlaceFlag],'BytesToData':BytesToData}
        
        #change to skip stead of reading
        while True:
            subBlockLenght = src.read(1)[0]
            if subBlockLenght == 0:
                break
            subBlockData = src.read(subBlockLenght)
            #print(len(subBlockData))
        self.Frames[-1].update(FrameDict)
        self.n_frames += 1
        #print('FrameDict: ',self.Frames[-1])
        #print('FreeMem:',gc.mem_free())
    
    def BlitFrameToScreen(self,FrameIndex,callback):
        startTime = time.time()
        frame_x = self.Frames[FrameIndex]['img'][0]
        frame_y = self.Frames[FrameIndex]['img'][1]
        frameSize = (self.Frames[FrameIndex]['img'][2],self.Frames[FrameIndex]['img'][3])
        startPos = (frame_x+self.x,frame_y+self.y)
        if len(self.decoded) > FrameIndex:
            FrameData = self.decoded[FrameIndex]
            self.blit(FrameData,callback,startPos,frameSize)
        else:
            src = open(self.path, "rb")
            src.seek(self.Frames[FrameIndex]['BytesToData'])
            frameLZW_min = src.read(1)[0]
            frameCompData = self.ReadFrameData(src)
            self.lzw_DecodeToScreen(frameCompData,callback,startPos,frameSize,frameLZW_min)
            src.close()
        #print('frameData Ready')
        #print('start',startPos)
        #print("imageBlited, Time: ",time.time()-startTime)
    
    def BlitAnimationToScreen(self,callback):
        self.BlitFrameToScreen(self.currentFrameIndex,callback)        
        if (time.ticks_ms()-self.AnimTime)//self.Frames[self.currentFrameIndex]['anim'][2] > 0:
            self.AnimTime = time.ticks_ms()
            self.currentFrameIndex += 1
            if self.currentFrameIndex > self.n_frames-1:
                self.currentFrameIndex = 0
                
    def getData(self,src):
        Supported_Extensions = {
        b'\xf9': self.ReadGraphicsControlBlock,        
        b'\xff': self.ReadApplicationBlock,
        b'\xfe': self.ReadCommentBlock,
        b'\x01': self.ReadPlainTextBlock,
        }
        while True:
            Block_ID = src.read(1)
            if Block_ID == b'!':
                Ext_Label = src.read(1)
                if Ext_Label in Supported_Extensions:
                    Supported_Extensions[Ext_Label](src)
                else:
                    print('Unknow Ext_Label:',Ext_Label)
                    break
            elif Block_ID == b',':
                imageDiscription = self.ReadFrame(src)
            elif Block_ID == b';':
                #print('GIF Decoded')
                src.close()
                break
            else:
                print('Unknow Block_ID:',Block_ID)
                break