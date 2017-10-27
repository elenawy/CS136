#!/usr/bin/env python

import sys
import math
from gsp import GSP
from util import argmax_index

from mewtbb import MewtBB

class MewtBudget(MewtBB):
    """Balanced bidding agent"""

    def __init__(self, id, value, budget):
        self.id = id
        self.value = value
        self.budget = budget
        self.past_clicks = 0
        self.exp_ct1 = []

        n_periods = 48
        for i in range(n_periods):
            self.exp_ct1.append(round(30 * math.cos(math.pi * i / 24) + 50))
    
    def initial_bid(self, reserve):
        return self.value

    def expected_utils(self, t, history, reserve):
        """
        Figure out the expected utility of bidding such that we win each
        slot, assuming that everyone else keeps their bids constant from
        the previous round.

        returns a list of utilities per slot.
        """
        prev_round = history.round(t - 1)
        m = len(prev_round.clicks)
        utilities = []

        for i in range(m):
            t_j = self.paymentGivenOtherBids(t, prev_round, i)
            if (t_j < reserve):
                t_j = reserve
            #if (t_j >= target_budget):
            #    utilities.append(float("-inf"))
            utilities.append(prev_round.clicks[i] * (self.value - t_j))

        return utilities

    def target_slot(self, t, target_budget, history, reserve):
        """Figure out the best slot to target, assuming that everyone else
        keeps their bids constant from the previous rounds.

        Returns (slot_id, min_bid, max_bid), where min_bid is the bid needed to tie
        the other-agent bid for that slot in the last round.  If slot_id = 0,
        max_bid is min_bid * 2
        """
        utilities = self.expected_utils(t, history, reserve)
        prev_round = history.round(t-1)
        sorted_index = sorted(range(len(utilities)),
                             key=lambda k: self.paymentGivenOtherBids(t, prev_round, k) * prev_round.clicks[k], reverse=True)
        index_list = [k for k, idx in enumerate(sorted_index) if self.paymentGivenOtherBids(t, prev_round, idx)  * prev_round.clicks[k] < target_budget]
        if (len(index_list) > 0):
            i = index_list[0]
        else:
            i = sorted_index[len(sorted_index)-1]
        info = self.slot_info(t, history, reserve)
        return info[i]

    def calc_relative_budget_factor(self, history):
        average_others_spent = float(sum(history.agents_spent) - history.agents_spent[self.id]) / (
        len(history.agents_spent) - 1)
        if (average_others_spent < 1 or history.agents_spent[self.id] < 1):
            return 1.0
        return float(average_others_spent / history.agents_spent[self.id])

    def calc_relative_ct_factor(self, t, prev_round):
        average_clicks_past = float(self.past_clicks) / t
        if (average_clicks_past < 1):
            return 1.0
        return sum(prev_round.clicks) / average_clicks_past

    def calc_baseline_budget(self, t, remaining_budget):
        t0 = t % len(self.exp_ct1)
        exp_total_ct1 = sum(self.exp_ct1[t0:len(self.exp_ct1)-1])
        if (exp_total_ct1 < 1):
            return remaining_budget
        return round(float(remaining_budget * self.exp_ct1[t0] / exp_total_ct1))

    def calc_target_budget(self, baseline_budget, relative_budget_factor, relative_ct_factor):
        target_budget = baseline_budget * relative_budget_factor * relative_ct_factor * 0.2
        return target_budget

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

        prev_round = history.round(t - 1)
        m = len(prev_round.clicks)

        self.past_clicks += sum(prev_round.clicks)
        remaining_budget = self.budget - history.agents_spent[self.id]
        base_budget = self.calc_baseline_budget(t, remaining_budget)
        b_factor = self.calc_relative_budget_factor(history)
        ct_factor = self.calc_relative_ct_factor(t, prev_round)
        target_budget = self.calc_target_budget(base_budget, b_factor, ct_factor)

        (slot, min_bid, max_bid) = self.target_slot(t, target_budget, history, reserve)

        target_payment = self.paymentGivenOtherBids(t, prev_round, slot)
        if target_payment < reserve:
            target_payment = reserve

        if target_payment > self.value:
            bid = self.value
        elif slot == 0:
            bid = self.value
        else:
            target_ctr = prev_round.clicks[slot]
            previous_ctr = prev_round.clicks[slot - 1]
            bid = - float(target_ctr * (self.value - target_payment)) / (previous_ctr) + self.value

        if bid > target_budget:
            return target_budget
        else:
            return bid

    def __repr__(self):
        return "%s(id=%d, value=%d)" % (
            self.__class__.__name__, self.id, self.value)
