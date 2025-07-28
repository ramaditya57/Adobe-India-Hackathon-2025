# Methodology: A Persona-Driven Approach to Intelligent Document Extraction

Navigating large collections of documents to find specific, relevant information is a significant challenge. This system addresses that challenge with a sophisticated, multi-layered methodology designed to think like the user. By deeply understanding the user's **persona** and **job-to-be-done**, it pinpoints and extracts the most valuable information from a PDF corpus.

---

## A Four-Stage Intelligence Pipeline

The extraction process is a pipeline that moves from a high-level overview down to fine-grained details, ensuring accuracy and relevance at every step.

### 1. Intelligent Document Sectioning 📑
Instead of treating PDFs as flat text files, the pipeline first deconstructs each document into its **semantic sections**. By analyzing structural cues like **font size and boldness**, the engine accurately identifies headers and groups the corresponding content. This initial step is crucial because it ensures all subsequent analysis is performed on meaningful, self-contained chunks of information, mirroring how a human would read the document.

### 2. Dynamic Relevance Scoring 🧠
The system's core intelligence lies in its ability to **dynamically adapt to each unique query**. It avoids rigid, pre-programmed rules and instead:
1.  **Generates Contextual Keywords**: It automatically parses the `persona` and `job-to-be-done` to create a bespoke set of keywords for the specific task.
2.  **Employs a Hybrid Scoring Model**: Each section is evaluated using a powerful combination of:
    * **Semantic Understanding**: A `SentenceTransformer` model (`all-MiniLM-L6-v2`) grasps the *meaning* and *intent* behind the text, finding relevant content even if it doesn't use the exact keywords.
    * **Lexical Boosting**: The dynamically generated keywords provide a targeted score boost, ensuring that sections containing critical terms are given priority.

### 3. Document-Level Prioritization 🏆
Not all documents are created equal. To mirror human intuition, the engine performs **document-level prioritization**. It first scores each PDF based on the relevance of its **filename** (e.g., a "Fill & Sign" guide is inherently more important for a forms-related task). This score provides a powerful boost to all sections within that document. This ensures that the system focuses its attention on the most promising sources first, dramatically improving the quality of the final results.

### 4. Precision Sentence-Cluster Extraction ✨
The final stage moves from broad relevance to **pinpoint precision**. For each of the top-ranked sections, the engine performs a micro-analysis to find the most valuable snippet. It scans every sentence, identifies the one with the highest relevance score, and extracts it along with its **immediate neighbors** (the preceding and succeeding sentences). This "3-sentence cluster" provides the user with the most potent piece of information, presented with just enough context to be perfectly understandable and actionable.

---
### Conclusion
In summary, this methodology creates a robust and intelligent pipeline that effectively mirrors human research patterns. It starts by understanding the high-level document landscape, then dynamically scores and ranks sections based on the user's specific needs, and finally drills down to extract the most precise and contextually rich information available.

---

## Execution Instructions

### Prerequisites
* [Docker](https://www.docker.com/get-started) must be installed and running on your system.

### Directory Structure
Before running, organize your files into the following structure. The `collection_name` folder is the main directory for your task.

```
/path/to/your/collection_name
|
|-- input.json  (Your JSON file with persona and job)
|
|-- /PDFs
    |-- doc1.pdf
    |-- doc2.pdf
    |-- ...
```

### Execution Steps
1.  **Prepare Files**: In a new, separate folder, save the Python script as `persona_extractor.py`, the `Dockerfile` provided previously, and a `requirements.txt` file.

2.  **Build the Docker Image**: Open a terminal in the folder containing your `Dockerfile` and run the build command. This will create a Docker image named `persona-extractor`.
    ```sh
    docker build -t persona-extractor .
    ```

3.  **Run the Extractor**: Execute the following command, replacing `/path/to/your/collection_name` with the actual, absolute path to your data folder.
    ```sh
    docker run --rm -v "/path/to/your/collection_name:/data" persona-extractor /data
    ```
    * **On Windows (Command Prompt)**: You may need to adjust the path format:
        `docker run --rm -v "C:\path\to\your\collection_name:/data" persona-extractor /data`

4.  **Get the Output**: An `challenge1b_output.json` file will be created inside your original `/path/to/your/collection_name` folder.