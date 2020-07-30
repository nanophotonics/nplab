# -*- coding: utf-8 -*-
"""
Created on Tue Mar 21 17:04:11 2017

@author: Will, Yago
"""
from __future__ import division
from __future__ import print_function
from builtins import str
from past.utils import old_div
import serial
import struct
import numpy as np
from nplab.instrument.apt_virtual_com_port import APT_VCP
from nplab.instrument.stage import Stage
from nplab.utils.notified_property import NotifiedProperty, DumbNotifiedProperty, register_for_property_changes
import types
import time

DC_status_motors = {'BBD102/BBD103': [], 'TDC001': []}
DEBUG = False

class APT_parameter(NotifiedProperty):
    """A quick way of creating a property that alters an apt parameter.

    NB the property will be read immediately after it's written, to ensure
    that the value we send to any listening controls/indicators is correct
    (otherwise we'd send them the value that was requested, even if it was
    not valid).  This behaviour can be disabled by setting read_back to False
    in the constructor.
    """

    def __init__(self, parameter_name, doc=None, read_back=True):
        """Create a property that reads and writes the given parameter.

        This internally uses the `get_camera_parameter` and
        `set_camera_parameter` methods, so make sure you override them.
        """
        if doc is None:
            doc = "Adjust the camera parameter '{0}'".format(parameter_name)
        super(APT_parameter, self).__init__(fget=self.fget,
                                            fset=self.fset,
                                            doc=doc,
                                            read_back=read_back)
        self.parameter_name = parameter_name

    def fget(self, obj):
        return obj.get_APT_parameter(self.parameter_name)

    def fset(self, obj, value):
        obj.set_APT_parameter(self.parameter_name, value)


class APT_VCP_motor(APT_VCP, Stage):
    """
    This class handles all the basic communication with APT virtual com for motors
    """

    axis_names = ('x', )
    def __init__(self, port=None, source=0x01, destination=None,
                 use_si_units=False, stay_alive = False, unit = 'm',**kwargs):
        """
        Set up the serial port, setting source and destinations, and hardware info.
        """
        APT_VCP.__init__(self, port=port, source=source, destination=destination,
                         use_si_units=use_si_units, stay_alive=stay_alive)  # this opens the port
        Stage.__init__(self,unit = unit)
        if self.model[1] in DC_status_motors:
            # Set the bit mask for DC controllers
            self.status_bit_mask = np.array([[0x00000001, 'forward hardware limit switch is active'],
                                             [0x00000002, 'reverse hardware limit switch is active'],
                                             [0x00000010, 'in motion, moving forward'],
                                             [0x00000020, 'in motion, moving reverse'],
                                             [0x00000040, 'in motion, jogging forward'],
                                             [0x00000080, 'in motion, jogging reverse'],
                                             [0x00000200, 'in motion, homing'],
                                             [0x00000400, 'homed (homing has been completed)'],
                                             [0x00001000, 'tracking'],
                                             [0x00002000, 'settled'],
                                             [0x00004000, 'motion error (excessive position error)'],
                                             [0x01000000, 'motor current limit reached'],
                                             [0x80000000, 'channel is enabled']])
            self.velocity_scaling_factor = 204.8  # for converting velocity to mm/sec
        else:
            # Set the bit mask for normal motor controllers
            self.status_bit_mask = np.array([[0x00000001, 'forward (CW) hardware limit switch is active'],
                                    [0x00000002, 'reverse (CCW) hardware limit switch is active'],
                                    [0x00000004, 'forward (CW) software limit switch is active'],
                                    [0x00000008, 'reverse (CCW) software limit switch is active'],
                                    [0x00000010, 'in motion, moving forward (CW)'],
                                    [0x00000020, 'in motion, moving reverse (CCW)'],
                                    [0x00000040, 'in motion, jogging forward (CW)'],
                                    [0x00000080, 'in motion, jogging reverse (CCW)'],
                                    [0x00000100, 'motor connected'],
                                    [0x00000200, 'in motion, homing'],
                                    [0x00000400, 'homed (homing has been completed)'],
                                    [0x00001000, 'interlock state (1 = enabled)']])

            # delattr(self, 'get_qt_ui')
        if type(destination) != dict and len(self.destination)==1:
            self.destination = {'x' : destination}
        else:
            self.axis_names = tuple(destination.keys())
            self.destination = destination
        self.make_all_parameters()

    '''MOVEMENT'''

#    def _waitForReply(self, msgCode, replysize):
#        self.write(msgCode)
#        reply = self.ser.read(replysize)
#        t0 = time.time()
#        while len(reply) == replysize:
#            reply = self.ser.read(replysize)
#            time.sleep(0.1)
#            if time.time() - t0 > 30:
#                return False
#        return True

    def _waitFinishMove(self,axis = None,debug=False):
        """A simple function to force movement to block the console """
        if axis == None:
            destination_ids = list(self.destination.keys())
        else:
            destination_ids = [axis]
        for dest in destination_ids:
            status = self.get_status_update(axis = dest)
            if debug > 0 or DEBUG:
                print(status)
            
            while any(['in motion' in x[1] for x in status]):
                time.sleep(0.1)
                status = self.get_status_update(axis = dest)

    def home(self,axis = None):
        """Rehome the stage with an axis input """
        if axis == None:
            destination_ids = self.axis_names
        else:
            destination_ids = tuple(axis)
        for dest in destination_ids:
            self.write(0x0443,destination_id = dest)
    #        self._waitForReply(0x0444, 6)
            self._waitFinishMove()

    def move(self, pos, axis=None, relative=False,channel_number = None,block = True):
        """ Move command allowing specification of axis, 
        relative, channel and if we want the function to be blocking"""
        if channel_number is None:
            channel_number = 1
        if not hasattr(pos, '__iter__'):
            pos = [pos]
        elif type(pos)==tuple:
            pos = list(pos)
        if axis is None:
            if len(pos)==len(self.axis_names):
                axes = self.axis_names
            else:
                self._logger.warn('What axis shall I move?')
        else:
            axes = tuple(axis)
        #create list of positions for each axis
        pos_list = [0]*len(self.axis_names)
        for i,axis  in enumerate(axes):
            axis_number = np.where(np.array(self.axis_names)==[axis])[0][0]
            pos_list[axis_number] = pos[i]
        pos = pos_list
        for axis in axes:
            axis_number = np.where(np.array(self.axis_names)==[axis])[0][0]
            if relative:
                pos[axis_number] = self.position[axis_number]+pos[axis_number]

            pos_in_counts = int(np.round(self.convert(pos[axis_number],'position','counts'),decimals = 0))
            data = bytearray(struct.pack('<HL', self.channel_number_to_identity[channel_number], pos_in_counts))
            try:
                self.write(0x0453, data=data,destination_id=axis)
                if block ==True:
                    self._waitFinishMove()
                self._recusive_move_num = 0
            except struct.error as e:
                self.log('Move failed with '+str(e),'warning')
                self._recusive_move_num+=1
                if self._recusive_move_num>10:
                    raise Exception('Stage mode failed!')
                self.move(pos[axis_number],axis=axis,channel_number=channel_number,block = block)
            axis_number += 1


    '''PARAMETERS'''


    def get_status_update(self, channel_number=1,axis = None):
        if self.model[1] in DC_status_motors:
            returned_message = self.query(0x0490, param1=self.channel_number_to_identity[channel_number],destination_id = axis)
        else:
            returned_message = self.query(0x0480, param1=self.channel_number_to_identity[channel_number],destination_id = axis)
        return self.update_status(returned_message['data'])

    def update_status(self, returned_message,debug=False):
        '''This command should update device properties from the update message
            however this has to be defined for every device as the status update format
            and commands vary,
            please implement me
            Args:
                The returned message from a status update request           (dict)
        '''
        if debug > 0 or DEBUG == True:
            N = len(returned_message)
            print("returned_message length:",N)
        if self.model[1] in DC_status_motors:
            channel, position, velocity, Reserved, status_bits = struct.unpack('<HLHHI', returned_message)
            #HLHHI
            #H - 2, L - 4, I - 4
            # self.position = position
            # self.velocity = velocity / self.velocity_scaling_factor
        else:
            
            channel, position, EncCnt,status_bits, ChanIdent2,_,_,_ = struct.unpack('<HILIHLLL',returned_message)
            # print "Status bits",status_bits
            # print "self.status_bit_mask",self.status_bit_mask[:, 0]
        bitmask = self._bit_mask_array(status_bits, [int(i) for i in self.status_bit_mask[:, 0]])
        self.status = self.status_bit_mask[np.where(bitmask)]
        if debug > 0 or DEBUG == True:
            print(self.status)
        return self.status


    def init_no_flash_programming(self):
        """ This message must be sent on startup to tell the controller
        the source and destination address - The manual says this MUST be
        sent as part of the intialisation process

        Labled as: MGMSG_HW_NO_FLASH_PROGRAMMING
        """
        self.write(0x0018)

    def get_position(self, axis = None,channel_number=1):
        '''Sets/Gets the live position count in the controller
            generally this should not be used to set the position
            instead the controller should determine its own position
            by performing a homing manoeuvre
            Args:
                postion:    (float) this is the real position value
                            which is then converted to APT units within the setter
                channel_number:     (int) This defaults to 1
        '''
        if axis is None:
            return np.array(([self.get_position(axis) for axis in self.axis_names]))
        else:
            if axis not in self.axis_names:
                raise ValueError("{0} is not a valid axis, must be one of {1}".format(axis, self.axis_names))
                
            returned_message = self.query(0x0411, param1=self.channel_number_to_identity[channel_number],
                                          destination_id = axis)
            data = returned_message['data']
            channel_id, position = struct.unpack('<HL', data)
        # position = self.convert_to_SI_position(position)
            return self.convert(position,'counts','position')

    def set_position(self, position, channel_number=1,axis = None):
        # position = self.convert_to_APT_position(position)
        data = bytearray(struct.pack('<HL', self.channel_number_to_identity[channel_number], position))
        self.write(0x0410, data=data,destination_id = axis)

    position = property(get_position, set_position)


    def convert(self, value, from_, to_):
        print('Not doing anything from ', from_, ' to ', to_)
        return value

    def make_parameter(self, param_dict, destination_id = None):
        """Makes a parameter dictionary and sets it as a property

        All parameters in the Thorlabs APT basically require the same command structure, so this function wraps any
        parameter creation to simplify the code. It takes a dictionary containing the name of the parameter you want to
        make, which will be used to create a property attribute by that name and a getter and a setter. The dictionary
        should also containg the getter and setter command codes, and the structure of the data that is passed in the
        getter and setter. Finally the dictionary should contain the names of each of the sub_parameters given by the
        setter and getter, whose values can be converted into normal units by overwriting the self.convert() function

        Examples:
            Make self.velocity_params property, together with a self.get_velocity_params and self.set_velocity_params
            functions. self.velocity_params will be a dictionary, containing 'channel_num', 'min_velocity',
            'acceleration' and 'max_velocity'. The velocities will be converted into velocity through the convert
            function and the acceleration will be converted into acceleration.

                >>> self.make_parameter(dict(name='velocity_params', set=0x0413, get=0x0414, structure='HLLL',
                >>>                     param_names=['channel_num', ['min_velocity', 'velocity'],
                >>>                                 ['acceleration', 'acceleration'], ['max_velocity', 'velocity']]))


        Args:
            param_dict:
                name        :   internal name that you want the parameter to have
                set         :   setter function
                get         :   getter function
                structure   :   binary structure of the data packets
                param_names :   names of the parameters in the structure

        Returns:

        """

        def getter(selfie, channel_number=1):
            returned_message = selfie.query(param_dict['get'], param1=selfie.channel_number_to_identity[channel_number],destination_id = destination_id)
            data = returned_message['data']
            data = struct.unpack('<' + param_dict['structure'], data)
            params = {}
            index = 0
            for name in param_dict['param_names']:
                if type(name) == str:
                    params[name] = data[index]
                elif type(name) == list:
                    params[name[0]] = selfie.convert(data[index], 'counts', name[1])
                index += 1
            return params

        def setter(selfie, params, channel_number=None):
            if channel_number is None:
                channel_number = params['channel_num']
            unstructured_data = ['<' + param_dict['structure'],
                                 selfie.channel_number_to_identity[channel_number]]
            for name in param_dict['param_names']:
                if name != 'channel_num':
                    if type(name) == str:
                        unstructured_data += [params[name]]
                    elif type(name) == list:
                        unstructured_data += [selfie.convert(params[name[0]], name[1], 'counts')]
            data = struct.pack(*unstructured_data)
            selfie.write(param_dict['set'], data=data, destination_id=destination_id )

        setattr(self, 'get_' + param_dict['name'], types.MethodType(getter, self))
        setattr(self, 'set_' + param_dict['name'], types.MethodType(setter, self))
        try:
            setattr(self, param_dict['name'], property('get_' + param_dict['name'], 'set_' + param_dict['name']))
        except AttributeError:
            print(param_dict['name'], ' already exists')

    def make_all_parameters(self):
        # TODO: add all the documentation for each of these parameters
        for axis in self.destination:
            self.make_parameter(dict(name=axis+'_encoder_counts', set=0x0409, get=0x040A, structure='HL', param_names=['channel_num', 'encoder_counts']),destination_id=axis)
            # self.make_parameter(dict(name='position', set=0x0410, get=0x0411, structure='HL', param_names=['channel_num', ['position', 'distance']]))
            self.make_parameter(dict(name=axis+'_velocity_params', set=0x0413, get=0x0414, structure='HLLL',
                                     param_names=['channel_num', ['min_velocity', 'velocity'],
                                                  ['acceleration', 'acceleration'], ['max_velocity', 'velocity']]),destination_id=axis)
            self.make_parameter(dict(name=axis+'_jog_params', set=0x0416, get=0x0417, structure='HHLLLLH',
                                     param_names=['channel_num', ['jog_step_size', 'distance'],
                                                  ['jog_min_velocity', 'velocity'], ['jog_acceleration', 'acceleration'],
                                                  ['jog_max_velocity', 'velocity'], 'jog_stop_mode']),destination_id=axis)
            self.make_parameter(dict(name=axis+'_gen_move_params', set=0x043C, get=0x043B, structure='HL',
                                     param_names=['channel_num', 'backlash']),destination_id = axis)
            self.make_parameter(dict(name=axis+'_power_params', set=0x0426, get=0x0427, structure='HHH',
                                     param_names=['channel_num', 'RestPower', 'MovePower']),destination_id = axis)
            self.make_parameter(dict(name=axis+'_move_rel_params', set=0x0446, get=0x0447, structure='HL',
                                     param_names=['channel_num', 'rel_dist']),destination_id = axis)
            self.make_parameter(dict(name=axis+'_move_abs_params', set=0x0451, get=0x0452, structure='HL',
                                     param_names=['channel_num', 'abs_dist']),destination_id = axis)
            self.make_parameter(dict(name=axis+'_home_params', set=0x0441, get=0x0442, structure='HHHLL',
                                     param_names=['channel_num', 'direction', 'limit_switch', 'velocity', 'offset']),destination_id=axis)
        # self.make_parameter(dict(name=, set=, get=, structure=, param_names=['channel_num']))


class DC_APT(APT_VCP_motor):
    #The different EncCnt (calibrations) for the different stage types
    DC_stages_EncCnt = {'MTS':34304.0,
             'PRM':1919.64*1E3,
             'Z8':34304.0,
             'Z6':24600,
             'DDSM100':2000,
             'DDS':20000,
             'MLS' : 20000
             }
    def __init__(self,  port=None, source=0x01, destination=None,use_si_units=True,unit = 'm',
                 stay_alive=True, stage_type = None):
        """
        Pass all of the correct arguments to APT_VCP_motor for the DC stages and create converters.
        """
        APT_VCP_motor.__init__(self, port=port, source=source, destination=destination,
                         use_si_units=True,unit = unit, stay_alive=stay_alive)  # this opens the port
        #Setup up conversion factors
        if self.model[1] == 'BBD102/BBD103': #Once the TBD001 controller is added it needs to be added here
            self.t_constant = 102.4E-6
        elif self.model[1] == 'TDC001':
            self.t_constant = 2048.0/(6.0E6)
        else:
            self.t_constant = None
        
        if stage_type != None:
            try:
                self.EncCnt = float(self.DC_stages_EncCnt[stage_type])
            except KeyError:
                self.EncCnt = None
                self._logger.warn('The stage type suggested is not listed and therefore a calibration cannot be set')
        else:
            self.EncCnt = None    
            
    def convert(self, value, from_, to_):
        if None in (self.EncCnt,self.t_constant):
            self._logger.warn('Conversion impossible: one of the constants has not been implemented')
            return value
        if from_ == 'counts':
            return self.counts_to[to_](self,value)
        elif to_ == 'counts':
            return self.si_to[from_](self,value)
        else:
            self._logger.warn(('Converting %s to %s is not possible!, returning raw value'%(from_, to_))) 
            return value

    def counts_to_pos(self,counts):
        return old_div(counts,self.EncCnt)*1E3
    def pos_to_counts(self,pos):
        return old_div(pos*self.EncCnt,1E3)
    
    def counts_to_vel(self,counts):
        return old_div(counts,(self.EncCnt*self.t_constant*65536))*1E3
    def vel_to_counts(self,vel):
        return old_div(vel*65536*self.t_constant*self.EncCnt,1E3)
        
    def counts_to_acc(self,counts):
        return old_div(counts,(self.EncCnt*self.t_constant**2*65536))*1E3
    def acc_to_counts(self,acc):
        return old_div(self.EncCnt*self.t_constant**2*65536*acc,1E3)
    def move_step(self,axis,direction):
        self.move_rel(self.stepsize*direction,axis)
    def _waitFinishMove(self,axis = None,debug=False):
        """A simple function to force movement to block the console """
        if axis == None:
            destination_ids = list(self.destination.keys())
        else:
            destination_ids = [axis]
        for dest in destination_ids:
            status = self.get_status_update(axis = dest)# \ # and all([not x[1].endswith('homing') for x in status])\
            while any(['in motion' in x[1] for x in status]):
 
                time.sleep(0.1)
                status = self.get_status_update(axis = dest)
                if debug > 0 or DEBUG:
                    print(status)
    def home(self,axis = None):
        """Rehome the stage with an axis input """
        if axis == None:
            destination_ids = self.axis_names
        else:
            destination_ids = tuple(axis)
        for dest in destination_ids:
            self.write(0x0443,destination_id = dest)
            self._waitForReply()
            self._waitFinishMove()
    counts_to = {'position' : counts_to_pos,
                 'velocity' : counts_to_vel,
                 'acceleration' : counts_to_acc}
    si_to = {'position' : pos_to_counts,
             'velocity' : vel_to_counts,
             'acceleration' : acc_to_counts}
    
class Stepper_APT_std(APT_VCP_motor):
    #The different EncCnt (calibrations) for the different stage types is microstep/mm
    stepper_stages_EncCnt = {'DRV001':51200,
             'DRV013':25600,
             'DRV014':25600,
             'NRT':25600,
             'LTS':25600,
             'DRV':20480,
             'FW' : 71,
             'NR' : 4693,
             }
    def __init__(self,  port=None, source=0x01, destination=None,use_si_units=True, stay_alive=True, stage_type = None):
        """
        Pass all of the correct arguments to APT_VCP_motor for the standard stepper controllers
        stages and create converters.
        """
        APT_VCP_motor.__init__(self, port=port, source=source, destination=destination,
                         use_si_units=True, stay_alive=stay_alive)  # this opens the port
        #Setup up conversion factors
        
        if stage_type != None:
            try:
                self.EncCnt = float(self.stepper_stages_EncCnt[stage_type])
            except KeyError:
                self.EncCnt = None
                self._logger.warn('The stage type suggested is not listed and therefore a calibration cannot be set')
        else:
            self.EncCnt = None
                
            
    def convert(self, value, from_, to_):
        if self.EncCnt==None:
            self._logger.warn('Conversion impossible: one of the constants has not been implemented')
            return value
        if from_ == 'counts':
            return self.counts_to_si(value)
        elif to_ == 'counts':
            return self.si_to_counts(value)
        else:
            self._logger.warn(('Converting %s to %s is not possible!, returning raw value'%(from_, to_))) 
            return value

    def counts_to_si(self,counts):
        return old_div(counts,self.EncCnt)*1E3
    def si_to_counts(self,pos):
        return old_div(pos*self.EncCnt,1E3)
    
class Stepper_APT_trinamics(APT_VCP_motor):
    #The different EncCnt (calibrations) for the different stage types is microstep/mm
    stepper_stages_EncCnt = {'DRV001':819200,
             'DRV013':409600,
             'DRV014':409600,
             'NRT':409600,
             'LTS':409600,
             'MLJ':409600,
             'DRV':327680,
             'FW' : 1138,
             'NR' : 75091,
             }
    def __init__(self,  port=None, source=0x01, destination=None,use_si_units=True, stay_alive=True, stage_type = None):
        """
        Pass all of the correct arguments to APT_VCP_motor for the Trinamics stepper controllers
        stages and create converters.
        """
        APT_VCP_motor.__init__(self, port=port, source=source, destination=destination,
                         use_si_units=True, stay_alive=stay_alive)  # this opens the port
        #Setup up conversion factors
        if stage_type!= None:
            try:
                self.EncCnt = float(self.stepper_stages_EncCnt[stage_type])
            except KeyError:
                self.EncCnt = None
                self._logger.warn('The stage type suggested is not listed and therefore a calibration cannot be set')
        else:
            self.EncCnt = None
                
            
    def convert(self, value, from_, to_):
        if None in (self.EncCnt,self.t_constant):
            self._logger.warn('Conversion impossible: one of the constants has not been implemented')
            return value
        if from_ == 'counts':
            return self.counts_to[to_](self,value)
        elif to_ == 'counts':
            return self.si_to[from_](self,value)
        else:
            self._logger.warn(('Converting %s to %s is not possible!, returning raw value'%(from_, to_))) 
            return value

    def counts_to_pos(self,counts):
        return old_div(counts,self.EncCnt)*1E3
    def pos_to_counts(self,pos):
        return old_div(pos*self.EncCnt,1E3)
    
    def counts_to_vel(self,counts):
        return old_div(counts,(self.EncCnt*53.68))*1E3
    def vel_to_counts(self,vel):
        return old_div(vel*53.68*self.EncCnt,1E3)
        
    def counts_to_acc(self,counts):
        return old_div(counts,(self.EncCnt/90.9))*1E3
    def acc_to_counts(self,acc):
        return old_div(self.EncCnt/90.9*acc,1E3)
        
    counts_to = {'position' : counts_to_pos,
                 'velocity' : counts_to_vel,
                 'acceleration' : counts_to_acc}
    si_to = {'position' : pos_to_counts,
             'velocity' : vel_to_counts,
             'acceleration' : acc_to_counts}
    
if __name__ == '__main__':
    print("pass")
    # microscope_stage = APT_VCP_motor(port='COM12', source=0x01, destination=0x21)
    r = DC_APT(port = 'COM13', destination = 0x01, stage_type = 'PRM' )
    DEBUG = True

    # tdc_cube = Stepper_APT_trinamics(port='/dev/ttyUSB1', source=0x01, destination=0x50)
    # # tdc_cube2 = APT_VCP_motor(port='COM20', source=0x01, destination=0x50)

    # tdc_cube.show_gui()
    # print tdc_cube.position
    # tdc_cube.home()
    # delattr(tdc_cube, 'get_qt_ui')
    # print tdc_cube.channel_number_to_identity['1']
    # tdc_cube.get_status_update()
    # print 'Status: ', tdc_cube.status
    # print 'Position: ', tdc_cube.get_position()

    # tdc_cube.make_all_parameters()
    # print tdc_cube.get_velocity_params()
    # print tdc_cube.velocity_params
    # tdc_cube.show_gui()
    # print tdc_cube.get_gen_move_params()
    # print tdc_cube.get_haha()

    # tdc_cube.home()

    # tdc_cube.move(0)
    # time.sleep(10)
