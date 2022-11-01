import binascii

import json

import Crypto
import Crypto.Random
from Crypto.Hash import SHA
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5

import socket
import requests
from flask import Flask, jsonify, request, render_template, g
from redis import Redis

from transaction import Transaction


app = Flask(__name__)

def get_redis():
    if not hasattr(g, 'redis'):
        g.redis = Redis(host="redis", db=0)
	return g.redis

@app.route('/client/home')
def index():
	return render_template('./index.html', hostname=socket.gethostname())

@app.route('/client/wallet', methods=['GET'])
def wallet():
    return render_template('./wallet.html', hostname=socket.gethostname())

@app.route('/client/wallet', methods=['POST'])
def generate_wallet():
	random_gen = Crypto.Random.new().read
	private_key = RSA.generate(1024, random_gen)
	public_key = private_key.publickey()
	response = {
		'private_key': binascii.hexlify(private_key.exportKey(format='DER')).decode('ascii'),
		'public_key': binascii.hexlify(public_key.exportKey(format='DER')).decode('ascii')
	}

	return jsonify(response), 200

@app.route('/client/transaction', methods=['GET'])
def transaction():
    return render_template('./transaction.html', hostname=socket.gethostname())

@app.route('/client/transaction', methods=['POST'])
def generate_transaction():

	sender_address = request.form['sender_address']
	sender_private_key = request.form['sender_private_key']
	recipient_address = request.form['recipient_address']
	value = request.form['amount']

	transaction = Transaction(sender_address, sender_private_key, recipient_address, value)

	redis = get_redis()
	redis.rpush('transaction', json.dumps(transaction.to_dict()))

	response = {'signature': transaction.get_signature()}

	return jsonify(response), 200


if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=8080, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    app.run(host='0.0.0.0', port=port)
