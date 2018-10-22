class Task(object):
    """Helper to store sporadic task parameters"""
    def __init__(self, name, budget, period):
        self.name = name
        self.budget = budget
        self.period = period

# Change these depending on how your system 'should' behave
# TODO: Autogen from extra info at start of scheduling dump?
RT_TASKS = [Task('C0T0', 0, 0.08), Task('C0T1', 0, 0.05),
            Task('C0T2', 0, 0.07), Task('C0T3', 0, 0.07),
            Task('C1T0', 0, 0.01), Task('C1T1', 0, 0.01),
            Task('C1T2', 0, 0.02), Task('C1T3', 0, 0.03)]
