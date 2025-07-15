#!/bin/env python
import argparse
from argparse import ArgumentParser

import hmax
from sas import SasParser, fdr_to_strips_plus


def compute_pcf(actions_ext, sigma):
    pcf = []
    for pre, add, cost in actions_ext:
        max_p_cost = -float('inf')
        for p in pre:
            if sigma[p] == float('inf'):
                continue
            if sigma[p] > max_p_cost:
                max_p_cost = sigma[p]
                max_p = p
            elif sigma[p] == max_p_cost and p[0] > max_p[0] or (p[0] == max_p[0] and p[1] > max_p[1]):
                max_p_cost = sigma[p]
                max_p = p
        pcf.append(max_p)
    return pcf


def construct_justification_graph(actions, pcf):
    edges = {}
    for i, (max_p, (pre, add, cost)) in enumerate(zip(pcf, actions)):
        if max_p not in edges:
            edges[max_p] = []
        for q in add:
            edges[max_p].append((q, cost, i))
    rev_edges = {}
    for from_vertex, to_vertices in edges.items():
        for to_vertex, cost, i in to_vertices:
            if to_vertex not in rev_edges:
                rev_edges[to_vertex] = []
            rev_edges[to_vertex].append((from_vertex, cost, i))
    return edges, rev_edges


def construct_action_landmark(edges, rev_edges):
    v_top = {True}
    stack = [True]
    while stack:
        vertex = stack.pop()
        if vertex not in rev_edges:
            continue
        for pred, cost, i in rev_edges[vertex]:
            if cost == 0 and pred not in v_top:
                v_top.add(pred)
                stack.append(pred)

    landmark = []
    u_bot = {False}
    stack = [False]
    while stack:
        vertex = stack.pop()
        if vertex not in edges:
            continue
        for neighbor, cost, i in edges[vertex]:
            if neighbor in v_top:
                landmark.append(i)
            elif neighbor not in u_bot:
                u_bot.add(neighbor)
                stack.append(neighbor)
    return landmark


def compute_h_lm_cut(
        facts,
        actions,
        s0,
        g,
        pre_to_actions
):
    init_g = g
    actions = actions + [
        ({False}, s0, 0),
        (g, {True}, 0)
    ]
    facts = facts + [True, False]
    for p in g:
        pre_to_actions[p] = pre_to_actions[p] + [len(actions) - 1]
    pre_to_actions[True] = []
    pre_to_actions[False] = [len(actions) - 2]
    s0 = {False}
    g = {True}

    h_lm_cut = 0
    sigma = hmax.compute_gamma_fixed_point(facts, actions, s0, g, True, pre_to_actions)

    max_cost = sigma[True]
    if max_cost == float('inf'):
        return float('inf')

    pcf = compute_pcf(actions, sigma)

    while max_cost != 0:
        # Construct justification graph
        edges, rev_edges = construct_justification_graph(actions, pcf)

        # Construct V_top and U_bot and its landmark
        landmark = construct_action_landmark(edges, rev_edges)

        m = float('inf')
        for i in landmark:
            cost = actions[i][2]
            if cost < m:
                m = cost

        if m == 0:
            break
        h_lm_cut += m

        # Lower costs of actions in landmark by m
        for i in landmark:
            pre, add, cost = actions[i]
            actions[i] = (pre, add, cost - m)

        sigma = hmax.compute_gamma_fixed_point(facts, actions, s0, g, True, pre_to_actions)

        max_cost = sigma[True]

        pcf = compute_pcf(actions, sigma)

    for p in init_g:
        pre_to_actions[p] = pre_to_actions[p][:-1]

    return h_lm_cut


def main(args: argparse.Namespace):
    input_file = args.input
    parser = SasParser(input_file)
    num_variables, initial_values, goal_state, actions = parser.parse()
    facts, actions, s0, g, pre_to_actions = fdr_to_strips_plus(actions, initial_values, goal_state)

    h_lm_cut = compute_h_lm_cut(facts, actions, s0, g, pre_to_actions)
    print(h_lm_cut)


if __name__ == '__main__':
    parser = ArgumentParser(
        description='Compute and print the LM-cut heuristic value of the initial state'
    )
    parser.add_argument(
        '--input', '-i', type=str,
        help='Path to a file containing the SAS representation of the task',
        required=True
    )
    main(parser.parse_args())
