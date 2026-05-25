import os
import json

TARGET_DIRS = [
    r"E:\Antigravity",
    r"E:\PHANDORA",
    r"E:\SISTEMA ONE",
    r"E:\SISTEMA_ONE",
    r"E:\Sistema_open_claude",
    r"E:\ZEUS"
]

IGNORE_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".obsidian", "dist", "build"}
GHOST_KEYWORDS = ["pass", "TODO", "mock", "fake", "simulate", "placeholder", "stub", "hardcoded", "dummy"]
TARGET_EXTS = {".py", ".js", ".ts", ".md", ".json", ".txt"}

results = {}

def scan_project(proj_path):
    stats = {
        "files_count": 0,
        "extensions": {},
        "architecture_folders": set(),
        "ghost_hits": {kw: 0 for kw in GHOST_KEYWORDS},
        "tech_stack": set()
    }
    
    if not os.path.exists(proj_path):
        return None
    
    for root, dirs, files in os.walk(proj_path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        
        # Detect architectural folders in the root
        if root == proj_path:
            stats["architecture_folders"] = set([d.upper() for d in dirs])
            
        for f in files:
            stats["files_count"] += 1
            ext = os.path.splitext(f)[1].lower()
            stats["extensions"][ext] = stats["extensions"].get(ext, 0) + 1
            
            if f == "package.json": stats["tech_stack"].add("Node.js")
            if f == "requirements.txt": stats["tech_stack"].add("Python")
            if f == "vercel.json": stats["tech_stack"].add("Vercel")
            
            if ext in TARGET_EXTS:
                file_path = os.path.join(root, f)
                try:
                    with open(file_path, "r", encoding="utf-8") as fp:
                        content = fp.read()
                        content_lower = content.lower()
                        for kw in GHOST_KEYWORDS:
                            if kw in content_lower:
                                stats["ghost_hits"][kw] += content_lower.count(kw)
                except Exception:
                    pass
                    
    stats["architecture_folders"] = list(stats["architecture_folders"])
    stats["tech_stack"] = list(stats["tech_stack"])
    return stats

for d in TARGET_DIRS:
    proj_name = os.path.basename(d)
    print(f"Scanning {proj_name}...")
    res = scan_project(d)
    if res:
        results[proj_name] = res

out_path = r"D:\Agente X\scan_results.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=4)
print(f"Scan complete. Results written to {out_path}")
