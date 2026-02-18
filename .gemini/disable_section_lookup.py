"""
Disable direct section lookup to enable FAQ book retrieval
"""

file_path = r'c:\Users\kalid\OneDrive\Documents\RAG\companies_act_2013\governance_db\retrieval_service_faiss.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find and comment out the entire section lookup block
# Look for the if section_match: block and comment it out
lines = content.split('\n')
new_lines = []
in_section_block = False
indent_level = 0

for i, line in enumerate(lines):
    # Detect start of section_match block
    if 'if section_match:' in line and not line.strip().startswith('#'):
        in_section_block = True
        indent_level = len(line) - len(line.lstrip())
        new_lines.append(' ' * indent_level + '# DISABLED: Direct section lookup (FAQ chunks have no section numbers)')
        new_lines.append(' ' * indent_level + '# Using vector search for all queries instead')
        new_lines.append(' ' * indent_level + '# ' + line.strip())
        continue
    
    # If in block, check if we've exited based on indentation
    if in_section_block:
        current_indent = len(line) - len(line.lstrip()) if line.strip() else indent_level + 4
        
        # Exit block when we hit a line with same or less indentation (and it's not empty)
        if line.strip() and current_indent <= indent_level:
            in_section_block = False
            new_lines.append(line)
        else:
            # Comment out this line
            if line.strip():
                new_lines.append(' ' * indent_level + '# ' + line.strip())
            else:
                new_lines.append(line)
    else:
        new_lines.append(line)

new_content = '\n'.join(new_lines)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("✓ Disabled direct section lookup")
print("✓ All queries will now use vector search")
print("✓ FAQ books will appear in results!")
print("\n⚠️  RESTART Flask server for changes to take effect")
