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
    def __init__(self,path):
        src = open(path, "rb")
        Header = self.getHeader(src)
        self.path = path
        dummybuffer = bytearray(os.stat(path)[6])
        self.ID_tag = Header[0]
        self.Version = Header[1]
        self.Width = Header[2]
        self.Height = Header[3]
        self.Field = Header[4][0]
        self.Background_ci = Header[5][0]
        self.Pixel_AR = Header[6][0]
        ColorTableLen = 0
        self.ColorTable = []
        self.ColorTable565 = []
        if (self.Field >> 7) & 1:
            ColorTableLen = 2**((self.Field & 0b111)+1)
            self.getColorTable(src,ColorTableLen)
            self.getColorTable565()
        print(path)
        print("Colors: ",ColorTableLen)
        print("Size: ",self.Width,",",self.Height)
        self.Frames = []
        self.loopcount = 0
        self.FrameTimes = []
        self.getData(src)
        print("loopcount: ",self.loopcount)
        print("frameTimes: ",self.FrameTimes)
        
    def getColorTable565(self):
        for color in self.ColorTable:
            self.ColorTable565.append(color565(color[0],color[1],color[2]))
            
    def lzw_DecodeToScreen(self,data,callback, palBits,useColor565=True):
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

        # LZW dictionary: index = code, value = entry (reference to another code,
        # final byte)
        lzwDict = [(None, i) for i in range(2 ** palBits + 2)]
        imageDataLen = 0
        scr_x = 0
        scr_y = 0
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
                    scr_x = count%self.Width
                    if scr_x == 0 and count != 0:
                         scr_y+= 1
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
            gc.collect()
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
        delay = blockDict['BlockData'][1]*10
        delay = delay+ blockDict['BlockData'][2]
        self.FrameTimes.append(delay)
        
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
        frameWidth = int.from_bytes(frameMetaData[4:6], 'little') 
        frameHeight = int.from_bytes(frameMetaData[6:8], 'little') 
        localTableFlag = frameMetaData[8] >> 7
        interlaceFlag = frameMetaData[8] >> 6
        BytesToData = src.tell()
        frameLZW_min = src.read(1)[0]
        FrameDict = {'Meta':{'locc':localTableFlag,'intlc':interlaceFlag},'BytesToData':BytesToData}
        if frameWidth != self.Width:
            FrameDict['Meta']['w'] = frameWidth
        if frameHeight != self.Height:   
            FrameDict['Meta']['h'] = frameHeight
        print('FrameDict: ',FrameDict)
        while True:
            subBlockLenght = src.read(1)[0]
            if subBlockLenght == 0:
                break
            subBlockData = src.read(subBlockLenght)
            #print(len(subBlockData))
        self.Frames.append(FrameDict)
        #print('FreeMem:',gc.mem_free())
    
    def BlitToScreen(self,FrameIndex,callback):
        startTime = time.time()
        src = open(self.path, "rb")
        src.seek(self.Frames[FrameIndex]['BytesToData'])
        frameLZW_min = src.read(1)[0]
        frameData = self.ReadFrameData(src)
        src.close()
        #print('frameData Ready')
        self.lzw_DecodeToScreen(frameData,callback,frameLZW_min)
        print("imageBlited, Time: ",time.time()-startTime)
        
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