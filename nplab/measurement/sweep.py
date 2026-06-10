from abc import abstractmethod
from threading import Lock
from typing import Callable, Dict, Generic, List, TypeVar
from h5py import Group

from nplab.measurement.action import Action, InterruptedException, MessageType, Result, Status

R = TypeVar("R")
D = TypeVar("D")

class Sweep(Action[R], Generic[R, D]):

    def __init__(self, name: str, tag: str, actions: List[Action] = []):

        super().__init__(name, tag)

        self._tag     = tag
        self._actions = actions
        self._current = None
        self._lLock   = Lock()

        self._listeners: List[Callable[[List[Action]], None]] = []


    def addActionListener(self, listener: Callable[[List[Action]], None]) -> Callable[[List[Action]], None]:
        with self._lLock:
            self._listeners.append(listener)
            return listener


    def removeActionListener(self, listener: Callable[[List[Action]], None]):
        
        with self._lLock:

            try:
                self._listeners.remove(listener)
            except:
                pass



    def addAction(self, action: Action[R]):
        self._actions.append(action)
        self.notifyActionListeners()


    def addActions(self, *actions: Action[R]):
        self._actions += actions


    def removeAction(self, action: Action[R]):
        self._actions.remove(action)
        self.notifyActionListeners()


    def clearActions(self):
        self._actions.clear()
        self.notifyActionListeners()


    def setActions(self, *actions: Action[R]):
        self._actions.clear()
        self._actions += actions
        self.notifyActionListeners()


    def notifyActionListeners(self):

        values  = self.getValues()
        actions = self.generate(values[0] if len(values) > 0 else None, self._actions)

        with self._lLock:
            
            for listener in self._listeners:
                
                try:
                    listener(actions)
                except:
                    pass


    def getActions(self) -> List[Action]:
        return self._actions.copy()
    

    def encodeAction(self):

        object            = super().encodeAction()
        object["actions"] = [a.encodeAction() for a in self._actions]

        return object
    

    def loadFromMap(self, map, equipment):

        super().loadFromMap(map, equipment)

        for aMap in map["actions"]:
            action = Action.loadAction(aMap, equipment)
            self.addAction(action)


    
    @abstractmethod
    def generate(self, value: D, actions: list) -> list:
        '''This method should take a sweep value and the list of actions to perform on each sweep iteration
           and return the list of all actions to be run for the specified sweep value. This may differ from the
           initial list, for instance, if each sweep requires an action to be completed before any others.
           For example, a sweep of voltage will require a "Change Voltage" action to be added to the start
           of the list for each iteration.'''
        pass

    
    @abstractmethod
    def valueToString(self, value: D) -> str:
        '''This method should take a sweep value and return a string representation of it.'''
        pass


    @abstractmethod
    def prepareDataForIteration(self, tag: str, value: D, data: R) -> R:
        '''This method does the same as the usual prepareData method, except it does it for each
           iteration of the sweep.'''
        pass

    @abstractmethod
    def getValues(self) -> List[D]:
        '''This method should return a list of all values to be swept over.'''
        pass


    def main(self, data: R = None):
        '''Sweep actions provide their own implementation of the main method, and thus this does not require
           overriding in extending classes.'''

        values = self.getValues()

        for value in values:

            actions     = self.generate(value, self._actions)
            preppedData = self.prepareDataForIteration(self._tag, value, data)

            with self._lLock:
                for listener in self._listeners:
                    try:
                        listener(actions)
                    except:
                        pass

            self.message(MessageType.INFO, "%s = %s." % (self._tag, self.valueToString(value)))

            for action in actions:
                action.reset()

            for action in actions:

                if self._interrupted:
                    raise InterruptedException()

                self._current = action

                listener = action.addMessageListener(lambda msg: self.passMessage(msg.propagate(self, value, "%s = %s" % (self._tag, self.valueToString(value)))))
                result   = action.run(preppedData)

                action.removeMessageListener(listener)

                for error in result.errors:
                    self._errors.append(error)

                if result.type == Status.INTERRUPTED:
                    raise InterruptedException()


        if len(self._errors) > 0:
            raise Exception("Errors were encountered during the sweep.")


    def interrupt(self):
        
        super().interrupt()

        if self._current is not None:
            self._current.interrupt()


    def reset(self):

        super().reset()

        for action in self._actions:
            action.reset()


    def finish(self, data: R = None):
        '''It is less likely that a sweep would require a finish method, thus it is no-longer considered abstract for a sweep.
           It can, however, still be overridden should it be needed.'''
        pass


class H5Sweep(Sweep[Group, D], Generic[D]):

    def __init__(self, name: str, tag: str, actions: List[Action] = []):
        super().__init__(name, tag, actions)


    def prepareData(self, name: str, description: str, data: Group):
        
        nm = "%s (%s)" % (name, self._tag)

        i = 1
        while nm in data:
            nm = "%s (%s) [%d]" % (name, self._tag, i)
            i += 1

        return data.create_group(nm)


    def prepareDataForIteration(self, tag: str, value: D, data: Group):

        nm = "%s = %s" % (tag, self.valueToString(value))

        i = 1
        while nm in data:
            nm = "%s = %s [%d]" % (tag, self.valueToString(value), i)
            i += 1
        
        return data.create_group(nm)
    
    
