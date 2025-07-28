# Adobe India Hackathon 2025: PDF Outline Extractor

This project is a submission for Round 1A of the "Connecting the Dots" challenge. The goal is to build a robust and efficient solution that extracts a structured outline (Title, H1, H2, H3) from PDF documents.

The solution is packaged in a lightweight, offline Docker container that meets all the specified performance and size constraints.

## Our Approach

To accurately identify headings, our solution goes beyond simply analyzing font sizes. It employs a multi-faceted heuristic approach that combines structural analysis with content-based rules.

The core logic is implemented in the `MultilingualHeadingExtractor` class and follows these steps:

1.  **Text Block Extraction:** The script first parses the PDF page by page using the `PyMuPDF` library, extracting all text blocks along with their properties, such as font size, font weight (bold), and page number.

2.  **Font Size Clustering:** Instead of relying on absolute font sizes, we identify potential heading font sizes by clustering them. This allows the system to adapt to documents that use different font scales and makes it resilient to minor font variations. The largest font clusters are assumed to correspond to H1, H2, and H3 levels.

3.  **Content-Based Heading Detection:** Each line of text is passed through a `is_likely_heading` function. This function uses a set of rules to determine if a line *reads* like a heading. It checks for:
    * Short line length.
    * Absence of sentence-ending punctuation.
    * Capitalization or numerical start.
    * Low density of common "stop words".

4.  **Multilingual Support (Bonus):** For the bonus points, the solution includes logic to detect the primary script of the text (e.g., Latin, Japanese, Chinese). It then applies language-specific rules for identifying headings, such as looking for common particles in Japanese or avoiding certain sentence structures.

5.  **Final Assembly:** Text blocks that are identified as headings through both font and content analysis are compiled into the final JSON output, sorted by page number and heading level.

## Libraries and Dependencies

* **PyMuPDF (fitz):** A high-performance Python library for PDF parsing and text extraction.

All dependencies are listed in the `requirements.txt` file and are installed within the Docker container.

## How to Build and Run

The solution is containerized using Docker and is designed to run completely offline.

### 1. Build the Docker Image

Navigate to the project's root directory in your terminal and run the following command. Replace `project1a` with your team or project name.

```bash
docker build --platform linux/amd64 -t project1a:latest .
```

### 2. Run the Solution

Place all the PDF files you want to process into the `input` directory. Then, run the following command to start the container. The script will automatically process all PDFs and place the corresponding JSON output in the `output` directory.

```bash
docker run --rm -v "$(pwd)/input:/app/input" -v "$(pwd)/output:/app/output" --network none project1a:latest
```

## Project Structure

```
/
|-- input/              # Place input PDFs here
|-- output/             # JSON output will be generated here
|-- Dockerfile          # Instructions to build the Docker image
|-- .dockerignore       # Specifies files to exclude from the image
|-- requirements.txt    # Lists Python dependencies
|-- extractor2.py       # Main application script
`-- utils.py            # (If you have one) Utility functions
```