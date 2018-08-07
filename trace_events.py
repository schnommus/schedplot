from si_prefix import si_format
from collections import defaultdict

from sel4_types import *

class TraceEvent(object):
    def __init__(self, name, detail_text, start_time, end_time=None,
                 cpu_id=None, exit_id=None, fault=False, tag=None):
        self.name = name
        self.detail_text = detail_text
        self.start_time = start_time
        self.end_time = end_time
        self.cpu_id = cpu_id
        self.exit_id = exit_id
        self.fault = fault
        self.tag = tag

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

def populate_events(args):
    final_event_time = None
    trace_events = []
    tasks = [Task('C0T0', 0, 0.08), Task('C0T1', 0, 0.05),
             Task('C0T2', 0, 0.07), Task('C0T3', 0, 0.07),
             Task('C1T0', 0, 0.01), Task('C1T1', 0, 0.01),
             Task('C1T2', 0, 0.02), Task('C1T3', 0, 0.03)]
    basic_stats = defaultdict(float)
    with open(args.in_filename, 'r') as f:
        first_event = None
        for line in f.readlines():

            values = tuple(line.strip().split(','))

            if len(values) == 10:
                (log_id, cpu_id, start, duration, path, path_word,
                    exit_tcb_addr, exit_tcb_name, fault, capreg) = values
            elif len(values) == 5:
                (log_id, cpu_id, start, duration, exit_tcb_addr) = values
                path = "8"
                path_word = "0"
                exit_tcb_name = "U[C{}]".format(cpu_id)
                fault = 7
                capreg = "0"
            else:
                print("Unknown scheduler log format")
                return

            # TODO: this shouldn't be necessary..
            if int(fault) >= 7:
                fault = 7

            if args.isolate_core is not None:
                if int(cpu_id) != args.isolate_core:
                    continue

            start = int(start)
            duration = int(duration)

            if args.modeswitch_entry_overhead is not None:
                start -= args.modeswitch_entry_overhead
                duration += args.modeswitch_entry_overhead

            if args.modeswitch_exit_overhead is not None:
                duration += args.modeswitch_exit_overhead

            start = float(start)/clock_speed
            duration = float(duration)/clock_speed

            if first_event is None:
                first_event = start

            start -= first_event

            # Always update this in case it's the 'last' event
            final_event_time = start + duration

            path_info = decode_kernel_path(
                    KernelEntryType(int(path)), int(path_word, 16), int(capreg, 16))

            path_tag = get_kernel_path_tag(
                    KernelEntryType(int(path)), int(path_word, 16), int(capreg, 16))

            exit_tcb_ident = "[0x{}|'{}']".format(exit_tcb_addr, exit_tcb_name)

            def detail(name, value):
                return "<b>{}:</b> {}".format(name, value)

            basic_stats['kernel_entries'] += 1
            basic_stats['kernel_cumulative_entry_time'] += duration
            basic_stats['kernel_average_entry_time'] = \
                basic_stats['kernel_cumulative_entry_time'] / basic_stats['kernel_entries']

            duration_string = "%s c (%s)" % (int(duration * clock_speed), print_time(duration))

            kernel_details = "<br/>".join([
                    detail("log_id", log_id),
                    detail("cpu_id", cpu_id),
                    detail("path_in", str(KernelEntryType(int(path)))),
                    detail("path_info", path_info),
                    detail("exit_to", exit_tcb_ident),
                    detail("current_fault", str(FaultType(int(fault)))),
                    detail("event_duration", duration_string),
                    ])

            kernel_name = "Kernel [CPU%s]" % cpu_id

            # Append the kernel event
            trace_events.append(
                TraceEvent(kernel_name,
                           kernel_details,
                           start,
                           start + duration,
                           int(cpu_id),
                           exit_tcb_ident,
                           False,
                           path_tag))

            # Possibly create a thread event if we have older kernel events on the same core
            # TODO: what happens with sched context donation?
            local_trace_events = filter(lambda e: e.cpu_id == int(cpu_id), trace_events)
            local_kernel_events = list(filter(lambda e: e.name == kernel_name, local_trace_events))
            if len(local_kernel_events) > 1:
                last_kernel_event = local_kernel_events[-2]
                last_event = local_kernel_events[-2]

                thread_name = last_kernel_event.exit_id
                thread_start = last_kernel_event.end_time
                thread_stop = start # of the current kernel event
                thread_duration = thread_stop - thread_start
                thread_duration_string = "%s c (%s)" % (int(thread_duration * clock_speed), print_time(thread_duration))

                thread_details = "<br/>".join([
                        detail("log_id", log_id + "*"),
                        detail("cpu_id", cpu_id),
                        detail("path_out", str(KernelEntryType(int(path)))),
                        detail("fault_out", str(FaultType(int(fault)))),
                        detail("next_thread", exit_tcb_ident), # next thread on the this core
                        detail("event_duration", thread_duration_string),
                        ])

                fault = FaultType(int(fault)) is not FaultType.NullFault

                actually_add_event = True

                for ignore_name in args.ignore_threads:
                    if ignore_name in thread_name:
                        actually_add_event = False

                if args.keep_threads != []:
                    actually_add_event = False
                    for keep_name in args.keep_threads:
                        if keep_name in thread_name:
                            actually_add_event = True

                if actually_add_event:
                    trace_events.append(
                        TraceEvent(thread_name,
                                   thread_details,
                                   thread_start,
                                   thread_stop,
                                   None, None, fault))

                    basic_stats[thread_name + '_entries'] += 1
                    basic_stats[thread_name + '_cumulative_entry_time'] \
                            += thread_stop - thread_start
                    basic_stats[thread_name + '_average_entry_time'] = \
                        basic_stats[thread_name + '_cumulative_entry_time'] / \
                            basic_stats[thread_name + '_entries']

    keys = list(basic_stats.keys())
    total_utilization = 0.0
    total_entry_time = 0.0
    for stat in keys:
        key = '_cumulative_entry_time'
        if key in stat:
            stat_name = stat.split('_cumulative_entry_time')[0]
            cumulative_entry_time = basic_stats[stat_name + '_cumulative_entry_time']
            total_entry_time += cumulative_entry_time
            utilization = cumulative_entry_time / final_event_time
            basic_stats[stat_name + '_utilisation'] = utilization
            total_utilization += utilization

    basic_stats['total_utilization'] = total_utilization
    basic_stats['total_entry_time'] = total_entry_time
    basic_stats['final_event_time'] = final_event_time

    for stat in basic_stats.keys():
        value = basic_stats[stat]
        if 'time' in stat:
            value = print_time(value)
        print("{} = {}".format(stat, value))

    return (trace_events, final_event_time, tasks)

