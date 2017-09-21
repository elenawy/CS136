#!/usr/bin/python


import random
import logging

from messages import Upload, Request
from util import even_split
from peer import Peer

class MewtTyrant(Peer):
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

        requests = []   
        # Symmetry breaking is good...
        random.shuffle(needed_pieces)
        
        # Sort peers by id.  This is probably not a useful sort, but other sorts may be useful.
        # we could sort by peer bandwith (larger bw, the more blocks we can download), 
        # or availability size (get pieces we need before agent completes its file and leaves)
        # peers.sort(key=lambda p: p.id) 
        random.shuffle(peers)

        sorted_np_count_lst = pieceAvailabilityCount2(peers, needed_pieces)
        if sorted_np_count_lst == None:
            print "No Requests: None of pieces needed are available"
            return requests


        # request all available pieces from all peers!
        # (up to self.max_requests from each)
        for peer in peers:
            av_set = set(peer.available_pieces)
            isect = list(av_set.intersection(np_set))

            # randomly shuffle intersect list
            random.shuffle(isect)
            n = min(self.max_requests, len(isect))
            
            # rarest-first piece-request strategy: request up to n rarest pieces from peer
            for _ ,piece_ids in sorted_np_count_lst:
                random.shuffle(piece_ids)
                for piece_id in piece_ids:
                    if (n <= 0):
                        break
                    if (piece_id in av_set):
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


    
