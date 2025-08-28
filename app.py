from flask import Flask, jsonify, request
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
from functools import wraps
import RPi.GPIO as gpio
import time
import jwt
import datetime
import logging
import os
from dotenv import load_dotenv
import threading

# Load environment variables
load_dotenv()

# Initialize logging with timestamp
log_level = os.getenv('LOG_LEVEL', 'INFO')
logging.basicConfig(
    filename='/garage/garage_project/flask-door.log',
    level=log_level,
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Fetch from environment variables
SECRET_KEY = os.getenv('SECRET_KEY')
USER_NAME = os.getenv('USER_NAME')
USER_PASSWORD = os.getenv('USER_PASSWORD')
PORT = int(os.getenv('PORT', 8443))

# Ensure required environment variables are set
if not all([SECRET_KEY, USER_NAME, USER_PASSWORD]):
    logging.error("Missing required environment variables. Please check your .env file.")
    raise EnvironmentError("Missing required environment variables")

# GPIO Pin Constants
PIN_DOWN_SENSOR = int(os.getenv('PIN_DOWN_SENSOR', 20))
PIN_UP_SENSOR = int(os.getenv('PIN_UP_SENSOR', 21))
PIN_DOOR_CONTROL = int(os.getenv('PIN_DOOR_CONTROL', 16))
PIN_BUZZER = int(os.getenv('PIN_BUZZER', 19))

# GPIO setup function
def setup_gpio():
    gpio.setmode(gpio.BCM)
    gpio.setwarnings(False)  # silence “channel already in use”
    gpio.setup(PIN_DOWN_SENSOR, gpio.IN, pull_up_down=gpio.PUD_UP)
    gpio.setup(PIN_UP_SENSOR, gpio.IN, pull_up_down=gpio.PUD_UP)
    gpio.setup(PIN_DOOR_CONTROL, gpio.OUT)
    gpio.setup(PIN_BUZZER, gpio.OUT)
    logging.info("GPIO setup completed")

# Cleanup GPIO resources
def cleanup_gpio():
    gpio.cleanup()
    logging.info("GPIO cleanup completed")

# Initialize Flask, CORS, and HTTPBasicAuth
app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "https://outgar.duckdns.org:8443",
            "https://lkwd.agency"
        ],
        "supports_credentials": False,
        "methods": ["GET", "POST"],
        "allow_headers": ["Authorization", "Content-Type"]
    }
})
auth = HTTPBasicAuth()

users = {
    USER_NAME: generate_password_hash(USER_PASSWORD)
}

@auth.verify_password
def verify_password(username, password):
    if username in users and check_password_hash(users.get(username), password):
        return username

# One-time GPIO setup
with app.app_context():
    setup_gpio()

# single relay fire at a time
relay_lock = threading.Lock()

# Define a decorator for token required
def token_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        authz = request.headers.get("Authorization", "")
        parts = authz.split()
        token = parts[1] if len(parts) == 2 and parts[0].lower() == "bearer" else None
        if not token:
            logging.warning("Request without token")
            return jsonify(error="Token required"), 401
        try:
            jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            logging.debug("Token successfully decoded")
        except jwt.ExpiredSignatureError:
            logging.warning("Expired token used")
            return jsonify(error="Token expired"), 401
        except jwt.InvalidTokenError:
            logging.warning("Invalid token used")
            return jsonify(error="Invalid token"), 401
        return f(*args, **kwargs)
    return decorator

# Toggle the door
def toggle_door():
    logging.info("Toggling door")
    activate_gpio_pin(PIN_DOOR_CONTROL, 0.5)

# Buzzer function
def buzz_buzzer():
    logging.info("Activating buzzer")
    activate_gpio_pin(PIN_BUZZER, 0.5)

# Activate GPIO pin for a duration
def activate_gpio_pin(pin, duration):
    logging.debug(f"Activating GPIO pin {pin} for {duration} seconds")
    with relay_lock:
        gpio.output(pin, gpio.HIGH)
        try:
            time.sleep(duration)
        finally:
            gpio.output(pin, gpio.LOW)
    logging.debug(f"GPIO pin {pin} deactivated")

# Check if door is down
def is_door_down():
    status = gpio.input(PIN_DOWN_SENSOR) == gpio.LOW
    logging.debug(f"Door down status: {status}")
    return status

# Check if door is up
def is_door_up():
    status = gpio.input(PIN_UP_SENSOR) == gpio.LOW
    logging.debug(f"Door up status: {status}")
    return status

# Global error handler
@app.errorhandler(Exception)
def handle_exception(e):
    logging.error(f"An unexpected error occurred: {e}", exc_info=True)
    return jsonify(error="An unexpected error occurred"), 500

# Routes
@app.route("/api/token", methods=["POST"])
@auth.login_required
def get_token():
    now = datetime.datetime.utcnow()
    payload = {
        "sub": auth.current_user(),
        "iat": now,
        "nbf": now,
        "exp": now + datetime.timedelta(minutes=30)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    logging.info(f"Token generated for user: {auth.current_user()}")
    return jsonify(token=token)

@app.route("/api/door/up", methods=["POST"])
@token_required
def door_up():
    logging.info("Request received to move door up")
    if is_door_up():
        logging.info("Door is already up")
        return jsonify(status="Door is already up"), 200
    toggle_door()
    logging.info("Door movement initiated (up)")
    return jsonify(status="Door is going up"), 200

@app.route("/api/door/down", methods=["POST"])
@token_required
def door_down():
    logging.info("Request received to move door down")
    if is_door_down():
        logging.info("Door is already down")
        return jsonify(status="Door is already down"), 200
    toggle_door()
    logging.info("Door movement initiated (down)")
    return jsonify(status="Door is going down"), 200

@app.route("/api/door/status", methods=["GET"])
@token_required
def door_status():
    logging.debug("Auth=%s, Origin=%s, UA=%s", request.headers.get("Authorization"), request.headers.get("Origin"), request.headers.get("User-Agent"))
    logging.debug("Auth=%s, Origin=%s, UA=%s", request.headers.get("Authorization"), request.headers.get("Origin"), request.headers.get("User-Agent"))
    logging.info("Request received for door status")
    if is_door_down():
        status = "down"
    elif is_door_up():
        status = "up"
    else:
        status = "in_transition"
    logging.info(f"Current door status: {status}")
    return jsonify(status=status)

@app.route('/health', methods=['GET'])
def health_check():
    logging.debug("Health check request received")
    return jsonify(status='healthy'), 200

if __name__ == "__main__":
    logging.info("Starting Flask application")
    try:
        # behind gunicorn/nginx -> no adhoc SSL here
        app.run(host="0.0.0.0", port=PORT)
    except Exception as e:
        logging.error(f"An error occurred while running the Flask app: {e}", exc_info=True)
    finally:
        cleanup_gpio()
        logging.info("Flask application shutting down")
