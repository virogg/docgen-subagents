import glob
import os
from typing import List, Optional


def get_repository_structure(repository_path: str,
                             excluded_dirs: Optional[List[str]] = None,
                             included_extensions: Optional[List[str]] = None,
                             max_depth: Optional[int] = None) -> str:
    """
    Generate a tree-like representation of the repository structure without files.

    Args:
        repository_path (str): Path to the repository.
        excluded_dirs (List[str], optional): Directories to exclude.
        included_extensions (List[str], optional): File extensions to include.
        max_depth (int, optional): Maximum depth to traverse.

    Returns:
        str: A tree-like representation of the repository structure.
    """
    if not os.path.exists(repository_path):
        raise FileNotFoundError(f"Repository {repository_path} not found")

    if excluded_dirs is None:
        excluded_dirs = ['.git', 'target', 'build', 'node_modules', 'dist']

    # Build exclude patterns
    exclude_patterns = [os.path.join('**', d, '**') for d in excluded_dirs]

    # Build include patterns based on extensions
    if included_extensions is None:
        include_patterns = ["*"]
    else:
        include_patterns = [f"*{ext}" for ext in included_extensions]

    # Get all files
    files = list_files(repository_path, include_patterns, exclude_patterns, max_depth)

    # Create a tree structure
    tree_structure = ["Repository Structure:"]
    prev_dirs = []

    for file_path in files:
        # Get relative path to the repository
        rel_path = os.path.relpath(file_path, repository_path)
        parts = rel_path.split(os.sep)

        # Output directory structure
        current_dirs = parts[:-1]  # All but the last part (file name)

        # Find the common prefix
        common_prefix_len = 0
        for i in range(min(len(prev_dirs), len(current_dirs))):
            if prev_dirs[i] == current_dirs[i]:
                common_prefix_len += 1
            else:
                break

        # Output new directories
        for i in range(common_prefix_len, len(current_dirs)):
            indent = "  " * i
            tree_structure.append(f"{indent}├── {current_dirs[i]}/")
        prev_dirs = current_dirs

    return "\n".join(tree_structure)


def list_files(directory_path: str,
               include_patterns: Optional[List[str]] = None,
               exclude_patterns: Optional[List[str]] = None,
               max_depth: Optional[int] = None) -> List[str]:
    """
    List all files in a directory matching the given patterns.

    Args:
        directory_path (str): Path to the directory to list.
        include_patterns (List[str], optional): Glob patterns to include.
        exclude_patterns (List[str], optional): Glob patterns to exclude.
        max_depth (int, optional): Maximum depth to traverse.

    Returns:
        List[str]: List of file paths matching the criteria.

    Raises:
        FileNotFoundError: If the directory doesn't exist.
    """
    if not os.path.exists(directory_path):
        raise FileNotFoundError(f"Directory {directory_path} not found")

    if not os.path.isdir(directory_path):
        raise ValueError(f"{directory_path} is not a directory")

    # Default patterns
    if include_patterns is None:
        include_patterns = ["*"]
    if exclude_patterns is None:
        exclude_patterns = []

    all_files = []
    
    for root, dirs, files in os.walk(directory_path):
        # Calculate current depth
        current_depth = root[len(directory_path):].count(os.sep)
        
        # Stop traversing deeper if max_depth is reached
        if max_depth is not None and current_depth >= max_depth:
            # Prevent descending into subdirectories
            dirs.clear()
            continue

        # Exclude directories from traversal if they match exclusions
        dirs[:] = [
            d for d in dirs 
            if d not in exclude_patterns
        ]

        for file_name in files:
            file_path = os.path.join(root, file_name)
            
            # Skip files larger than 1MB (as per original logic)
            if os.path.getsize(file_path) >= 1024 * 1024:
                continue

            # Check if file matches any include pattern
            included = any(
                glob.fnmatch.fnmatch(file_name, pattern)
                for pattern in include_patterns
            )

            if included:
                all_files.append(file_path)

    # Sort files for consistency
    all_files.sort()
    return all_files
