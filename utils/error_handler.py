"""
Centralized error handling for the Bedrock application
"""
import sys
import traceback
import logging
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.clock import Clock

logger = logging.getLogger("ErrorHandler")

class ErrorHandler:
    """Central class for handling errors in the application"""
    
    @staticmethod
    def init():
        """Initialize global exception handler"""
        # Set up global exception handler
        sys.excepthook = ErrorHandler._global_exception_handler
        logger.info("Global exception handler installed")
        
        return True
    
    @staticmethod
    def _global_exception_handler(exc_type, exc_value, exc_traceback):
        """Handle uncaught exceptions globally"""
        # Log the exception
        logger.critical("Uncaught exception:", exc_info=(exc_type, exc_value, exc_traceback))
        
        # Format exception details
        error_msg = f"Uncaught {exc_type.__name__}: {exc_value}"
        error_traceback = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        
        # Try to show in UI if possible
        try:
            app = App.get_running_app()
            if app:
                # Schedule error popup to run in main thread
                Clock.schedule_once(
                    lambda dt: ErrorHandler.show_error_popup(error_msg, error_traceback), 
                    0
                )
        except:
            # If App.get_running_app() fails, just print
            print(f"FATAL ERROR: {error_msg}", file=sys.stderr)
            print(error_traceback, file=sys.stderr)
    
    @staticmethod
    def handle_exception(func):
        """Decorator for functions to catch and handle exceptions"""
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Exception in {func.__name__}:", exc_info=True)
                # Try to get app instance for UI feedback
                try:
                    app = App.get_running_app()
                    if hasattr(app, 'play_sound'):
                        app.play_sound("error")
                except:
                    pass
                return None
        return wrapper
    
    @staticmethod
    def show_error_popup(title, message, fatal=False):
        """Display error in a popup window"""
        try:
            layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
            
            # Error message
            msg_label = Label(
                text=message,
                size_hint_y=0.8,
                text_size=(400, None),
                halign='left',
                valign='top'
            )
            
            # Action buttons
            button_layout = BoxLayout(orientation='horizontal', 
                                     size_hint_y=0.2, 
                                     spacing=10)
            
            def close_popup(instance):
                popup.dismiss()
            
            def restart_app(instance):
                app = App.get_running_app()
                popup.dismiss()
                if app:
                    app.stop()
                    # Schedule restart 
                    Clock.schedule_once(lambda dt: ErrorHandler._restart_app(), 1)
            
            # Close button
            close_button = Button(text='Close')
            close_button.bind(on_release=close_popup)
            button_layout.add_widget(close_button)
            
            # Add restart button for fatal errors
            if fatal:
                restart_button = Button(text='Restart App')
                restart_button.bind(on_release=restart_app)
                button_layout.add_widget(restart_button)
            
            # Assemble layout
            layout.add_widget(msg_label)
            layout.add_widget(button_layout)
            
            # Create and show popup
            popup = Popup(
                title=title,
                content=layout,
                size_hint=(0.8, 0.5),
                auto_dismiss=not fatal
            )
            popup.open()
            
            # Try to play error sound
            try:
                app = App.get_running_app()
                if hasattr(app, 'play_sound'):
                    app.play_sound("error")
            except:
                pass
                
            return popup
                
        except Exception as e:
            # If popup creation fails, log and print
            logger.error(f"Failed to show error popup: {e}", exc_info=True)
            print(f"ERROR: {title}\n{message}", file=sys.stderr)
    
    @staticmethod
    def _restart_app():
        """Attempt to restart the application"""
        try:
            import os
            import sys
            python = sys.executable
            os.execl(python, python, *sys.argv)
        except Exception as e:
            logger.error(f"Failed to restart application: {e}", exc_info=True)
            sys.exit(1)