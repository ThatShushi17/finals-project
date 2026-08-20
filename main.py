# TODO: remove some stuff in shaders/simulation/?

import pygame
from engine import App

window_size = (1600, 900)

pygame.init()
pygame.font.init()
pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 4)
pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)

pygame_flags = pygame.OPENGL | pygame.DOUBLEBUF #| pygame.RESIZABLE
pygame.display.set_mode(window_size, pygame_flags)
pygame.display.set_caption("Physics Simulation")

app = App(window_size)

while app.running:
	app.tick()

pygame.quit()
quit()