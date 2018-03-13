#!/bin/python3

import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore
from pyqtgraph.Point import Point
from enum import Enum
from collections import defaultdict

data = """0,kernel,1,2957114191,2957118726
0,ff277500,1,2957118726,2957143504
1,kernel,5,2957143504,2957205260
1,f7fee100,5,2957205260,2975324079
2,kernel,0,2975324079,2975388561
2,ff106100,0,2975388561,2978085793
3,kernel,0,2978085793,2978169383
3,ff277500,0,2978169383,2978191917
4,kernel,5,2978191917,2978257820
4,f7fee900,5,2978257820,2999130046
5,kernel,0,2999130046,2999188907
5,ff277500,0,2999188907,2999204300
6,kernel,5,2999204300,2999263193
6,f7feed00,5,2999263193,3000249042
7,kernel,0,3000249042,3000303147
7,ff106100,0,3000303147,3020141288
8,kernel,0,3020141288,3020204600
8,ff277500,0,3020204600,3020220879
9,kernel,5,3020220879,3020284518
9,f7fee500,5,3020284518,3025170573
10,kernel,0,3025170573,3025224506
10,ff106100,0,3025224506,3041156048
11,kernel,0,3041156048,3041224328
11,ff277500,0,3041224328,3041238579
12,kernel,5,3041238579,3041297147
12,f7fee100,5,3041297147,3050098330
13,kernel,0,3050098330,3050151670
13,ff106100,0,3050151670,3062174831
14,kernel,0,3062174831,3062250081
14,ff277500,0,3062250081,3062269551
15,kernel,5,3062269551,3062332452
15,f7fee900,5,3062332452,3075024964
16,kernel,0,3075024964,3075084766
16,ff106100,0,3075084766,3083206039
17,kernel,0,3083206039,3083266269
17,ff277500,0,3083266269,3083281411
18,kernel,5,3083281411,3083338861
18,f7feed00,5,3083338861,3099967194
19,kernel,0,3099967194,3100011854
19,ff106100,0,3100011854,3104212852
20,kernel,0,3104212852,3104278670
20,ff277500,0,3104278670,3104293838
21,kernel,5,3104293838,3104352250
21,f7fee500,5,3104352250,3124894856
22,kernel,0,3124894856,3124963991
22,ff106100,0,3124963991,3125228929
23,kernel,0,3125228929,3125311134
23,ff277500,0,3125311134,3125331682
24,kernel,5,3125331682,3125396123
24,f7fee100,5,3125396123,3146282164
25,kernel,0,3146282164,3146402364
25,ff277500,0,3146402364,3146431342
26,kernel,5,3146431342,3146496983
26,f7fee900,5,3146496983,3149821982
27,kernel,0,3149821982,3149883230
27,ff106100,0,3149883230,3167373224
28,kernel,0,3167373224,3167451004
28,ff277500,0,3167451004,3167470845
29,kernel,5,3167470845,3167534247
29,f7feed00,5,3167534247,3174746980
30,kernel,0,3174746980,3174807784
30,ff106100,0,3174807784,3188407219
31,kernel,0,3188407219,3188467115
31,ff277500,0,3188467115,3188481282
32,kernel,5,3188481282,3188541926
32,f7fee500,5,3188541926,3199671360
33,kernel,0,3199671360,3199723558
33,ff106100,0,3199723558,3209415978
34,kernel,0,3209415978,3209480811
34,ff277500,0,3209480811,3209489343"""

app = QtGui.QApplication([])
win = pg.GraphicsWindow()
win.setWindowTitle('schedplot')
layout = pg.GraphicsLayout()
win.setCentralItem(layout)

class KernelEntryType(Enum):
    Interrupt = 0,
    UnknownSyscall = 1,
    UserLevelFault = 2,
    DebugFault = 3,
    VMFault = 4,
    Syscall = 5,
    UnimplementedDevice = 6,

class TraceEvent(object):
    def __init__(self, name, detail_text, start_time, end_time=None):
        self.name = name
        self.detail_text = detail_text
        self.start_time = start_time
        self.end_time = end_time


trace_events = [
            TraceEvent("Task A", "yep, task A", 0, 2),
            TraceEvent("Task A", "yep, task A", 3, 4),
            TraceEvent("Task A", "yep, task A", 7, 7.5),
            TraceEvent("Task B", "yep, task B", 2, 3),
            TraceEvent("Task B", "yep, task B", 4, 6),
            TraceEvent("Task C", "yep, task C", 6, 7),
            TraceEvent("Task C", "yep, task C", 7.5, 8),
            TraceEvent("Interrupt", "yep, irq1", 4.5),
            TraceEvent("Interrupt", "yep, irq2", 5),
            ]

trace_events = []
first_event = None
for line in data.split('\n'):
    log_id, name, path, start, stop = tuple(line.split(','))
    start = float(start)/1000000000
    stop = float(stop)/1000000000
    if first_event is None:
        first_event = start

    start -= first_event
    stop -= first_event

    trace_events.append(TraceEvent(name, "N: %s - P: %s" % (log_id, path), start, stop))

def group_events(events):
    """Sort trace events by name, forming a dictionary of event lists under each name sorted by start time"""
    event_groups = defaultdict(list)
    for event in events:
        event_groups[event.name].append(event)
    for group_name in event_groups.keys():
        event_groups[group_name] = sorted(event_groups[group_name], key=lambda e: e.start_time)
    return event_groups

def create_event_axis(grouped_events):
    task_axis = pg.AxisItem(orientation='left')
    task_axis.setTicks([
        [(index+0.5, name) for index, name in enumerate(grouped_events.keys())],
        ])
    return task_axis

def get_event_at(x, y, grouped_events):
    """Given a position on the graph, find the event at that position"""
    event_index = round(y-0.5)
    if event_index >= 0 and event_index < len(grouped_events.keys()):
        candidate_events = grouped_events[list(grouped_events.keys())[event_index]]
        if len(candidate_events) > 0:
            if candidate_events[0].end_time is not None:
                # If this set has end times, find something that matches
                return next(filter(lambda e: x > e.start_time and x < e.end_time, candidate_events), None)
            else:
                # No end time, just pick the closest
                return min(candidate_events, key=lambda e: abs(e.start_time - x))

    return None

g_events = group_events(trace_events)

noscroll_viewbox = pg.ViewBox()
noscroll_viewbox.setMouseEnabled(x=False, y=False)
hscroll_viewbox = pg.ViewBox()
hscroll_viewbox.setMouseEnabled(x=True, y=False)
plot_upper = layout.addPlot(row=0, col=0, axisItems={'left': create_event_axis(g_events)}, viewBox=hscroll_viewbox)
plot_lower = layout.addPlot(row=1, col=0, viewBox=noscroll_viewbox)
layout.layout.setRowStretchFactor(0, 3)

region = pg.LinearRegionItem()
region.setZValue(10)
# Add the LinearRegionItem to the ViewBox, but tell the ViewBox to exclude this
# item when doing auto-range calculations.
plot_lower.addItem(region, ignoreBounds=True)

plot_upper.setAutoVisible(y=True)

def plot_data(plot_target, grouped_events):
    n_events = len(grouped_events.keys())
    y_offset = 0
    for event_name in grouped_events.keys():
        event_list = grouped_events[event_name]
        if len(event_list) > 0:
            event_plot = None

            if event_list[0].end_time is not None:
                all_begs = []
                all_ends = []
                for e in event_list:
                    all_begs.append(e.start_time)
                    all_ends.append(e.end_time)
                colour = pg.hsvColor(y_offset/n_events)
                event_plot = pg.BarGraphItem(x0=all_begs, x1=all_ends, height=1, y0=[y_offset]*len(all_begs), brush=colour)
            else:
                all_begs = []
                for e in event_list:
                    all_begs.append(e.start_time)
                colour = pg.hsvColor(y_offset/n_events)
                y_points = [y_offset+0.5]*len(all_begs)
                event_plot = pg.ScatterPlotItem(x=all_begs, y=y_points, brush=colour, size=20, symbol='t')

            plot_target.addItem(event_plot)
            y_offset += 1

plot_data(plot_upper, g_events)
plot_data(plot_lower, g_events)

tooltip = pg.TextItem(anchor=(1, 1), fill=pg.mkBrush(0, 0, 0, 128))
tooltip.setPos(0, 0)
plot_upper.addItem(tooltip)

def update():
    region.setZValue(10)
    minX, maxX = region.getRegion()
    plot_upper.setXRange(minX, maxX, padding=0)
    plot_upper.setYRange(0, len(g_events.keys()), padding=0)

region.sigRegionChanged.connect(update)

def updateRegion(window, viewRange):
    rgn = viewRange[0]
    region.setRegion(rgn)

plot_upper.sigRangeChanged.connect(updateRegion)

region.setRegion([1, 2])

tooltip_format = """
<span style='font-size: 12pt; color: white'>%s</span> <br/>
<span style='font-size: 10pt; color: white'>%s</span>
"""

def mouseMoved(evt):
    pos = evt[0]  ## using signal proxy turns original arguments into a tuple
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

proxy = pg.SignalProxy(plot_upper.scene().sigMouseMoved, rateLimit=60, slot=mouseMoved)

## Start Qt event loop unless running in interactive mode or using pyside.
if __name__ == '__main__':
    import sys
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
