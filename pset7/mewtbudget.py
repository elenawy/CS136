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
            else:
                utilities.append(prev_round.clicks[i] * (self.value - t_j))

        return utilities

    def target_slot(self, t, target_budget, history, reserve):
        """Figure out the best slot to target, assuming that everyone else
        keeps their bids constant from the previous rounds.

        Returns (slot_id, min_bid, max_bid), where min_bid is the bid needed to tie
        the other-agent bid for that slot in the last round.  If slot_id = 0,
        max_bid is min_bid * 2
        """
        i = argmax_index(self.expected_utils(t, history, reserve))
        info = self.slot_info(t, history, reserve)
        return info[i]

    def calc_relative_budget_factor(self, history):
        average_others_spent = float(sum(history.agents_spent) - history.agents_spent[self.id]) / (len(history.agents_spent) - 1)
        if float(history.agents_spent[self.id]) == 0:
            return 1
        else:
            return float(history.agents_spent[self.id]) / average_others_spent

    def calc_relative_ct_factor(self, t, prev_round):
        average_clicks_past = float(self.past_clicks) / t
        if average_clicks_past == 0:
            return 1
        else:
            return sum(prev_round.clicks) / average_clicks_past

    def calc_baseline_budget(self, t, remaining_budget):
        return remaining_budget * self.exp_ct1[t] / sum(self.exp_ct1[t:])

    def calc_target_budget(self, baseline_budget, relative_budget_factor, relative_ct_factor):
        target_budget = baseline_budget * relative_ct_factor
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

        bid = self.initial_bid(reserve)
        if (t == 0):
            return self.initial_bid(reserve)

        prev_round = history.round(t - 1)
        m = len(prev_round.clicks)

        # for calculating target budget
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

