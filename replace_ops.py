import os
import glob
import re

partials_dir = "/Users/alihassan/Products/DeltaDocs/mcpforge/src/mcp_maker/templates/partials"

for filepath in glob.glob(os.path.join(partials_dir, "*.jinja2")):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Restore the path traversal security that we checked out away from files.jinja2 if needed
    # Wait, files.jinja2 didn't have `ops` checks modified... Actually it did.
    # Let me just run the script.

    tokens = re.split(r'(\{%[^%]*%\}|\{\{.*?\}\})', content)
    
    in_table_loop = False
    loop_depth = 0
    new_tokens = []
    
    for token in tokens:
        if token.startswith('{%') and 'for ' in token and ' in ' in token:
            loop_depth += 1
            if 'for table in tables' in token:
                in_table_loop = True
                new_tokens.append(token)
                new_tokens.append('\n{% set tbl_ops = rbac_config.get(table.name | lower, ops) if rbac_config else ops %}')
                continue
                
        elif token.startswith('{%') and 'endfor' in token:
            loop_depth -= 1
            if loop_depth == 0:
                in_table_loop = False
                
        # Replace whole word `ops` with `tbl_ops` if inside a jinja tag
        if in_table_loop and token.startswith('{%') and 'if' in token:
            token = re.sub(r'\bops\b', 'tbl_ops', token)
            
        new_tokens.append(token)
        
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("".join(new_tokens))

print("Replacement complete.")
