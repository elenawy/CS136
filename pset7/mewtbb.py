#!/usr/bin/env python

import sys
import math
from gsp import GSP
from util import argmax_index

class MewtBB:
    """Balanced bidding agent"""
    def __init__(self, id, value, budget):
        self.id = id
        self.value = value
        self.budget = budget

    def initial_bid(self, reserve):
        return self.value / 2


    def slot_info(self, t, history, reserve):
        """Compute the following for each slot, assuming that everyone else
        keeps their bids constant from the previous rounds.

        Returns list of tuples [(slot_id, min_bid, max_bid)], where
        min_bid is the bid needed to tie the other-agent bid for that slot
        in the last round.  If slot_id = 0, max_bid is 2* min_bid.
        Otherwise, it's the next highest min_bid (so bidding between min_bid
        and max_bid would result in ending up in that slot)
        """
        prev_round = history.round(t-1)
        other_bids = filter(lambda (a_id, b): a_id != self.id, prev_round.bids)

        clicks = prev_round.clicks
        def compute(s):
            (min, max) = GSP.bid_range_for_slot(s, clicks, reserve, other_bids)
            if max == None:
                max = 2 * min
            return (s, min, max)
            
        info = map(compute, range(len(clicks)))
#        sys.stdout.write("slot info: %s\n" % info)
        return info


    def expected_utils(self, t, history, reserve):
        """
        Figure out the expected utility of bidding such that we win each
        slot, assuming that everyone else keeps their bids constant from
        the previous round.

        returns a list of utilities per slot.
        """
        prev_round = history.round(t-1)
        m = 5
        utilities = []

        for i in range(m):
            utilities.append(self.getPos_j(t,i) * (self.value - self.paymentGivenOtherBids(t, history, i)))

        return utilities

    def getPos_j(self, t, j):
        m = 5
        ct_1 = round(30*math.cos(math.pi*t / 24) + 50)
        clicks_in_pos_j = []

        for i in range(m):
            clicks_in_pos_j[i] *= 0.75 ** (i-1)

        sum_ct = sum(range(m))
        ct_j = clicks_in_pos_j[j]
        pos_j = float(ct_j) / sum_ct

        return pos_j 

    def paymentGivenOtherBids(self, t, history, j):
        prev_round = history(round(t-1))
        other_bids = filter(lambda (a_id, b): a_id != self.id, prev_round.bids)
        other_bids.sort(key=lambda x: x[1])

        if j > len(other_bids):
            return 0
        else:
            return other_bids[j-1][1]

    def target_slot(self, t, history, reserve):
        """Figure out the best slot to target, assuming that everyone else
        keeps their bids constant from the previous rounds.

        Returns (slot_id, min_bid, max_bid), where min_bid is the bid needed to tie
        the other-agent bid for that slot in the last round.  If slot_id = 0,
        max_bid is min_bid * 2
        """
        i =  argmax_index(self.expected_utils(t, history, reserve))
        info = self.slot_info(t, history, reserve)
        return info[i]

    def bid(self, t, history, reserve):
        # The Balanced bidding strategy (BB) is the strategy for a player j that, given
        # bids b_{-j},
        # - targets the slot s*_j which maximizes his utility, that is,
        # s*_j = argmax_s {clicks_s (v_j - t_s(j))}.
        # - chooses his bid b' for the next round so as to
        # satisfy the following equation:
        # clicks_{s*_j} (v_j - t_{s*_j}(j)) = clicks_{s*_j-1}(v_j - b')
        # (p_x is the price/click in slot x)
        # If s*_j is the top slot, bid the value v_j

        if (t == 0):
            return self.initial_bid()

        prev_round = history.round(t-1)
        (slot, min_bid, max_bid) = self.target_slot(t, history, reserve)


        target_payment = self.paymentGivenOtherBids(t, history, slot)
        if target_payment < reserve:
            target_payment = reserve

        if target_payment > self.value:
            return self.value
        elif slot == 0:
            return self.value
        else:
            target_ctr = getPos_j(t, slot)
            previous_ctr = getPos_j(t, slot-1)
            bid = - float(target_pos(self.value - target_payment)) / (previous_ctr) + self.value
            return bid

    def __repr__(self):
        return "%s(id=%d, value=%d)" % (
            self.__class__.__name__, self.id, self.value)


