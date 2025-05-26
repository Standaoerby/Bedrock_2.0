# pages/pigs.py
from utils.common import BasePage
from kivy.properties import NumericProperty, ColorProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Color, Rectangle
import os
import logging

logger = logging.getLogger("PigsScreen")

class CustomProgressBar(BoxLayout):
    """Кастомный прогресс бар"""
    
    value = NumericProperty(50)
    bar_color = ColorProperty([0, 0.6, 0.8, 1])
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
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
        """Обновить канвас"""
        # Update background rectangle
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        
        # Update foreground rectangle based on value
        self.fg_color.rgba = self.bar_color
        self.fg_rect.pos = self.pos
        self.fg_rect.size = (self.width * (self.value / 100), self.height)

class PigsScreen(BasePage):
    """Экран ухода за питомцами"""
    
    def on_pre_enter(self):
        """Вход на экран"""
        logger.info("Entering PigsScreen")
        self.update_bars()
        
        # Check status every 20 minutes
        self.schedule_timer(lambda dt: self.update_bars(), 20 * 60)

    def update_bars(self):
        """Обновить все полосы и изображение питомцев"""
        app = self.get_app()
        vals, integral = app.pigs_service.get_all_values()
        
        # Update progress bars
        water_bar = self.safe_get_widget('water_bar')
        food_bar = self.safe_get_widget('food_bar')
        clean_bar = self.safe_get_widget('clean_bar')
        
        if water_bar:
            water_bar.value = vals["water"]
        if food_bar:
            food_bar.value = vals["food"]
        if clean_bar:
            clean_bar.value = vals["clean"]
        
        # Log values
        logger.debug(f"Bar values: Water={vals['water']:.1f}, Food={vals['food']:.1f}, Clean={vals['clean']:.1f}")
        
        # Update status display
        percent = int(integral * 100)
        self.safe_set_widget_text('pigs_status_label', f"Status: {percent}%")
        
        # Update the pigs image based on status percentage
        self.update_pigs_image(percent)

    def update_pigs_image(self, percent):
        """Обновить изображение питомцев на основе статуса"""
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
        pigs_image = self.safe_get_widget('pigs_image')
        if pigs_image:
            if os.path.exists(image_path):
                pigs_image.source = image_path
            else:
                logger.warning(f"Image not found: {image_path}")

    def reset_bar(self, key):
        """Сбросить определённую полосу"""
        app = self.get_app()
        app.pigs_service.reset_bar(key)
        self.update_bars()
        logger.info(f"Reset bar: {key}")