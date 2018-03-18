#!/bin/python3

import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore
from pyqtgraph.Point import Point

from trace_events import *

app = QtGui.QApplication([])
win = pg.GraphicsWindow()
win.setWindowTitle('schedplot')
layout = pg.GraphicsLayout()
win.setCentralItem(layout)

(trace_events, final_event_time, tasks) = populate_events('sample.txt')

def create_time_axis():
    time_axis = pg.AxisItem(orientation='bottom')
    time_axis.setLabel(units='S')
    time_axis.enableAutoSIPrefix(True)
    return time_axis

def create_event_axis(grouped_events):
    task_axis = pg.AxisItem(orientation='left')
    task_axis.setTicks([
        [(index+0.5, name.replace(']', ']\n')) for index, name in enumerate(grouped_events.keys())],
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
noscroll_viewbox.setLimits(xMin=0, xMax=final_event_time)
hscroll_viewbox = pg.ViewBox()
hscroll_viewbox.setMouseEnabled(x=True, y=False)
plot_upper = layout.addPlot(row=0, col=0,
    axisItems={'left': create_event_axis(g_events), 'bottom': create_time_axis()},
    viewBox=hscroll_viewbox)
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

def plot_data(plot_target, grouped_events):
    n_events = len(grouped_events.keys())
    y_offset = 0
    for event_name in grouped_events.keys():
        event_list = grouped_events[event_name]

        if len(event_list) > 0:
            event_plot = None
            fault_plot = None

            all_tags = []

            if event_list[0].end_time is not None:
                all_begs = []
                all_ends = []
                all_faults = []
                for e in event_list:
                    all_begs.append(e.start_time)
                    all_ends.append(e.end_time)
                    if e.fault:
                        all_faults.append(e.end_time)
                    if e.tag is not None:
                        tag = pg.TextItem(anchor=(1, 1), fill=pg.mkBrush(0, 0, 0, 128))
                        tag.setPos(e.end_time, y_offset)
                        tag.setText(e.tag)
                        all_tags.append(tag)
                colour = pg.hsvColor(y_offset/n_events)
                event_plot = pg.BarGraphItem(x0=all_begs, x1=all_ends, height=1, y0=[y_offset]*len(all_begs), brush=colour)
                y_points = [y_offset+0.5]*len(all_faults)
                fault_plot = pg.ScatterPlotItem(x=all_faults, y=y_points, brush='r', size=20, symbol='x')
            else:
                all_begs = []
                for e in event_list:
                    all_begs.append(e.start_time)
                colour = pg.hsvColor(y_offset/n_events)
                y_points = [y_offset+0.5]*len(all_begs)
                event_plot = pg.ScatterPlotItem(x=all_begs, y=y_points, brush=colour, size=20, symbol='t')

            plot_target.addItem(event_plot)

            if fault_plot is not None:
                plot_target.addItem(fault_plot)

            for tag in all_tags[0:200]:
                plot_target.addItem(tag)

            # Plot task parameter arrows (deadlines)
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
<span style='font-size: 10pt; color: white'><b>%s</b></span> <br/>
<span style='font-size: 8pt; color: white'>%s</span>
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
