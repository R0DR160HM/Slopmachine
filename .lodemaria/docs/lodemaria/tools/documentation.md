### File: lodemaria/tools/documentation.py

#### Purpose and Role

This script provides an incremental, model-written version of the project documentation. It indexes non-gitignored files, documents new or changed files, and persists the index across runs. The document content is then rendered in real-time to live updates in the terminal.

#### Public/Exported Classes

1. **\_git_files**: Non-ignored files based on git itself (tracked + untracked that are not excluded).
2. **\_gitignore_patterns**: Patterns from the root .gitignore.
3. **\_fallback_files**: Recursively walks excluding `.gitignore` and non-tracked files within the root directory.

#### Notable Internal Logic

- **Hashing Files**: The script hashes each file to ensure uniqueness across different systems.
- **Doc Processing**: It processes source code files, documents new or changed ones, and persists the index. It also refreshes stylesheets and markdown whenever documentation changes.
  
#### When Several Companion Files are Given

- **Organizing Documentation**: The script organizes companion files into a single unit (one for each project group).
- **Style Sheets and Markdown**: Stylesheets and markdown are hashed but never documented.

#### General Documentation

- **Project Overview**: A comprehensive overview of the entire project is generated.
- **Docs for Groups**: Documents are categorized by group, with new documents appearing first in the index.
- **File Changes**: New files or changes are detected and indexed, then re-written in the index.
- **Failed Groups**: The script handles groups that may have been deleted or removed during an interrupted run.

#### Entry Point

- **Writing Project Documentation**: Runs the document generation process based on the current folder's structure.
- **Index Persistence**: Persisted indices are maintained across runs to avoid redundant processing.

This documentation is useful for developers who need a quick overview of the project's codebase and any changes over time.
