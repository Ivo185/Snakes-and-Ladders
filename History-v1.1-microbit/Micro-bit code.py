from microbit import *
import random

display.show(Image.HAPPY)

while True:
    if accelerometer.was_gesture('shake'):
        for _ in range(8):
            display.show(random.randint(1, 6))
            sleep(80)

        zar = random.randint(1, 6)
        display.show(zar)

        print(zar)

        sleep(1000)