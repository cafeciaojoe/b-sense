import time
import numpy as np

import cflib.crtp
from cflib.crazyflie.swarm import CachedCfFactory
from cflib.crazyflie.swarm import Swarm
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncLogger import SyncLogger

import pyqtgraph as pg
import pyqtgraph.opengl as gl
from pyqtgraph import functions as fn
from pyqtgraph.Qt import QtCore


uris = [
    'radio://0/80/2M/E7E7E7E703',
    'radio://0/80/2M/E7E7E7E704',
    # Add more URIs if you want more copters in the swarm
]

# setting up the plotting area.
app = pg.mkQApp("GLScatterPlotItem Example")
w = gl.GLViewWidget()
w.show()
w.setWindowTitle('pyqtgraph example: GLScatterPlotItem')
w.setCameraPosition(distance=10)
g = gl.GLGridItem()
w.addItem(g)
axisitem = gl.GLAxisItem()
w.addItem(axisitem)

# the tye and size of the mesh
md = gl.MeshData.sphere(rows=2, cols=3, radius=.1)


def make_uri_mesh_dict(uris):
    #for every uri, make and add the mesh item, store the uri and the item in a dict, retur the dict
    _dict = {}
    for i in range(0,len(uris)):
        _dict[uris[i]] = gl.GLMeshItem(meshdata=md, smooth=False, drawFaces=False, drawEdges=True, edgeColor=(1, 1, 1, 1))
        w.addItem(_dict[uris[i]])
        # this line is for debugging, just to check that they have been added.
        _dict[uris[i]].translate(i,i,i)
        #print(_dict)
    return _dict

class DataSource(QtCore.QObject):
    """Object representing a complex data producer."""
    new_data = QtCore.pyqtSignal(dict)
    finished = QtCore.pyqtSignal()

    def __init__(self, num_iterations=1000, parent=None):
        super().__init__(parent)
        self._should_end = False
        self._count = 0
        self._num_iters = num_iterations

    def run_data_collection(self):
        swarm.parallel_safe(self.log_sync)
        print("Data source finishing")
        self.finished.emit()

    # there is one log_sync function running for every crazyflie.
    def log_sync(self, scf):
        lg_vars = {
            'stateEstimate.x': 'float',
            'stateEstimate.y': 'float',
            'stateEstimate.z': 'float',
            'stateEstimate.roll': 'float',
            'stateEstimate.pitch': 'float',
            'stateEstimate.yaw': 'float',
        }

        lg_stab = LogConfig(name='Position', period_in_ms=100)
        for key in lg_vars:
            #add each variable to the logconfig
            lg_stab.add_variable(key, lg_vars[key])

        _dict = {}
        with SyncLogger(scf, lg_stab) as logger:
            endTime = time.time() + 10
            for log_entry in logger:
                #package the data into a dictionary of arrays, send dict to other thread
                uri = scf.cf.link_uri
                timestamp = log_entry[0]
                data = log_entry[1]
                _array = np.empty(0)
                # turn the 6 log entries into a 1 x 6 np array
                for key in data:
                    #print(data[key])
                    _array = np.concatenate((_array,[data[key]]))
                _dict[uri] = _array
                self.new_data.emit(_dict)
                # the function passed in below is the one that triggers the timer.
                QtCore.QTimer.singleShot(0,self.log_sync)

                if time.time() > endTime or self._should_end is True:
                    break

    def _process_marker_data(self, count, collected_data):
        # TODO unpack (maybe not even) arrays, copy, perform operations, send copy
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

def updatePlot(pos_dict):
    # TODO use uri_pos_dict to reference uri_mesh dict and update graph.
    print(pos_dict)



    #uri=pos_dict.get("uri")
    #m1.translate(pos_d[0], pos_d[1], pos_d[2])
    # sp1.setData(pos=pos)

if __name__ == '__main__':
    uri_mesh_dict = make_uri_mesh_dict(uris)
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

        print("Waiting for data source thread to close gracefully...")
        data_thread.quit()
        data_thread.wait(5000)
        print("see ya ")
