#!/usr/bin/python


import random
import logging
import math

from messages import Upload, Request
from util import even_split
from peer import Peer

class MewtTyrant(Peer):
    def post_init(self):
        print "post_init(): %s here!" % self.id
        self.dummy_state = dict()
        self.dummy_state["cake"] = "lie"
        # f_ji: For each peer j, peer i maintains estimates of expected download rate f_ji 
        # FORM: peer_id --> rate
        self.download_rate_estimates = {}
        
        # T_j = expected upload rate T_j required for reciprocation by peer j.
        # FORM: peer_id --> rate
        self.threshold_upload_rate = {}
        
        self.unchoked_peers = set()

        # peers that Peer unchoked in previous r rounds, and count; count = 0 means not unchoked, 
        # count > 0 means unchoked. count > k means unchoked k times in prevous r rounds.
        # FORM: peer_id --> count
        self.times_unchoked_by_peer = {}

        self.total_downloads_gave = 0
        self.num_unchoke_slots = 0

        self.upload_percentage_old = 0

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
        # random.shuffle(peers)

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
       
        g = .1      # gamma 
        r = 3     # 3 periods backwards check
        a = .20     # 20%
        
        bandwidth_capacity = self.up_bw

        self.unchoked_peers = set()

        # determine the list of peers who are requesting pieces from Agent; there are no duplicates
        requesting_peers = []
        for request in requests:
            if request.requester_id not in requesting_peers:
                requesting_peers.append(request.requester_id)

        # bandwidths assigned to peers
        bws = []

        if (round < 1):
            # initialize tracking dictionaries and our two parameters f_ji and T_j
            for peer in peers:
                self.times_unchoked_by_peer[peer.id] = 0

                self.num_unchoke_slots = int(math.sqrt(self.up_bw)) 

                # fix initialize the parameters based of starting peer
                self.download_rate_estimates[peer.id] = self.up_bw / float (self.num_unchoke_slots)
                self.threshold_upload_rate[peer.id] =  self.up_bw / float(self.num_unchoke_slots)

            chosen_peers = []
            if len(requesting_peers) >= self.num_unchoke_slots:
                chosen_peers = random.sample(requesting_peers,self.num_unchoke_slots)
            else:
                chosen_peers = requesting_peers
            for chosen_p in chosen_peers:
                self.unchoked_peers.add(chosen_p)

            # assign bandwith
            if len(self.unchoked_peers) > 0:
                bws = even_split(bandwidth_capacity, len(self.unchoked_peers))
            else:
                # don't allocate bandwidth if no peers are unchoked
                bws = [0 for _ in range (len(self.unchoked_peers))]

            # gave all bandwidth
            self.total_downloads_gave = bandwidth_capacity  


            uploads = [Upload(self.id, peer_id, bw)
                   for (peer_id, bw) in zip(self.unchoked_peers, bws)]

        else:
            # use the algorithm in the book to determine unchoke slots and capacity. 

            # update which peers unchoked this peer

            seen_unchoked_by_peer = set()
            # get downloads from previous round
            downloads = history.downloads[round-1]

            for download in downloads:
                if download.from_id not in seen_unchoked_by_peer:
                    self.times_unchoked_by_peer[download.from_id] += 1
                    seen_unchoked_by_peer.add(download.from_id)
            # if agent was not unchoked by a peer set it to 0
            for peer in peers:
                if peer.id not in seen_unchoked_by_peer:
                    self.times_unchoked_by_peer[peer.id] = 0

            updatePeerAfterRound(self, history, g, a, r, peers) 

            # sort requesting peers by f_ij / T_ij
            random.shuffle(requesting_peers)
            sortedPeers = sorted(requesting_peers, reverse=True, key= lambda x: float(self.download_rate_estimates[x] / self.threshold_upload_rate[x]))

            for p in sortedPeers:
                bandwidth_allocated = self.threshold_upload_rate[p]
                if bandwidth_capacity >= bandwidth_allocated:
                    self.unchoked_peers.add(p)
                    bandwidth_capacity -= bandwidth_allocated

                    self.total_downloads_gave += bandwidth_allocated
                    bws.append(bandwidth_allocated)
                else:
                    continue

            self.num_unchoke_slots = len(self.unchoked_peers)

            uploads = [Upload(self.id, peer_id, bw)
                   for (peer_id, bw) in zip(self.unchoked_peers, bws)]

        return uploads

# will be called at beginning of the round to update for the last round that just occured
def updatePeerAfterRound(self, history, g, a, r, peers):
    for uc_peer_id in self.unchoked_peers:

        # case b)
        # check if peer j reciprocated and unchoked peer i, by looking at count 
        _, count = self.times_unchoked_by_peer[uc_peer_id]
        if count > 0: # peer j did unchoke i
            self.download_rate_estimates[uc_peer_id] = calculateTotalDownloadedFromPeer(self, history, uc_peer_id)
            
            # case c) peer j has unchoked i for each of last r periods
            if count >= r:
                self.threshold_upload_rate[uc_peer_id] *= float(1 - g) 

        else:  # case a) peer j did not unchoke i
            self.threshold_upload_rate[uc_peer_id] *= float(1 + a)
            have_messages = 0
            for p in peers:
                if p.id == uc_peer_id:
                    have_messages = len(p.available_pieces)
            self.download_rate_estimates[uc_peer_id] =  have_messages/ 8.


def calculateTotalDownloadedFromPeer(self, history, uploader_id):
    curr_round = history.current_round()
    previous_round = curr_round - 1

    downloads = []
    if previous_round > 0:
        downloads = history.downloads[previous_round]
    else:
        downloads = []

    downloads = history.downloads

    total_downloaded = 0
    for download in downloads:
        if download.from_id == uploader_id:
            total_downloaded += download.blocks

    return total_downloaded


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


