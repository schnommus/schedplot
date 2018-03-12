#!/bin/python3

import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore
from pyqtgraph.Point import Point

app = QtGui.QApplication([])
win = pg.GraphicsWindow()
win.setWindowTitle('schedplot')
l = pg.GraphicsLayout()
win.setCentralItem(l)

task_info = {
            "Task A": [(0, 2), (3, 4), (7, 7.5)],
            "Task B": [(2, 3), (4, 6)],
            "Task C": [(6, 7), (7.5, 8)]
        }

task_axis = pg.AxisItem(orientation='left')
task_axis.setTicks([
    [(index+0.5, name) for index, name in enumerate(task_info.keys())],
    ])

noscroll_viewbox = pg.ViewBox()
noscroll_viewbox.setMouseEnabled(x=False, y=False)
hscroll_viewbox = pg.ViewBox()
hscroll_viewbox.setMouseEnabled(x=True, y=False)
plot_upper = l.addPlot(row=0, col=0, axisItems={'left': task_axis}, viewBox=hscroll_viewbox)
plot_lower = l.addPlot(row=1, col=0, viewBox=noscroll_viewbox)
l.layout.setRowStretchFactor(0, 3)

region = pg.LinearRegionItem()
region.setZValue(10)
# Add the LinearRegionItem to the ViewBox, but tell the ViewBox to exclude this
# item when doing auto-range calculations.
plot_lower.addItem(region, ignoreBounds=True)

plot_upper.setAutoVisible(y=True)

def plot_data(plot_target):
    n_tasks = len(task_info)
    y_offset = 0
    for task_name in task_info.keys():
        all_begs = []
        all_ends = []
        for entry in task_info[task_name]:
            all_begs.append(entry[0])
            all_ends.append(entry[1])
        colour = pg.hsvColor(y_offset/n_tasks)
        task_bars = pg.BarGraphItem(x0=all_begs, x1=all_ends, height=1, y0=[y_offset]*len(all_begs), brush=colour)
        y_offset += 1
        plot_target.addItem(task_bars)

plot_data(plot_upper)
plot_data(plot_lower)

def update():
    region.setZValue(10)
    minX, maxX = region.getRegion()
    plot_upper.setXRange(minX, maxX, padding=0)

region.sigRegionChanged.connect(update)

def updateRegion(window, viewRange):
    rgn = viewRange[0]
    region.setRegion(rgn)

plot_upper.sigRangeChanged.connect(updateRegion)

region.setRegion([1, 2])

## Start Qt event loop unless running in interactive mode or using pyside.
if __name__ == '__main__':
    import sys
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
