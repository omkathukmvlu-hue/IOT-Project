"""
GPIO output configuration.
GPIO17 / physical pin 11 drives the LED through a series resistor.
Buzzer is intentionally not enabled until its voltage/current is confirmed.
"""
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO = None
    GPIO_AVAILABLE = False

LED_PIN = 17  # BCM GPIO17, physical pin 11
_initialized = False

def setup():
    global _initialized
    if not GPIO_AVAILABLE or _initialized:
        return
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LED_PIN, GPIO.OUT, initial=GPIO.LOW)
    _initialized = True

def set_alarm_outputs(active):
    setup()
    if GPIO_AVAILABLE and _initialized:
        GPIO.output(LED_PIN, GPIO.HIGH if active else GPIO.LOW)

def cleanup():
    if GPIO_AVAILABLE and _initialized:
        try:
            GPIO.output(LED_PIN, GPIO.LOW)
            GPIO.cleanup(LED_PIN)
        except Exception:
            pass
