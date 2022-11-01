from collections import OrderedDict

import binascii
import hashlib
import json
import random

from time import time
from uuid import uuid4

import copy

import Crypto
import Crypto.Random
from Crypto.Hash import SHA
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5


BLOCKCHAIN_ID = "ZA_BLOCKCHAIN"
MINING_REWARD = 1
MINING_DIFFICULTY = 2


class Blockchain:

    def __init__(self):

        self.transactions = []
        self.chain = []
        self.nodes = set()
        #Generate random number to be used as node_id
        self.node_id = str(uuid4()).replace('-', '')
        #Create genesis block
        self.create_init_block()

    def register_node(self, node_url):
        parsed_url = urlparse(node_url)
        if parsed_url.netloc:
            self.nodes.add(parsed_url.netloc)
        elif parsed_url.path:
            self.nodes.add(parsed_url.path)
        else:
            raise ValueError('Invalid URL')

    def verify_transaction_signature(self, sender_address, recipient_address, value, signature):

        public_key = RSA.importKey(binascii.unhexlify(sender_address))
        verifier = PKCS1_v1_5.new(public_key)
        h = SHA.new(str({'sender_address': sender_address,
                        'recipient_address': recipient_address,
                        'value': value}).encode('utf8'))

        return verifier.verify(h, binascii.unhexlify(signature))

    def submit_transaction(self, sender_address, recipient_address, value, signature):

        transaction = OrderedDict({'sender_address': sender_address,
                                   'recipient_address': recipient_address,
                                   'value': value})

        if sender_address == BLOCKCHAIN_ID:
            self.transactions.append(transaction)   #Reward for mining a block
        else:
            transaction_verification = self.verify_transaction_signature(sender_address, recipient_address, value, signature)
            if transaction_verification:
                self.transactions.append(transaction)
            else:
                return False

        return len(self.chain) + 1

    def create_init_block(self):

        init_transaction = OrderedDict({'sender_address': BLOCKCHAIN_ID,
                                   'recipient_address': BLOCKCHAIN_ID,
                                   'value': 9999})

        init_block = {'block_number': len(self.chain),
                 'timestamp': time(),
                 'transactions': [init_transaction],
                 'nonce': random.randint(1, 256),
                 'previous_hash': None}

        self.chain.append(init_block)

    def create_block(self, nonce, previous_hash):

        block = {'block_number': len(self.chain),
                'timestamp': time(),
                'transactions': copy.copy(self.transactions),
                'nonce': nonce,
                'previous_hash': previous_hash}

        # Reset the current list of transactions
        self.transactions = []

        self.chain.append(block)
        return block

    def hash(self, block):

        block_string = json.dumps(block, sort_keys=True).encode()

        return hashlib.sha256(block_string).hexdigest()

    def proof_of_work(self):

        last_block = self.chain[-1]
        last_hash = self.hash(last_block)

        nonce = 0
        while self.valid_proof(self.transactions, last_hash, nonce) is False:
            nonce += 1

        return nonce

    def valid_proof(self, transactions, last_hash, nonce, difficulty=2):

        guess = (str(transactions)+str(last_hash)+str(nonce)).encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:difficulty] == '0'*difficulty

    def valid_chain(self, chain):

        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            #print(last_block)
            #print(block)
            #print("\n-----------\n")
            # Check that the hash of the block is correct
            if block['previous_hash'] != self.hash(last_block):
                return False

            # Check that the Proof of Work is correct
            transactions = block['transactions'][:-1]
            transaction_elements = ['sender_address', 'recipient_address', 'value']
            transactions = [OrderedDict((k, transaction[k]) for k in transaction_elements) for transaction in transactions]

            if not self.valid_proof(transactions, block['previous_hash'], block['nonce'], MINING_DIFFICULTY):
                return False

            last_block = block
            current_index += 1

        return True

    def update_chain(self, new_chain):

        for block in self.chain[1:]:
            hash = self.hash(block)
            current_index = 1
            found = False
            while current_index < len(new_chain):
                current_block = new_chain[current_index]
                if current_block['previous_hash'] == hash:
                    found = True
                current_index += 1
            last_block = new_chain[-1]
            if self.hash(last_block) == hash:
                    found = True

            if not found:
                transactions = block['transactions']
                for transaction in transactions:
                    self.transactions.append(transaction)

        self.chain = new_chain
