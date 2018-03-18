from si_prefix import si_format
from collections import defaultdict

from sel4_types import *

class TraceEvent(object):
    def __init__(self, name, detail_text, start_time, end_time=None, cpu_id=None, exit_id=None, fault=False):
        self.name = name
        self.detail_text = detail_text
        self.start_time = start_time
        self.end_time = end_time
        self.cpu_id = cpu_id
        self.exit_id = exit_id
        self.fault = fault

class Task(object):
    def __init__(self, name, budget, period):
        self.name = name
        self.budget = budget
        self.period = period

def group_events(events):
    """Sort trace events by name, forming a dictionary of event lists under each name sorted by start time"""
    event_groups = defaultdict(list)
    for event in events:
        event_groups[event.name].append(event)
    for group_name in event_groups.keys():
        event_groups[group_name] = sorted(event_groups[group_name], key=lambda e: e.start_time)
    return event_groups


def print_time(t):
    return si_format(t, precision=3) + 's'

clock_speed = 498000000

def populate_events(file_name):
    final_event_time = None
    trace_events = []
    tasks = [Task('task 0', 0.45, 2.0), Task('task 1', 0.5, 0.7)]
    with open(file_name, 'r') as f:
        first_event = None
        for line in f.readlines():

            values = tuple(line.strip().split(','))

            (log_id, cpu_id, start, duration, path, path_word,
                exit_tcb_addr, exit_tcb_name, fault) = values

            start = float(start)/clock_speed
            duration = float(duration)/clock_speed

            if first_event is None:
                first_event = start

            start -= first_event

            # Always update this in case it's the 'last' event
            final_event_time = start + duration

            path_info = decode_kernel_path(KernelEntryType(int(path)), int(path_word, 16))

            exit_tcb_ident = "[0x{}] '{}'".format(exit_tcb_addr, exit_tcb_name)

            def detail(name, value):
                return "<b>{}:</b> {}".format(name, value)

            kernel_details = "<br/>".join([
                    detail("log_id", log_id),
                    detail("cpu_id", cpu_id),
                    detail("path_in", str(KernelEntryType(int(path)))),
                    detail("path_info", path_info),
                    detail("exit_to", exit_tcb_ident),
                    detail("current_fault", str(FaultType(int(fault)))),
                    detail("event_duration", print_time(duration)),
                    ])

            kernel_name = "Kernel"

            # Append the kernel event
            trace_events.append(
                TraceEvent(kernel_name,
                           kernel_details,
                           start,
                           start + duration,
                           int(cpu_id),
                           exit_tcb_ident))

            # Possibly create a thread event if we have older kernel events on the same core
            # TODO: what happens with sched context donation?
            local_trace_events = filter(lambda e: e.cpu_id == int(cpu_id), trace_events)
            local_kernel_events = list(filter(lambda e: e.name == kernel_name, local_trace_events))
            if len(local_kernel_events) > 1:
                last_kernel_event = local_kernel_events[-2]

                thread_name = last_kernel_event.exit_id
                thread_start = last_kernel_event.end_time
                thread_stop = start # of the current kernel event

                thread_details = "<br/>".join([
                        detail("log_id", log_id + "*"),
                        detail("cpu_id", cpu_id),
                        detail("path_out", str(KernelEntryType(int(path)))),
                        detail("fault_out", str(FaultType(int(fault)))),
                        detail("next_thread", exit_tcb_ident), # next thread on the this core
                        detail("event_duration", print_time(thread_stop - thread_start)),
                        ])

                fault = FaultType(int(fault)) is not FaultType.NullFault

                trace_events.append(
                    TraceEvent(thread_name,
                               thread_details,
                               thread_start,
                               thread_stop,
                               None, None, fault))

    return (trace_events, final_event_time, tasks)
