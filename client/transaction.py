from collections import OrderedDict

import binascii

import Crypto
import Crypto.Random
from Crypto.Hash import SHA
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5

class Transaction:

    def __init__(self, sender_address, sender_private_key, recipient_address, value):
        self.sender_address = sender_address
        self.sender_private_key = sender_private_key
        self.recipient_address = recipient_address
        self.value = value
        
        #sign transaction with private key
        private_key = RSA.importKey(binascii.unhexlify(self.sender_private_key))
        signer = PKCS1_v1_5.new(private_key)
        h = SHA.new(str({'sender_address': sender_address, 
                        'recipient_address': recipient_address, 
                        'value': value}).encode('utf8'))
        self.signature = binascii.hexlify(signer.sign(h)).decode('ascii')

    def get_signature(self):
        return self.signature

    def to_dict(self):
        return {'sender_address': self.sender_address,
                'recipient_address': self.recipient_address,
                'value': self.value,
                'signature': self.signature}