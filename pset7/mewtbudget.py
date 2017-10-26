#!/usr/bin/env python

import sys

from gsp import GSP
from util import argmax_index

class MewtBudget(MewtBB):
    """Balanced bidding agent"""
    def __init__(self, id, value, budget):
        self.id = id
        self.value = value
        self.budget = budget 

    def expected_utils(self, t, history, reserve):
        """
        Figure out the expected utility of bidding such that we win each
        slot, assuming that everyone else keeps their bids constant from
        the previous round.

        returns a list of utilities per slot.
        """
        prev_round = history.round(t-1)
        m = len(prev_round.clicks)
        utilities = []

        for i in range(m):
            t_j = self.paymentGivenOtherBids(t, prev_round, i)
            if (t_j < reserve):
                t_j = reserve
            if (t_j >= target_budget):
                utilities.append(float("-inf"))
            else:
                utilities.append(prev_round.clicks[i] * (self.value - t_j))

        return utilities


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

        bid = self.initial_bid()
        if (t == 0):
            return self.initial_bid()

        prev_round = history.round(t-1)
        m = len(prev_round.clicks)
        (slot, min_bid, max_bid) = self.target_slot(t, history, reserve)


        target_payment = self.paymentGivenOtherBids(t, prev_round, slot)
        if target_payment < reserve:
            target_payment = reserve


        if target_payment > self.value:
            bid = self.value
        elif slot == 0:
            bid = self.value
        else:
            target_ctr = prev_round.clicks[slot]
            previous_ctr = prev_round.clicks[slot-1]
            bid = - float(target_ctr * (self.value - target_payment)) / (previous_ctr) + self.value

        if bid > target_budget:
            return target_budget
        else:
            return bid
    def __repr__(self):
        return "%s(id=%d, value=%d)" % (
            self.__class__.__name__, self.id, self.value)


