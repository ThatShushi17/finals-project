from ..components import Tab, TabHandler#, Plot, Frame

class SimulationTab(Tab):
    def __int__(
        self,
        handler: TabHandler,
    ):
        super().__init__(handler=handler)