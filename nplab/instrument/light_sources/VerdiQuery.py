class VerdiQueryClass(object):
    @property
    def baseplate_temperature(self):
        """Returns the measured laser head baseplate temperature in C"""
        return self.read_number("BT")
        
    @property
    def baud_rate(self):
        """Return the baud rate of the Verdi serial port"""
        return self.read_number("B")
        
    @property
    def diode_currents(self):
        """Returns the measured diode currents in amps"""
        return self.read_number("C")
        
    @property
    def delta_calibration(self):
        """Return the diode current delta calibration"""
        return self.read_number("CD")
        
    @property
    def diode_1_current(self):
        """Returns the measured laser diode 1 current in amps"""
        return self.read_number("D1C")
        
    @property
    def diode_2_current(self):
        """Returns the measured laser diode 2 current in amps"""
        return self.read_number("D2C")
        
    @property
    def diode_1_heatsink_temperature(self):
        """Returns the laser diode 1 heatsink temperature in C"""
        return self.read_number("D1HST")
        
    @property
    def diode_2_heatsink_temperature(self):
        """Returns the laser diode 2 heatsink temperature in C"""
        return self.read_number("D2HST")
        
    @property
    def diode_1_operating_hours(self):
        """Returns the number of operating hours on the laser diode 1"""
        return self.read_number("D1H")
        
    @property
    def diode_2_operating_hours(self):
        """Returns the number of operating hours on the laser diode 2"""
        return self.read_number("D2H")
        
    @property
    def diode_1_power(self):
        """Returns light output power from diode 1 photocell"""
        return self.read_number("D1PC")
        
    @property
    def diode_2_power(self):
        """Returns light output power from diode 2 photocell"""
        return self.read_number("D2PC")
        
    @property
    def diode_1_aging_factor(self):
        """Returns the factor that accounts for diode 1 aging"""
        return self.read_number("D1RCF")
        
    @property
    def diode_2_aging_factor(self):
        """Returns the factor that accounts for diode 2 aging"""
        return self.read_number("D2RCF")
        
    @property
    def diode_1_maximum_current(self):
        """Returns the maximum current at which diode 1 will be allowed to operate"""
        return self.read_number("D1RCM")
        
    @property
    def diode_2_maximum_current(self):
        """Returns the maximum current at which diode 2 will be allowed to operate"""
        return self.read_number("D2RCM")
        
    @property
    def diode_1_status(self):
        """Returns the status of diode 1 temperature servo {0:"OPEN", 1:"LOCKED", 2:"SEEKING", 3:"FAULT", 4:"OPTIMIZING"}"""
        dico = {0:"OPEN", 1:"LOCKED", 2:"SEEKING", 3:"FAULT", 4:"OPTIMIZING"}
        return self.read_dict_number("D1SS", dico)
    @property
    def diode_2_status(self):
        """Returns the status of diode 2 temperature servo {0:"OPEN", 1:"LOCKED", 2:"SEEKING", 3:"FAULT", 4:"OPTIMIZING"}"""
        dico = {0:"OPEN", 1:"LOCKED", 2:"SEEKING", 3:"FAULT", 4:"OPTIMIZING"}
        return self.read_dict_number("D2SS", dico)
    @property
    def diode_1_set_temperature(self):
        """Returns the diode 1 set temperature in C"""
        return self.read_number("D1ST")
        
    @property
    def diode_2_set_temperature(self):
        """Returns the diode 2 set temperature in C"""
        return self.read_number("D2ST")
        
    @property
    def diode_1_temperature_servo_level(self):
        """Returns laser diode 1 temperature servo drive level"""
        return self.read_number("D1TD")
        
    @property
    def diode_2_temperature_servo_level(self):
        """Returns laser diode 2 temperature servo drive level"""
        return self.read_number("D2TD")
        
    @property
    def diode_1_temperature(self):
        """Returns the measured laser diode 1 temperature in C"""
        return self.read_number("D1T")
        
    @property
    def diode_2_temperature(self):
        """Returns the measured laser diode 2 temperature in C"""
        return self.read_number("D2T")
        
    @property
    def diode_1_ref_voltage(self):
        """Return a reference voltage used to measure the temperature of diode 1"""
        return self.read_number("D15V")
        
    @property
    def diode_2_ref_voltage(self):
        """Return a reference voltage used to measure the temperature of diode 2"""
        return self.read_number("D25V")
        
    @property
    def diode_optimization_status(self):
        """Returns diode 1 optimization status {0:False, 1:True}"""
        dico = {0:False, 1:True}
        return self.read_dict_number("DIOS", dico)
    @property
    def etalon_servo_level(self):
        """Returns etalon temperature servo drive level"""
        return self.read_number("ED")
        
    @property
    def etalon_status(self):
        """Returns the status of the etalon temperature servo  {0:"OPEN", 1:"LOCKED", 2:"SEEKING", 3:"FAULT"}"""
        dico = {0:"OPEN", 1:"LOCKED", 2:"SEEKING", 3:"FAULT"}
        return self.read_dict_number("ESS", dico)
    @property
    def etalon_set_temperature(self):
        """Returns etalon set temperature in C"""
        return self.read_number("EST")
        
    @property
    def etalon_temperature(self):
        """Returns the measured Etalon temperature in C"""
        return self.read_number("ET")
        
    @property
    def operating_hours(self):
        """Returns the number of operating hours on the system head"""
        return self.read_number("HH")
        
    @property
    def keyswitch(self):
        """Returns keyswitch {0:"OFF",  1:"ENABLE"}"""
        dico = {0:"OFF",  1:"ENABLE"}
        return self.read_dict_number("K", dico)
    @property
    def laser(self):
        """Returns {0:'OFF', 1:'ON', 2:'FAULT'}"""
        dico = {0:'OFF', 1:'ON', 2:'FAULT'}
        return self.read_dict_number("L", dico)
    @property
    def LBO_servo_level(self):
        """Returns LBO temperature servo drive level"""
        return self.read_number("LBOD")
        
    @property
    def LBO_header_status(self):
        """Returns the status of the LBO heater {0:'OFF', 1:'ON'}"""
        dico = {0:'OFF', 1:'ON'}
        return self.read_dict_number("LBOH", dico)
    @property
    def LBO_optimization_status(self):
        """Returns the if the system is able to run LBO optimization status {1:True, 0:False}"""
        dico = {1:True, 0:False}
        return self.read_dict_number("LBOOS", dico)
    @property
    def LBO_set_temperature(self):
        """Returns LBO set temperature in C"""
        return self.read_number("LBOST")
        
    @property
    def LBO_servo_status(self):
        """Returns the status of the LBO temperature servo   {0:"OPEN", 1:"LOCKED", 2:"SEEKING", 3:"FAULT", 4:"OPTIMIZING"}"""
        dico = {0:"OPEN", 1:"LOCKED", 2:"SEEKING", 3:"FAULT", 4:"OPTIMIZING"}
        return self.read_dict_number("LBOSS", dico)
    @property
    def LBO_temperature(self):
        """Returns the measured LOB temperature in C"""
        return self.read_number("LBOT")
        
    @property
    def power(self):
        """Returns the calibrated output power in watts"""
        return self.read_number("P")
        
    @property
    def light_loop_servo(self):
        """Returns the status of the light loop servo {0:"OPEN", 1:"LOCKED", 2:"SEEKING", 3:"FAULT"}"""
        dico = {0:"OPEN", 1:"LOCKED", 2:"SEEKING", 3:"FAULT"}
        return self.read_dict_number("LRS", dico)
    @property
    def operation_mode(self):
        """Returns the mode of operation, whether current or light control {1:"light", 0:"current"}"""
        dico = {1:"light", 0:"current"}
        return self.read_dict_number("M", dico)
    @property
    def power_supply_operating_hours(self):
        """Returns the number of power supply operating hours"""
        return self.read_number("PSH")
        
    @property
    def set_power(self):
        """Returns the light regulation set power in watts"""
        return self.read_number("SP")
        
    @property
    def shutter(self):
        """Returns the status of the external shutter {0:"CLOSED", 1:"OPEN"}"""
        dico = {0:"CLOSED", 1:"OPEN"}
        return self.read_dict_number("S", dico)
    @property
    def version_number(self):
        """Returns the power supply software version number"""
        return self.read_number("SV")
        
    @property
    def vanadate_set_temperature(self):
        """Returns vanadate set temperature in C"""
        return self.read_number("VST")
        
    @property
    def vanadate_temperature(self):
        """Returns the measured vanadate temperature in C"""
        return self.read_number("VT")
        
    @property
    def vanadate_servo_level(self):
        """Returns vanadate temperature servo drive level"""
        return self.read_number("VD")
        
    @property
    def vanadate_status(self):
        """Returns the status of the vanadate temperature servo  {0:"OPEN", 1:"LOCKED", 2:"SEEKING", 3:"FAULT"}"""
        dico = {0:"OPEN", 1:"LOCKED", 2:"SEEKING", 3:"FAULT"}
        return self.read_dict_number("VSS", dico)

VerdiRS232QueryList = ['BT', 'B', 'C', 'CD', 'D1C', 'D2C', 'D1HST', 'D2HST', 'D1H', 'D2H', 'D1PC', 'D2PC', 'D1RCF', 'D2RCF', 'D1RCM', 'D2RCM', 'D1SS', 'D2SS', 'D1ST', 'D2ST', 'D1TD', 'D2TD', 'D1T', 'D2T', 'D15V', 'D25V', 'DIOS', 'ED', 'ESS', 'EST', 'ET', 'HH', 'K', 'L', 'LBOD', 'LBOH', 'LBOOS', 'LBOST', 'LBOSS', 'LBOT', 'P', 'LRS', 'M', 'PSH', 'SP', 'S', 'SV', 'VST', 'VT', 'VD', 'VSS']

VerdiQueryList = ['baseplate_temperature',
	'baud_rate',
	'diode_currents',
	'delta_calibration',
	'diode_1_current',
	'diode_2_current',
	'diode_1_heatsink_temperature',
	'diode_2_heatsink_temperature',
	'diode_1_operating_hours',
	'diode_2_operating_hours',
	'diode_1_power',
	'diode_2_power',
	'diode_1_aging_factor',
	'diode_2_aging_factor',
	'diode_1_maximum_current',
	'diode_2_maximum_current',
	'diode_1_status',
	'diode_2_status',
	'diode_1_set_temperature',
	'diode_2_set_temperature',
	'diode_1_temperature_servo_level',
	'diode_2_temperature_servo_level',
	'diode_1_temperature',
	'diode_2_temperature',
	'diode_1_ref_voltage',
	'diode_2_ref_voltage',
	'diode_optimization_status',
	'etalon_servo_level',
	'etalon_status',
	'etalon_set_temperature',
	'etalon_temperature',
	'operating_hours',
	'keyswitch',
	'laser',
	'LBO_servo_level',
	'LBO_header_status',
	'LBO_optimization_status',
	'LBO_set_temperature',
	'LBO_servo_status',
	'LBO_temperature',
	'power',
	'light_loop_servo',
	'operation_mode',
	'power_supply_operating_hours',
	'set_power',
	'shutter',
	'version_number',
	'vanadate_set_temperature',
	'vanadate_temperature',
	'vanadate_servo_level',
	'vanadate_status']
