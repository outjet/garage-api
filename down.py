import RPi.GPIO as gpio
import time

# GPIO Pin Constants
PIN_DOOR_CONTROL = 16

# GPIO setup
gpio.setmode(gpio.BCM)
gpio.setup(PIN_DOOR_CONTROL, gpio.OUT)

# Activate GPIO pin for a duration to close the door
def force_close_door():
    gpio.output(PIN_DOOR_CONTROL, gpio.HIGH)
    time.sleep(0.5)  # Adjust duration as necessary
    gpio.output(PIN_DOOR_CONTROL, gpio.LOW)
    gpio.cleanup()

if __name__ == "__main__":
    force_close_door()
