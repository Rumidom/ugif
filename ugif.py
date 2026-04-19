import struct
import gc
import os
import time
import micropython
from array import array

@micropython.viper
def ByteArrayReverse(Barr:ptr8,BarrOut:ptr8,l:int):
    for x in range(l):
        BarrOut[x] = Barr[l-1-x]

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
        src.close()
        
    def setPosition(self,x,y):
        self.x = x
        self.y = y
        
    def getColorTable565(self):
        for color in self.ColorTable:
            self.ColorTable565.append(color565(color[0],color[1],color[2]))
    
    @micropython.native
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
    

    @micropython.native
    def get_CodeValue(self,Code,codeTable,byteTable,ColorTableLen):
        if Code < ColorTableLen:
            return Code.to_bytes(1)
        else:
            nextCode = Code
            Barr = bytearray()
            while nextCode > ColorTableLen:
                index = nextCode-(ColorTableLen+2)
                nextCode = codeTable[index]
                Barr.append(byteTable[index])
            Barr.append(nextCode)
            Barr_len = len(Barr)
            BarrOut = bytearray(Barr_len)
            ByteArrayReverse(Barr,BarrOut,Barr_len)
            return BarrOut
    
    @micropython.native
    def lzw_DecompressToScreen(self,src,callback,startPos,frameSize,LZW_Min_Code,useColor565=True,useram=False,monocrome=False):
        ## LZW algorithm
        ColorTableLen = 2**LZW_Min_Code
        ClearCode = ColorTableLen
        ImgEndCode = ColorTableLen + 1
        CodeLen = LZW_Min_Code+1
        lastCode = 0
        K = 0
        Code = None
        Codekey = None
        indexStream = bytearray()
        datablock = bytearray(256)
        datablockIndex = 0
        codeTable = array('i',[])
        byteTable = bytearray()
        byte = 0
        BitIndex = 0
        newTableIndex = ImgEndCode + 1
        ByteCount = 0
        FirstCodeFlag = False
        newentry = None
        
        ## Output to ram
        outbit_index = 0
        outbyte = 0b00000000
        
        ## Output to Screen
        imageDataLen = 0
        scr_x = startPos[0]
        scr_y = startPos[1]
        
        while True:       
            CodeKey = 0
            for i in range(CodeLen):   
                if ByteCount == 0:
                    ByteCount = src.read(1)[0]
                    datablock = src.read(ByteCount)
                    datablockIndex = 0
                                
                if BitIndex == 0:
                    byte = datablock[datablockIndex]
                    datablockIndex += 1
                    ByteCount -= 1
                
                if (byte >> BitIndex) & 1:
                    CodeKey = CodeKey | 1<<i
                BitIndex += 1
                if BitIndex == 8:
                    BitIndex = 0

            if CodeKey == ClearCode:
                codeTable = array('i',[])
                byteTable = bytearray()
                newTableIndex = ImgEndCode+1
                FirstCodeFlag = False
                CodeLen = LZW_Min_Code+1         
            elif CodeKey == ImgEndCode:
                break
            else:
                if not FirstCodeFlag:
                    newEntry = self.get_CodeValue(CodeKey,codeTable,byteTable,ColorTableLen)
                    FirstCodeFlag = True
                else:
                    if (CodeKey < newTableIndex):
                        codearr = self.get_CodeValue(CodeKey,codeTable,byteTable,ColorTableLen)
                        newEntry = codearr
                        K = codearr[0]
                    else:
                        lastcodearr = self.get_CodeValue(lastCode,codeTable,byteTable,ColorTableLen)
                        K = lastcodearr[0]
                        newEntry = lastcodearr + bytearray([K])                    
                    try:
                        codeTable.append(lastCode)
                        byteTable.append(K)
                    except Exception as e:
                        print(micropython.mem_info())
                        raise(e)
                        
                    if newTableIndex >= 2**CodeLen-1:
                        if CodeLen < 12:
                            CodeLen += 1
                        
                    newTableIndex += 1
                lastCode = CodeKey
                for i,Entrybyte in enumerate(newEntry):
                    count = i+imageDataLen
                    scr_x = count%frameSize[0] + startPos[0]
                    if scr_x == startPos[0] and count != 0:
                         scr_y+= 1
                    if monocrome:
                        callback(scr_x,scr_y,Entrybyte)
                        if useram:
                            outbyte =  outbyte | (Entrybyte << outbit_index)
                            outbit_index += 1
                            if outbit_index > 7:
                                outbit_index = 0 
                                indexStream.append(outbyte)
                                outbyte = 0b00000000
                    else:
                        if useColor565:
                            callback(scr_x,scr_y,self.ColorTable565[Entrybyte])
                        else:
                            callback(scr_x,scr_y,self.ColorTable[Entrybyte])
                    gc.collect()
                imageDataLen += len(newEntry)
                if useram and not monocrome:
                    indexStream += newentry
            gc.collect()
        if (len(indexStream)>0):
            self.decoded.append(indexStream)
            
    @micropython.native
    def getColorTable(self,src,ColorTableLen):
        for i in range(ColorTableLen):
            self.ColorTable.append((src.read(1)[0],src.read(1)[0],src.read(1)[0]))
    
    @micropython.native
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
    @micropython.native
    def ReadSubBlocks(self,src):
        subBlocksList = []
        while True:
            subBlockLenght = src.read(1)[0]
            if subBlockLenght == 0:
                break
            subBlockData = src.read(subBlockLenght)
            subBlocksList.append(subBlockData)
        return subBlocksList    
    @micropython.native
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
    @micropython.native
    def ReadBlock(self,src):
        Block_Dict = {'SubBlocks':[]}
        BlockLenght = src.read(1)[0]
        Block_Dict['BlockData'] = src.read(BlockLenght)
        Block_Dict['SubBlocks'] = self.ReadSubBlocks(src)
        return Block_Dict
    @micropython.native
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
    @micropython.native
    def ReadApplicationBlock(self,src):
        #print('ApplicationBlock')
        blockdict = self.ReadBlock(src)
        if blockdict['BlockData'] == b'NETSCAPE2.0':
            self.loopcount = int.from_bytes(blockdict['SubBlocks'][0][1:], 'little')
    @micropython.native
    def ReadPlainTextBlock(self,src):
        #print('PlainTextBlock')
        self.ReadBlock(src)
    @micropython.native        
    def ReadCommentBlock(self,src):
        #print('CommentBlock')
        self.ReadBlock(src)
    @micropython.native
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
        
    @micropython.native
    def BlitFrameToScreen(self,FrameIndex,callback,testFlag = False):
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
            #frameCompData = self.ReadFrameData(src)
            #self.lzw_DecodeToScreen(frameCompData,callback,startPos,frameSize,frameLZW_min,monocrome=self.monocrome,useram=self.monocrome)
            if testFlag:
                self.lzw_DecompressToScreen(src,callback,startPos,frameSize,frameLZW_min,monocrome=self.monocrome,useram=self.monocrome)
            else:
                frameCompData = self.ReadFrameData(src)
                self.lzw_DecodeToScreen(frameCompData,callback,startPos,frameSize,frameLZW_min,monocrome=self.monocrome,useram=self.monocrome)
            src.close()
        #print('frameData Ready')
        #print('start',startPos)
        #print("imageBlited, Time: ",time.time()-startTime)
    @micropython.native
    def BlitAnimationToScreen(self,callback):
        self.BlitFrameToScreen(self.currentFrameIndex,callback)        
        if (time.ticks_ms()-self.AnimTime)//self.Frames[self.currentFrameIndex]['anim'][2] > 0:
            self.AnimTime = time.ticks_ms()
            self.currentFrameIndex += 1
            if self.currentFrameIndex > self.n_frames-1:
                self.currentFrameIndex = 0
                
    @micropython.native
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