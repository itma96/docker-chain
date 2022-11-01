from collections import OrderedDict
import binascii

import Crypto
import Crypto.Random
from Crypto.Hash import SHA
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5

#import hashlib
import re
import json
from time import sleep
#from urllib.parse import urlparse
#from uuid import uuid4

from threading import Thread

import socket
import requests
from flask import Flask, jsonify, request, render_template, g
from flask_cors import CORS
from redis import Redis

from blockchain import Blockchain

BLOCKCHAIN_ID = "ZA_BLOCKCHAIN"
WORKER_ID = "WORKER_" + socket.gethostname()
MINING_REWARD = 1
MINING_DIFFICULTY = 2


# Instantiate the Node
app = Flask(__name__)
CORS(app)

# Instantiate the Blockchain
blockchain = Blockchain()

neighbours = set()

def get_redis():
    g.redis = Redis(host="redis", db=0)
    return g.redis

@app.route('/worker/home')
def index():
    return render_template('./index.html', hostname=socket.gethostname())

@app.route('/worker/configure')
def configure():
    return render_template('./configure.html', hostname=socket.gethostname())

@app.route('/worker/transactions/get', methods=['GET'])
def get_transactions():

    #Get transactions from transactions pool
    transactions = blockchain.transactions

    response = {'transactions': transactions}
    return jsonify(response), 200

@app.route('/worker/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200

@app.route('/worker/mine', methods=['GET'])
def mine():
    # Run the proof of work algorithm to get nonce
    last_block = blockchain.chain[-1]
    nonce = blockchain.proof_of_work()

    # We must receive a reward for finding the nonce
    #blockchain.submit_transaction(sender_address=MINING_SENDER, recipient_address=WORKER_ID, value=MINING_REWARD, signature="")

    # Forge the new Block by adding it to the chain
    previous_hash = blockchain.hash(last_block)
    block = blockchain.create_block(nonce, previous_hash)

    response = {
        'message': "New Block Forged",
        'block_number': block['block_number'],
        'transactions': block['transactions'],
        'nonce': block['nonce'],
        'previous_hash': block['previous_hash'],
    }

    return jsonify(response), 200

@app.route('/worker/nodes/get', methods=['GET'])
def get_nodes():
    nodes = list(neighbours)
    response = {'nodes': nodes}
    return jsonify(response), 200

@app.route('/worker/nodes/register', methods=['POST'])
def register_nodes():
    values = request.form
    nodes = values.get('nodes').replace(" ", "").split(',')

    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    pattern = re.compile(r"\w{12}")

    for node in nodes:
        result = pattern.match(node)
        if result:
            neighbours.add(node)
        else:
            raise ValueError('Invalid ID')

    response = {
        'message': 'New nodes have been added',
        'total_nodes': [node for node in neighbours],
    }
    return jsonify(response), 201

@app.route('/worker/nodes/resolve', methods=['GET'])
def consensus():
    #replaced = blockchain.resolve_conflicts()

    new_chain = None
    replaced = False

    max_length = len(blockchain.chain)

    redis = Redis(host="redis", db=0)
    p = redis.pubsub()
    redis.publish('SYNCH_REQ', json.dumps({'sender_id': socket.gethostname()}))

    p.subscribe(['SYNCH_REPL'])
    r = len(neighbours)
    while r > 0:
        msg = p.get_message()
        if msg != None and msg["type"] == 'message':
            if msg["channel"] == 'SYNCH_REPL':
                data = json.loads(msg["data"])
                worker_id = data["id"]
                print 'Received SYNCH_REPL from ' + str(worker_id)
                worker_chain = data["chain"]
                if len(worker_chain) > max_length:
                    max_length = len(worker_chain)
                    new_chain = worker_chain
                if new_chain:
                    replaced = True

                r -= 1

    if replaced:
        redis.publish('CHAIN_UPDATED', json.dumps({'sender_id': socket.gethostname(), 'new_chain': new_chain}))
        response = {
            'message': 'Our chain was replaced',
            'new_chain': new_chain
        }
    else:
        redis.publish('CHAIN_UPDATED', json.dumps({'sender_id': socket.gethostname(), 'new_chain': blockchain.chain}))
        response = {
            'message': 'Our chain is authoritative',
            'new_chain': blockchain.chain
        }

    return jsonify(response), 200

def listen_for_transactions():
    redis = Redis(host="redis", db=0)
    while True:
        data = redis.blpop(['transaction'], timeout=0)
        transaction = json.loads(data[1])
        sender_address = transaction["sender_address"]
        recipient_address = transaction["recipient_address"]
        value = transaction["value"]
        signature = transaction["signature"]
        # Submit a new Transaction
        transaction_result = blockchain.submit_transaction(sender_address, recipient_address, value, signature)
        if transaction_result == False:
            print 'Invalid Transaction!'
        else:
            print 'Transaction will be added to Block '+ str(transaction_result)
        sleep(5)

def listen_for_synch_req():
    redis = Redis(host="redis", db=0)
    p = redis.pubsub()
    p.subscribe(['SYNCH_REQ'])
    while True:
        msg = p.get_message()
        if msg and msg["type"] == 'message':
            if msg["channel"] == 'SYNCH_REQ':
                data = json.loads(msg["data"])
                sender_id = data["sender_id"]
                if sender_id != socket.gethostname():
                    print 'Received SYNCH_REQ from ' + str(sender_id)
                    redis.publish('SYNCH_REPL', json.dumps({'id': socket.gethostname(), 'chain': blockchain.chain}))
        sleep(5)

def listen_for_chain_updated():
    redis = Redis(host="redis", db=0)
    p = redis.pubsub()
    p.subscribe(['CHAIN_UPDATED'])
    while True:
        msg = p.get_message()
        if msg != None and msg["type"] == 'message':
            if msg["channel"] == 'CHAIN_UPDATED':
                data = json.loads(msg["data"])
                sender_id = data["sender_id"]
                print 'Received CHAIN_UPDATED from ' + str(sender_id)
                new_chain = data["new_chain"]
                blockchain.update_chain(new_chain)
        sleep(5)

if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=8080, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    #Wait for redis to start up first
    sleep(10)

    #Start listen_for_transactions thread
    t = Thread(target=listen_for_transactions)
    t.setDaemon(True)
    t.start()

    #Start listen_for_synch_req thread
    t = Thread(target=listen_for_synch_req)
    t.setDaemon(True)
    t.start()

    #Start listen_for_chain_updated thread
    t = Thread(target=listen_for_chain_updated)
    t.setDaemon(True)
    t.start()

    app.run(host='0.0.0.0', port=port)
