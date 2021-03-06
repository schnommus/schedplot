#!/bin/python3

import sys
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore
from pyqtgraph.Point import Point
import argparse

from trace_events import *

def create_time_axis():
    """Render the time axis using correct SI prefixes"""
    time_axis = pg.AxisItem(orientation='bottom')
    time_axis.setLabel(units='S')
    time_axis.enableAutoSIPrefix(True)
    return time_axis

def sorted_keys(grouped_events):
    """Sort events by thread names"""
    keys = list(grouped_events.keys())
    keys = sorted(keys, key=lambda s: s.split('|')[-1])
    return list(reversed(keys))

def create_event_axis(grouped_events):
    """Prettyprint thread names on x-axis"""
    task_axis = pg.AxisItem(orientation='left')
    task_axis.setTicks([
        [(index+0.5, name.replace('|', '|\n')) for index, name in enumerate(sorted_keys(grouped_events))],
        ])
    return task_axis

def get_event_at(x, y, grouped_events):
    """Given a position on the graph, find the event at that position"""
    event_index = round(y-0.5)
    if event_index >= 0 and event_index < len(grouped_events.keys()):
        candidate_events = grouped_events[sorted_keys(grouped_events)[event_index]]
        if len(candidate_events) > 0:
            if candidate_events[0].end_time is not None:
                # If this set has end times, find something that matches
                return next(filter(lambda e: x > e.start_time and x < e.end_time, candidate_events), None)
            else:
                # No end time, just pick the closest
                return min(candidate_events, key=lambda e: abs(e.start_time - x))

    return None

def get_kernel_events_in_range(xmin, xmax, grouped_events):
    """Retrieve all the kernel invocations that occur between 2 time endpoints"""
    kernel_event_titles = filter(lambda x: 'Kernel' in x, sorted_keys(grouped_events))
    events = []
    for title in kernel_event_titles:
        for e in grouped_events[title]:
            if e.end_time > xmin and e.start_time < xmax:
                events.append(e)
    return events

def logbuf_overhead_reality_string(args, selected_region, kernel_events):
    """Compute 'projected' time given sequence of kernel events and a selected region
       Selected region should be from end of last event in first thread to start of first event
       in second thread. Assumes no simultaneous kernel events!"""

    if args.logbuf_overhead is None or args.modeswitch_overhead is None:
        return "unknown overheads!"

    region_cycles = int(selected_region * clock_speed);

    total_logbuf_overhead = 0.0
    n_kernel_entries = 0
    for e in kernel_events:
        total_logbuf_overhead += args.logbuf_overhead
        n_kernel_entries += 1

    reality_cycles = region_cycles - total_logbuf_overhead + args.modeswitch_overhead

    # nsc = null syscalls, klb = kernel log buffer overheads
    return "{} c (1 nsc + {} klb)".format(reality_cycles, n_kernel_entries)


def plot_data(plot_target, grouped_events, tasks, final_event_time, args):
    """Top-level function which actually plots all the trace events. Only needs to be called once"""

    n_events = len(grouped_events.keys())
    y_offset = 0

    # For every thread (including Kernel 0...N)
    for event_name in sorted_keys(grouped_events):
        event_list = grouped_events[event_name]

        # If there are any events
        if len(event_list) > 0:
            event_plot = None
            fault_plot = None

            all_tags = []

            if event_list[0].end_time is not None:
                # It's an event with a duration
                all_begs = []
                all_ends = []
                all_faults = []
                for e in event_list:
                    all_begs.append(e.start_time)
                    all_ends.append(e.end_time)
                    if e.fault:
                        all_faults.append(e.end_time)

                    # This is pretty slow!
                    if args.label_putchar and e.tag is not None:
                        tag = pg.TextItem(anchor=(1, 1), fill=pg.mkBrush(0, 0, 0, 128))
                        tag.setPos(e.end_time, y_offset)
                        tag.setText(e.tag)
                        all_tags.append(tag)

                colour = pg.hsvColor(y_offset/n_events, alpha=1.0)
                event_plot = pg.BarGraphItem(x0=all_begs, x1=all_ends, height=1, y0=[y_offset]*len(all_begs), brush=colour)
                y_points = [y_offset+0.5]*len(all_faults)

                # If this event ends with a fault, plot it
                fault_plot = pg.ScatterPlotItem(x=all_faults, y=y_points, brush='r', size=20, symbol='x')
            else:
                # It's a one-shot event (not currently used)
                all_begs = []
                for e in event_list:
                    all_begs.append(e.start_time)
                colour = pg.hsvColor(y_offset/n_events)
                y_points = [y_offset+0.5]*len(all_begs)
                event_plot = pg.ScatterPlotItem(x=all_begs, y=y_points, brush=colour, size=20, symbol='t')

            plot_target.addItem(event_plot)

            if fault_plot is not None:
                plot_target.addItem(fault_plot)

            if args.label_putchar:
                # Too slow for now
                for tag in all_tags:
                    plot_target.addItem(tag)

            # Plot task parameter arrows (deadlines)
            if args.show_deadlines:
                for task in tasks:
                    if task.name in event_name:
                        values = np.arange(0, final_event_time, task.period)
                        for x in values:
                            a = pg.ArrowItem(angle=-90, tipAngle=45, baseAngle=10,
                                             headLen=13, tailLen=11, tailWidth=4,
                                             pen={'color': 'k', 'width': 1},
                                             brush='w')
                            a.setPos(x, y_offset)
                            plot_target.addItem(a)

            y_offset += 1

def start_application(args):
    (trace_events, final_event_time, tasks) = populate_events(args)

    app = QtGui.QApplication([])
    win = pg.GraphicsWindow()
    win.setWindowTitle('schedplot')
    layout = pg.GraphicsLayout()
    win.setCentralItem(layout)

    g_events = group_events(trace_events)

    # Set up all the view controls
    noscroll_viewbox = pg.ViewBox()
    noscroll_viewbox.setMouseEnabled(x=True, y=False)
    noscroll_viewbox.setLimits(xMin=0, xMax=final_event_time)
    hscroll_viewbox = pg.ViewBox()
    hscroll_viewbox.setMouseEnabled(x=True, y=False)
    plot_upper = layout.addPlot(row=0, col=0,
        axisItems={'left': create_event_axis(g_events), 'bottom': create_time_axis()},
        viewBox=hscroll_viewbox)
    plot_upper.showGrid(x=True)
    plot_lower = layout.addPlot(row=1, col=0, viewBox=noscroll_viewbox)
    layout.layout.setRowStretchFactor(0, 3)

    region = pg.LinearRegionItem()
    region.setZValue(10)
    region.setBounds((0, final_event_time))
    region.setRegion((0, final_event_time))

    # Add the LinearRegionItem to the ViewBox, but tell the ViewBox to exclude this
    # item when doing auto-range calculations.
    plot_lower.addItem(region, ignoreBounds=True)

    plot_upper.setAutoVisible(y=True)

    # Plot main window and minimap
    plot_data(plot_upper, g_events, tasks, final_event_time, args)
    plot_data(plot_lower, g_events, tasks, final_event_time, args)

    # Create the event tooltip
    tooltip = pg.TextItem(anchor=(1, 1), fill=pg.mkBrush(0, 0, 0, 128))
    tooltip.setPos(0, 0)
    plot_upper.addItem(tooltip)

    # Create the overhead estimation box
    span_time = pg.TextItem(anchor=(1, 1), fill=pg.mkBrush(0, 0, 0, 128))
    span_time.setPos(0, 0)
    span_time_format = """
    <span style='font-size: 10pt; color: white'>[selected] <b>%s c</b> (%s)</span> <br/>
    <span style='font-size: 9pt; color: white'>[estimate] <b>%s</b></span>
    """
    span_time.setVisible(True)
    plot_lower.addItem(span_time)

    # Set up GUI callbacks
    def update():
        region.setZValue(10)
        minX, maxX = region.getRegion()
        plot_upper.setXRange(minX, maxX, padding=0)
        plot_upper.setYRange(0, len(g_events.keys()), padding=0)
        plot_lower.setYRange(0, len(g_events.keys()), padding=0)

    region.sigRegionChanged.connect(update)

    def updateRegion(window, viewRange):
        rgn = viewRange[0]
        region.setRegion(rgn)

    plot_upper.sigRangeChanged.connect(updateRegion)

    region.setRegion([1, 2])

    tooltip_format = """
    <span style='font-size: 10pt; color: white'><b>%s</b></span> <br/>
    <span style='font-size: 8pt; color: white'>%s</span>
    """

    # Check for tooltips on trace events
    def mouseUpper(pos):
        if plot_upper.sceneBoundingRect().contains(pos):
            mousePoint = hscroll_viewbox.mapSceneToView(pos)
            event = get_event_at(mousePoint.x(), mousePoint.y(), g_events)

            if event is None:
                tooltip.setVisible(False)
                return

            tooltip.setHtml(tooltip_format % (event.name, event.detail_text))
            tooltip.setPos(mousePoint.x(), mousePoint.y())
            tooltip.setVisible(True)
        else:
            tooltip.setVisible(False)
            return

    # Recalculate overhead accounting results on lower window
    def mouseLower(pos):
        if plot_lower.sceneBoundingRect().contains(pos):
            mousePoint = noscroll_viewbox.mapSceneToView(pos)
            minX, maxX = region.getRegion()
            span_sec = maxX - minX;
            span_cycles = int(span_sec * clock_speed);
            kernel_events = get_kernel_events_in_range(minX, maxX, g_events)
            region_reality_string = logbuf_overhead_reality_string(args, maxX - minX, kernel_events)
            span_time.setHtml(span_time_format % (span_cycles, print_time(span_sec), region_reality_string))
            span_time.setPos(mousePoint.x(), mousePoint.y())
            span_time.setVisible(True)
        else:
            span_time.setVisible(False)
            return

    # Monster to handle all mouse events for upper and lower windows
    def mouseMoved(evt):
        pos = evt[0]  # using signal proxy turns original arguments into a tuple
        mouseUpper(pos)
        mouseLower(pos)

    proxy = pg.SignalProxy(plot_upper.scene().sigMouseMoved, rateLimit=60, slot=mouseMoved)

    ## Start Qt event loop unless running in interactive mode or using pyside.
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()


parser = argparse.ArgumentParser(description='Plot and perform metrics on scheduler dumps')

parser.add_argument('in_filename', help='Filename of scheduler dump to process')
parser.add_argument('--isolate_core', default=None, type=int, help='Only display readings from this core')
parser.add_argument('--ignore_threads', default=[], type=str, nargs='*',
        help="Don't create thread events with these TCB names")
parser.add_argument('--keep_threads', default=[], type=str, nargs='*',
        help="Only create thread events with these TCB names")
parser.add_argument('--label_putchar', dest='label_putchar',
                    default=False, action='store_true', help="Display seL4_DebugPutChar calls inline with scheduling trace")
parser.add_argument('--show_deadlines', dest='show_deadlines',
                    default=False, action='store_true', help="Display sporadic task model implicit deadlines on top of task traces")
parser.add_argument('--modeswitch_overhead', default=None, type=int, help='Measured modeswitch overhead (in + out) in cycles')
parser.add_argument('--logbuf_overhead', default=None, type=int, help='Measured overhead of log buffer (minus modeswitch overhead) in cycles')
parser.add_argument('--clock_speed', default=498000000, type=int, help='CPU clock speed in Hz (498MHz [sabre] default!)')

if __name__ == '__main__':
    args = parser.parse_args()
    start_application(args)
