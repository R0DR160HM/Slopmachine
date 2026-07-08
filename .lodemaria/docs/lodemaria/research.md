# Deep Research Mode: A Multi-Phase Autonomous Research Pipeline

Deep research mode is a powerful feature that enables autonomous, multi-phase research operations. It interprets the user's message, gathers an overview, writes an abstract, derives subtopics, dives into each one, synthesizes a report and closes with images.

Triggered when the user's message matches DEEP_RESEARCH_RE (e.g., "deep research" or "pesquisa profunda"), the pipeline performs the following steps:

1. **Phase 1: Extract Keywords**:
   - The user's message is cleaned to extract keywords that define the main object of the research.
   - These keywords are forced into every search query, ensuring the research never drifts to generic pages.

2. **Phase 2: General Research**:
   - A general text search based on the extracted keywords is run.
   - News results are also included if requested.

3. **Phase 3: Write an Abstract**:
   - The results of the search are summarized into an abstract using the LLM model.

4. **Phase 4: Derive Subtopics**:
   - The abstract is used to derive subtopics based on a predefined set of rules.
   - Each subtopic is forced into every subquery, ensuring the research never drifts to generic pages.

5. **Phase 5: Deep Research on Each Subtopic**:
   - For each subtopic, a specific text and news search is performed.
   - The results are collected and stored in a list.

6. **Phase 6: Synthesize Everything into One Cohesive Report**:
   - The collected data is combined into a cohesive report using the LLM model.
   - Relevant images are displayed at the end of the report.

7. **Phase 7: Relevant Images to Close It Off**:
   - A final search based on the keywords and subtopics is performed to find relevant images.
   - These images are displayed in the report.

This multi-phase approach ensures that the research is comprehensive, accurate, and reliable, making it ideal for both academic and professional use cases.
