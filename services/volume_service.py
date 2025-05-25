"""
Volume Control Service for physical buttons
Handles GPIO button presses for volume up/down control
"""
import time
import subprocess
import logging
from threading import Thread, Lock
from utils.error_handler import ErrorHandler

# Configure logging
logger = logging.getLogger("VolumeControlService")

# GPIO pins for volume buttons
VOLUME_UP_PIN = 23
VOLUME_DOWN_PIN = 24

# Volume control settings
MIN_VOLUME = 0
MAX_VOLUME = 100
VOLUME_STEP = 5
DEBOUNCE_TIME = 0.2  # seconds

class VolumeControlService:
    """Service for handling physical volume control buttons"""
    
    def __init__(self, app=None):
        """Initialize volume control service
        
        Args:
            app: Main application instance for sound feedback
        """
        self.app = app
        self.running = False
        self.thread = None
        
        # GPIO setup
        self.gpio_available = False
        self.gpio_lib = None
        self.gpio_handle = None
        
        # Volume state
        self._current_volume = self._get_system_volume()
        self._volume_lock = Lock()
        
        # Button state tracking
        self._last_button_time = {VOLUME_UP_PIN: 0, VOLUME_DOWN_PIN: 0}
        self._last_button_state = {VOLUME_UP_PIN: True, VOLUME_DOWN_PIN: True}  # True = not pressed (pull-up)
        
        # Callback events
        self._volume_change_callback = None
        
        logger.info("Volume control service initialized")
    
    @ErrorHandler.handle_exception
    def start(self):
        """Start the volume control service"""
        try:
            # Initialize GPIO
            self._init_gpio()
            
            if not self.gpio_available:
                logger.warning("GPIO not available - volume buttons disabled")
                return False
            
            # Get initial volume
            self._current_volume = self._get_system_volume()
            logger.info(f"Initial system volume: {self._current_volume}%")
            
            # Start monitoring thread
            self.running = True
            self.thread = Thread(target=self._monitor_buttons, daemon=True)
            self.thread.start()
            
            logger.info("Volume control service started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error starting volume control service: {e}")
            return False
    
    def _init_gpio(self):
        """Initialize GPIO for volume buttons"""
        try:
            # Try lgpio first (preferred for Pi 5)
            try:
                import lgpio
                self.gpio_handle = lgpio.gpiochip_open(0)
                
                # Set up both buttons with pull-up resistors
                lgpio.gpio_claim_input(self.gpio_handle, VOLUME_UP_PIN, lgpio.SET_PULL_UP)
                lgpio.gpio_claim_input(self.gpio_handle, VOLUME_DOWN_PIN, lgpio.SET_PULL_UP)
                
                self.gpio_lib = "lgpio"
                self.gpio_available = True
                logger.info(f"GPIO initialized with lgpio (pins {VOLUME_UP_PIN}, {VOLUME_DOWN_PIN})")
                return
                
            except ImportError:
                logger.info("lgpio not available, trying RPi.GPIO")
            except Exception as e:
                logger.warning(f"lgpio initialization failed: {e}")
            
            # Fallback to RPi.GPIO
            try:
                import RPi.GPIO as GPIO
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(VOLUME_UP_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                GPIO.setup(VOLUME_DOWN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                
                self.gpio_lib = "RPi.GPIO"
                self.gpio_available = True
                logger.info(f"GPIO initialized with RPi.GPIO (pins {VOLUME_UP_PIN}, {VOLUME_DOWN_PIN})")
                return
                
            except ImportError:
                logger.warning("RPi.GPIO not available")
            except Exception as e:
                logger.warning(f"RPi.GPIO initialization failed: {e}")
            
            # No GPIO available
            self.gpio_available = False
            logger.warning("No GPIO library available for volume buttons")
            
        except Exception as e:
            logger.error(f"Error initializing GPIO: {e}")
            self.gpio_available = False
    
    def _read_button(self, pin):
        """Read button state from GPIO"""
        try:
            if not self.gpio_available:
                return True  # Not pressed
                
            if self.gpio_lib == "lgpio":
                import lgpio
                return bool(lgpio.gpio_read(self.gpio_handle, pin))
            elif self.gpio_lib == "RPi.GPIO":
                import RPi.GPIO as GPIO
                return bool(GPIO.input(pin))
            else:
                return True
                
        except Exception as e:
            logger.error(f"Error reading button {pin}: {e}")
            return True
    
    def _monitor_buttons(self):
        """Background thread to monitor button presses"""
        logger.info("Button monitoring started")
        
        while self.running:
            try:
                current_time = time.time()
                
                # Check volume up button
                self._check_button(VOLUME_UP_PIN, current_time, self._volume_up)
                
                # Check volume down button  
                self._check_button(VOLUME_DOWN_PIN, current_time, self._volume_down)
                
                # Small delay to avoid excessive CPU usage
                time.sleep(0.05)  # 50ms polling
                
            except Exception as e:
                logger.error(f"Error in button monitoring: {e}")
                time.sleep(0.1)  # Brief pause on error
    
    def _check_button(self, pin, current_time, action_callback):
        """Check individual button state and handle press events"""
        try:
            current_state = self._read_button(pin)
            last_state = self._last_button_state.get(pin, True)
            last_time = self._last_button_time.get(pin, 0)
            
            # Button pressed (state goes from True to False due to pull-up)
            if last_state and not current_state:
                # Check debounce time
                if current_time - last_time > DEBOUNCE_TIME:
                    logger.debug(f"Button {pin} pressed")
                    action_callback()
                    self._last_button_time[pin] = current_time
            
            # Update state
            self._last_button_state[pin] = current_state
            
        except Exception as e:
            logger.error(f"Error checking button {pin}: {e}")
    
    def _volume_up(self):
        """Handle volume up button press"""
        try:
            with self._volume_lock:
                new_volume = min(self._current_volume + VOLUME_STEP, MAX_VOLUME)
                if new_volume != self._current_volume:
                    self._set_system_volume(new_volume)
                    self._current_volume = new_volume
                    logger.info(f"Volume up: {self._current_volume}%")
                    
                    # Play feedback sound
                    self._play_feedback_sound("success")
                    
                    # Trigger callback
                    if self._volume_change_callback:
                        self._volume_change_callback(self._current_volume, "up")
                else:
                    logger.debug("Volume already at maximum")
                    self._play_feedback_sound("error")
                    
        except Exception as e:
            logger.error(f"Error in volume up: {e}")
    
    def _volume_down(self):
        """Handle volume down button press"""
        try:
            with self._volume_lock:
                new_volume = max(self._current_volume - VOLUME_STEP, MIN_VOLUME)
                if new_volume != self._current_volume:
                    self._set_system_volume(new_volume)
                    self._current_volume = new_volume
                    logger.info(f"Volume down: {self._current_volume}%")
                    
                    # Play feedback sound
                    self._play_feedback_sound("click")
                    
                    # Trigger callback
                    if self._volume_change_callback:
                        self._volume_change_callback(self._current_volume, "down")
                else:
                    logger.debug("Volume already at minimum") 
                    self._play_feedback_sound("error")
                    
        except Exception as e:
            logger.error(f"Error in volume down: {e}")
    
    def _get_system_volume(self):
        """Get current system volume level"""
        try:
            # Use amixer to get master volume
            result = subprocess.run(
                ['amixer', 'get', 'Master'], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            
            if result.returncode == 0:
                # Parse volume from output
                for line in result.stdout.split('\n'):
                    if '[' in line and '%' in line:
                        # Extract percentage
                        start = line.find('[') + 1
                        end = line.find('%')
                        if start > 0 and end > start:
                            volume_str = line[start:end]
                            return int(volume_str)
            
            logger.warning("Could not parse volume from amixer output")
            return 50  # Default volume
            
        except subprocess.TimeoutExpired:
            logger.error("Timeout getting system volume")
            return 50
        except Exception as e:
            logger.error(f"Error getting system volume: {e}")
            return 50
    
    def _set_system_volume(self, volume):
        """Set system volume level"""
        try:
            # Ensure volume is within bounds
            volume = max(MIN_VOLUME, min(volume, MAX_VOLUME))
            
            # Use amixer to set master volume
            result = subprocess.run(
                ['amixer', 'set', 'Master', f'{volume}%'], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to set volume: {result.stderr}")
                return False
                
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("Timeout setting system volume")
            return False
        except Exception as e:
            logger.error(f"Error setting system volume: {e}")
            return False
    
    def _play_feedback_sound(self, sound_name):
        """Play feedback sound for button press"""
        try:
            if self.app and hasattr(self.app, 'play_sound'):
                self.app.play_sound(sound_name)
        except Exception as e:
            logger.debug(f"Could not play feedback sound: {e}")
    
    def stop(self):
        """Stop the volume control service"""
        self.running = False
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        
        # Cleanup GPIO
        try:
            if self.gpio_lib == "lgpio" and self.gpio_handle is not None:
                import lgpio
                lgpio.gpiochip_close(self.gpio_handle)
            elif self.gpio_lib == "RPi.GPIO":
                import RPi.GPIO as GPIO
                GPIO.cleanup([VOLUME_UP_PIN, VOLUME_DOWN_PIN])
        except Exception as e:
            logger.error(f"Error cleaning up GPIO: {e}")
        
        logger.info("Volume control service stopped")
    
    def get_volume(self):
        """Get current volume level"""
        with self._volume_lock:
            return self._current_volume
    
    def set_volume(self, volume):
        """Set volume level programmatically"""
        try:
            with self._volume_lock:
                volume = max(MIN_VOLUME, min(volume, MAX_VOLUME))
                if self._set_system_volume(volume):
                    self._current_volume = volume
                    logger.info(f"Volume set to: {volume}%")
                    
                    # Trigger callback
                    if self._volume_change_callback:
                        self._volume_change_callback(volume, "set")
                    
                    return True
                return False
        except Exception as e:
            logger.error(f"Error setting volume: {e}")
            return False
    
    def set_volume_change_callback(self, callback):
        """Set callback function for volume changes
        
        Args:
            callback: Function to call with (volume, action) parameters
                     action can be 'up', 'down', or 'set'
        """
        self._volume_change_callback = callback
        logger.info("Volume change callback set")
    
    def get_status(self):
        """Get service status for debugging"""
        return {
            'running': self.running,
            'gpio_available': self.gpio_available,
            'gpio_lib': self.gpio_lib,
            'current_volume': self._current_volume,
            'volume_step': VOLUME_STEP,
            'debounce_time': DEBOUNCE_TIME,
            'button_pins': {
                'volume_up': VOLUME_UP_PIN,
                'volume_down': VOLUME_DOWN_PIN
            }
        }