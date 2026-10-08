from ..components import Tab, TabHandler, Button, Label, Container

from collections.abc import Callable

class OptionsTab(Tab):
    def __int__(
        self,
        handler: TabHandler,
        title: str,
        button_names: list[str],
        button_callbacks: list[Callable[[], None]]
    ):
        self.container = Container()
        super().__init__(handler, [self.container])
        
        self.title = Label((0, 0), title)
        self.container.add_child(self.title)
        for name, callback in zip(button_names, button_callbacks):
            self.container.add_child(Button((0, 0), (1, 1), name, callback))