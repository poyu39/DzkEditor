import binascii
import csv
import argparse
import os

import PIL.Image as Image


class DZK:
    def __init__(self, dzk_path, output_path, encoding='GBK', font_width=16, font_height=16):
        self.dzk_path = dzk_path
        self.output_path = output_path
        self.dzk_filename = dzk_path.split('/')[-1]
        self.encoding = encoding
        self.font_width = font_width
        self.font_height = font_height
        
        self.hex_data = None
        self.char_dict = {}
        
        self.load()
        self.parse()
    
    def load(self):
        with open(self.dzk_path, 'rb') as f:
            self.hex_data = binascii.hexlify(f.read()).decode('utf-8')
    
    def get_encode_char(self, offset, encoding):
        if encoding == 'GBK':
            '''
                GBK 編碼範圍
                0x8140 ~ 0xFEFE
                前兩位的範圍是81-FE
                後兩位的範圍是40-FF，除了 7F FF
            '''
            hex = (0x81 + offset // 191, 0x40 + offset % 191)
            try:
                char = bytes(hex).decode(self.encoding)
            except UnicodeDecodeError:
                if hex[1] == 0x7F or hex[1] == 0xFF:
                    return self.get_encode_char(offset + 1, encoding)
                else:
                    # print(f'Invalid encode: {hex[0]:02X}{hex[1]:02X}')
                    char = 'none'
            return offset, hex, char
    
    def parse(self):
        # 字元是由左到右，由上到下。
        # char_row_hex_len 是字元一行所佔用的 hex 長度。
        char_row_hex_len = self.font_width // 8 * 2
        char_total_hex_len = char_row_hex_len * self.font_height
        offset = 0
        for i in range(0, len(self.hex_data), char_total_hex_len):
            pixel_hexs = self.hex_data[i:i + char_total_hex_len]
            offset, char_hex, char = self.get_encode_char(offset, self.encoding)
            for i in range(0, len(pixel_hexs), char_row_hex_len):
                # 現在字元所有的 hex
                this_hex = pixel_hexs[i:i + char_row_hex_len]
                # 兩兩一組
                c_list = []
                for j in range(0, len(this_hex), 2):
                    c_list.append(this_hex[j:j + 2])
                # 一行的 pixel data
                pixel_row = ''.join([bin(int(c, 16))[2:].zfill(8) for c in c_list])
                if char_hex is not None:
                    if char_hex in self.char_dict:
                        self.char_dict[char_hex] += pixel_row
                    else:
                        self.char_dict[char_hex] = pixel_row
            offset += 1
    
    def set_new_char(self, hex, pixel_data):
        self.char_dict[hex] = pixel_data
    
    def is_none(self, hex):
        if hex in self.char_dict:
            if self.char_dict[hex] == '0' * self.font_width * self.font_height:
                return True
            else:
                return False
    
    def read_bmp(self, bmp_path, width=16, height=16):
        bmp = Image.open(bmp_path)
        pixel_data = ''
        for i in range(height):
            for j in range(width):
                pixel = bmp.getpixel((j, i))
                if pixel == 0:
                    pixel_data += '1'
                else:
                    pixel_data += '0'
        return pixel_data
    
    def display(self, hex):
        pixel_data = self.char_dict.get(hex)
        if pixel_data:
            for i in range(0, len(pixel_data), self.font_width):
                print(pixel_data[i:i + self.font_width])
        else:
            print('No such hex data.')
    
    def export_decode(self):
        with open(f'./{self.output_path}/{self.dzk_filename}_decode.txt', 'wb') as f:
            for char_hex, pixel_data in self.char_dict.items():
                f.write(f'{char_hex[0]:02X}{char_hex[1]:02X}\n'.encode('utf-8'))
                for i in range(0, len(pixel_data), self.font_width):
                    f.write(f'{pixel_data[i:i + self.font_width]}\n'.encode('utf-8'))
                f.write(b'\n')
    
    def export_dzk(self):
        with open(f'./{self.output_path}/{self.dzk_filename}_modify.DZK', 'wb') as f:
            for _, pixel_data in self.char_dict.items():
                # pixel_data 轉為 16 進位寫入 dzk
                # print(pixel_data)
                pixel_data_hex = hex(int(pixel_data, 2))[2:].zfill(self.font_width * self.font_height // 4)
                f.write(binascii.unhexlify(pixel_data_hex))

if __name__ == '__main__':
    argparser = argparse.ArgumentParser()
    argparser.add_argument('--dzk', type=str, default='../font/SongTi_12_1616_GBK.DZK')
    argparser.add_argument('--bmp_path', type=str, default='../bmp/')
    argparser.add_argument('--key_path', type=str, default='./key.csv')
    argparser.add_argument('--output_path', type=str, default='../output')
    argparser.add_argument('--encode', type=str, default='GBK')
    argparser.add_argument('--fw', type=int, default=16)
    argparser.add_argument('--fh', type=int, default=16)
    
    args = argparser.parse_args()
    
    dzk = DZK(args.dzk, args.output_path, args.encode, args.fw, args.fh)
    
    hex_keys = csv.DictReader(open(args.key_path))
    for hex_key in hex_keys:
        char_hex = (int(hex_key['hex'][:2], 16), int(hex_key['hex'][2:], 16))
        pixel_data = dzk.read_bmp(os.path.join(args.bmp_path, f"{hex_key['bmp']}.bmp"), args.fw, args.fh)
        is_overwrie = dzk.is_none(hex)
        dzk.set_new_char(char_hex, pixel_data)
        print(f"Add new char: {hex_key['hex']}, {hex_key['bmp']}.bmp, Overwrite: {is_overwrie}")
    
    dzk.export_decode()
    dzk.export_dzk()