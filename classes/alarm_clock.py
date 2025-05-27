from datetime import datetime
from kivy.clock import Clock
from classes.alarm_popup import AlarmPopup
import logging
import os
import traceback

# Configure logging
logger = logging.getLogger("AlarmClock")

class AlarmClock:
    """Manages alarm checking and triggering"""
    
    def __init__(self, app, check_interval=30):
        """
        Initialize alarm clock service
        
        Args:
            app: Main application instance
            check_interval: How often to check alarm time in seconds
        """
        self.app = app
        self.check_interval = check_interval
        self.alarm_event = None
        self.active_popup = None
        self.last_check_date = None  # To detect date changes
        self.debug_mode = True  # Enable debug logging
        self.check_count = 0  # Counter for debugging
        
        # FIXED: Add protection flags
        self._popup_creating = False
        self._last_trigger_time = None
        
    def start(self):
        """Start the alarm clock service"""
        # Check every 30 seconds by default
        self.alarm_event = Clock.schedule_interval(self.check_alarm, self.check_interval)
        logger.info(f"✅ Alarm clock service started (check interval: {self.check_interval}s)")
        
        # Immediate check for debugging
        Clock.schedule_once(lambda dt: self.check_alarm(dt, force_debug=True), 1)
        
    def stop(self):
        """Stop the alarm clock service"""
        if self.alarm_event:
            self.alarm_event.cancel()
            self.alarm_event = None
        
        # Close any active popups safely
        if self.active_popup:
            try:
                # FIXED: Don't call stop_alarm on popup to avoid recursion
                self.active_popup._stop_sound_only()
                self.active_popup = None
            except Exception as e:
                logger.error(f"❌ Error stopping popup: {e}")
                self.active_popup = None
                
        logger.info("✅ Alarm clock service stopped")
        
    def check_alarm(self, dt, force_debug=False):
        """Check if it's time to trigger the alarm"""
        self.check_count += 1
        current_time = datetime.now()
        current_date = current_time.date()
        
        # Debug logging every 10 checks or when forced
        should_debug = self.debug_mode and (self.check_count % 10 == 0 or force_debug)
        
        if should_debug:
            logger.info(f"🔍 Alarm check #{self.check_count} at {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # If date changed, log it (helpful for debugging)
        if self.last_check_date != current_date:
            self.last_check_date = current_date
            logger.info(f"📅 Date changed to {current_date}")
            
        # Get current day of week (Mon, Tue, etc.)
        current_day = current_time.strftime("%a")
        
        # Format current time to HH:MM
        current_time_str = current_time.strftime("%H:%M")
        
        # Get alarm settings
        alarm = self.app.alarm_service.get_alarm()
        if not alarm:
            if should_debug:
                logger.warning("❌ No alarm configuration found")
            return
            
        alarm_time = alarm.get("time", "")
        alarm_enabled = alarm.get("enabled", False)
        alarm_repeat = alarm.get("repeat", [])
        alarm_ringtone = alarm.get("ringtone", "morning.mp3")
        alarm_fadein = alarm.get("fadein", False)
        
        if should_debug:
            logger.info(f"⏰ Alarm config: time={alarm_time}, enabled={alarm_enabled}")
            logger.info(f"📅 Current: {current_time_str} on {current_day}")
            logger.info(f"🔄 Repeat days: {alarm_repeat}")
            logger.info(f"🎵 Ringtone: {alarm_ringtone}, fadein: {alarm_fadein}")
            logger.info(f"🖥️ Active popup: {self.active_popup is not None}")
        
        # Check individual conditions
        time_matches = current_time_str == alarm_time
        day_matches = current_day in alarm_repeat
        
        if should_debug:
            logger.info(f"🔍 Conditions: enabled={alarm_enabled}, time_match={time_matches}, day_match={day_matches}")
        
        # FIXED: Prevent duplicate triggers within same minute
        current_minute_key = f"{current_date}_{current_time_str}"
        if self._last_trigger_time == current_minute_key:
            if should_debug:
                logger.info("⏸️ Already triggered this minute, skipping")
            return
        
        # Check if alarm should trigger
        if alarm_enabled and time_matches and day_matches:
            logger.info(f"🚨 ALARM TRIGGERED! Time: {current_time_str}, Day: {current_day}")
            
            # Check if ringtone file exists
            ringtone_path = os.path.join("media/ringtones", alarm_ringtone)
            if not os.path.exists(ringtone_path):
                logger.warning(f"❌ Alarm triggered but ringtone file not found: {ringtone_path}")
                # List available files for debugging
                try:
                    ringtone_dir = "media/ringtones"
                    if os.path.exists(ringtone_dir):
                        available_files = os.listdir(ringtone_dir)
                        logger.info(f"📁 Available ringtones: {available_files}")
                    else:
                        logger.warning(f"📁 Ringtones directory doesn't exist: {ringtone_dir}")
                except Exception as e:
                    logger.error(f"❌ Error listing ringtones: {e}")
                
                # Fall back to system sound
                self.app.play_sound("error")
                return
            
            logger.info(f"🎵 Ringtone file found: {ringtone_path}")
            
            # Mark this minute as triggered
            self._last_trigger_time = current_minute_key
            
            # Trigger alarm
            self.trigger_alarm(alarm_ringtone, alarm_fadein)
        else:
            # Log why alarm didn't trigger (but only occasionally to avoid spam)
            if should_debug and alarm_enabled:
                reasons = []
                if not time_matches:
                    reasons.append(f"time mismatch (need {alarm_time}, got {current_time_str})")
                if not day_matches:
                    reasons.append(f"day mismatch (need {alarm_repeat}, got {current_day})")
                if reasons:
                    logger.info(f"⏸️ Alarm not triggered: {', '.join(reasons)}")
            elif should_debug and not alarm_enabled:
                logger.info("⏸️ Alarm disabled")
            
    def trigger_alarm(self, ringtone, fadein):
        """Show alarm popup and play sound"""
        try:
            # FIXED: Prevent multiple popups
            if self.active_popup or self._popup_creating:
                logger.warning("⚠️ Alarm already active or creating, ignoring new trigger")
                return
                
            self._popup_creating = True
            logger.info(f"🚨 Creating alarm popup with ringtone: {ringtone}")
            
            # Create and show alarm popup
            self.active_popup = AlarmPopup(ringtone=ringtone, fadein=fadein)
            
            # FIXED: Simpler dismiss handling without recursion
            self.active_popup.bind(on_dismiss=self._on_popup_dismiss_safe)
            
            self.active_popup.open()
            
            # Start playing the alarm sound
            self.active_popup.start_alarm()
            
            self._popup_creating = False
            logger.info(f"✅ Alarm triggered successfully with ringtone: {ringtone}, fadein: {fadein}")
            
            # Add system notification
            if hasattr(self.app, 'notification_service'):
                self.app.notification_service.add(f"Alarm triggered at {datetime.now().strftime('%H:%M')}", "system")
            
        except Exception as e:
            self._popup_creating = False
            logger.error(f"❌ Error triggering alarm: {e}")
            logger.error(traceback.format_exc())
        
    def _on_popup_dismiss_safe(self, instance):
        """FIXED: Safe popup dismiss handler without recursion"""
        try:
            logger.info("📤 Popup dismissed event received")
            
            # Simply clear the reference - don't try to stop anything
            # The popup handles its own cleanup in on_dismiss
            self.active_popup = None
            
            # Add notification that alarm was dismissed
            if hasattr(self.app, 'notification_service'):
                self.app.notification_service.add("Alarm dismissed", "system")
                
        except Exception as e:
            logger.error(f"❌ Error in popup dismiss handler: {e}")
            # Ensure we clear the reference even if there's an error
            self.active_popup = None
        
    def stop_alarm(self):
        """Stop the currently active alarm if any"""
        if self.active_popup:
            try:
                # FIXED: Only stop sound through popup's safe method
                self.active_popup._stop_sound_only()
                
                # Schedule dismiss to avoid recursion
                Clock.schedule_once(lambda dt: self.active_popup._dismiss_safely(), 0)
                
                logger.info("✅ Alarm stop initiated")
                return True
            except Exception as e:
                logger.error(f"❌ Error stopping alarm: {e}")
                # Force clear on error
                self.active_popup = None
                return False
        else:
            logger.info("ℹ️ No active alarm to stop")
            return False
    
    def test_alarm_now(self):
        """Test alarm immediately (for debugging)"""
        logger.info("🧪 Testing alarm immediately...")
        
        try:
            alarm = self.app.alarm_service.get_alarm()
            if not alarm:
                logger.error("❌ No alarm configuration for testing")
                return False
                
            ringtone = alarm.get("ringtone", "morning.mp3")
            fadein = alarm.get("fadein", False)
            
            logger.info(f"🎵 Testing with ringtone: {ringtone}, fadein: {fadein}")
            self.trigger_alarm(ringtone, fadein)
            return True
            
        except Exception as e:
            logger.error(f"❌ Error testing alarm: {e}")
            return False
    
    def get_status(self):
        """Get alarm clock status for debugging"""
        status = {
            'running': self.alarm_event is not None,
            'check_interval': self.check_interval,
            'check_count': self.check_count,
            'active_popup': self.active_popup is not None,
            'debug_mode': self.debug_mode,
            'popup_creating': self._popup_creating,
            'last_trigger_time': self._last_trigger_time
        }
        
        # Add current alarm config
        try:
            alarm = self.app.alarm_service.get_alarm()
            status['current_alarm'] = alarm
        except:
            status['current_alarm'] = None
            
        return status
    
    def set_debug_mode(self, enabled):
        """Enable/disable debug logging"""
        self.debug_mode = enabled
        logger.info(f"🔧 Debug mode {'enabled' if enabled else 'disabled'}")
    
    def force_check(self):
        """Force an immediate alarm check (for debugging)"""
        logger.info("🔍 Forcing immediate alarm check...")
        self.check_alarm(0, force_debug=True)