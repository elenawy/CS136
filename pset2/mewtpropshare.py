# This is the PropShare client

import random
import logging

from messages import Upload, Request
from util import even_split
from peer import Peer
from mewtstd import MewtStd 

class MewtPropShare(MewtStd):
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

        if (round < 1):
            return []

        # if no requests are made, then agent does not create any uploads
        if len(requests) == 0:
            return []
        
        # determine the list of peers who are requesting pieces from Agent
        requesting_peers = []
        for request in requests:
            if request.requester_id not in requesting_peers:
                requesting_peers.append(request.requester_id)

        previous_round = round - 1
        downloads = history.downloads[previous_round]
        # dictionary of {requester: amt uploaded to peer i, ... }
        amt_uploaded = {}
        total_uploaded_by_requesting_peers = 0
        unchoked_peers = set()
        for download in downloads:
            peer_id = download.from_id
            blocks = download.blocks
            if peer_id in requesting_peers:
                total_uploaded_by_requesting_peers += blocks
                unchoked_peers.add(peer_id)
                if peer_id in amt_uploaded:
                    amt_uploaded[peer_id] += blocks
                else:
                    amt_uploaded[peer_id] = blocks

        bws = []
        for uc_peer in unchoked_peers:
            blocks = amt_uploaded[uc_peer]
            percent_bw_allocated = (blocks / float(total_uploaded_by_requesting_peers)) * .9
            bws.append(int(self.up_bw*percent_bw_allocated))

        # check if there is someone to optimistical unchoke
        if len(unchoked_peers) < len(requesting_peers):
            optimistic_unchoke_peer = random.choice(requesting_peers)
            while (optimistic_unchoke_peer in unchoked_peers):
                optimistic_unchoke_peer = random.choice(requesting_peers)

            unchoked_peers.add(optimistic_unchoke_peer)
            bws.append(int(.1 * self.up_bw))


        uploads = [Upload(self.id, peer_id, bw)
                   for (peer_id, bw) in zip(unchoked_peers, bws)]

        return uploads