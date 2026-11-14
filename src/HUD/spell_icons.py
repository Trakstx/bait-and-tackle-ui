"""Local spell icon sheets -> small PNGs using only the standard library."""
import struct
import zlib
from pathlib import Path

def tga_rgba(data):
    if len(data)<18:raise ValueError('Incomplete TGA')
    ident,cmap,kind,_,_,_,_,_,width,height,depth,descriptor=struct.unpack('<BBBHHBHHHHBB',data[:18])
    if cmap or kind not in (2,10) or depth not in (24,32) or not 0<width<=1024 or not 0<height<=1024:raise ValueError('Unsupported TGA')
    size=depth//8;offset=18+ident;count=width*height;raw=bytearray()
    if kind==2:raw.extend(data[offset:offset+count*size])
    else:
        while len(raw)<count*size:
            if offset>=len(data):raise ValueError('Incomplete RLE')
            packet=data[offset];offset+=1;n=(packet&127)+1
            if packet&128:
                pixel=data[offset:offset+size];offset+=size;raw.extend(pixel*n)
            else:
                raw.extend(data[offset:offset+n*size]);offset+=n*size
    if len(raw)!=count*size:raise ValueError('Incomplete TGA pixels')
    result=bytearray(count*4)
    for y in range(height):
        sy=y if descriptor&32 else height-1-y
        for x in range(width):
            sx=width-1-x if descriptor&16 else x
            i=(sy*width+sx)*size;j=(y*width+x)*4
            result[j:j+4]=bytes((raw[i+2],raw[i+1],raw[i],raw[i+3] if size==4 else 255))
    return width,height,result

def png_rgba(width,height,pixels):
    def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    rows=b''.join(b'\0'+bytes(pixels[y*width*4:(y+1)*width*4]) for y in range(height))
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(rows))+chunk(b'IEND',b'')

class SpellIcons:
    def __init__(self,game):self.game=Path(game);self.sheets={};self.icons={}
    def get(self,index):
        index=int(index)
        if not 0<=index<4096:raise ValueError('Invalid spell icon')
        if index in self.icons:return self.icons[index]
        sheet=index//36+1;cell=index%36
        if sheet not in self.sheets:
            path=self.game/'uifiles'/'default'/f'Spells{sheet:02}.tga'
            self.sheets[sheet]=tga_rgba(path.read_bytes())
        width,height,pixels=self.sheets[sheet];left=(cell%6)*40;top=(cell//6)*40
        if left+40>width or top+40>height:raise ValueError('Icon is outside sheet')
        crop=b''.join(pixels[((top+y)*width+left)*4:((top+y)*width+left+40)*4] for y in range(40))
        self.icons[index]=png_rgba(40,40,crop);return self.icons[index]
