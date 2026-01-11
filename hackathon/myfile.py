import os
import json

# Create translations directory
if not os.path.exists('translations'):
    os.makedirs('translations')
    print("Created translations directory")

# Create basic English file with minimal content
basic_translations = {
    "app_name": "ASHA EHR",
    "dashboard": "Dashboard",
    "patients": "Patients",
    "profile": "Profile",
    "logout": "Logout",
    "language": "Language"
}

for lang in ['en', 'hi', 'mr', 'pa', 'bn']:
    file_path = f'translations/{lang}.json'
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(basic_translations, f, indent=4, ensure_ascii=False)
    print(f"Created {file_path}")

print("Translation files created successfully!")