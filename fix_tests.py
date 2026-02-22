import os
import re

for root, _, files in os.walk('tests'):
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            with open(path, 'r') as file:
                content = file.read()
            
            # Replace "".join(...) with "\n\n".join(...)
            new_content = content.replace('code = "".join(generate_server_code', 'code = "\\n\\n".join(generate_server_code')
            
            if new_content != content:
                with open(path, 'w') as file:
                    file.write(new_content)
                print(f"Updated {path}")
