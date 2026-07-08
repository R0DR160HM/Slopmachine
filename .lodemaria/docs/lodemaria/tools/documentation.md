```markdown
# lodemaria/tools/documentation.py

## Purpose and Role

`lodemaria/tools/documentation.py` is a script designed to analyze, document, and update the project's source files. The script uses an AI model (configured by `DOC_MODEL`) to generate markdown documentation for each file and a separate generator (`DOC_SYNTH_MODEL`) to compile this documentation into a comprehensive overview of the whole project.

## File Discovery

The script identifies non-gitignored files in the current working directory, ignoring dotfiles and those inside dotfolders like `.git`, `.vscode`, etc. It uses `fnmatch` to match patterns defined in `.gitignore` files, ensuring only relevant files are considered.

## Index Persistence

The script stores the hash of every file worth indexing in a JSON file named `index.json`. This index is loaded and updated incrementally whenever new or changed files are found. The original hashing mechanism used by Git for tracked files is maintained to keep existing content consistent with git's history.

## Grouping (Companion Files Documented Together)

The script organizes documentation into groups based on the path of each file, ensuring that related components are documented together in one place. This helps maintain a clear and organized codebase.

## Model Calls

- **Strip Fence**: Unwraps any response wrapped entirely in one ``` fence.
- **Ask Streaming**: Sends a prompt to the model in real-time as it processes the output, rendering it live in the terminal.

## Entry Point

The main function `write_project_documentation()` performs the following steps:
1. Indexes the current directory for documentable files.
2. Compares the index with an old version (if available) to identify new, changed, or removed groups of files and documents them individually.
3. Compiles a comprehensive overview of the project using another model (`DOC_SYNTH_MODEL`) and updates the `PROJECT.md` file.
4. Removes empty directories left by stale-documentation removal.

## Notes

- The script uses the OLLAMA_OPTIONS to customize the behavior of the OpenAI model used for document generation.
- The index is persisted incrementally, ensuring that existing content remains consistent with git's history.

## Conclusion

By combining efficient file discovery, robust documentation generation, and a comprehensive overview, `lodemaria/tools/documentation.py` helps maintain high-quality code documentation and ensures consistency across the project.
