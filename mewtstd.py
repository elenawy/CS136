#!/usr/bin/python

# This is a Bit Torrent Reference Client peer that 

import random
import logging
import math

from messages import Upload, Request
from util import even_split
from peer import Peer

class MewtStd(Peer):
    def post_init(self):
        print "post_init(): %s here!" % self.id
        self.dummy_state = dict()
        self.dummy_state["cake"] = "lie"
        self.optimistically_unchoked_peer = None
    
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

        # logging.debug("%s here: still need pieces %s" % (
        #     self.id, needed_pieces))
        # logging.debug("%s still here. Here are some peers:" % self.id)

        # for p in peers:
        #     logging.debug("id: %s, available pieces: %s" % (p.id, p.available_pieces))

        # logging.debug("And look, I have my entire history available too:")
        # logging.debug("look at the AgentHistory class in history.py for details")
        # logging.debug(str(history))

        requests = []   # We'll put all the things we want here
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
        Agent History -- history for all previous rounds

        returns: list of Upload objects.

        In each round, this will be called after requests().
        """
        

        round = history.current_round()
        # logging.debug("%s again.  It's round %d." % (
        #     self.id, round))

        # if no requests are made, then agent does not create any uploads
        if len(requests) == 0:
            return []
        
        # number of rounds to track in history to determine unchoke slots
        num_rounds_backtracking = 2
        num_unchoke_slots = int(math.sqrt(self.up_bw))

        # set of peers who get an unchoke slot
        unchoked_peers = set()

        # determine the list of peers who are requesting pieces from Agent
        requesting_peers = []
        for request in requests:
            if request.requester_id not in requesting_peers:
                requesting_peers.append(request.requester_id)

        
        # if round is less than 2 just randomly allocate unchoke slots, otherwise determine by highest download rate
        if (round < 2):
            chosen_peers = []
            if len(requesting_peers) >= num_unchoke_slots:
                chosen_peers = random.sample(requesting_peers,num_unchoke_slots)
            else:
                chosen_peers = requesting_peers
            for chosen_p in chosen_peers:
                unchoked_peers.add(chosen_p)

        else:
            # {peer: download_rate, .....}
            peer_by_download_rate_map = findPeerByDownloadRateInLastNRounds(
                num_rounds_backtracking, self, requesting_peers, history)

            # [(peer_id, download rate), ...] in descending order
            sorted_peer_by_download_rate = sorted(peer_by_download_rate_map.items(), key=lambda x:x[1], reverse=True)

            # find top 3 peers and their download rate
            for peer_id, download_rate in sorted_peer_by_download_rate[:num_unchoke_slots]:
                unchoked_peers.add(peer_id)

        # every 4th round, optimistically unchoke a peer that is not one of the top 3 peers
        if (round > 0 and round % 3 == 0 and len(requesting_peers) > len(unchoked_peers)):
            self.optimistically_unchoked_peer = random.choice(requesting_peers)
            while (self.optimistically_unchoked_peer in unchoked_peers):
                self.optimistically_unchoked_peer = random.choice(requesting_peers)
            unchoked_peers.add(self.optimistically_unchoked_peer) 
        elif (self.optimistically_unchoked_peer != None):
            unchoked_peers.add(self.optimistically_unchoked_peer)
        
        bws = []
        if len(unchoked_peers) > 0:
            bws = even_split(self.up_bw, len(unchoked_peers))
        else:
            # don't allocate bandwidth if no peers are unchoked
            bws = [0 for _ in range (len(unchoked_peers))]

        uploads = [Upload(self.id, peer_id, bw)
                   for (peer_id, bw) in zip(unchoked_peers, bws)]

        return uploads


# return piece availability count for all needed pieces
def pieceAvailabilityCount(peers, needed_pieces):
    # create piece: count dictionary
    piece_count_dict = {}

    check_pieces_available = False;
    for p in peers:
        for piece in p.available_pieces:
            if (piece in needed_pieces):
                if piece in piece_count_dict:
                    piece_count_dict[piece] += 1
                else:
                    piece_count_dict[piece] = 1
                    check_pieces_available = True

    if (check_pieces_available == False):
        print "None of pieces needed are available"
        return None

    return piece_count_dict


def pieceAvailabilityCount2(peers, needed_pieces):
    # create count: [piece, piece] dictionary

    piece_count_dict = pieceAvailabilityCount(peers, needed_pieces)

    if piece_count_dict == None: 
        return None

    count_piece_dict = {}


    for piece, count in piece_count_dict.items():
        if count in count_piece_dict:
            count_piece_dict[count].append(piece)
        else:
            count_piece_dict[count] = [piece]

    sorted_list = sorted(count_piece_dict.items())
    return sorted_list

# find how much each requesting_peer has downloaded to Agent in last n rounds
def findPeerByDownloadRateInLastNRounds(n, self, requesting_peers, history):
    rd  = history.current_round() - 1
    downloads_by_agent = history.downloads

    peer_upload_to_agent_dict = {}

    while (n > 0 and rd >= 0):
        for download in downloads_by_agent[rd]:
            if (download.from_id in requesting_peers and download.to_id == self.id):
                from_peer = download.from_id

                # track how many blocks that agent received from peer in this rd
                if (from_peer in peer_upload_to_agent_dict):
                    peer_upload_to_agent_dict[from_peer] += download.blocks
                else:
                    peer_upload_to_agent_dict[from_peer] = download.blocks

        # decrease the round
        rd-= 1
        # decrease n
        n -= 1

    return peer_upload_to_agent_dict










