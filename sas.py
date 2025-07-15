class SasParser:
    """
    The SAS file representation parser
    """
    def __init__(self, sas_file_name):
        """
        Initialize a new SAS parser with the contents of the provided file.
        :param sas_file_name: path to the file containing the SAS problem
        """
        with open(sas_file_name, 'rt') as f:
            self.lines = list(f)

    def _eat_line(self):
        """
        Consume a line from the loaded lines.
        :return: the consumed line, or empty string if there are no lines left
        """
        if self.lines:
            line = self.lines[0].strip()
            self.lines = self.lines[1:]
            return line
        else:
            return ''

    def _parse_header(self):
        """
        Parse the initial SAS file header.
        :return: the version number and a flag indicating whether action costs are used
        """
        assert self._eat_line() == 'begin_version'
        version_number = int(self._eat_line())
        assert self._eat_line() == 'end_version'
        assert self._eat_line() == 'begin_metric'
        uses_action_costs = self._eat_line() == '1'
        assert self._eat_line() == 'end_metric'
        return version_number, uses_action_costs

    def _parse_variables(self):
        """
        Parse the variables section.
        :return: the number of variables
        """
        num_variables = int(self._eat_line())
        for var_index in range(num_variables):
            assert self._eat_line() == 'begin_variable'
            _var_name = self._eat_line()
            _axiom_layer = self._eat_line()
            var_range = int(self._eat_line())
            for i in range(var_range):
                _value_name = self._eat_line()
            assert self._eat_line() == 'end_variable'
        return num_variables

    def _parse_mutex_groups(self):
        """
        Parse the mutex groups section.
        """
        num_mutex_groups = int(self._eat_line())
        for i in range(num_mutex_groups):
            assert self._eat_line() == 'begin_mutex_group'
            num_facts = int(self._eat_line())
            for j in range(num_facts):
                self._eat_line()
            assert self._eat_line() == 'end_mutex_group'

    def _parse_initial_state(self, num_variables):
        """
        Parse the initial state section.
        :param num_variables: the number of variables in the problem
        :return: a list containing the initial value for each variable
        """
        initial_values = []
        assert self._eat_line() == 'begin_state'
        for i in range(num_variables):
            initial_values.append(int(self._eat_line()))
        assert self._eat_line() == 'end_state'
        return initial_values

    def _parse_goal_state(self):
        """
        Parse the goal state section.
        :return: a list containing the assignments to variables in the goal state
        """
        assert self._eat_line() == 'begin_goal'
        num_assignments = int(self._eat_line())
        assignments = []
        for i in range(num_assignments):
            var_index, value = self._eat_line().split(' ')
            var_index = int(var_index)
            value = int(value)
            assignments.append((var_index, value))
        assert self._eat_line() == 'end_goal'
        return assignments

    def _parse_actions(self):
        """
        Parse the operators section.
        :return: a list containing the action name, cost, prevailing variables and effect variables tuple.
        """
        num_actions = int(self._eat_line())
        actions = []
        for i in range(num_actions):
            assert self._eat_line() == 'begin_operator'
            action_name = self._eat_line()

            num_prevailing_var = int(self._eat_line())
            prevailing_vars = []
            for j in range(num_prevailing_var):
                var_index, value = self._eat_line().split(' ')
                var_index = int(var_index)
                value = int(value)
                prevailing_vars.append((var_index, value))

            num_effect_var = int(self._eat_line())
            effect_vars = []
            for j in range(num_effect_var):
                _, effected_var, changed_from, changed_to = self._eat_line().split(' ')
                effected_var = int(effected_var)
                changed_from = int(changed_from)
                changed_to = int(changed_to)
                effect_vars.append((effected_var, changed_from, changed_to))

            action_cost = int(self._eat_line())
            assert self._eat_line() == 'end_operator'
            actions.append((action_name, action_cost, prevailing_vars, effect_vars))
        return actions

    def parse(self):
        """
        Parse the whole file.
        :return: the number of variables, the initial state, goal state and the list of actions
        """
        version_number, uses_action_costs = self._parse_header()
        assert version_number == 3
        num_variables = self._parse_variables()
        self._parse_mutex_groups()
        initial_values = self._parse_initial_state(num_variables)
        goal_state = self._parse_goal_state()
        actions = self._parse_actions()
        return num_variables, initial_values, goal_state, actions


def fdr_to_strips_plus(
        actions,
        initial_state,
        goal_state
):
    """
    Convert the original FDR task into a STRIPS task with actions' delete effects removed.
    :param actions: the FDR actions
    :param initial_state: the FDR initial state
    :param goal_state: the FDR goal state
    :return:
    """
    strips_initial_state = set(enumerate(initial_state))
    strips_goal_state = set(goal_state)

    strips_variables = strips_initial_state.union(strips_goal_state)

    strips_actions = []
    for name, cost, prevailing_vars, effected_vars in actions:
        pre = set(prevailing_vars)
        pre.update((var_index, changed_from) for var_index, changed_from, changed_to in effected_vars if changed_from != -1)
        add = set((var_index, changed_to) for var_index, changed_from, changed_to in effected_vars)

        strips_actions.append((pre, add, cost))

        strips_variables.update(pre)
        strips_variables.update(add)

    strips_variables = list(strips_variables)
    pre_to_actions = {f: [] for f in strips_variables}

    for i, (pre, add, cost) in enumerate(strips_actions):
        for f in pre:
            pre_to_actions[f].append(i)

    return strips_variables, strips_actions, strips_initial_state, strips_goal_state, pre_to_actions
