#!/usr/bin/env python3
"""Decode obfuscated strings in TISControlProtocol"""
import base64
import re
import os
from pathlib import Path

def decode_alpha(encoded: str) -> str:
    """Decode alpha__ obfuscated string"""
    return base64.b64decode(encoded).decode('utf-8')

def decode_beta(encoded: str, **kwargs) -> str:
    """Decode beta__ obfuscated string with format"""
    decoded = base64.b64decode(encoded).decode('utf-8')
    return decoded.format(**kwargs)

def process_file(filepath: Path):
    """Process a single Python file to decode obfuscation"""
    print(f"\n📄 Processing: {filepath.name}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    changes = 0
    
    # Find all alpha__("...") calls
    alpha_pattern = r'alpha__\("([^"]+)"\)'
    for match in re.finditer(alpha_pattern, content):
        encoded = match.group(1)
        try:
            decoded = decode_alpha(encoded)
            old_call = match.group(0)
            new_call = f'"{decoded}"'
            content = content.replace(old_call, new_call, 1)
            changes += 1
            print(f"  ✅ alpha__(...) → \"{decoded}\"")
        except Exception as e:
            print(f"  ❌ Failed to decode: {encoded} ({e})")
    
    # Find all beta__("...", __var0=...) calls
    beta_pattern = r'beta__\("([^"]+)"([^)]*)\)'
    for match in re.finditer(beta_pattern, content):
        encoded = match.group(1)
        params = match.group(2)
        try:
            decoded = decode_alpha(encoded)
            old_call = match.group(0)
            # Replace {__var0} with {var0} for Python format strings
            decoded_formatted = decoded.replace('{__var0}', '{var0}').replace('{__var1}', '{var1}')
            new_call = f'"{decoded_formatted}".format({params.strip(", ")})'
            content = content.replace(old_call, new_call, 1)
            changes += 1
            print(f"  ✅ beta__(...) → \"{decoded_formatted}\".format(...)")
        except Exception as e:
            print(f"  ❌ Failed to decode: {encoded} ({e})")
    
    if changes > 0:
        # Remove alpha__ and beta__ imports
        content = re.sub(r'from\s+\.\s+import\s+alpha__,\s*beta__\n?', '', content)
        content = re.sub(r'from\s+TISControlProtocol\s+import\s+alpha__,\s*beta__\n?', '', content)
        
        # Backup original
        backup_path = filepath.with_suffix('.py.bak')
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(original_content)
        
        # Write decoded version
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"  💾 Saved {changes} changes (backup: {backup_path.name})")
    else:
        print(f"  ℹ️  No obfuscated strings found")
    
    return changes

def main():
    """Decode all Python files in TISControlProtocol"""
    base_dir = Path(__file__).parent
    print(f"🔍 Scanning: {base_dir}")
    
    total_changes = 0
    processed = 0
    
    # Process all .py files recursively
    for pyfile in base_dir.rglob("*.py"):
        if pyfile.name == "decode_obfuscation.py":
            continue  # Skip this script
        
        changes = process_file(pyfile)
        total_changes += changes
        processed += 1
    
    print(f"\n{'='*60}")
    print(f"✨ Completed!")
    print(f"   Files processed: {processed}")
    print(f"   Total changes: {total_changes}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
