from kivymd.uix.screen import MDScreen
from kivy.properties import StringProperty, BooleanProperty, ListProperty, ObjectProperty
import json
import os
from datetime import datetime, time

class SettingsScreen(MDScreen):
    # Текущие настройки
    current_theme = StringProperty("minecraft")
    available_themes = ListProperty([])  # Будем заполнять динамически
    dark_mode_enabled = BooleanProperty(False)
    dark_mode_available = BooleanProperty(False)  # Доступен ли темный режим для текущей темы
    username = StringProperty("")
    
    # Разбитая дата рождения для удобства ввода
    birth_day = StringProperty("")
    birth_month = StringProperty("")
    birth_year = StringProperty("")
    
    def on_pre_enter(self):
        self.scan_available_themes()
        self.load_settings()
        self.check_dark_mode_availability()
        self.update_dark_mode_button()
    
    def scan_available_themes(self):
        """Сканирует директорию themes/ для поиска доступных тем"""
        themes_dir = "themes"
        themes = []
        
        try:
            if os.path.exists(themes_dir) and os.path.isdir(themes_dir):
                # Получаем все папки в директории themes/
                theme_folders = [f for f in os.listdir(themes_dir) 
                               if os.path.isdir(os.path.join(themes_dir, f))]
                
                # Проверяем каждую папку на валидность темы
                for theme in theme_folders:
                    theme_path = os.path.join(themes_dir, theme)
                    # Проверяем наличие light или dark папки
                    if os.path.exists(os.path.join(theme_path, "light")) or \
                       os.path.exists(os.path.join(theme_path, "dark")):
                        themes.append(theme)
                
                print(f"Найдены темы: {themes}")
            else:
                print(f"Директория тем '{themes_dir}' не найдена")
        except Exception as e:
            print(f"Ошибка при сканировании тем: {e}")
        
        # Обновляем список доступных тем
        self.available_themes = themes if themes else ["minecraft"]  # По умолчанию minecraft
    
    def check_dark_mode_availability(self):
        """Проверяет, доступен ли темный режим для текущей темы"""
        theme_path = os.path.join("themes", self.current_theme)
        dark_path = os.path.join(theme_path, "dark")
        
        self.dark_mode_available = os.path.exists(dark_path) and os.path.isdir(dark_path)
        print(f"Темный режим для темы '{self.current_theme}': {'доступен' if self.dark_mode_available else 'недоступен'}")
        
        # If dark mode is not available, force disable it
        if not self.dark_mode_available:
            self.dark_mode_enabled = False
    
    def update_dark_mode_button(self):
        """Update the dark mode button UI"""
        if hasattr(self.ids, "dark_mode_button"):
            self.ids.dark_mode_button.text = "ON" if self.dark_mode_enabled else "OFF"
            self.ids.dark_mode_button.disabled = not self.dark_mode_available
            # Update color based on state
            app = self.get_app()
            if app:
                if self.dark_mode_enabled:
                    self.ids.dark_mode_button.color = app.theme_config.get("colors", {}).get("active", [0, 1, 0, 1])
                else:
                    self.ids.dark_mode_button.color = app.theme_config.get("colors", {}).get("inactive", [0.6, 0.6, 0.6, 1])
    
    def load_settings(self):
        """Загружает настройки из файла конфигурации"""
        try:
            with open("config/user.json", "r", encoding="utf-8") as f:
                settings = json.load(f)
                
                # Установка значений из файла
                self.current_theme = settings.get("theme", "minecraft")
                self.dark_mode_enabled = settings.get("theme_mode", "light") == "dark"
                self.username = settings.get("username", "")
                
                # Разбор даты рождения
                birthdate = settings.get("birthdate", "")
                if birthdate:
                    try:
                        date = datetime.strptime(birthdate, "%Y-%m-%d")
                        self.birth_year = str(date.year)
                        self.birth_month = str(date.month)
                        self.birth_day = str(date.day)
                    except:
                        self.birth_year = ""
                        self.birth_month = ""
                        self.birth_day = ""
        except Exception as e:
            print(f"Ошибка при загрузке настроек: {e}")
    
    def save_all_settings(self):
        """Сохранить все настройки в файл"""
        try:
            # Play UI sound
            app = self.get_app()
            if app:
                app.play_sound("success")
            
            # Получаем значения из полей ввода (они могли измениться)
            if hasattr(self.ids, 'username_input'):
                self.username = self.ids.username_input.text
                
            # Обновляем дату рождения из полей
            self.update_birthdate()
            
            # Формируем объект настроек
            settings = {
                "theme": self.current_theme,
                "theme_mode": "dark" if self.dark_mode_enabled else "light",
                "auto_dark_mode": True,  # Автоматический переход на темную тему
                "username": self.username,
                "birthdate": self.get_birthdate_string()
            }
            
            print(f"Сохраняем настройки: {settings}")
            
            # Создаем директорию config, если она не существует
            if not os.path.exists("config"):
                os.makedirs("config")
                print("Создана директория config")
                
            # Сохраняем настройки
            with open("config/user.json", "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
                
            # Обновляем настройки приложения
            app = self.get_app()
            if app:
                app.theme_name = self.current_theme
                app.theme_mode = "dark" if self.dark_mode_enabled else "light"
                
                # Import the load_theme_config function from main
                try:
                    from main import load_theme_config
                    app.theme_config = load_theme_config(app.theme_name, app.theme_mode)
                except ImportError:
                    # Fallback if import fails - recreate the theme config directly
                    print("Не удалось импортировать load_theme_config, используем резервный способ")
                    path = f"themes/{app.theme_name}/{app.theme_mode}/theme.json"
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            app.theme_config = json.load(f)
                    except Exception as e:
                        print(f"Ошибка при загрузке темы: {e}")
                        # Fallback to default theme config
                        app.theme_config = {
                            "background_image": "",
                            "menu_button_normal": "",
                            "font_name": "Minecraftia",
                            "font_color": [1, 1, 1, 1],
                            "menu_selected_color": [1, 1, 1, 1],
                            "menu_unselected_color": [0.7, 0.7, 0.7, 1],
                            "overlay_images": {}
                        }
                
                print(f"Настройки приложения обновлены: {app.theme_name}, {app.theme_mode}")
                
                # Перезагрузка экранов для применения новой темы
                app.root.ids.screen_manager.current = "settings"
            else:
                print("Не удалось получить экземпляр приложения")
                
            print("Настройки успешно сохранены!")
        except Exception as e:
            import traceback
            print(f"Ошибка при сохранении настроек: {e}")
            print(traceback.format_exc())
    
    def change_theme(self, theme):
        """Изменить текущую тему"""
        if theme != self.current_theme:
            self.current_theme = theme
            self.check_dark_mode_availability()
            self.update_dark_mode_button()
            
            # Если выбрана тема без темного режима, отключаем опцию
            if not self.dark_mode_available:
                self.dark_mode_enabled = False
    
    def toggle_dark_mode(self, enabled):
        """Включить/выключить темный режим"""
        app = self.get_app()
        if self.dark_mode_available:
            self.dark_mode_enabled = enabled
            if enabled:
                app.play_sound("success")
            self.update_dark_mode_button()
        else:
            self.dark_mode_enabled = False
    
    def update_birthdate(self):
        """Обновить объединенную дату рождения из отдельных полей"""
        try:
            # Получаем значения из полей ввода, если они доступны
            if hasattr(self.ids, 'birth_day') and hasattr(self.ids, 'birth_month') and hasattr(self.ids, 'birth_year'):
                day_text = self.ids.birth_day.text.strip()
                month_text = self.ids.birth_month.text.strip()
                year_text = self.ids.birth_year.text.strip()
                
                # Только обновляем, если все поля заполнены
                if day_text and month_text and year_text:
                    day = int(day_text)
                    month = int(month_text)
                    year = int(year_text)
                    
                    # Базовые проверки
                    if 1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= 2100:
                        self.birth_day = str(day)
                        self.birth_month = str(month)
                        self.birth_year = str(year)
                        print(f"Дата рождения обновлена: {day}/{month}/{year}")
                    else:
                        print(f"Неверная дата: {day}/{month}/{year}")
                else:
                    print("Не все поля даты заполнены")
        except Exception as e:
            print(f"Ошибка при обновлении даты рождения: {e}")
    
    def get_birthdate_string(self):
        """Получить строку даты рождения в формате YYYY-MM-DD"""
        try:
            day = int(self.birth_day) if self.birth_day else 1
            month = int(self.birth_month) if self.birth_month else 1
            year = int(self.birth_year) if self.birth_year else 2000
            return f"{year:04d}-{month:02d}-{day:02d}"
        except:
            return "2000-01-01"  # Значение по умолчанию
    
    def get_app(self):
        """Получить экземпляр приложения"""
        try:
            from kivy.app import App
            app = App.get_running_app()
            return app
        except Exception as e:
            print(f"Ошибка при получении приложения: {e}")
            return None