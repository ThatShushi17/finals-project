import pygame

class FrameData:
	def __init__(self):
		self.cur_frame = -1
		self.window_size = pygame.display.get_surface().get_size()
		self.consumed_events: set[int] = set()

	def update(self, dt: float):
		self.cur_frame += 1
		self.consumed_events.clear()

		self.mouse_pos = pygame.mouse.get_pos()
		self.events = pygame.event.get()
		self.dt = dt

		new_window_size = pygame.display.get_surface().get_size()
		self.window_resized = new_window_size == self.window_size
		self.window_size = new_window_size

	def is_event_consumed(self, event: pygame.event.Event) -> bool:
		return id(event) in self.consumed_events

	def consume_event(self, event: pygame.event.Event) -> None:
		self.consumed_events.add(id(event))
