#!/bin/env python
import argparse
from argparse import ArgumentParser
from enum import Enum

from sas import SasParser, fdr_to_strips_plus
from hmax import compute_h_max
from lmcut import compute_h_lm_cut
from dataclasses import dataclass


def get_path(parent, goal_state):
    actions = []
    total_cost = 0
    state = goal_state
    while state in parent:
        state, action, cost = parent[state]
        actions.append(action)
        total_cost += cost

    return actions[::-1], total_cost


def a_star(s0, is_goal, get_applicable, h):
    parent = {}
    g = {s0: 0}
    open_list = [(s0, h(s0))]

    while open_list:
        min_priority = float('inf')
        for i, (it, priority) in enumerate(open_list):
            if priority < min_priority:
                min_priority = priority
                min_index = i

        s, f_s = open_list.pop(min_index)

        if is_goal(s):
            return get_path(parent, s)

        for a, cost, s1 in get_applicable(s):
            v = g.get(s, float('inf')) + cost
            if v < g.get(s1, float('inf')):
                g[s1] = v
                parent[s1] = (s, a, cost)
                open_list.append((s1, v + h(s1)))

    return [], -1


@dataclass
class SelectorNode:
    selection_variable: int
    children: list


@dataclass
class GeneratorNode:
    generated_operators: list


def get_actions_with_var_in_pre(var, value, actions, applicable_actions):
    current_applicable_actions = []
    for i in applicable_actions:
        name, cost, prevailing, effect = actions[i]
        done = False
        for v, val in prevailing:
            if var == v:
                if value == val:
                    current_applicable_actions.append(i)
                done = True
                break
        if done:
            continue
        for v, changed_from, changed_to in effect:
            if var == v:
                if changed_from != -1 and value == changed_from:
                    current_applicable_actions.append(i)
                break
    return current_applicable_actions


def at_least_one_action_has_var_in_pre(var, actions, applicable_actions):
    for i in applicable_actions:
        name, cost, prevailing, effect = actions[i]
        for v, val in prevailing:
            if var == v:
                return True
        for v, changed_from, changed_to in effect:
            if changed_from != -1 and var == v:
                return True
    return False


def generate_children(var, domains, actions, applicable_actions):
    if var < len(domains):
        domain = domains[var]
        if not at_least_one_action_has_var_in_pre(var, actions, applicable_actions):
            return generate_children(var + 1, domains, actions, applicable_actions)

        selector_node = SelectorNode(var, [])
        all_current_applicable = []
        for value in range(domain):
            current_applicable_actions = get_actions_with_var_in_pre(var, value, actions, applicable_actions)
            all_current_applicable += current_applicable_actions
            child = generate_children(var + 1, domains, actions, current_applicable_actions)
            selector_node.children.append(child)
        inapplicable = [a for a in applicable_actions if a not in all_current_applicable]
        child = generate_children(var + 1, domains, actions, inapplicable)
        selector_node.children.append(child)
        return selector_node
    else:
        return GeneratorNode(applicable_actions)


def get_applicable_from_tree(node, state):
    if isinstance(node, SelectorNode):
        return (get_applicable_from_tree(node.children[state[node.selection_variable]], state) +
                get_applicable_from_tree(node.children[-1], state))
    else:
        return node.generated_operators


def print_node(node):
    if isinstance(node, SelectorNode):
        print(node.selection_variable, len(node.children))
        for child in node.children:
            print_node(child)
    elif isinstance(node, GeneratorNode):
        print(node.generated_operators)


class SuccessorGenerator:
    def __init__(self, num_variables, facts, actions):
        self.actions = actions
        domains = [set() for v in range(num_variables)]
        for var, value in facts:
            domains[var].add(value)
        domains = [max(domain) + 1 for domain in domains]
        self.root = generate_children(0, domains, actions, list(range(len(actions))))

    def get_applicable(self, state):
        applicable = get_applicable_from_tree(self.root, state)
        applicable_actions = []
        for index in applicable:
            name, cost, prevail, effect = self.actions[index]
            next_state = list(state)
            for var_index, change_from, change_to in effect:
                next_state[var_index] = change_to
            applicable_actions.append((name, cost, tuple(next_state)))
        return applicable_actions


class HeuristicName(str, Enum):
    HMAX = 'hmax'
    LMCUT = 'lmcut'


def main(args: argparse.Namespace):
    input_file_name = args.input
    heuristic_name = args.heuristic.value
    parser = SasParser(input_file_name)
    num_variables, initial_values, goal_state, actions = parser.parse()
    facts, str_actions, str_initial_state, str_goal_state, pre_to_actions = fdr_to_strips_plus(
        actions, initial_values, goal_state
    )

    successor_generator = SuccessorGenerator(num_variables, facts, actions)

    def is_goal(state):
        for var_index, value in goal_state:
            if state[var_index] != value:
                return False
        return True

    def get_applicable(state):
        applicable1 = successor_generator.get_applicable(state)
        return applicable1

    def h_max_heuristic(state):
        s = {(var_index, value) for var_index, value in enumerate(state)}
        return compute_h_max(facts, str_actions, s, str_goal_state, pre_to_actions)

    def h_lm_cut_heuristic(state):
        s = {(var_index, value) for var_index, value in enumerate(state)}
        h_lmcut = compute_h_lm_cut(facts, str_actions, s, str_goal_state, pre_to_actions)
        return h_lmcut

    if heuristic_name == HeuristicName.HMAX:
        path, total_cost = a_star(tuple(initial_values), is_goal, get_applicable, h_max_heuristic)
    elif heuristic_name == HeuristicName.LMCUT:
        path, total_cost = a_star(tuple(initial_values), is_goal, get_applicable, h_lm_cut_heuristic)
    else:
        assert False, 'unreachable'

    for action in path:
        print(action)

    print(f'Plan cost: {total_cost}')


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument(
        '--input', '-i', type=str,
        help='Path to a file containing the SAS representation of the task',
        required=True
    )
    parser.add_argument(
        '--heuristic', type=HeuristicName,
        choices=[heuristic_name.value for heuristic_name in HeuristicName],
        help='The type of heuristic to use',
        required=True
    )
    main(parser.parse_args())
