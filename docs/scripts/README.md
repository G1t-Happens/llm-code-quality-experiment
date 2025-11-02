# Source Code Extraction Script

This Bash script recursively extracts source code files from a project into a single text file. It supports file extension filters and directory exclusions, and automatically skips generated or binary files.

## Usage

```bash
./extract_sourcecode.sh -p <project_path> -o <output_file> -e <.ext ...> [-x <exclude_dir ...>]
```

## Options

- `-p, --path <path>`  
  Project root directory (default: current directory)

- `-o, --output <file>`  
  Output text file (default: `extracted_sources.txt`)

- `-e, --ext <.ext ...>`  
  File extensions to include, e.g., `.java`, `.groovy`, `.xml`. At least one required.

- `-x, --exclude <dir ...>`  
  Additional directories or paths to exclude from extraction

- `-h, --help`  
  Show help message

## Notes

- Binary files are automatically skipped.
- Common generated directories (`build`, `target`, `*/generated/*`) are excluded by default.
- Works with any project structure (not limited to Spring Boot).
