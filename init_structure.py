
import os

project_structure = {
    "Bedrock_OS": [
        "main.py",
        "main.kv",
        "README.md",
        "screens/home",
        "screens/alarm",
        "screens/schedule",
        "screens/weather",
        "screens/pigs",
        "screens/settings",
        "services/api",
        "services/config",
        "services/hardware",
        "services/media",
        "services/notifications",
        "themes/minecraft",
        "themes/minecraft/fonts",
        "themes/minecraft/images",
        "themes/minecraft/images/icons",
        "themes/minecraft/light/",
        "themes/minecraft/dark/",
        "assets/images",
        "data",
        "utils"
    ]
}

def create_structure(base_path, structure):
    for root, items in structure.items():
        for item in items:
            full_path = os.path.join(base_path, root, item)
            if '.' in os.path.basename(full_path):
                # it's a file
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'w', encoding='utf-8') as f:
                    pass
            else:
                # it's a folder
                os.makedirs(full_path, exist_ok=True)

if __name__ == "__main__":
    create_structure(".", project_structure)
    print("✅ Структура проекта создана.")
