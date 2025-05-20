#!/bin/bash

# Журналирование
exec > /home/standa/bedrock-app/logs/launch_log.txt 2>&1
date
echo "Starting Bedrock App..."

# Ждем завершения загрузки графической подсистемы
sleep 10

# Проверяем, что DISPLAY установлен
if [ -z "$DISPLAY" ]; then
  export DISPLAY=:0.0
  echo "DISPLAY was not set, now set to $DISPLAY"
fi

# Force display parameters (пробуем несколько вариантов выходов)
xrandr --output HDMI-1 --mode 1024x600 --rate 60 2>/dev/null || \
xrandr --output HDMI-0 --mode 1024x600 --rate 60 2>/dev/null || \
xrandr --output HDMI --mode 1024x600 --rate 60 2>/dev/null || \
true

echo "Display configured"

# Hide the cursor
unclutter -idle 0.1 -root &
echo "Cursor hidden"

# Turn off screensaver and power management
xset s off
xset s noblank
xset -dpms
echo "Screensaver and power management disabled"

# Tell window manager to not manage our window
export SDL_VIDEO_WINDOW_POS=0,0
export SDL_VIDEODRIVER=x11

# Set up environment variables for Kivy
export KIVY_GL_BACKEND=sdl2
export KIVY_WINDOW=sdl2
export SDL_VIDEO_FULLSCREEN_HEAD=0

# Remove window decorations and go fullscreen
# Попробуем иначе запустить менеджер окон
matchbox-window-manager -use_titlebar no -use_cursor no &
echo "Window manager started"

# Подождем, чтобы окружение успело инициализироваться
sleep 3

# Launch the app
cd /home/standa/bedrock-app
echo "Activating virtual environment"
source /home/standa/bedrock-venv/bin/activate
echo "Starting Bedrock app"
python main.py