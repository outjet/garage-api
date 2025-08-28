from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from functools import wraps
import RPi.GPIO as gpio
import time
import jwt
import datetime
import logging
import os

# Initialize Flask and CORS
app = Flask(__name__)
CORS(app)

# Initialize logging with timestamp
log_level = os.environ.get('LOG_LEVEL', 'DEBUG')
logging.basicConfig(
    filename='flask-door.log',
    level=log_level,
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


# Fetch from environment variables or fallback to defaults
SECRET_KEY = os.environ.get('SECRET_KEY', 'af32m09FAnienafpxx09gg32ppMnanM')
USER_NAME = os.environ.get('USER_NAME', 'outjet')
USER_PASSWORD = os.environ.get('USER_PASSWORD', 'gaxxe')

# GPIO Pin Constants
PIN_DOWN_SENSOR = 20
PIN_UP_SENSOR = 21
PIN_DOOR_CONTROL = 16
PIN_BUZZER = 19

# GPIO setup (Do it once)
def setup_gpio():
    gpio.setmode(gpio.BCM)
    gpio.setup(PIN_DOWN_SENSOR, gpio.IN, pull_up_down=gpio.PUD_UP)
    gpio.setup(PIN_UP_SENSOR, gpio.IN, pull_up_down=gpio.PUD_UP)
    gpio.setup(PIN_DOOR_CONTROL, gpio.OUT)
    gpio.setup(PIN_BUZZER, gpio.OUT)

# Cleanup GPIO resources
def cleanup_gpio():
    gpio.cleanup()

# Existing code: token_required, buzz_buzzer, etc.
# Define a decorator for token required
def token_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        if request.endpoint == 'get_token':
            return f(*args, **kwargs)

        token = request.headers.get("Authorization")
        if not token:
            return jsonify(error="Token required"), 401
        try:
            jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify(error="Token expired"), 401
        except:
            return jsonify(error="Invalid token"), 401
        return f(*args, **kwargs)
    return decorator

# Toggle the door
def toggle_door():
    activate_gpio_pin(PIN_DOOR_CONTROL, 0.5)

# Buzzer function
def buzz_buzzer():
    activate_gpio_pin(PIN_BUZZER, 0.5)

# Activate GPIO pin for a duration
def activate_gpio_pin(pin, duration):
    gpio.output(pin, gpio.HIGH)
    time.sleep(duration)
    gpio.output(pin, gpio.LOW)

# Check if door is down
def is_door_down():
    return gpio.input(PIN_DOWN_SENSOR) == gpio.LOW

# Check if door is up
def is_door_up():
    return gpio.input(PIN_UP_SENSOR) == gpio.LOW

# Global error handler
@app.errorhandler(Exception)
def handle_exception(e: Exception):
    logging.error(f"An unexpected error occurred: {e}")
    return jsonify(error=str(e)), 500

toggle_door()
