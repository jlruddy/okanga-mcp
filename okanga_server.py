#!/usr/bin/env python3
"""
Created by Justin Ruddy "CosmoVandalay" - 1st commit 26-nov 2025
Okanga MCP Server - Debug iOS development issues without screenshots

Helps diagnose:
- Library loading problems
- Build configuration errors
- Framework search path issues
- Missing dependencies
- Simulator problems

New Capabilities (Token Optimization):
- Smart Swift Structure Parsing (read code outlines)
- Server-side text search (grep)
- Partial file reading (snippets)
"""

import os
import json
import subprocess
import plistlib
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("OkangaMCP")

# ============================================================================
# TOKEN OPTIMIZATION & SOURCE MANAGEMENT (NEW)
# ============================================================================

def _estimate_tokens(text: str) -> int:
    """Rough estimation of tokens (1 token ~= 4 chars)."""
    return len(text) // 4

@mcp.tool()
def read_swift_structure(file_path: str) -> Dict[str, Any]:
    """
    Reads the high-level structure of a Swift file, hiding function bodies.
    Use this FIRST to understand a file's contents before reading the full code.
    
    Args:
        file_path: Path to the .swift file
        
    Returns:
        The file content with function bodies replaced by '// ... implementation ...'
    """
    p = Path(file_path).expanduser().resolve()
    
    if not p.exists():
        return {"error": f"File not found: {file_path}"}
    
    if p.suffix != ".swift":
        return {"error": "This tool is optimized for .swift files only"}

    try:
        with open(p, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        structured_lines = []
        brace_depth = 0
        in_multiline_comment = False
        skipped_block = False

        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Simple comment handling
            if "/*" in stripped: in_multiline_comment = True
            if "*/" in stripped: in_multiline_comment = False
            
            # Count braces (very basic heuristic)
            open_braces = line.count("{")
            close_braces = line.count("}")
            
            # Determine if we keep this line
            # We keep level 0 (top level) and level 1 (inside class/struct)
            # We hide level 2+ (inside functions/computed props)
            should_keep = brace_depth < 2 or stripped.startswith("import")
            
            # Update depth for next line
            # Note: We update depth AFTER checking if we keep the start of the block
            # This ensures we see 'func myFunc() {' but not the next line.
            
            if should_keep:
                structured_lines.append(f"{i+1}: {line.rstrip()}")
                skipped_block = False
            else:
                if not skipped_block:
                    structured_lines.append(f"{i+1}: {' ' * (brace_depth * 2)}// ... implementation hidden ...")
                    skipped_block = True
            
            brace_depth += (open_braces - close_braces)

        content = "\n".join(structured_lines)
        return {
            "path": str(p),
            "structure_content": content,
            "original_size": len(lines),
            "token_estimate": _estimate_tokens(content),
            "savings": f"{100 - (len(structured_lines)/len(lines)*100):.1f}% reduction"
        }

    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def read_file_snippet(file_path: str, start_line: int, end_line: int) -> Dict[str, Any]:
    """
    Reads a specific range of lines from a file.
    
    Args:
        file_path: Path to the file
        start_line: First line to read (1-based index)
        end_line: Last line to read (inclusive)
    """
    p = Path(file_path).expanduser().resolve()
    
    if not p.exists():
        return {"error": f"File not found: {file_path}"}
        
    try:
        with open(p, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            
        # Adjust for 0-based indexing
        start_idx = max(0, start_line - 1)
        end_idx = min(len(all_lines), end_line)
        
        selected_lines = all_lines[start_idx:end_idx]
        content = "".join(selected_lines)
        
        return {
            "path": str(p),
            "range": f"Lines {start_line}-{end_line}",
            "content": content,
            "total_file_lines": len(all_lines)
        }
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def search_project(query: str, project_path: str, case_sensitive: bool = False) -> Dict[str, Any]:
    """
    Fast text search (grep) across the project. Use this to find where variables/functions are defined.
    Automatically excludes .git, Pods, DerivedData, and .build folders.
    
    Args:
        query: Regex or string pattern to search for
        project_path: Root directory to search
        case_sensitive: Whether to respect case (default False)
    """
    p = Path(project_path).expanduser().resolve()
    
    # Exclusions
    exclude_dirs = "{.git,Pods,DerivedData,.build,.swiftpm,fastlane}"
    
    cmd = ["grep", "-rn"] # Recursive, Line number
    
    if not case_sensitive:
        cmd.append("-i")
        
    cmd.extend(["--exclude-dir=" + exclude_dirs, query, str(p)])
    
    try:
        # Run grep
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        matches = []
        lines = result.stdout.strip().split('\n')
        
        # Limit results to prevent context flooding
        truncated = False
        if len(lines) > 50:
            lines = lines[:50]
            truncated = True
            
        for line in lines:
            if not line: continue
            parts = line.split(':', 2) # path:line:content
            if len(parts) >= 3:
                matches.append({
                    "file": parts[0],
                    "line": parts[1],
                    "match": parts[2].strip()
                })
                
        return {
            "query": query,
            "match_count": len(matches),
            "matches": matches,
            "truncated_results": truncated,
            "note": "Showing top 50 matches. Refine query if needed."
        }
        
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def check_file_size(file_path: str) -> Dict[str, Any]:
    """
    Check the size and estimated token count of a file.
    Use this before reading large files to see if you should use 'read_swift_structure' instead.
    """
    p = Path(file_path).expanduser().resolve()
    
    if not p.exists():
        return {"error": "File not found"}
        
    try:
        stats = p.stat()
        size_bytes = stats.st_size
        # Rough heuristic: 1 token ~= 4 bytes of text
        est_tokens = size_bytes // 4
        
        status = "safe"
        if est_tokens > 10000: status = "very_large"
        elif est_tokens > 2000: status = "large"
        
        return {
            "path": str(p),
            "size_bytes": size_bytes,
            "estimated_tokens": est_tokens,
            "status": status,
            "recommendation": "Use read_swift_structure" if status != "safe" and p.suffix == ".swift" else "Safe to read"
        }
    except Exception as e:
        return {"error": str(e)}

# ============================================================================
# PROJECT STRUCTURE & CONFIGURATION
# ============================================================================

@mcp.tool()
def analyze_xcode_project(project_path: str) -> Dict[str, Any]:
    """
    Comprehensive analysis of Xcode project structure.
    
    Args:
        project_path: Path to .xcodeproj or .xcworkspace file
    
    Returns:
        Project structure, targets, schemes, and configuration overview
    """
    p = Path(project_path).expanduser().resolve()
    
    if not p.exists():
        return {"error": f"Project not found: {project_path}"}
    
    result = {
        "project_path": str(p),
        "project_name": p.stem,
        "project_type": p.suffix,  # .xcodeproj or .xcworkspace
        "contents": {}
    }
    
    # Check for workspace
    if p.suffix == ".xcworkspace":
        result["is_workspace"] = True
        # Read workspace contents
        contents_file = p / "contents.xcworkspacedata"
        if contents_file.exists():
            try:
                with open(contents_file, 'r') as f:
                    result["workspace_contents"] = f.read()
            except Exception as e:
                result["workspace_error"] = str(e)
    
    # Check for project file
    if p.suffix == ".xcodeproj":
        result["is_project"] = True
        pbxproj = p / "project.pbxproj"
        if pbxproj.exists():
            try:
                # Just get size for now - full parsing is complex
                result["project_file_size"] = pbxproj.stat().st_size
                result["project_file_exists"] = True
            except Exception as e:
                result["project_error"] = str(e)
    
    # Check for Podfile
    podfile = p.parent / "Podfile"
    result["has_cocoapods"] = podfile.exists()
    if result["has_cocoapods"]:
        try:
            with open(podfile, 'r') as f:
                result["podfile_content"] = f.read()
        except Exception as e:
            result["podfile_error"] = str(e)
    
    # Check for Package.swift
    package_swift = p.parent / "Package.swift"
    result["has_swift_package"] = package_swift.exists()
    
    # Check for Carthage
    cartfile = p.parent / "Cartfile"
    result["has_carthage"] = cartfile.exists()
    
    return result


@mcp.tool()
def read_build_settings(
    project_path: str,
    scheme: Optional[str] = None,
    configuration: str = "Debug"
) -> Dict[str, Any]:
    """
    Extract build settings from Xcode project using xcodebuild.
    
    Args:
        project_path: Path to .xcodeproj or .xcworkspace
        scheme: Scheme name (optional, will use default)
        configuration: Build configuration (Debug/Release)
    
    Returns:
        Build settings including paths, frameworks, linker flags
    """
    p = Path(project_path).expanduser().resolve()
    
    if not p.exists():
        return {"error": f"Project not found: {project_path}"}
    
    # Build xcodebuild command
    cmd = ["xcodebuild", "-showBuildSettings"]
    
    if p.suffix == ".xcworkspace":
        cmd.extend(["-workspace", str(p)])
    else:
        cmd.extend(["-project", str(p)])
    
    if scheme:
        cmd.extend(["-scheme", scheme])
    
    cmd.extend(["-configuration", configuration])
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            return {
                "error": "xcodebuild failed",
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        
        # Parse build settings
        settings = {}
        current_target = None
        
        for line in result.stdout.split('\n'):
            line = line.strip()
            
            if line.startswith("Build settings for action build and target"):
                current_target = line.split("target")[-1].strip().rstrip(":")
                settings[current_target] = {}
            elif " = " in line and current_target:
                key, value = line.split(" = ", 1)
                settings[current_target][key.strip()] = value.strip()
        
        return {
            "configuration": configuration,
            "scheme": scheme,
            "targets": settings
        }
        
    except subprocess.TimeoutExpired:
        return {"error": "xcodebuild command timed out"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def check_framework_search_paths(project_path: str) -> Dict[str, Any]:
    """
    Specifically check framework and library search paths.
    This is the #1 cause of library loading issues.
    
    Args:
        project_path: Path to .xcodeproj or .xcworkspace
    
    Returns:
        Framework search paths and validation of their existence
    """
    settings = read_build_settings(project_path)
    
    if "error" in settings:
        return settings
    
    result = {
        "search_paths_by_target": {},
        "validation": {}
    }
    
    for target_name, target_settings in settings.get("targets", {}).items():
        paths_info = {
            "framework_search_paths": [],
            "library_search_paths": [],
            "header_search_paths": [],
            "swift_include_paths": []
        }
        
        # Extract search paths
        if "FRAMEWORK_SEARCH_PATHS" in target_settings:
            paths_info["framework_search_paths"] = target_settings["FRAMEWORK_SEARCH_PATHS"].split()
        
        if "LIBRARY_SEARCH_PATHS" in target_settings:
            paths_info["library_search_paths"] = target_settings["LIBRARY_SEARCH_PATHS"].split()
        
        if "HEADER_SEARCH_PATHS" in target_settings:
            paths_info["header_search_paths"] = target_settings["HEADER_SEARCH_PATHS"].split()
        
        if "SWIFT_INCLUDE_PATHS" in target_settings:
            paths_info["swift_include_paths"] = target_settings["SWIFT_INCLUDE_PATHS"].split()
        
        result["search_paths_by_target"][target_name] = paths_info
        
        # Validate paths exist
        validation = {}
        for path_type, paths in paths_info.items():
            validation[path_type] = {}
            for path in paths:
                # Clean up Xcode variables
                clean_path = path.replace("$(inherited)", "").strip()
                if clean_path and not clean_path.startswith("$"):
                    expanded = Path(clean_path).expanduser()
                    validation[path_type][path] = {
                        "exists": expanded.exists(),
                        "expanded_path": str(expanded)
                    }
        
        result["validation"][target_name] = validation
    
    return result


@mcp.tool()
def list_linked_frameworks(project_path: str) -> Dict[str, Any]:
    """
    List all frameworks and libraries linked in the project.
    
    Args:
        project_path: Path to .xcodeproj or .xcworkspace
    
    Returns:
        Linked frameworks/libraries and their status
    """
    settings = read_build_settings(project_path)
    
    if "error" in settings:
        return settings
    
    result = {}
    
    for target_name, target_settings in settings.get("targets", {}).items():
        frameworks = []
        
        # Get linked frameworks from OTHER_LDFLAGS
        if "OTHER_LDFLAGS" in target_settings:
            flags = target_settings["OTHER_LDFLAGS"]
            # Parse -framework flags
            parts = flags.split()
            i = 0
            while i < len(parts):
                if parts[i] == "-framework" and i + 1 < len(parts):
                    frameworks.append({
                        "name": parts[i + 1],
                        "type": "framework"
                    })
                    i += 2
                elif parts[i].startswith("-l"):
                    frameworks.append({
                        "name": parts[i][2:],
                        "type": "library"
                    })
                    i += 1
                else:
                    i += 1
        
        result[target_name] = frameworks
    
    return result


# ============================================================================
# BUILD LOGS & ERROR ANALYSIS
# ============================================================================

@mcp.tool()
def get_recent_build_logs(
    project_path: str,
    max_logs: int = 3
) -> Dict[str, Any]:
    """
    Read recent Xcode build logs from DerivedData.
    
    Args:
        project_path: Path to .xcodeproj or .xcworkspace
        max_logs: Maximum number of recent logs to return
    
    Returns:
        Recent build logs with errors and warnings extracted
    """
    p = Path(project_path).expanduser().resolve()
    project_name = p.stem
    
    # Find DerivedData
    derived_data = Path.home() / "Library" / "Developer" / "Xcode" / "DerivedData"
    
    if not derived_data.exists():
        return {"error": "DerivedData directory not found"}
    
    # Look for project-specific derived data
    project_dirs = []
    for item in derived_data.iterdir():
        if item.is_dir() and item.name.startswith(project_name):
            project_dirs.append(item)
    
    if not project_dirs:
        return {"error": f"No DerivedData found for project: {project_name}"}
    
    # Get most recent project dir
    project_dirs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    latest_derived = project_dirs[0]
    
    # Look for build logs
    logs_dir = latest_derived / "Logs" / "Build"
    
    if not logs_dir.exists():
        return {"error": "Build logs directory not found"}
    
    log_files = sorted(
        logs_dir.glob("*.xcactivitylog"),
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )[:max_logs]
    
    result = {
        "derived_data_path": str(latest_derived),
        "logs_dir": str(logs_dir),
        "logs": []
    }
    
    for log_file in log_files:
        log_info = {
            "path": str(log_file),
            "timestamp": datetime.fromtimestamp(log_file.stat().st_mtime).isoformat(),
            "size": log_file.stat().st_size
        }
        
        # Note: .xcactivitylog files are gzipped and binary
        # For actual parsing, you'd need to decompress and parse
        # For now, just provide metadata
        log_info["note"] = "Binary log file - use Xcode or xcodebuild to view"
        
        result["logs"].append(log_info)
    
    return result


@mcp.tool()
def run_clean_build(
    project_path: str,
    scheme: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run a clean build and capture output for analysis.
    USE WITH CAUTION - This actually runs a build.
    
    Args:
        project_path: Path to .xcodeproj or .xcworkspace
        scheme: Scheme to build (optional)
    
    Returns:
        Build output with errors/warnings extracted
    """
    p = Path(project_path).expanduser().resolve()
    
    if not p.exists():
        return {"error": f"Project not found: {project_path}"}
    
    # Clean first
    clean_cmd = ["xcodebuild", "clean"]
    
    if p.suffix == ".xcworkspace":
        clean_cmd.extend(["-workspace", str(p)])
    else:
        clean_cmd.extend(["-project", str(p)])
    
    if scheme:
        clean_cmd.extend(["-scheme", scheme])
    
    try:
        clean_result = subprocess.run(
            clean_cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # Now build
        build_cmd = list(clean_cmd)
        build_cmd[1] = "build"  # Replace 'clean' with 'build'
        
        build_result = subprocess.run(
            build_cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        # Extract errors and warnings
        errors = []
        warnings = []
        
        for line in build_result.stderr.split('\n'):
            if 'error:' in line.lower():
                errors.append(line.strip())
            elif 'warning:' in line.lower():
                warnings.append(line.strip())
        
        return {
            "success": build_result.returncode == 0,
            "returncode": build_result.returncode,
            "errors": errors,
            "warnings": warnings,
            "stdout": build_result.stdout[-2000:] if build_result.stdout else "",  # Last 2000 chars
            "stderr": build_result.stderr[-2000:] if build_result.stderr else ""
        }
        
    except subprocess.TimeoutExpired:
        return {"error": "Build timed out"}
    except Exception as e:
        return {"error": str(e)}


# ============================================================================
# DEPENDENCIES & PACKAGE MANAGEMENT
# ============================================================================

@mcp.tool()
def check_cocoapods_status(project_path: str) -> Dict[str, Any]:
    """
    Check CocoaPods installation and pod status.
    
    Args:
        project_path: Path to project directory (not .xcodeproj)
    
    Returns:
        CocoaPods status, installed pods, and potential issues
    """
    p = Path(project_path).expanduser().resolve()
    
    # If given .xcodeproj, go up to parent
    if p.suffix == ".xcodeproj":
        p = p.parent
    
    result = {
        "project_dir": str(p),
        "has_podfile": False,
        "has_podfile_lock": False,
        "pods_installed": False
    }
    
    # Check for Podfile
    podfile = p / "Podfile"
    result["has_podfile"] = podfile.exists()
    
    if result["has_podfile"]:
        try:
            with open(podfile, 'r') as f:
                result["podfile_content"] = f.read()
        except Exception as e:
            result["podfile_error"] = str(e)
    
    # Check for Podfile.lock
    podfile_lock = p / "Podfile.lock"
    result["has_podfile_lock"] = podfile_lock.exists()
    
    if result["has_podfile_lock"]:
        try:
            with open(podfile_lock, 'r') as f:
                result["podfile_lock_content"] = f.read()
        except Exception as e:
            result["podfile_lock_error"] = str(e)
    
    # Check Pods directory
    pods_dir = p / "Pods"
    result["pods_installed"] = pods_dir.exists()
    
    if result["pods_installed"]:
        # List installed pods
        installed_pods = []
        pods_manifest = pods_dir / "Manifest.lock"
        if pods_manifest.exists():
            try:
                with open(pods_manifest, 'r') as f:
                    result["manifest_lock"] = f.read()
            except Exception as e:
                result["manifest_error"] = str(e)
        
        # Count pod directories
        pod_subdirs = [d for d in pods_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
        result["installed_pod_count"] = len(pod_subdirs)
        result["installed_pods"] = [d.name for d in pod_subdirs]
    
    # Check if pod command is available
    try:
        pod_version = subprocess.run(
            ["pod", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        result["pod_version"] = pod_version.stdout.strip()
    except Exception:
        result["pod_command_available"] = False
    
    return result


@mcp.tool()
def check_swift_packages(project_path: str) -> Dict[str, Any]:
    """
    Check Swift Package Manager dependencies.
    
    Args:
        project_path: Path to .xcodeproj or .xcworkspace
    
    Returns:
        Swift package dependencies and their status
    """
    p = Path(project_path).expanduser().resolve()
    
    # If given .xcodeproj, go up to parent
    if p.suffix == ".xcodeproj":
        p = p.parent
    
    result = {
        "project_dir": str(p),
        "has_package_swift": False,
        "packages": []
    }
    
    # Check for Package.swift
    package_swift = p / "Package.swift"
    result["has_package_swift"] = package_swift.exists()
    
    if result["has_package_swift"]:
        try:
            with open(package_swift, 'r') as f:
                result["package_swift_content"] = f.read()
        except Exception as e:
            result["package_swift_error"] = str(e)
    
    # Check for Package.resolved
    package_resolved = p / "Package.resolved"
    if package_resolved.exists():
        try:
            with open(package_resolved, 'r') as f:
                resolved_content = json.load(f)
                result["resolved_packages"] = resolved_content
        except Exception as e:
            result["package_resolved_error"] = str(e)
    
    # Check .build directory
    build_dir = p / ".build"
    result["has_build_dir"] = build_dir.exists()
    
    return result


# ============================================================================
# INFO.PLIST & CONFIGURATION FILES
# ============================================================================

@mcp.tool()
def read_info_plist(project_path: str, target: Optional[str] = None) -> Dict[str, Any]:
    """
    Read and validate Info.plist file.
    
    Args:
        project_path: Path to .xcodeproj
        target: Specific target (optional, will find automatically)
    
    Returns:
        Info.plist contents and validation
    """
    p = Path(project_path).expanduser().resolve()
    
    # If given .xcodeproj, go up to parent to find source files
    if p.suffix == ".xcodeproj":
        p = p.parent
    
    result = {
        "project_dir": str(p),
        "info_plists": []
    }
    
    # Search for Info.plist files
    plist_files = list(p.rglob("Info.plist"))
    
    for plist_file in plist_files:
        plist_info = {
            "path": str(plist_file),
            "relative_path": str(plist_file.relative_to(p))
        }
        
        try:
            with open(plist_file, 'rb') as f:
                plist_data = plistlib.load(f)
                plist_info["contents"] = plist_data
                
                # Extract key info
                plist_info["bundle_id"] = plist_data.get("CFBundleIdentifier", "Not set")
                plist_info["version"] = plist_data.get("CFBundleShortVersionString", "Not set")
                plist_info["build"] = plist_data.get("CFBundleVersion", "Not set")
                plist_info["display_name"] = plist_data.get("CFBundleDisplayName", "Not set")
                
        except Exception as e:
            plist_info["error"] = str(e)
        
        result["info_plists"].append(plist_info)
    
    return result


# ============================================================================
# SIMULATOR MANAGEMENT
# ============================================================================

@mcp.tool()
def list_simulators() -> Dict[str, Any]:
    """
    List available iOS simulators and their states.
    
    Returns:
        List of simulators with status
    """
    try:
        result = subprocess.run(
            ["xcrun", "simctl", "list", "devices", "--json"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return {"error": result.stderr}
        
        devices_data = json.loads(result.stdout)
        
        # Simplify the output
        simulators = []
        for runtime, devices in devices_data.get("devices", {}).items():
            for device in devices:
                simulators.append({
                    "name": device.get("name"),
                    "udid": device.get("udid"),
                    "state": device.get("state"),
                    "runtime": runtime,
                    "available": device.get("isAvailable", False)
                })
        
        return {
            "simulators": simulators,
            "total_count": len(simulators)
        }
        
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_active_simulators() -> Dict[str, Any]:
    """
    Get currently running simulators.
    
    Returns:
        List of active simulators
    """
    try:
        result = subprocess.run(
            ["xcrun", "simctl", "list", "devices", "--json"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return {"error": result.stderr}
        
        devices_data = json.loads(result.stdout)
        
        active = []
        for runtime, devices in devices_data.get("devices", {}).items():
            for device in devices:
                if device.get("state") == "Booted":
                    active.append({
                        "name": device.get("name"),
                        "udid": device.get("udid"),
                        "runtime": runtime
                    })
        
        return {
            "active_simulators": active,
            "count": len(active)
        }
        
    except Exception as e:
        return {"error": str(e)}


# ============================================================================
# DIAGNOSTIC SUMMARY
# ============================================================================

@mcp.tool()
def diagnose_project(project_path: str) -> Dict[str, Any]:
    """
    Comprehensive diagnostic of Xcode project.
    Runs multiple checks to identify common issues.
    
    Args:
        project_path: Path to .xcodeproj or .xcworkspace
    
    Returns:
        Diagnostic report with identified issues and suggestions
    """
    p = Path(project_path).expanduser().resolve()
    
    result = {
        "project_path": str(p),
        "timestamp": datetime.now().isoformat(),
        "checks": {},
        "issues": [],
        "suggestions": []
    }
    
    # Check 1: Project exists and is valid
    result["checks"]["project_exists"] = p.exists()
    if not p.exists():
        result["issues"].append(f"Project not found at: {p}")
        return result
    
    # Check 2: Dependencies
    if p.suffix == ".xcodeproj":
        parent = p.parent
    else:
        parent = p
    
    pods_status = check_cocoapods_status(str(parent))
    result["checks"]["cocoapods"] = pods_status
    
    if pods_status.get("has_podfile") and not pods_status.get("pods_installed"):
        result["issues"].append("Podfile exists but pods not installed")
        result["suggestions"].append("Run: pod install")
    
    # Check 3: Build settings
    build_settings = read_build_settings(str(p))
    result["checks"]["build_settings"] = "error" not in build_settings
    
    if "error" in build_settings:
        result["issues"].append(f"Cannot read build settings: {build_settings.get('error')}")
    
    # Check 4: Framework search paths
    framework_paths = check_framework_search_paths(str(p))
    result["checks"]["framework_paths"] = framework_paths
    
    if "error" not in framework_paths:
        # Check for missing paths
        for target, validation in framework_paths.get("validation", {}).items():
            for path_type, paths in validation.items():
                for path, status in paths.items():
                    if not status.get("exists"):
                        result["issues"].append(
                            f"Missing {path_type} for {target}: {path}"
                        )
                        result["suggestions"].append(
                            f"Verify path exists or remove from build settings: {status.get('expanded_path')}"
                        )
    
    # Check 5: Info.plist
    plist_check = read_info_plist(str(p))
    result["checks"]["info_plist"] = plist_check
    
    if not plist_check.get("info_plists"):
        result["issues"].append("No Info.plist file found")
        result["suggestions"].append("Create Info.plist file for your target")
    
    # Summary
    result["summary"] = {
        "total_issues": len(result["issues"]),
        "total_suggestions": len(result["suggestions"]),
        "status": "OK" if len(result["issues"]) == 0 else "ISSUES_FOUND"
    }
    
    return result


if __name__ == "__main__":
    mcp.run()
