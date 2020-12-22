import pygame
from pygame.locals import *
import random

import asyncio
import alpha_packet
from bleak import discover,BleakClient


class GameParams:
    def __init__(self):
        self.scroll_speed = 4
        self.pipe_gap = 200
        self.pipe_frequency = 1500
        self.screen_width = 864
        self.screen_height = 936
        self.fps = 60
        self.font = pygame.font.SysFont('Bauhaus 93', 60)
        self.bg = pygame.image.load('img/bg.png')
        self.ground_img = pygame.image.load('img/ground.png')


class GameState:
    def __init__(self):
        self.flying = False
        self.game_over = False
        self.last_pipe = -1500
        self.score = 0
        self.pass_pipe = False
        self.run = True
        self.ground_scroll = 0
        self.myo_clicked = False


class Bird(pygame.sprite.Sprite):

    def __init__(self, x, y, game_state):
        pygame.sprite.Sprite.__init__(self)
        self.images = []
        self.index = 0
        self.counter = 0
        for num in range (1, 4):
            img = pygame.image.load(f"img/bird{num}.png")
            self.images.append(img)
        self.image = self.images[self.index]
        self.rect = self.image.get_rect()
        self.rect.center = [x, y]
        self.vel = 0
        self.clicked = False
        self.game_state = game_state

    def update(self):

        if self.game_state.flying == True:
            #apply gravity
            self.vel += 0.5
            if self.vel > 8:
                self.vel = 8
            if self.rect.bottom < 768:
                self.rect.y += int(self.vel)

        if self.game_state.game_over == False:
            #jump
            if (pygame.mouse.get_pressed()[0] == 1 or gstate.myo_clicked) and not self.clicked:
                self.clicked = True
                self.vel = -10
            if pygame.mouse.get_pressed()[0] == 0 and not gstate.myo_clicked:
                self.clicked = False

            #handle the animation
            flap_cooldown = 5
            self.counter += 1
            
            if self.counter > flap_cooldown:
                self.counter = 0
                self.index += 1
                if self.index >= len(self.images):
                    self.index = 0
                self.image = self.images[self.index]


            #rotate the bird
            self.image = pygame.transform.rotate(self.images[self.index], self.vel * -2)
        else:
            #point the bird at the ground
            self.image = pygame.transform.rotate(self.images[self.index], -90)



class Pipe(pygame.sprite.Sprite):
    def __init__(self, x, y, position, pipe_gap, scroll_speed):
        pygame.sprite.Sprite.__init__(self)
        self.image = pygame.image.load("img/pipe.png")
        self.rect = self.image.get_rect()
        self.scroll_speed = scroll_speed
        #position variable determines if the pipe is coming from the bottom or top
        #position 1 is from the top, -1 is from the bottom
        if position == 1:
            self.image = pygame.transform.flip(self.image, False, True)
            self.rect.bottomleft = [x, y - int(pipe_gap / 2)]
        elif position == -1:
            self.rect.topleft = [x, y + int(pipe_gap / 2)]

    def update(self):
        self.rect.x -= self.scroll_speed
        if self.rect.right < 0:
            self.kill()



class Button():
    def __init__(self, x, y, image):
        self.image = image
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)

    def draw(self, screen):
        action = False

        #get mouse position
        pos = pygame.mouse.get_pos()

        #check mouseover and clicked conditions
        if self.rect.collidepoint(pos):
            if pygame.mouse.get_pressed()[0] == 1:
                action = True

        #draw button
        screen.blit(self.image, (self.rect.x, self.rect.y))

        return action


def disconnect_callback(client):
    print('Client {0} disconnected'.format(client.address))


def notify_callback(sender: int, data: bytearray):
    packet = alpha_packet.unpack_packet(data)
    myo_val = packet['myo']
    if myo_val > 100:
        gstate.myo_clicked = True
    else:
        gstate.myo_clicked = False


async def connect_to_alpha():
    alpha_dev = None
    print('--------------------------')
    print('-- Scanning for devices --')
    print('--------------------------')
    devices = await discover()
    for d in devices:
        print(d)
        if 'FANTMalpha' in d.name:
            alpha_dev = d
    print('***Found Device: {0}'.format(alpha_dev))
    client = BleakClient(alpha_dev.address)
    try:
        await client.connect()
    except Exception as e:
        print(e)
    print('-----------------------')
    print('-- Scanning services --')
    print('-----------------------')
    svcs = await client.get_services()
    nus_svc = None
    for s in svcs:
        print(s)
        if 'Nordic UART Service' in s.description:
            nus_svc = s
    print('***Found Service: {0}'.format(nus_svc))
    print('------------------------------')
    print('-- Scanning characteristics --')
    print('------------------------------')
    nus_svc_tx = None
    for ch in nus_svc.characteristics:
        print(ch)
        if 'Nordic UART TX' in ch.description:
            nus_svc_tx = ch
    print('***Found Characteristic: {0}'.format(nus_svc_tx))
    print('---------------------------------')
    print('-- Listening for notifications --')
    print('---------------------------------')
    client.set_disconnected_callback(disconnect_callback)
    await client.start_notify(nus_svc_tx.uuid, notify_callback)
    return client


#function for outputting text onto the screen
def draw_text(screen, text, font, x, y):
    img = font.render(text, True, (255,255,255))
    screen.blit(img, (x, y))


def reset_game(pipe_group, flappy):
    pipe_group.empty()
    flappy.rect.x = 100
    flappy.rect.y = int(gparams.screen_height / 2)
    gstate.score = 0

async def main():
    # connect to alpha
    client = await connect_to_alpha()
    # init screen and clock
    screen = pygame.display.set_mode((gparams.screen_width, gparams.screen_height))
    pygame.display.set_caption('Flappy Bird')
    clock = pygame.time.Clock()
    # create ad hoc restart button
    button_img = pygame.image.load('img/restart.png')
    button = Button(gparams.screen_width // 2 - 50, gparams.screen_height // 2 - 100, button_img)
    # create the sprite groups for collision
    white = (255,255,255)
    pipe_group = pygame.sprite.Group()
    bird_group = pygame.sprite.Group()
    flappy = Bird(100, int(gparams.screen_height / 2), gstate)
    bird_group.add(flappy)

    while gstate.run:
        await asyncio.sleep(0.01)
        clock.tick(gparams.fps)

        #draw background
        screen.blit(gparams.bg, (0,0))

        # draw the active sprites
        pipe_group.draw(screen)
        bird_group.draw(screen)
        bird_group.update()

        #draw and scroll the ground
        screen.blit(gparams.ground_img, (gstate.ground_scroll, 768))

        #check the score
        if len(pipe_group) > 0:
            if bird_group.sprites()[0].rect.left > pipe_group.sprites()[0].rect.left\
                and bird_group.sprites()[0].rect.right < pipe_group.sprites()[0].rect.right\
                and gstate.pass_pipe == False:
                gstate.pass_pipe = True
            if gstate.pass_pipe == True:
                if bird_group.sprites()[0].rect.left > pipe_group.sprites()[0].rect.right:
                    gstate.score += 1
                    gstate.pass_pipe = False
        draw_text(screen, str(gstate.score), gparams.font, int(gparams.screen_width / 2), 20)

        #look for collision
        if pygame.sprite.groupcollide(bird_group, pipe_group, False, False) or flappy.rect.top < 0:
            gstate.game_over = True
        #once the bird has hit the ground it's game over and no longer flying
        if flappy.rect.bottom >= 768:
            gstate.game_over = True
            gstate.flying = False

        if gstate.flying == True and gstate.game_over == False:
            #generate new pipes
            time_now = pygame.time.get_ticks()
            if time_now - gstate.last_pipe > gparams.pipe_frequency:
                pipe_height = random.randint(-100, 100)
                btm_pipe = Pipe(gparams.screen_width, int(gparams.screen_height / 2) + pipe_height, -1, gparams.pipe_gap, gparams.scroll_speed)
                top_pipe = Pipe(gparams.screen_width, int(gparams.screen_height / 2) + pipe_height, 1, gparams.pipe_gap, gparams.scroll_speed)
                pipe_group.add(btm_pipe)
                pipe_group.add(top_pipe)
                gstate.last_pipe = time_now

            pipe_group.update()

            gstate.ground_scroll -= gparams.scroll_speed
            if abs(gstate.ground_scroll) > 35:
                gstate.ground_scroll = 0

        #check for game over and reset
        if gstate.game_over == True:
            if button.draw(screen):
                gstate.game_over = False
                reset_game(pipe_group, flappy)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                gstate.run = False
            if event.type == pygame.MOUSEBUTTONDOWN and not gstate.flying and not gstate.game_over:
                gstate.flying = True

        pygame.display.update()



pygame.init()
# init game state
gparams = GameParams()
gstate = GameState()
asyncio.run(main())
pygame.quit()
