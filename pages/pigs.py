from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
import os
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import NumericProperty, ColorProperty
from kivy.graphics import Color, Rectangle

# Custom progress bar class
class CustomProgressBar(BoxLayout):
    value = NumericProperty(50)  # Default value
    bar_color = ColorProperty([0, 0.6, 0.8, 1])  # Default blue color
    
    def __init__(self, **kwargs):
        super(CustomProgressBar, self).__init__(**kwargs)
        self.bind(size=self.update_canvas)
        self.bind(pos=self.update_canvas)
        self.bind(value=self.update_canvas)
        
        # Initial canvas drawing
        with self.canvas:
            # Background
            self.bg_color = Color(0.2, 0.2, 0.2, 0.8)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
            
            # Foreground (progress)
            self.fg_color = Color(*self.bar_color)
            self.fg_rect = Rectangle(pos=self.pos, size=(0, 0))
    
    def update_canvas(self, *args):
        # Update background rectangle
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        
        # Update foreground rectangle based on value
        self.fg_color.rgba = self.bar_color
        self.fg_rect.pos = self.pos
        self.fg_rect.size = (self.width * (self.value / 100), self.height)

class PigsScreen(Screen):
    def on_enter(self):
        self.update_bars()
        # Check status every 20 minutes instead of every 60 seconds
        self._clock_ev = Clock.schedule_interval(lambda dt: self.update_bars(), 20 * 60)  

    def on_leave(self):
        if hasattr(self, "_clock_ev"):
            self._clock_ev.cancel()

    def update_bars(self):
        app = self.get_app()
        vals, integral = app.pigs_service.get_all_values()
        
        # Update progress bars
        self.ids.water_bar.value = vals["water"]
        self.ids.food_bar.value = vals["food"]
        self.ids.clean_bar.value = vals["clean"]
        
        # Print values for debugging
        print(f"Bar values: Water={vals['water']}, Food={vals['food']}, Clean={vals['clean']}")
        
        # Update status display
        percent = int(integral * 100)
        self.ids.pigs_status_label.text = f"Status: {percent}%"
        
        # Update the pigs image based on status percentage
        self.update_pigs_image(percent)

    def update_pigs_image(self, percent):
        """Update the pigs image based on the status percentage"""
        if 85 <= percent <= 100:
            image_file = "pigs_1.png"
        elif 50 <= percent < 85:
            image_file = "pigs_2.png"
        elif 20 <= percent < 50:
            image_file = "pigs_3.png"
        else:  # 0-20%
            image_file = "pigs_4.png"
        
        # Set the image source
        image_path = os.path.join("assets", "images", image_file)
        
        # Check if the image exists before setting
        if os.path.exists(image_path):
            self.ids.pigs_image.source = image_path
        else:
            print(f"Warning: Image not found: {image_path}")

    def reset_bar(self, key):
        app = self.get_app()
        app.pigs_service.reset_bar(key)
        # Update both bars and image immediately
        self.update_bars()

    def get_app(self):
        from kivy.app import App
        return App.get_running_app()