#!/usr/bin/python

# This is a Bit Torrent Reference Client peer that 

import random
import logging

from messages import Upload, Request
from util import even_split
from peer import Peer

class MewtStd(Peer):
    def post_init(self):
        print "post_init(): %s here!" % self.id
        self.dummy_state = dict()
        self.dummy_state["cake"] = "lie"
    
    def requests(self, peers, history):
        """
        peers: available info about the peers (who has what pieces)
        history: what's happened so far as far as this peer can see

        returns: a list of Request() objects

        This will be called after update_pieces() with the most recent state.
        """
        needed = lambda i: self.pieces[i] < self.conf.blocks_per_piece
        needed_pieces = filter(needed, range(len(self.pieces)))
        np_set = set(needed_pieces)  # sets support fast intersection ops.


        logging.debug("%s here: still need pieces %s" % (
            self.id, needed_pieces))

        logging.debug("%s still here. Here are some peers:" % self.id)
        for p in peers:
            logging.debug("id: %s, available pieces: %s" % (p.id, p.available_pieces))

        logging.debug("And look, I have my entire history available too:")
        logging.debug("look at the AgentHistory class in history.py for details")
        logging.debug(str(history))

        requests = []   # We'll put all the things we want here
        # Symmetry breaking is good...
        random.shuffle(needed_pieces)
        
        # Sort peers by id.  This is probably not a useful sort, but other sorts may be useful.
        # we could sort by peer bandwith (larger bw, the more blocks we can download), 
        # or availability size (get pieces we need before agent completes its file and leaves)
        peers.sort(key=lambda p: p.id) 

        np_count_dict = pieceAvailabilityCount(peers, needed_pieces)

        # greatest to least availability
        sorted_np_count_lst = sort(np_count_dict.items(), Reverse=True)

        # request all available pieces from all peers!
        # (up to self.max_requests from each)
        for peer in peers:
            av_set = set(peer.available_pieces)
            isect = av_set.intersection(np_set)
            random.shuffle(isect)
            n = min(self.max_requests, len(isect))
            
            # rarest-first piece-request strategy: request up to n rarest pieces from peer
            for piece_id, _ in sorted_np_count_lst:
                if (n <= 0) {
                    break
                }
                # get the block we want to start downloading the piece and make the request to the peer
                start_block = self.pieces[piece_id]
                r = Request(self.id, peer.id, piece_id, start_block)
                requests.append(r)
                
                #decrement request count
                n -= 1

        return requests


    def uploads(self, requests, peers, history):
        """
        requests -- a list of the requests for this peer for this round
        peers -- available info about all the peers
        history -- history for all previous rounds

        returns: list of Upload objects.

        In each round, this will be called after requests().
        """

        round = history.current_round()
        logging.debug("%s again.  It's round %d." % (
            self.id, round))
        # One could look at other stuff in the history too here.
        # For example, history.downloads[round-1] (if round != 0, of course)
        # has a list of Download objects for each Download to this peer in
        # the previous round.


        if len(requests) == 0:
            logging.debug("No one wants my pieces!")
            chosen = []
            bws = []
        else:
            logging.debug("Still here: uploading to a random peer")
            # change my internal state for no reason
            self.dummy_state["cake"] = "pie"

            request = random.choice(requests)
            chosen = [request.requester_id]
            # Evenly "split" my upload bandwidth among the one chosen requester
            bws = even_split(self.up_bw, len(chosen))

        # create actual uploads out of the list of peer ids and bandwidths
        uploads = [Upload(self.id, peer_id, bw)
                   for (peer_id, bw) in zip(chosen, bws)]
        
        return uploads


# return piece availability count for pieces that are needed
def pieceAvailabilityCount(peers, needed_pieces):
    piece_count_dict = {}

    check_pieces_available = False;
    for p in peers:
        for piece in p.available_pieces:
            if piece in needed_pieces:
                if piece in piece_count_dict:
                    piece_count_dict[piece] += 1
                else:
                    piece_count_dict[piece] = 1
                    check_pieces_available = True

    if check_pieces_available == False:
        print "None of pieces needed are available"
        return None

    return piece_count_dict


def downloadRateByPeerInLastNRounds(n, agent, peers, history):
    rd  = history.current_round - 1

    downloads_by_agent = history.downloads[agent]

    peer_upload_to_agent_dict = {}

    peer_uploadspeed_to_agent_dict = {}

    while n > 0:
        for download in downloads_by_agent[rd]:
            if download.from_id in peers and download.to_id == agent:
                peer = download.from_id

                # track how many blocks that agent received from peer over past n periods
                if peer in peer_upload_to_agent_dict:
                    peer_upload_to_agent_dict[peer] += download.blocks
                else:
                    peer_upload_to_agent_dict[peer] = download.blocks
                
                # update the uploadspeed that peer uploaded to the agent
                peer_uploadspeed_to_agent_dict[peer] = peer.up_bw

        # decrease the round
        rd-= 1
        # decrease n
        n -= 1

    return downloadRateByPeerInLastNRounds










