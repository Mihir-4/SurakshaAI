import os

# Comprehensive ignore list for various project types
IGNORE = {
    # Version Control
    ".git", ".svn", ".hg",
    
    # Python
    "__pycache__", "venv", "env", ".venv", ".env",
    ".pytest_cache", ".mypy_cache", ".tox", ".coverage",
    "*.egg-info", ".eggs", "htmlcov",
    
    # JavaScript/Node/React/Next
    "node_modules", ".next", ".nuxt", "out", ".output",
    "coverage", ".cache", ".parcel-cache", ".turbo",
    "dist", "build", ".svelte-kit",
    
    # Flutter/Dart - AGGRESSIVE FILTERING
    ".dart_tool", ".flutter-plugins", ".flutter-plugins-dependencies",
    ".packages", "pubspec.lock",
    
    # Java/Gradle/Maven/Android
    ".gradle", "gradle", "target", "bin",
    ".settings", ".classpath", ".project",
    
    # IDEs
    ".idea", ".vscode", ".eclipse", ".fleet",
    "*.swp", "*.swo", "*~",
    
    # OS
    ".DS_Store", "Thumbs.db", "desktop.ini",
    
    # Other
    "tmp", "temp", ".tmp", "logs",
    
    # Your custom ignores
    "chapters", ".generate_structure.py", "usinglater", 
    "chapter_extractor.py"
}

# Folders that should be completely skipped (even deeper recursion)
IGNORE_SUBTREE = {
    ".dart_tool",
    "ephemeral",
    ".plugin_symlinks",
    ".symlinks",
    "example",  # Skip example folders in plugins
    "xcshareddata",
    "xcuserdata",
    "project.xcworkspace",
    "Pods",
    ".kotlin",
    "generated_plugin_registrant",
    "cpp_client_wrapper",  # Flutter Windows generated
}

IGNORE_EXTENSIONS = {
    ".pyc", ".pyo", ".log", ".tmp", 
    ".swp", ".swo", ".class", ".o", ".so",
    ".dylib", ".dll", ".exe", ".jar", ".war",
    ".iml", ".lock", ".pdb", ".exp", ".lib",
    ".stamp", ".filecache", ".d",  # Build artifacts
}

# Special patterns (files that should be ignored)
IGNORE_PATTERNS = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "poetry.lock", "Pipfile.lock", 
    "pubspec.lock",  # Dart lock file
    ".env.local", ".env.production", ".env.development",
    "generated_plugin_registrant",
    "GeneratedPluginRegistrant",
    ".flutter-plugins-dependencies",
}

# Platform folders to minimize (only show top level, not contents)
PLATFORM_FOLDERS = {
    "ios", "android", "macos", "linux", "windows", "web"
}

FOLDER_EMOJI = "📁"
FILE_EMOJI = "📄"

def should_ignore(name, path, parent_dir=""):
    """Check if file/folder should be ignored"""
    # Check if entire subtree should be ignored
    if name in IGNORE_SUBTREE:
        return True
    
    # Check exact name match
    if name in IGNORE:
        return True
    
    # Check extension
    _, ext = os.path.splitext(name)
    if ext in IGNORE_EXTENSIONS:
        return True
    
    # Check patterns
    if name in IGNORE_PATTERNS:
        return True
    
    # Ignore generated files
    if name.startswith("generated_"):
        return True
    
    # Check wildcard patterns in IGNORE
    for pattern in IGNORE:
        if '*' in pattern:
            if pattern.startswith('*'):
                if name.endswith(pattern[1:]):
                    return True
            elif pattern.endswith('*'):
                if name.startswith(pattern[:-1]):
                    return True
    
    return False

def should_collapse_folder(name, path):
    """Check if we should show folder but not its contents"""
    # For platform folders in Flutter projects
    # Only collapse if they're at a certain depth
    return False  # Disable for now, as it's complex

def generate_tree(root_dir, prefix="", max_depth=None, current_depth=0, min_platform_depth=False):
    """Generate tree structure with optional depth limit"""
    if max_depth is not None and current_depth >= max_depth:
        return
    
    try:
        entries = [e for e in os.listdir(root_dir) 
                  if not should_ignore(e, os.path.join(root_dir, e))]
    except PermissionError:
        return
    
    folders = sorted([e for e in entries if os.path.isdir(os.path.join(root_dir, e))])
    files = sorted([e for e in entries if os.path.isfile(os.path.join(root_dir, e))])
    
    # For Flutter projects, show platform folders minimally
    platform_folders = [f for f in folders if f in PLATFORM_FOLDERS]
    other_folders = [f for f in folders if f not in PLATFORM_FOLDERS]
    
    # Show important folders first, then platform folders
    folders = other_folders + platform_folders
    entries = folders + files
    
    for idx, entry in enumerate(entries):
        path = os.path.join(root_dir, entry)
        is_last = idx == len(entries) - 1
        connector = "└── " if is_last else "├── "
        
        if os.path.isdir(path):
            # Check if this is a platform folder and we should minimize it
            is_platform = entry in PLATFORM_FOLDERS
            depth_limit = 1 if is_platform and current_depth > 0 else max_depth
            
            print(f"{prefix}{connector}{FOLDER_EMOJI} {entry}/")
            extension_prefix = "    " if is_last else "│   "
            
            # Limit depth for platform folders
            if is_platform and current_depth > 0:
                # Show minimal platform folder contents
                try:
                    sub_entries = [e for e in os.listdir(path) 
                                  if not should_ignore(e, os.path.join(path, e))]
                    if len(sub_entries) > 5:  # Too many items, show count
                        print(f"{prefix}{extension_prefix}    ... ({len(sub_entries)} items)")
                        continue
                except:
                    pass
            
            generate_tree(path, prefix + extension_prefix, depth_limit, current_depth + 1)
        else:
            print(f"{prefix}{connector}{FILE_EMOJI} {entry}")

def save_to_file(root_dir, output_file, max_depth=None):
    """Save tree structure to a file"""
    import sys
    from io import StringIO
    
    old_stdout = sys.stdout
    sys.stdout = StringIO()
    
    root_name = os.path.basename(os.path.abspath(root_dir))
    print(f"{FOLDER_EMOJI} {root_name}/")
    generate_tree(root_dir, max_depth=max_depth)
    
    output = sys.stdout.getvalue()
    sys.stdout = old_stdout
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(output)
    
    print(f"✅ Tree structure saved to: {output_file}")
    print(output)

if __name__ == "__main__":
    print("🌳 Project Structure Generator")
    print("=" * 50)
    
    project_path = input("📂 Enter project path (default: current directory): ").strip() or "."
    
    # Check if path exists
    if not os.path.exists(project_path):
        print(f"❌ Error: Path '{project_path}' does not exist!")
        exit(1)
    
    # Optional: limit depth
    depth_input = input("📏 Max depth (default: unlimited, recommended: 4-6): ").strip()
    max_depth = int(depth_input) if depth_input.isdigit() else None
    
    # Detect project type and suggest depth
    if os.path.exists(os.path.join(project_path, "pubspec.yaml")):
        print("🎯 Detected: Flutter/Dart project")
        if max_depth is None:
            max_depth = 4  # Default for Flutter
            print(f"   Auto-setting depth to {max_depth} for Flutter project")
    elif os.path.exists(os.path.join(project_path, "package.json")):
        print("🎯 Detected: Node.js/JavaScript project")
    elif os.path.exists(os.path.join(project_path, "requirements.txt")) or os.path.exists(os.path.join(project_path, "setup.py")):
        print("🎯 Detected: Python project")
    
    # Optional: save to file
    save_option = input("💾 Save to file? (y/N): ").strip().lower()
    
    print("\n" + "=" * 50 + "\n")
    
    root_name = os.path.basename(os.path.abspath(project_path))
    
    if save_option == 'y':
        output_file = input("📝 Output filename (default: structure.txt): ").strip() or "structure.txt"
        save_to_file(project_path, output_file, max_depth)
    else:
        print(f"{FOLDER_EMOJI} {root_name}/")
        generate_tree(project_path, max_depth=max_depth)
    
    print("\n" + "=" * 50)
    print("✨ Done!")