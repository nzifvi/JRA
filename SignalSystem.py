from enum import Enum, auto

class ComponentState(Enum):
    INIT    = auto()
    RUNNING = auto()
    ERROR   = auto()
    STOP    = auto()

class RobotState(Enum):
    ROTATE         = auto()
    DRIVE          = auto()
    INIT           = auto()
    PATH_BLOCKED   = auto()
    FINISHED       = auto()

class Channel:
    def __init__(self, name:str, states):
        self.channelName = name
        self.states = states

        self.state = None
        self.value = None

    def setState(self, state):
        if state in self.states:
            self.state = state
        else:
            raise ValueError(f"State {state} is not a valid state for {self.channelName} channel")

    def setValue(self, value):
        self.value = value

    def getState(self):
        return self.state

    def getValue(self):
        return self.value

class BiDirectionalChannel:
    def __init__(self, name, masterStates, workerStates):
        self.workerChannel = Channel("worker", workerStates)
        self.masterChannel = Channel(name, masterStates)

    def setMasterChannelState(self, state):
        self.masterChannel.setState(state)

    def setMasterChannelValue(self, value):
        self.masterChannel.setValue(value)

    def getMasterChannelState(self):
        return self.masterChannel.getState()

    def getMasterChannelValue(self):
        return self.masterChannel.getValue()

    def setWorkerChannelState(self, state):
        self.workerChannel.setState(state)

    def setWorkerChannelValue(self, value):
        self.workerChannel.setValue(value)

    def getWorkerChannelState(self):
        return self.workerChannel.getState()

    def getWorkerChannelValue(self):
        return self.workerChannel.getValue()
