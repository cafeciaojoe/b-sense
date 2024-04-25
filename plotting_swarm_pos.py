import time
import numpy as np

import cflib.crtp
from cflib.crazyflie.swarm import CachedCfFactory
from cflib.crazyflie.swarm import Swarm

import pyqtgraph as pg
import pyqtgraph.opengl as gl
from pyqtgraph import functions as fn
from pyqtgraph.Qt import QtCore

uris = {
    'radio://0/80/2M/E7E7E7E703',
    'radio://0/80/2M/E7E7E7E704',
    # Add more URIs if you want more copters in the swarm
}

app = pg.mkQApp("GLScatterPlotItem Example")
w = gl.GLViewWidget()
w.show()
w.setWindowTitle('pyqtgraph example: GLScatterPlotItem')
w.setCameraPosition(distance=10)

g = gl.GLGridItem()
w.addItem(g)

md = gl.MeshData.sphere(rows=4, cols=8, radius=.1)
m1 = gl.GLMeshItem(meshdata=md, smooth=False, drawFaces=False, drawEdges=True, edgeColor=(1, 1, 1, 1))
w.addItem(m1)

axisitem = gl.GLAxisItem()
w.addItem(axisitem)

def updatePlot(pos_dict):
    pos_d=pos_dict.get("markers")
    print(pos_d)

    m1.translate(pos_d[0], pos_d[1], pos_d[2])
    # sp1.setData(pos=pos)

class DataSource(QtCore.QObject):
    """Object representing a complex data producer."""
    new_data = QtCore.pyqtSignal(dict)
    finished = QtCore.pyqtSignal()

    def __init__(self, num_iterations=1000, parent=None):
        super().__init__(parent)
        self._should_end = False
        self._count = 0
        self._num_iters = num_iterations
        self._marker_data = [0,0,0]


    def run_data_collection(self):
        if self._should_end or self._count >= self._num_iters:
            print("Data source finishing")
            self.finished.emit()
            return

        #position data is collected from the swarm
        collected_data = swarm.get_estimated_positions()

        #data is processed (so it can be fed to the graph)
        processed_data = self._process_marker_data(self._count, collected_data)
        self._count += 1

        data_dict = {
            "markers": processed_data,
        }
        self.new_data.emit(data_dict)
        QtCore.QTimer.singleShot(0,self.run_data_collection)

    def _process_marker_data(self, count, collected_data):
        pos = collected_data['radio://0/80/2M/E7E7E7E703']
        xn = pos.x
        yn = pos.y
        zn = pos.z
        new_pos = np.array([xn, yn, zn])

        current_pos_4x4 = pg.transformToArray(m1.transform())
        xc = current_pos_4x4[(0, 3)]
        yc = current_pos_4x4[(1, 3)]
        zc = current_pos_4x4[(2, 3)]
        current_pos = np.array([xc, yc, zc])

        pos_d = np.subtract(new_pos, current_pos)

        self._marker_data[0] = pos_d[0]
        self._marker_data[1] = pos_d[1]
        self._marker_data[2] = pos_d[2]

        return self._marker_data.copy()

    def stop_data(self):
        print("Data source is quitting...")
        self._should_end = True

if __name__ == '__main__':
    cflib.crtp.init_drivers()
    factory = CachedCfFactory(rw_cache='./cache')

    with Swarm(uris, factory=factory) as swarm:
        swarm.reset_estimators()
        data_thread = QtCore.QThread(parent=w)
        data_source = DataSource()
        data_source.moveToThread(data_thread)
        # update the visualization when there is new data
        data_source.new_data.connect(updatePlot)
        # start data generation when the thread is started
        data_thread.started.connect(data_source.run_data_collection)
        # if the data source finishes before the window is closed, kill the thread
        # to clean up resources
        data_source.finished.connect(data_thread.quit)
        # when the thread has ended, delete the data source from memory
        data_thread.finished.connect(data_source.deleteLater)

        data_thread.start()
        pg.exec()

        # if the window is closed, tell the data source to stop
        # w.closing.connect(data_source.stop_data)
        data_source.stop_data()

        print("Waiting for data source to close gracefully...")
        data_thread.quit()
        data_thread.wait(5000)
        print("see ya ")
