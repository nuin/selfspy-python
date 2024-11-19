"""
Password checking functionality for Selfspy
"""

import os
from typing import Optional
from Crypto.Cipher import Blowfish

DIGEST_NAME = 'password.digest'
MAGIC_STRING = (
    b'\xc5\x7fdh\x05\xf6\xc5=\xcfh\xafv\xc0\xf4\x13i*.O\xf6\xc2\x8d\x0f\x87\xdb'
    b'\x9f\xc2\x88\xac\x95\xf8\xf0\xf4\x96\xe9\x82\xd1\xca[\xe5\xa32\xa0\x03\n'
    b'D\x12\n\x1dr\xbc\x03\x9bE\xd3q6\x89Cwi\x10\x92\xdf(#\x8c\x87\x1b3\xd6\xd4'
    b'\x8f\xde)\xbe\x17\xbf\xe4\xae\xb73\\\xcb\x7f\xd3\xc4\x89\xd0\x88\x07\x90'
    b'\xd8N,\xbd\xbd\x93j\xc7\xa3\xec\xf3P\xff\x11\xde\xc9\xd6 \x98\xe8\xbc\xa0'
    b'|\x83\xe90Nw\xe4=\xb53\x08\xf0\x14\xaa\xf9\x819,X~\x8e\xf7mB\x13\xe9;\xde'
    b'\x9e\x10\xba\x19\x95\xd4p\xa7\xd2\xa9o\xbdF\xcd\x83\xec\xc5R\x17":K\xceAiX'
    b'\xc1\xe8\xbe\xb8\x04m\xbefA8\x99\xee\x00\x93\xb4\x00\xb3\xd4\x8f\x00@Q\xe9'
    b'\xd5\xdd\xff\x8d\x93\xe3w6\x8ctRQK\xa9\x97a\xc1UE\xdfv\xda\x15\xf5\xccA)\xec'
    b'^]AW\x17/h)\x12\x89\x15\x0e#8"\x7f\x16\xd6e\x91\xa6\xd8\xea \xb9\xdb\x93W'
    b'\xce9\xf2a\xe7\xa7T=q'
)

def check(data_dir: str, cipher: Optional[Blowfish.BlowfishCipher], read_only: bool = False) -> bool:
    """Check if the password is correct"""
    fname = os.path.join(data_dir, DIGEST_NAME)
    
    if os.path.exists(fname):
        if cipher is None:
            return False
            
        with open(fname, 'rb') as f:
            stored = f.read()
        return cipher.decrypt(stored) == MAGIC_STRING
        
    else:
        if cipher is not None and not read_only:
            encrypted = cipher.encrypt(MAGIC_STRING)
            with open(fname, 'wb') as f:
                f.write(encrypted)
        return True

def create_cipher(password: str) -> Optional[Blowfish.BlowfishCipher]:
    """Create a Blowfish cipher from password"""
    if not password:
        return None
        
    return Blowfish.new(
        hashlib.md5(password.encode()).digest(),
        Blowfish.MODE_ECB
    )