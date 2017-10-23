#!/usr/bin/python

# This is the Tournament client

import random
import logging
import math

from messages import Upload, Request
from util import even_split
from peer import Peer
from mewtstd import MewtStd 


class MewtTourney(MewtStd):
    def post_init(self):
        print "post_init(): %s here!" % self.id
        self.dummy_state = dict()
        self.dummy_state["cake"] = "lie"
    
    def uploads(self, requests, peers, history):
        """
        requests -- a list of the requests for this peer for this round
        peers -- available info about all the peers
        history -- history for all previous rounds

        returns: list of Upload objects.

        In each round, this will be called after requests().
        """

        round = history.current_round()
        previous_round = round - 1

        num_unchoke_slots = int(math.sqrt(self.up_bw))

        if (round < 1):
            return []

        # determine the list of peers who are requesting pieces from Agent; there are no duplicates
        requesting_peers = []
        for request in requests:
            if request.requester_id not in requesting_peers:
                requesting_peers.append(request.requester_id)

        # bandwidths assigned to peers
        bws = []


        needed = lambda i: self.pieces[i] < self.conf.blocks_per_piece
        needed_pieces = filter(needed, range(len(self.pieces)))
        np_set = set(needed_pieces)  # sets support fast intersection ops.

        peer_to_amt_needed_pieces = getNumNeededPiecesPeerHas(np_set, peers, requesting_peers)

        sorted_peers_by_np = sorted(peer_to_amt_needed_pieces.items(), reverse=True, key= lambda x: x[1])

        unchoked_peers = set()
        for k in range(min(num_unchoke_slots, len(sorted_peers_by_np))):
            unchoked_peers.add(sorted_peers_by_np[k][0].id)
            
        # every 3rd round, optimistically unchoke a peer that is not one of the top unchoked peers
        if (round > 0 and round % 3 == 0 and len(requesting_peers) > len(unchoked_peers)):
            optimistically_unchoked_peer = random.choice(requesting_peers)
            while (optimistically_unchoked_peer in unchoked_peers):
                optimistically_unchoked_peer = random.choice(requesting_peers)
            unchoked_peers.add(optimistically_unchoked_peer)
        

        if len(unchoked_peers) > 0:
            bws = even_split(self.up_bw, len(unchoked_peers))
        else:
            # don't allocate bandwidth if no peers are unchoked
            bws = [0 for _ in range (len(unchoked_peers))]

        uploads = [Upload(self.id, peer_id, bw)
                   for (peer_id, bw) in zip(unchoked_peers, bws)]

            
        return uploads

def getNumNeededPiecesPeerHas(needed_pieces, peers, requesting_peers):

    peer_to_amt_np = {}

    for peer in peers:
        if peer.id in requesting_peers:
            av_pieces = peer.available_pieces
            count = 0
            for np in needed_pieces:
                if np in av_pieces:
                    count += 1
            peer_to_amt_np[peer] = count

    return peer_to_amt_np



