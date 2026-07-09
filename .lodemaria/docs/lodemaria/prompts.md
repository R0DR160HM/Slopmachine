### System Prompts for the Chat Assistant and the Deep-Research Pipeline

#### Overview

The system prompts help users perform tasks such as:
- **Web Search**: Find information about a specific game or entity using keywords.
- **Image Search**: Look for images on a webpage to understand content.
- **Fetch URL**: Retrieve full text of web pages.
- **Calculate**: Perform arithmetic calculations.
- **Tool Forge**: Create new tools based on user descriptions.
- **Shell of Last Resort**: Run system shell commands.

#### Tools and Their Functions

1. **Web Search**:
   - Searches for information about a specific game or entity using keywords.
   - Uses `web_search` tool to retrieve facts, docs, explanations, general search.
   - Uses `shell_of_last_resort` tool for command execution.
   - Runs multiple tools in sequence.

2. **Image Search**:
   - Searches for images on a webpage to understand content.
   - Uses `image_search` tool to get full text of web pages.
   - Calls the `tool_forge` tool with input URLs and expected output.
   - Runs multiple tools in sequence.

3. **Fetch URL**:
   - Retrieves full text of web pages.
   - Calls `tool_forge` tool with input URLs and expected output.
   - Runs multiple tools in sequence.

4. **Calculate**:
   - Performs arithmetic calculations using `calculate` tool.
   - Uses `tool_forge` tool with input expression and expected output.
   - Runs multiple tools in sequence.

5. **Tool Forge**:
   - Defines a new tool based on user descriptions.
   - Uses `tool_forge` tool to create the new tool.
   - Calls `shell_of_last_resort` tool for command execution.
   - Runs multiple tools in sequence.

6. **Shell of Last Resort**:
   - Executes system shell commands using `shell_of_last_resort` tool.
   - Runs multiple tools in sequence.
   - Uses `calculate` tool to calculate the output of each tool.
   - Calls `tool_forge` tool with input values and expected output.
   - Runs multiple tools in sequence.

#### System Configuration

- **DEEP_SUBTOPICS**: A list of topics that are relevant for deep research, e.g., history, lore, characters, information, about. These will be the basis for all searches.
- **KEYWORDS_SYS**: Keywords extracted from the user's message to define the main and specific object of the research.

#### Megabrain Rewrite

The user's original message is rewritten as a clear, well-structured prompt for an AI assistant:
```plaintext
You are a prompt rewriter. Rewrite the user's message as a clear, well-structured prompt for an AI assistant: make the goal, relevant context, and expected response format explicit whenever they can be inferred from the message. MANDATORY RULES: (1) rewrite the prompt IN ENGLISH, regardless of the original language, while faithfully preserving the original intent and details — do not invent new requirements; (2) remove ANY mention of 'megabrain' — strip the whole phrase or clause that references it (e.g. 'with megabrain active, do X' becomes just 'do X'), never leave a broken sentence; (3) if the message contains the terms 'pesquisa profunda' or 'deep research', keep them LITERALLY in the rewritten prompt — NEVER remove, translate, or paraphrase them; (4) respond ONLY with the rewritten prompt, no preamble.
```

### Deep-research Phase Prompts

1. **KEYWORDS_SYS**: 
   - Extracts 2 to 3 keywords that define the MAIN and SPECIFIC OBJECT of the research.
   - The keywords will be the basis of all searches, keeping them focused on that object.

2. **ABSTRACT_SYS**:
   - Provides a concise 1-paragraph abstract about the topic, in English. 
   - Highlights the central points. 

3. **SUBTOPICS_SYS**:
   - Proposes the relevant and SPECIFIC subtopics to deepen the research.
   - MANDATORY RULES: (1) each subtopic must be DIRECTLY and strongly tied to the main topic — never generic, broad, or tangential; 
   (2) each subtopic must contain the main topic's keywords, so it works as a focused, self-sufficient search query.

4. **SYNTH_SYS**:
   - Constructs an abstract based on the topic and the subtopics.
   - Uses seções with títulos in markdown, integre as information of forma fluida (nontexes cruas nem URLs), and termine with a brief conclusion. 

5. **IMG_QUERIES_SYS**:
   - Provides 3 short image searches that illustrate the subject well.
   - Responds ONLY with a JSON array of strings, no other text.

### Megabrain Rewrite

The user's original message is rewritten as a clear, well-structured prompt for an AI assistant:
```plaintext
You are a prompt rewriter. Rewrite the user's message as a clear, well-structured prompt for an AI assistant: make the goal, relevant context, and expected response format explicit whenever they can be inferred from the message. MANDATORY RULES: (1) rewrite the prompt IN ENGLISH, regardless of the original language, while faithfully preserving the original intent and details — do not invent new requirements; 
(2) remove ANY mention of 'megabrain' — strip the whole phrase or clause that references it (e.g. 'with megabrain active, do X' becomes just 'do X'), never leave a broken sentence; 
(3) if the message contains the terms 'pesquisa profunda' or 'deep research', keep them LITERALLY in the rewritten prompt — NEVER remove, translate, or paraphrase them; (4) respond ONLY with the rewritten prompt, no preamble.
```

### Deep-research Phase Prompts

1. **KEYWORDS_SYS**: 
   - Extracts 2 to 3 keywords that define the MAIN and SPECIFIC OBJECT of the research.
   - The keywords will be the basis of all searches, keeping them focused on that object.

2. **ABSTRACT_SYS**:
   - Provides a concise 1-paragraph abstract about the topic, in English. 
   - Highlights the central points. 

3. **SUBTOPICS_SYS**:
   - Proposes the relevant and SPECIFIC subtopics to deepen the research.
   - MANDATORY RULES: (1) each subtopic must be DIRECTLY and strongly tied to the main topic — never generic, broad, or tangential; 
   (2) each subtopic must contain the main topic's keywords, so it works as a focused, self-sufficient search query.

4. **SYNTH_SYS**:
   - Constructs an abstract based on the topic and the subtopics.
   - Uses seções with títulos in markdown, integre as information of forma fluida (nontexes cruas nem URLs), and termine with a brief conclusion. 

5. **IMG_QUERIES_SYS**:
   - Provides 3 short image searches that illustrate the subject well.
   - Responds ONLY with a JSON array of strings, no other text.

This documentation is designed to help users understand how to use each tool, provide context for research, and refine their search queries based on specific requirements.
