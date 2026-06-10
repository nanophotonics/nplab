from nplab.measurement import *
import h5py

class TemplateMeasurement(H5Action):

    # =====[ Parameters ]========================================================================
    # Define your measurement parameters here. The syntax is as follows:
    #
    # name = Parameter[datatype](name = "...", defaultValue = ..., [type = ...], [options = [...]])
    #
    # Examples:
    #
    # voltages = Parameter[List[float]](name = "Voltages [V]", defaultValue = [0,1,2,3,4,5])
    # delay    = Parameter[int](name = "Delay Time", defaultValue = 500, type = Type.TIME)
    # type     = Parameter[str](name = "Sweep Type", defaultValue = "Voltage", options = ["Voltage", "Current", "Power"])
    #
    # These can then be accessed within the methods below via "self"
    # ===========================================================================================

    # =====[ Instruments ]=======================================================================
    # Define the instruments needed for this measurement here. The syntax is as follows:
    #
    # name = Instrument[type](name = "...", required = True/False)
    #
    # Examples:
    #
    # voltSource = Instrument[VSource](name = "Voltage Source", required = True)
    # currMeter  = Instrument[IMeter](name = "Ammeter", required = True)
    # camera     = Instrument[Camera](name = "Camera", required = False)
    #
    # Thsese can then be accessed within the methods below via "self"
    # ===========================================================================================

    def __init__(self, description):
        # Define what you want the human-readable name of this measurement type to be
        super().__init__("Measurement Name Here", description)

    
    def main(self, data: h5py.Group = None) -> Result[h5py.Group]:
        # Write your measurement code here, using the parameters and instruments defined above
        pass


    def finish(self, data: h5py.Group = None):
        # Write code that you want to be always called when the measurement has finished here
        pass

