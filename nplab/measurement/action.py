import numpy as np
import pyjisa.autoload
import importlib
from jisa.devices import Instrument as JInstrument
from jisa.devices.camera.frame import Frame
from jisa.devices.spectrometer.spectrum import Spectrum
from jisa.results import ResultTable

from abc import ABC, abstractmethod
from enum import Enum
from threading import Lock, Thread
import threading
from typing import Callable, Dict, Generic, List, Tuple, TypeVar, Union, Type as Tpe
import h5py
from qtpy.QtWidgets import QWidget
from typing_extensions import Self

class InterruptedException(Exception):
    
    def __init__(self, *args):
        super().__init__(*args)


class Status(Enum):
    '''Enumeration of all possible statuses for an action'''

    QUEUED      = 0
    RUNNING     = 1
    SUCCESS     = 2
    ERROR       = 3
    INTERRUPTED = 4


class Type(Enum):

    AUTO       = 0
    TIME       = 1
    FILE_SAVE  = 2
    FILE_OPEN  = 3
    DIRECTORY  = 4
    SCIENTIFIC = 5
    SLIDER     = 6


class MessageType(Enum):
    '''Enumeration of all possible types of message emitted by an action'''

    INFO    = 0
    WARNING = 1
    ERROR   = 2


T = TypeVar("T")

class Parameter(Generic[T]):

    def __init__(self, name: str, defaultValue: T, type: Type = Type.AUTO, options: List[T] = [], range: Tuple[T, T] = (None, None), customWidget: QWidget = None, customGetter: Callable[[], T] = None, customSetter: Callable[[T], None] = None):

        self._name         : str                 = name
        self._defaultValue : T                   = defaultValue
        self._values       : Dict[object, T]     = {}
        self._type         : Type                = type
        self._options      : List[T]             = options
        self._range        : Tuple[T, T]         = range
        self._customWidget : QWidget             = customWidget
        self._customGetter : Callable[[], T]     = customGetter
        self._customSetter : Callable[[T], None] = customSetter


    def __set__(self, obj, value: T):
        self._values[obj] = value
        Action.lastActions[obj.__class__] = obj

    
    def __get__(self, obj, type=None) -> Union[T, Self]:

        if (obj is None):
            return self

        if (obj in self._values):
            return self._values[obj]
        else:
            return self._defaultValue
    

I = TypeVar("I")

class Instrument(Generic[I]):

    def __init__(self, name: str, type: Tpe[I], required: bool = True):

        self._name     = name
        self._required = required
        self._values   = {}
        self._type     = type


    def __set__(self, obj, value: I):
        self._values[obj] = value
        Action.lastActions[obj.__class__] = obj


    def __get__(self, obj, type=None) -> Union[I, None, Self]:

        if (obj is None):
            return self
        
        if (obj in self._values):
            return self._values[obj]
        else:
            return None
        
        
class PathPart:

    def __init__(self, part, sweepValue = None, sweepText: str = None):

        self.part       = part
        self.sweepValue = sweepValue
        self.sweepText  = sweepText


class Message:

    def __init__(self, type: MessageType, message: str, path: List[PathPart], timestamp: int = None):

        if timestamp is None:
            import time
            timestamp = int(time.time())

        self.type      = type
        self.message   = message
        self.path      = path
        self.timestamp = timestamp


    def propagate(self, part, sweepValue = None, sweepText: str = None):
        return Message(self.type, self.message, [PathPart(part, sweepValue, sweepText)] + self.path, self.timestamp)


    @property
    def pathString(self):
        return " → ".join(["%s (%s)" % (p.part.name, p.sweepText) if p.sweepText is not None else p.part.name for p in self.path])


R = TypeVar("R")

class PValue(Generic[T]):

    def __init__(self, parameter: Parameter[T], getter: Callable[[], T], setter: Callable[[T], None]):

        self._parameter = parameter
        self._getter    = getter
        self._setter    = setter

        self.name    = parameter._name
        self.options = parameter._options
        self.type    = parameter._type
        self.range   = parameter._range
        self.custom  = parameter._customWidget
        self.customG = parameter._customGetter
        self.customS = parameter._customSetter


    def get(self) -> T:
        return self._getter()
    

    def set(self, value: T):
        self._setter(value)


    value = property(get, set)


class IValue(Generic[I]):

    def __init__(self, instrument: Instrument[I], getter: Callable[[], I], setter: Callable[[I], None]):

        self._instrument = instrument
        self._getter     = getter
        self._setter     = setter

        self.name     = instrument._name
        self.type     = instrument._type
        self.required = instrument._required


    def get(self) -> I:
        return self._getter()
    

    def set(self, value: I):
        self._setter(value)


    value: I = property(get, set)


class Result(Generic[R]):

    def __init__(self, type: Status, errors: List[Exception], messages: List[Message], data: R = None):

        self.type     = type
        self.errors   = errors
        self.messages = messages
        self.data     = data



class Action(ABC, Generic[R]):
    '''Base class to represent individual actions.'''

    lastActions = {}

    def __init__(self, name: str, description: str):
        
        self.name        : str    = name
        self.description : str    = description

        self._status : Status = Status.QUEUED

        self._statusListeners  : List[Callable[[Status], None]]  = []
        self._messageListeners : List[Callable[[Message], None]] = []

        self._thread      : Thread  = None
        self._interrupted : bool    = False
        self._errors      : list    = []
        self._lastMessage : Message = None
        self._lLock       : Lock    = Lock()

        if self.__class__ in Action.lastActions:

            last = Action.lastActions[self.__class__]

            lastP = last.getParameters()
            thisP = self.getParameters()

            lastI = last.getInstruments()
            thisI = self.getInstruments()

            for tp in thisP:
                lp = [p for p in lastP if p.name == tp.name][0]
                tp.set(lp.get())

            for ti in thisI:
                li = [i for i in lastI if i.name == ti.name][0]
                ti.set(li.get())

        Action.lastActions[self.__class__] = self


    def start(self, data: R = None):
        
        thread = Thread(None, lambda: self.run(data))
        thread.start()


    def interrupt(self):
        self._interrupted = True


    def getStatus(self) -> Status:
        return self._status


    def setStatus(self, status: Status):

        self._status = status
        
        with self._lLock:

            for listener in self._statusListeners:
                
                try:
                    listener(status)
                except:
                    pass


    status = property(getStatus, setStatus)


    def run(self, data: R = None) -> Result:

        self._interrupted = False
        self._thread      = threading.current_thread()

        self._errors.clear()

        messages = []

        listener = self.addMessageListener(lambda message: messages.append(message))

        self.status = Status.RUNNING
        self.infoMessage("Started.")

        prepared = self.prepareData(self.name, self.description, data)

        try:

            missing = []
            
            for ival in self.getInstruments():
                if ival.required and ival.get() is None:
                    missing.append(ival.name)

            if len(missing) > 0:
                raise Exception("Missing required instrument(s): %s" % ", ".join(missing))

            self.main(prepared)

            if self._interrupted:
                raise InterruptedException()
            else:
                self.status = Status.SUCCESS

        except InterruptedException as e:
            self.status = Status.INTERRUPTED
            self.warningMessage("Interrupted.")
            self.interrupted(prepared)

        except Exception as e:
            self.status = Status.ERROR
            self._errors.append(e)
            self.errorMessage(str(e))
            self.error(self._errors, prepared)

        finally:

            try:
                self.finish(prepared)
            except Exception as e:
                self.errorMessage("Finisher failed: " + str(e))
            finally:
                self.infoMessage("Finished.")
                self.removeMessageListener(listener)


        return Result(self.status, self._errors, messages, prepared)
    

    def addStatusListener(self, listener: Callable[[Status], None]) -> Callable[[Status], None]:
        with self._lLock:
            self._statusListeners.append(listener)
            return listener
    

    def removeStatusListener(self, listener: Callable[[Status], None]):
        
        with self._lLock:

            try:
                self._statusListeners.remove(listener)
            except:
                pass


    def addMessageListener(self, listener: Callable[[Message], None]) -> Callable[[Message], None]:
        with self._lLock:
            self._messageListeners.append(listener)
            return listener


    def removeMessageListener(self, listener: Callable[[Message], None]):

        with self._lLock:

            try:
                self._messageListeners.remove(listener)
            except:
                pass


    def message(self, type: MessageType, message: str):

        msg = Message(type, message, [PathPart(self)])
        self._lastMessage = msg
        self.passMessage(msg)


    def getLastMessage(self) -> Message:
        return self._lastMessage
    

    def infoMessage(self, message: str):
        self.message(MessageType.INFO, message)


    def warningMessage(self, message: str):
        self.message(MessageType.WARNING, message)


    def errorMessage(self, message: str):
        self.message(MessageType.ERROR, message)


    def passMessage(self, msg: Message):
        with self._lLock:
            for listener in self._messageListeners:
                try:
                    listener(msg)
                except:
                    pass


    def checkpoint(self):
        '''Call this at points in your measurement code where it is safe for the measurement to be interrupted'''

        if self._interrupted:
            raise InterruptedException()


    def sleep(self, milliseconds: int):
        '''Makes the current tread sleep for the specified integer number of milliseconds'''

        from time import sleep

        if self._interrupted:
            raise InterruptedException()

        sleep(milliseconds / 1e3)

        if self._interrupted:
            raise InterruptedException()
        
    
    def getParameters(self) -> List[PValue]:

        cls    = type(self)
        params = []

        for name in dir(cls):

            obj = getattr(cls, name)

            if type(obj) is not Parameter:
                continue

            params.append(PValue(obj, lambda n=name: getattr(self, n), lambda v, n=name: setattr(self, n, v)))

        return params
        
    
    def getInstruments(self) -> List[IValue]:

        cls         = type(self)
        instruments = []

        for name in dir(cls):

            obj = getattr(cls, name)

            if type(obj) is not Instrument:
                continue

            instruments.append(IValue(obj, lambda n=name: getattr(self, n), lambda v, n=name: setattr(self, n, v)))

        return instruments
    

    def getInstrumentName(self, instrument) -> str:

        if instrument is None:
            return "None"

        if hasattr(instrument, "getName"):
            return instrument.getName()
        elif hasattr(instrument, "name"):
            return instrument.name
        else:
            str(instrument)


    def getInstrumentMap(self) -> Dict:

        object = {}

        for ival in self.getInstruments():
            object[ival.name] = self.getInstrumentName(ival.value)

        return object


    def loadInstrumentsFromMap(self, map: Dict, equipment):

        ivals = self.getInstruments()

        for (name, instName) in map.items():

            try:
                foundIVal = [i for i in ivals if i.name == name][0]
                foundInst = [i for i in equipment if self.getInstrumentName(i) == instName][0]
                foundIVal.set(foundInst)
            except Exception as e:
                print(e)
                pass


    def getParameterMap(self) -> Dict[str, object]:
        return {p.name: p.value for p in self.getParameters()}
    

    def loadParametersFromMap(self, map: Dict[str, object]):

        parameters = self.getParameters()

        for (name, value) in map.items():

            matches = [p for p in parameters if p.name == name and type(p.value) == type(value)]

            if len(matches) > 0:

                found       = matches[0]
                found.value = value


    def getParameterJSON(self) -> str:
        import json
        return json.dumps(self.getParameterMap())
    

    def encodeAction(self) -> Dict:

        return {
            "module"      : self.__class__.__module__,
            "class"       : self.__class__.__qualname__,
            "description" : self.description,
            "parameters"  : self.getParameterMap(),
            "instruments" : self.getInstrumentMap()
        }
    

    def loadFromMap(self, map: Dict, equipment: List):
        self.loadParametersFromMap(map["parameters"])
        self.loadInstrumentsFromMap(map["instruments"], equipment)



    @classmethod
    def loadAction(clss, map: Dict, equipment: List):

        module      = map["module"]
        classN      = map["class"]
        constructor = getattr(importlib.import_module(module), classN)
        description = map["description"]

        action: Action = constructor(description)

        action.loadFromMap(map, equipment)

        return action


    def loadParametersFromJSON(self, data: str):
        import json
        self.loadParametersFromMap(json.loads(data))


    def reset(self):
        self.status = Status.QUEUED
        self._errors.clear()
        self._interrupted = False
        

    @abstractmethod
    def prepareData(self, name: str, description: str, data: R) -> R:
        '''The object returned by this method is what is given to the main, finish, error, and interrupted methods.
           It should therefore be used to prepare the data structure for the measurement. For instance, in a H5 structure
           this method is used to create a new group.'''
        ...

    @abstractmethod
    def main(self, data: R = None):
        '''The main method of this action. This is where one should put the code this action is meant to run'''
        ...


    @abstractmethod
    def finish(self, data: R = None):
        '''This method is always called after main() has finished, regardless of whether it finished successfully or not'''
        ...
    
    
    def error(self, errors: List[Exception], data = None):
        '''This method is only called if the main() method finished in error (called before calling finish())'''
        ...


    def interrupted(self, data: R = None):
        '''This method is only called in the main() method is interrupted before completion (called before finish())'''
        ...


    def widget(self) -> QWidget:
        '''This method should return a QWidget that contains whatever GUI element you want to be displayed as this
           action is running. Otherwise it should return None.'''
        return None



class SimpleAction(Action[None]):

    def prepareData(self, name, decription, data):
        return data


class H5Action(Action[h5py.Group]):

    def prepareData(self, name: str, description: str, data: h5py.Group):

        nm = "%s (%s)" % (name, description)

        i = 1
        while nm in data:
            nm = "%s (%s) [%d]" % (name, description, i)
            i += 1

        return data.create_group(nm)
    

    def writeFrame(self, frame: Frame, group: h5py.Group, name: str) -> h5py.Dataset:
        
        ds = group.create_dataset(name = name, data = np.array(frame.getNPArray()).view(np.uint8))
        ds.attrs["Timestamp"] = frame.getTimestamp()
        self.writeAttributes(frame.getAttributes(), ds)

        return ds
    

    def writeSpectrum(self, spectrum: Spectrum, group: h5py.Group, name: str) -> h5py.Dataset:

        ds = group.create_dataset(name = name, data = np.array([np.array(spectrum.getWavelengths()), np.array(spectrum.getCounts())]))
        ds.attrs["Timestamp"] = spectrum.getTimestamp()
        self.writeAttributes(spectrum.getAttributes(), ds)

        return ds


    def writeAttributes(self, attributes: Dict, ds: h5py.HLObject):

        for key, value in attributes.items():
            
            if isinstance(value, JInstrument.AutoQuantity):

                ds.attrs[key + ": Auto"]  = value.isAuto()
                value = value.getValue()
                key   = key + ": Value"
        

            if isinstance(value, JInstrument.OptionalQuantity):

                ds.attrs[key + ": Used"]  = value.isUsed()
                value = value.getValue()
                key   = key + ": Value"


            if isinstance(value, ResultTable):

                con = [[str(v) for v in r] for r in value.asStringArray()]
                con = [[str(c.getTitle()) for c in value.getColumns()]] + con
                ds.attrs[key] = con

            else:
                ds.attrs[key] = str(value)