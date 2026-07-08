# `lodemaria/config.py`: Static Configuration Shared Across the Application

The `lodemaria` project utilizes a centralized configuration file, `config.py`, to manage various settings and constants that govern its behavior. This file is designed to be easily modified or extended as needed for different deployment scenarios or specific use cases.

## Overview

- **DEFAULT_MODEL**: The default model used when the user mentions "megabrain" in a message.
- **MEGABRAIN_MODEL**: The model activated when the user specifically requests assistance with megabrain-related tasks.
- **FORGE_MODEL**: The model utilized by `tool_forge` to generate new tools written in Python.
- **DOC_MODEL**: The model employed by `write_project_documentation` for generating per-file documentation.
- **DOC_SYNTH_MODEL**: The model that synthesizes the general `PROJECT.md` from the per-file docs, a prose task, so the general model fits better than the coder one.
- **DOC_GROUP_MAX_CHARS**: Combined per-file docs fed to the doc model for the general `PROJECT.md`, with a maximum character limit of 20,000 chars per file group.
- **DOC_PROJECT_MAX_CHARS**: The total maximum character limit for the combined per-file docs and the general `PROJECT.md`.
- **DEFAULT_MAX_RESULTS**: Maximum search results requested per query.
- **FORGED_RESULT_MAX_CHARS**: Char budget for the conversation we send each turn before truncating it to the `FORGED_RESULT_MAX_CHARS` limit, so a runaway tool cannot flood the context window.
- **NUM_CTX**: Context window (tokens) sent to Ollama. Set explicitly so behaviour is predictable instead of relying on Ollama's small default (~2048-4096).
- **OLLAMA_OPTIONS**: Options passed on every `ollama.chat()` call, specifically setting `num_thread` and `num_ctx` to the configured value.
- **HISTORY_CHAR_BUDGET**: Char budget for the conversation we send each turn. Roughly `NUM_CTX * 4` chars per token minus headroom for the model's own reply.
- **MAX_TOOL_CALLS**: Maximum number of tool calls allowed within a single user turn to prevent infinite loops.

## Internal Logic

The configuration file includes several constants that control various aspects of the system, such as:

- **DEFAULT_MODEL** and **MEGABRAIN_MODEL**: These are used for different modes in the application.
- **FORGE_MODEL**, **DOC_MODEL**, and **DOC_SYNTH_MODEL**: These models are used by different parts of the application for specific tasks.
- **NUM_CTX**: This setting is explicitly set to `30_000`, ensuring a predictable context window size for Ollama.
- **OLLAMA_OPTIONS** and **HISTORY_CHAR_BUDGET**: These options control how messages are trimmed, with `NUM_CTX * 4` being a rough estimate of the character budget per turn.

## Notable Side Effects

- **Deep research mode**: This allows for more detailed explorations of topics by fetching full text from external sources.
- **Configuration management**: The ability to easily modify or extend the configuration settings through this file makes it highly configurable for different use cases and environments.

This centralized approach ensures that all components of the `lodemaria` project can be managed and updated efficiently, making it easier to maintain and scale the system.
