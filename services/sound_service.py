"""
Centralized service for sound management
"""
import pygame
import os
import time
import logging
import traceback

# Configure logging
logger = logging.getLogger("SoundService")

class SoundService:
    """Centralized service for sound operations"""
    
    def __init__(self):
        self.sounds = {}
        self.last_sound_time = 0
        self.last_sound_name = ""
        self.pygame_available = False
        self.initialize()
    
    def initialize(self):
        """Initialize the sound system"""
        try:
            # Initialize pygame for sound support
            self.pygame_available = self._initialize_pygame_mixer()
            
            if self.pygame_available:
                self.load_sounds()
                logger.info(f"Sound service initialized with {len(self.sounds)} sounds")
            else:
                logger.warning("Sound service initialized but pygame is not available")
                
            return self.pygame_available
        except Exception as e:
            logger.error(f"Error initializing sound service: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def _initialize_pygame_mixer(self):
        """Initialize pygame mixer with multiple fallback configurations"""
        try:
            # Try multiple initialization configurations
            init_configs = [
                # Try default config first
                {"frequency": 44100, "size": -16, "channels": 2, "buffer": 4096},
                # Fallback configs with more compatible settings
                {"frequency": 44100, "size": 16, "channels": 2, "buffer": 1024},
                {"frequency": 48000, "size": -16, "channels": 1, "buffer": 1024},
                {"frequency": 22050, "size": -16, "channels": 1, "buffer": 512},
                # Minimal configuration as last resort
                {"frequency": 22050, "size": 8, "channels": 1, "buffer": 512},
                # Try with no parameters as final fallback
                {}
            ]
            
            # Try each configuration until one works
            init_error = None
            for config in init_configs:
                try:
                    logger.info(f"Trying pygame.mixer.init with config: {config}")
                    pygame.mixer.init(**config)
                    logger.info(f"Successfully initialized pygame mixer with config: {config}")
                    return True
                except Exception as e:
                    init_error = e
                    logger.warning(f"Failed to initialize pygame mixer with config {config}: {e}")
                    # Try to quit mixer before trying another config
                    try:
                        pygame.mixer.quit()
                    except:
                        pass
            
            if init_error:
                logger.error(f"All pygame mixer initialization attempts failed: {init_error}")
            
            return False
        except ImportError:
            logger.error("Pygame not available for sound support")
            return False
        except Exception as e:
            logger.error(f"Unexpected error initializing pygame: {e}")
            return False
    
    def load_sounds(self):
        """Load sound effects using pygame with enhanced error handling"""
        sound_files = {
            "click": ["assets/sounds/click.ogg", "assets/sounds/click.wav", "assets/sounds/click.mp3"],
            "success": ["assets/sounds/success.ogg", "assets/sounds/success.wav", "assets/sounds/success.mp3"],
            "error": ["assets/sounds/error.ogg", "assets/sounds/error.wav", "assets/sounds/error.mp3"]
        }
        
        # Ensure sound directory exists
        os.makedirs("assets/sounds", exist_ok=True)
        
        if not self.pygame_available:
            logger.warning("Pygame not available, cannot load sounds")
            return
        
        try:
            # Try to load each sound
            for sound_name, paths in sound_files.items():
                # Try each path until one works
                loaded = False
                for path in paths:
                    if os.path.exists(path):
                        try:
                            logger.info(f"Attempting to load sound {sound_name} from {path}")
                            sound = self._load_sound(path)
                            if sound and hasattr(sound, '_sound') and sound._sound:
                                self.sounds[sound_name] = sound
                                logger.info(f"Successfully loaded sound: {sound_name} from {path}")
                                loaded = True
                                break
                            else:
                                logger.warning(f"Sound loaded but not initialized correctly: {sound_name} from {path}")
                        except Exception as e:
                            logger.warning(f"Failed to load sound {sound_name} from {path}: {e}")
                    else:
                        logger.warning(f"Sound file not found: {path}")
                
                if not loaded:
                    logger.warning(f"Could not load sound: {sound_name}, no valid paths found")
            
            logger.info(f"Loaded {len(self.sounds)} sounds")
            
        except Exception as e:
            logger.error(f"Error in load_sounds: {e}")
            logger.error(traceback.format_exc())
    
    def _load_sound(self, path):
        """Load a sound file using pygame"""
        try:
            return PyGameSound(path)
        except Exception as e:
            logger.error(f"Error loading sound {path}: {e}")
            return None
    
    def play_sound(self, sound_name="click"):
        """Play a sound by name with simple debounce and recovery on errors"""
        if not self.pygame_available:
            logger.debug(f"Cannot play sound {sound_name}: pygame not available")
            return
            
        current_time = time.time()
        
        # Debounce - avoid playing sounds too rapidly
        if sound_name == self.last_sound_name and (current_time - self.last_sound_time) < 0.05:
            return
            
        self.last_sound_time = current_time
        self.last_sound_name = sound_name
        
        # Play the sound if it's loaded
        if sound_name in self.sounds:
            try:
                # Check if the sound is actually loaded
                sound = self.sounds[sound_name]
                if not sound or not sound._sound:
                    logger.warning(f"Sound {sound_name} is not properly loaded")
                    return
                    
                # For small UI sounds, try to just play the original if available
                if sound.state == 'stop':
                    sound.play()
                else:
                    # If original is playing, try to load and play a new instance
                    new_sound = self._load_sound(sound.source)
                    if new_sound and new_sound._sound:
                        new_sound.play()
                    else:
                        logger.warning(f"Failed to create new instance of sound {sound_name}")
            except Exception as e:
                logger.warning(f"Error playing sound {sound_name}: {e}")
                
                # Try to reload the sound if error occurred
                try:
                    # Reload sound
                    if os.path.exists(self.sounds[sound_name].source):
                        self.sounds[sound_name] = self._load_sound(self.sounds[sound_name].source)
                        logger.info(f"Reloaded sound: {sound_name}")
                except Exception as reload_error:
                    logger.error(f"Error reloading sound {sound_name}: {reload_error}")
        else:
            logger.debug(f"Sound not found: {sound_name}")
    
    def load_sound_file(self, path):
        """Load a specific sound file and return the sound object"""
        if not self.pygame_available:
            logger.warning(f"Cannot load sound {path}: pygame not available")
            return None
            
        if not os.path.exists(path):
            logger.warning(f"Sound file not found: {path}")
            return None
            
        try:
            return self._load_sound(path)
        except Exception as e:
            logger.error(f"Error loading sound file {path}: {e}")
            return None
    
    def cleanup(self):
        """Clean up resources when shutting down"""
        try:
            # Stop all sounds
            for sound_name, sound in self.sounds.items():
                try:
                    if sound and sound.state != 'stop':
                        sound.stop()
                except:
                    pass
            self.sounds.clear()
            
            # Quit pygame mixer
            if self.pygame_available:
                try:
                    pygame.mixer.quit()
                    logger.info("Pygame mixer stopped")
                except:
                    pass
        except Exception as e:
            logger.error(f"Error cleaning up sounds: {e}")


class PyGameSound:
    """A wrapper class for pygame.mixer.Sound to match SoundLoader API"""
    def __init__(self, source):
        self.source = source
        self._sound = None
        self._channel = None
        self._volume = 1.0
        self._loop = 0  # 0 = no loop, -1 = infinite loop
        self._state = 'stop'
        self.length = 1.0  # Default length in seconds
        
        # Try to load the sound
        if pygame.mixer.get_init():
            try:
                self._sound = pygame.mixer.Sound(source)
            except Exception as e:
                logger.error(f"Error loading sound {source}: {e}")
    
    @property
    def volume(self):
        return self._volume
    
    @volume.setter
    def volume(self, value):
        self._volume = max(0.0, min(1.0, value))
        if self._sound:
            try:
                self._sound.set_volume(self._volume)
            except Exception as e:
                logger.error(f"Error setting volume: {e}")
    
    @property
    def state(self):
        # Update state if playing on a channel
        if self._channel and hasattr(self._channel, 'get_busy'):
            try:
                if self._channel.get_busy():
                    self._state = 'playing'
                else:
                    self._state = 'stop'
            except Exception as e:
                logger.error(f"Error checking channel state: {e}")
                self._state = 'stop'
        else:
            self._state = 'stop'
        return self._state
    
    @property
    def loop(self):
        return self._loop
    
    @loop.setter
    def loop(self, value):
        self._loop = -1 if value else 0
    
    def play(self):
        if self._sound:
            try:
                # Play on a new channel - pygame gives us back the Channel object
                self._channel = self._sound.play(loops=self._loop)
                if self._channel and hasattr(self._channel, 'set_volume'):
                    self._channel.set_volume(self._volume)
                self._state = 'playing'
            except Exception as e:
                logger.error(f"Error playing sound: {e}")
                self._state = 'stop'
    
    def stop(self):
        if self._channel and hasattr(self._channel, 'stop'):
            try:
                self._channel.stop()
                self._state = 'stop'
            except Exception as e:
                logger.error(f"Error stopping sound: {e}")