from abc import ABC, abstractmethod
from threading import Lock, Thread
import threading
from typing import Callable, Generic, List, TypeVar, Union

import h5py
import jpype
from qtpy.QtCore import QThread, QThreadPool

from nplab.measurement.action import Action, Message, MessageType, PathPart, Result, Status

R = TypeVar("R")

class ActionQueue(Generic[R], ABC):

    def __init__(self):
        
        self._actions     : List[Action[Union[R,None]]] = []
        self._messages    : List[Message]               = []
        self._running     : bool                        = False
        self._thread      : Thread                      = None
        self._interrupted : bool                        = False
        self._current     : Action                      = None
        self._result      : Result                      = None
        self._lock        : Lock                        = Lock()

        self._messageListeners : List[Callable[[Message], None]]      = []
        self._actionListeners  : List[Callable[[List[Action]], None]] = []
        self._finishListeners  : List[Callable[[Result], None]]       = []


    @abstractmethod
    def prepareData(self, data: R) -> R:
        pass


    @abstractmethod
    def finaliseData(self, data: R, result: Result):
        pass


    def _main(self, data: R):
        
        jpype.attachThreadToJVM()
        self.message(Message(MessageType.INFO, "Queue started.", []))

        # Prepare our data object for use
        data     = self.prepareData(data)
        errors   = []
        messages = []
        status   = Status.SUCCESS

        try:

            for action in self._actions:

                if self._interrupted:
                    status = Status.INTERRUPTED
                    break

                self._current = action

                # Attach a message listener just while we're running this action
                listener = action.addMessageListener(self.message)
                result   = action.run(data)
                
                action.removeMessageListener(listener)

                errors   += result.errors
                messages += result.messages

                # If the action was interrupted, then the whole queue should stop
                if result.type == Status.INTERRUPTED:
                    status = Status.INTERRUPTED
                    break

                elif result.type == Status.ERROR:
                    status = Status.ERROR

        finally:

            self._result = Result(status, errors, messages, data)

            self.finaliseData(data, self._result)
            
            self.message(Message(MessageType.INFO, "Queue finished (%s)." % status.name, []))
            self._running = False

            for listener in self._finishListeners:
                listener(self._result)


    def start(self, data: R):

        with self._lock:

            # If we're already running, ignore the call
            if self._running:
                return

            self._running     = True
            self._interrupted = False
            self._result      = None
            self._thread      = Thread(None, lambda: self._main(data))
            
            for action in self._actions:
                action.reset()

            self._thread.start()


    def awaitResult(self) -> Result:

        with self._lock:
            if not self._running:
                return self._result
        
        self._thread.join()
        return self._result
        

    def run(self, data: R) -> Result:

        # If we're already running, ignore the call
        with self._lock:
            if self._running:
                return

        self.start(data)
        return self.awaitResult()


    def interrupt(self):

        with self._lock:
            if not self._running:
                return

        self._interrupted = True
        self._current.interrupt()


    @property
    def actions(self) -> List[Action[Union[R,None]]]:
        return list(self._actions)


    @property
    def isRunning(self) -> bool:
        with self._lock:
            return self._running

    
    def notifyActionListeners(self):
        for listener in self._actionListeners:
            listener(self._actions)

    
    def message(self, message: Message):

        self._messages.append(message)

        for listener in self._messageListeners:
            listener(message)


    def checkIsRunning(self):
        with self._lock:
            if self._running:
                raise Exception("Cannot modify an ActionQueue that is currently running.")
        

    def addAction(self, action: Action):
        self.checkIsRunning()
        self._actions.append(action)
        self.notifyActionListeners()


    def addActions(self, *actions: Action):
        self.checkIsRunning()
        self._actions += actions
        self.notifyActionListeners()

    
    def removeAction(self, action: Action):
        self.checkIsRunning()
        self._actions.remove(action)
        self.notifyActionListeners()


    def swapActions(self, a: Action, b: Action):

        self.checkIsRunning()

        if a not in self._actions or b not in self._actions:
            raise Exception("Can only swap actions that are both present in the queue already.")
        
        indexA = self._actions.index(a)
        indexB = self._actions.index(b)

        self._actions[indexA] = b
        self._actions[indexB] = a

        self.notifyActionListeners()


    def swapActionsByIndex(self, a: int, b: int):

        self.checkIsRunning()

        length = len(self._actions)

        if a >= length or a < 0 or b >= length or b < 0:
            raise IndexError("Invalid index.")
        
        actionA = self._actions[a]
        actionB = self._actions[b]

        self._actions[a] = actionB
        self._actions[b] = actionA

        self.notifyActionListeners()


    def addActionListener(self, listener: Callable[[List[Action]], None]) -> Callable[[List[Action]], None]:
        self._actionListeners.append(listener)
        return listener
    

    def addMessageListener(self, listener: Callable[[Message], None]) -> Callable[[Message], None]:
        self._messageListeners.append(listener)
        return listener

    def addFinishListener(self, listener: Callable[[Result], None]) -> Callable[[Result], None]:
        self._finishListeners.append(listener)
        return listener

    
class H5ActionQueue(ActionQueue[h5py.Group]):

    def __init__(self, namePattern: str = r"Queue Run %d"):
        super().__init__()
        self._namePattern = namePattern


    @property
    def namePattern(self) -> str:
        return self._namePattern


    @namePattern.setter
    def namePattern(self, pattern: str):
        self._namePattern = pattern


    def prepareData(self, data: h5py.Group) -> h5py.Group:
        
        try:
            self._namePattern % 1
        except:
            self._namePattern = self._namePattern.replace(r"%", r"") + r"_%d"

        counter = 0
        name    = self._namePattern % counter

        while name in data:
            counter += 1
            name     = self._namePattern % counter

        return data.create_group(name)
    
    def finaliseData(self, data, result):
        from datetime import datetime
        data.create_dataset("Messages", data=[[datetime.fromtimestamp(m.timestamp).strftime(r'%Y-%m-%d %H:%M:%S'), m.pathString, m.type.name, m.message] for m in result.messages])


class AnyActionQueue(ActionQueue[object]):

    def __init(self):
        super().__init__()

    def prepareData(self, data):
        return data

    def finaliseData(self, data, result):
        pass


    