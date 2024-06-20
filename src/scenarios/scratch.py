#!/usr/bin/env python3
# Copyright (c) 2023 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
#
# Original: https://github.com/ariard/bitcoin/blob/30f5d5b270e4ff195e8dcb9ef6b7ddcc5f6a1bf2/test/functional/mempool_replacement_cycling.py#L5    # noqa


"""Test replacement cycling attacks against Lightning channels"""

import asyncio
from datetime import timedelta
from nostr_sdk import (Keys, Client,  EventBuilder, Filter, Metadata,
                       init_logger, LogLevel)
import time

from test_framework.key import (
    ECKey
)

from test_framework.messages import (
    CTransaction,
    CTxIn,
    CTxInWitness,
    CTxOut,
    COutPoint,
    sha256,
    COIN,
)

from test_framework.util import (
    assert_equal
)

from test_framework.script import (
    CScript,
    hash160,
    OP_HASH160,
    OP_EQUAL,
    OP_ELSE,
    OP_ENDIF,
    OP_CHECKSIG,
    OP_SWAP,
    OP_SIZE,
    OP_NOTIF,
    OP_DROP,
    OP_CHECKMULTISIG,
    OP_EQUALVERIFY,
    OP_0,
    OP_2,
    OP_TRUE,
    SegwitV0SignatureHash,
    SIGHASH_ALL,
)

from warnet.test_framework_bridge import WarnetTestFramework

from test_framework.wallet import MiniWallet


def cli_help():
    return "Run a replacement cycling attack - based on ariard's work"


def get_funding_redeemscript(funder_pubkey, fundee_pubkey):
    return CScript(
        [OP_2, funder_pubkey.get_bytes(), fundee_pubkey.get_bytes(), OP_2, OP_CHECKMULTISIG])


def get_anchor_single_key_redeemscript(pubkey):
    return CScript([pubkey.get_bytes(), OP_CHECKSIG])


def generate_funding_chan(wallet, coin, funder_pubkey, fundee_pubkey) -> CTransaction:
    witness_script = get_funding_redeemscript(funder_pubkey, fundee_pubkey)
    witness_program = sha256(witness_script)
    script_pubkey = CScript([OP_0, witness_program])

    funding_tx = CTransaction()
    funding_tx.vin.append(CTxIn(COutPoint(int(coin['txid'], 16), coin['vout']), b""))
    funding_tx.vout.append(CTxOut(int(49.99998 * COIN), script_pubkey))
    funding_tx.rehash()

    wallet.sign_tx(funding_tx)
    return funding_tx


def generate_parent_child_tx(wallet, coin, sat_per_vbyte):
    # We build a junk parent transaction for the second-stage HTLC-preimage
    junk_parent_fee = 158 * sat_per_vbyte

    junk_script = CScript([OP_TRUE])
    junk_scriptpubkey = CScript([OP_0, sha256(junk_script)])

    junk_parent = CTransaction()
    junk_parent.vin.append(CTxIn(COutPoint(int(coin['txid'], 16), coin['vout']), b""))
    junk_parent.vout.append(CTxOut(int(49.99998 * COIN - junk_parent_fee), junk_scriptpubkey))

    wallet.sign_tx(junk_parent)
    junk_parent.rehash()

    child_tx_fee = 158 * sat_per_vbyte

    child_tx = CTransaction()
    child_tx.vin.append(CTxIn(COutPoint(int(junk_parent.hash, 16), 0), b"", 0))
    child_tx.vout.append(
        CTxOut(int(49.99998 * COIN - (junk_parent_fee + child_tx_fee)), junk_scriptpubkey))

    child_tx.wit.vtxinwit.append(CTxInWitness())
    child_tx.wit.vtxinwit[0].scriptWitness.stack = [junk_script]
    child_tx.rehash()

    return junk_parent, child_tx


def generate_preimage_tx(input_amount, sat_per_vbyte, funder_seckey, fundee_seckey, hashlock,
                         commitment_tx, preimage_parent_tx):
    commitment_fee = 158 * 2  # Old sat per vbyte

    witness_script = CScript([fundee_seckey.get_pubkey().get_bytes(), OP_SWAP, OP_SIZE, 32,
                              OP_EQUAL, OP_NOTIF, OP_DROP, 2, OP_SWAP,
                              funder_seckey.get_pubkey().get_bytes(), 2, OP_CHECKMULTISIG, OP_ELSE,
                              OP_HASH160, hashlock, OP_EQUALVERIFY, OP_CHECKSIG, OP_ENDIF])

    spend_script = CScript([OP_TRUE])
    spend_scriptpubkey = CScript([OP_0, sha256(spend_script)])

    preimage_fee = 148 * sat_per_vbyte
    receiver_preimage = CTransaction()
    receiver_preimage.vin.append(CTxIn(COutPoint(int(commitment_tx.hash, 16), 0), b"", 0))
    receiver_preimage.vin.append(CTxIn(COutPoint(int(preimage_parent_tx.hash, 16), 0), b"", 0))
    receiver_preimage.vout.append(
        CTxOut(int(2 * input_amount - (commitment_fee + preimage_fee * 3)), spend_scriptpubkey))

    sig_hash = SegwitV0SignatureHash(witness_script, receiver_preimage, 0, SIGHASH_ALL,
                                     commitment_tx.vout[0].nValue)
    fundee_sig = fundee_seckey.sign_ecdsa(sig_hash) + b'\x01'

    # Spend the commitment transaction HTLC output
    receiver_preimage.wit.vtxinwit.append(CTxInWitness())
    receiver_preimage.wit.vtxinwit[0].scriptWitness.stack = [fundee_sig, b'a' * 32, witness_script]

    # Spend the parent transaction OP_TRUE output
    junk_script = CScript([OP_TRUE])
    receiver_preimage.wit.vtxinwit.append(CTxInWitness())
    receiver_preimage.wit.vtxinwit[1].scriptWitness.stack = [junk_script]
    receiver_preimage.rehash()

    return receiver_preimage


def create_chan_state(funding_txid, funding_vout, funder_seckey, fundee_seckey, input_amount,
                      input_script, sat_per_vbyte, timelock, hashlock, nsequence,
                      preimage_parent_tx):
    witness_script = CScript([fundee_seckey.get_pubkey().get_bytes(), OP_SWAP, OP_SIZE, 32,
                              OP_EQUAL, OP_NOTIF, OP_DROP, 2, OP_SWAP,
                              funder_seckey.get_pubkey().get_bytes(), 2, OP_CHECKMULTISIG, OP_ELSE,
                              OP_HASH160, hashlock, OP_EQUALVERIFY, OP_CHECKSIG, OP_ENDIF])
    witness_program = sha256(witness_script)
    script_pubkey = CScript([OP_0, witness_program])

    # Expected size = 158 vbyte
    commitment_fee = 158 * sat_per_vbyte
    commitment_tx = CTransaction()
    commitment_tx.vin.append(CTxIn(COutPoint(int(funding_txid, 16), funding_vout), b"", 0x1))
    commitment_tx.vout.append(CTxOut(int(input_amount - 158 * sat_per_vbyte), script_pubkey))

    sig_hash = SegwitV0SignatureHash(input_script, commitment_tx, 0, SIGHASH_ALL, int(input_amount))
    funder_sig = funder_seckey.sign_ecdsa(sig_hash) + b'\x01'
    fundee_sig = fundee_seckey.sign_ecdsa(sig_hash) + b'\x01'

    commitment_tx.wit.vtxinwit.append(CTxInWitness())
    commitment_tx.wit.vtxinwit[0].scriptWitness.stack = [b'', funder_sig, fundee_sig, input_script]
    commitment_tx.rehash()

    spend_script = CScript([OP_TRUE])
    spend_scriptpubkey = CScript([OP_0, sha256(spend_script)])

    timeout_fee = 158 * sat_per_vbyte
    offerer_timeout = CTransaction()
    offerer_timeout.vin.append(CTxIn(COutPoint(int(commitment_tx.hash, 16), 0), b"", nsequence))
    offerer_timeout.vout.append(CTxOut(int(input_amount - (commitment_fee + timeout_fee)),
                                       spend_scriptpubkey))
    offerer_timeout.nLockTime = timelock

    sig_hash = SegwitV0SignatureHash(witness_script, offerer_timeout, 0, SIGHASH_ALL,
                                     commitment_tx.vout[0].nValue)
    funder_sig = funder_seckey.sign_ecdsa(sig_hash) + b'\x01'
    fundee_sig = fundee_seckey.sign_ecdsa(sig_hash) + b'\x01'

    offerer_timeout.wit.vtxinwit.append(CTxInWitness())
    offerer_timeout.wit.vtxinwit[0].scriptWitness.stack = [b'', fundee_sig, funder_sig, b'',
                                                           witness_script]
    offerer_timeout.rehash()

    preimage_fee = 148 * sat_per_vbyte
    receiver_preimage = CTransaction()
    receiver_preimage.vin.append(CTxIn(COutPoint(int(commitment_tx.hash, 16), 0), b"", 0))
    receiver_preimage.vin.append(CTxIn(COutPoint(int(preimage_parent_tx.hash, 16), 0), b"", 0))
    receiver_preimage.vout.append(
        CTxOut(int(2 * input_amount - (commitment_fee + preimage_fee * 3)), spend_scriptpubkey))

    sig_hash = SegwitV0SignatureHash(witness_script, receiver_preimage, 0, SIGHASH_ALL,
                                     commitment_tx.vout[0].nValue)
    fundee_sig = fundee_seckey.sign_ecdsa(sig_hash) + b'\x01'

    # Spend the commitment transaction HTLC output
    receiver_preimage.wit.vtxinwit.append(CTxInWitness())
    receiver_preimage.wit.vtxinwit[0].scriptWitness.stack = [fundee_sig, b'a' * 32, witness_script]

    # Spend the parent transaction OP_TRUE output
    junk_script = CScript([OP_TRUE])
    receiver_preimage.wit.vtxinwit.append(CTxInWitness())
    receiver_preimage.wit.vtxinwit[1].scriptWitness.stack = [junk_script]
    receiver_preimage.rehash()

    return commitment_tx, offerer_timeout, receiver_preimage


class ReplacementCyclingTest(WarnetTestFramework):

    def set_test_params(self):
        self.num_nodes = 2

    def test_replacement_cycling(self):
        alice = self.nodes[0]
        alice_seckey = ECKey()
        alice_seckey.set((1).to_bytes(32, "big"), True)

        asyncio.run(self.query_nostr())

    async def query_nostr(self):
        keys = Keys.generate()
        client = Client(keys)
        client.add_relay("wss://service/nostr-service")
        client.connect()
        event = EventBuilder.new_text_note("Test note from scratch.py", [])
        client.send_event(event)




    def run_test(self):
        address = "bcrt1p9yfmy5h72durp7zrhlw9lf7jpwjgvwdg0jr0lqmmjtgg83266lqsekaqka"    # noqa

        self.generatetoaddress(self.nodes[0], nblocks=101,address=address)

        self.wallet = MiniWallet(self.nodes[0])

        self.test_replacement_cycling()


if __name__ == '__main__':
    ReplacementCyclingTest().main()
