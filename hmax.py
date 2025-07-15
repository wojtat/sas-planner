#!/bin/env python

import sys
import numpy as np

from sas import SasParser, fdr_to_strips_plus


def compute_gamma_fixed_point(
        facts,
        actions,
        s,
        g,
        compute_fully,
        pre_to_actions
):
    sigma = {p: float('inf') for p in facts}
    for p in s:
        sigma[p] = 0

    for pre, add, cost in actions:
        if not pre:
            for p in add:
                sigma[p] = min(cost, sigma[p])

    counter = [len(pre) for pre, add, cost in actions]
    finished = set()

    if compute_fully:
        while len(finished) != len(facts):
            cheapest_fact_cost = None
            cheapest_fact = None
            for p in facts:
                if p in finished:
                    continue
                if cheapest_fact_cost is None or sigma[p] < cheapest_fact_cost:
                    cheapest_fact = p
                    cheapest_fact_cost = sigma[p]
            finished.add(cheapest_fact)

            for i in pre_to_actions[cheapest_fact]:
                counter[i] -= 1
                if counter[i] == 0:
                    pre, add, cost = actions[i]
                    for p in add:
                        v = cost + cheapest_fact_cost
                        if v < sigma[p]:
                            sigma[p] = v
    else:
        while not g.issubset(finished):
            cheapest_fact_cost = None
            cheapest_fact = None
            for p in facts:
                if p in finished:
                    continue
                if cheapest_fact_cost is None or sigma[p] < cheapest_fact_cost:
                    cheapest_fact = p
                    cheapest_fact_cost = sigma[p]
            finished.add(cheapest_fact)

            for i in pre_to_actions[cheapest_fact]:
                counter[i] -= 1
                if counter[i] == 0:
                    pre, add, cost = actions[i]
                    for p in add:
                        v = cost + cheapest_fact_cost
                        if v < sigma[p]:
                            sigma[p] = v

    return sigma


def _compute_gamma_fixed_point(
        facts,
        actions,
        s,
        g,
        compute_fully,
        pre_to_actions
):
    fact_to_index = {f: i for i, f in enumerate(facts)}

    # Precompute actions
    # actions_pre = np.zeros((len(actions), len(facts)), dtype=np.bool_)
    # actions_add = np.zeros((len(actions), len(facts)), dtype=np.bool_)
    # actions_costs = np.zeros(len(actions), dtype=np.int32)
    # for i, (pre, add, cost) in enumerate(actions):
    #     for p in pre:
    #         actions_pre[i, fact_to_index[p]] = True
    #     for p in add:
    #         actions_add[i, fact_to_index[p]] = True
    #     actions_costs[i] = cost

    sigma = np.empty(len(facts))
    sigma[:] = np.inf
    for p in s:
        sigma[fact_to_index[p]] = 0

    # sigma = {p: float('inf') for p in facts}
    # for p in s:
    #     sigma[p] = 0

    num_finished_actions = 0
    counter = [len(pre) for pre, add, cost in actions]

    for i, (pre, add, cost) in enumerate(actions):
        if not pre:
            num_finished_actions += 1
            for p in add:
                p_i = fact_to_index[p]
                if cost < sigma[p_i]:
                    sigma[p_i] = cost

    finished = np.zeros(len(facts), dtype=np.bool_)
    num_finished = 0

    #while num_finished != len(facts) if compute_fully else not g.issubset(finished):
    while num_finished != len(facts) and num_finished_actions != len(actions):
        cheapest_fact_i = np.argmin(np.where(finished, np.inf, sigma))
        # cheapest_cost = float('inf')
        # for fact_i, cost in enumerate(sigma):
        #     if fact_i in finished:
        #         continue
        #
        #     if cheapest_cost == float('inf') or cost < cheapest_cost:
        #         cheapest_cost = cost
        #         cheapest_fact_i = fact_i
        cheapest_cost = sigma[cheapest_fact_i]

        if cheapest_cost == float('inf'):
            break

        finished[cheapest_fact_i] = True
        num_finished += 1
        cheapest_fact = facts[cheapest_fact_i]

        # for i, (pre, add, cost) in enumerate(actions):
        for i in pre_to_actions[cheapest_fact]:
            pre, add, cost = actions[i]
            # if cheapest_fact not in pre:
            #     continue

            counter[i] -= 1
            if counter[i] == 0:
                #num_finished_actions += 1
                for p in add:
                    p_i = fact_to_index[p]
                    v = cost + cheapest_cost
                    if v < sigma[p_i]:
                        sigma[p_i] = v

    return {facts[f_i]: (int(cost) if cost < np.inf else cost) for f_i, cost in enumerate(sigma)}


def compute_h_max(
        facts,
        actions,
        s0,
        g,
        pre_to_actions
):
    sigma = compute_gamma_fixed_point(facts, actions, s0, g, False, pre_to_actions)

    max_cost = -float('inf')
    for p in g:
        if sigma[p] > max_cost:
            max_cost = sigma[p]

    return max_cost


def main(input_file):
    parser = SasParser(input_file)
    num_variables, initial_values, goal_state, actions = parser.parse()
    facts, actions, s0, g, pre_to_actions = fdr_to_strips_plus(actions, initial_values, goal_state)

    h_max = compute_h_max(facts, actions, s0, g, pre_to_actions)
    print(h_max)


if __name__ == '__main__':
    main(sys.argv[1])
