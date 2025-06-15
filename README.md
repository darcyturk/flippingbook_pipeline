# FlippingBook Data Extraction Pipeline

This project is a complete, automated workflow for scraping product information from online FlippingBook catalogs. It handles everything from web automation and network interception to parallelized OCR, producing clean, structured JSON files for each product. The architecture is designed to be modular, traceable, and performant.

## ✨ Features

* **Multi-Step Architecture**: The pipeline is broken into three distinct, runnable steps for traceability and debugging.
* **Automated Web Scraping**: Uses Playwright to launch a headless browser and capture the catalog's structure from network data.
* **Targeted Image Processing**: Downloads full-page images and programmatically crops out individual product areas for precise analysis.
* **Parallelized OCR**: Leverages all available CPU cores to run OCR on multiple product images simultaneously, dramatically reducing processing time.
* **Structured Output**: Produces clean, commented, and structured JSON files for each extracted product.
* **Automated Setup**: Includes a `setup.sh` script to automate the installation of all system and Python dependencies.

## ✅ Prerequisites

Before you begin, ensure you have the following installed on your system:

* Python 3.8+
* Git
* Homebrew (on macOS) or `apt-get` (on Debian/Ubuntu) for system package management.

## 🛠️ Setup and Installation

A setup script is provided to automate the installation of all necessary dependencies.

> **Note:** The setup script will create a Python virtual environment (`venv`) to keep the project's dependencies isolated.

1.  **Clone the Repository:**
    ```bash
    git clone [https://github.com/YOUR_USERNAME/flippingbook-pipeline.git](https://github.com/YOUR_USERNAME/flippingbook-pipeline.git)
    cd flippingbook-pipeline
    ```

2.  **Make the Setup Script Executable:**
    This command gives your system permission to run the script. You only need to do this once.
    ```bash
    chmod +x setup.sh
    ```

3.  **Run the Setup Script:**
    This will install Tesseract, all Python packages, and the necessary Playwright browser binaries.
    ```bash
    ./setup.sh
    ```

## 🚀 How to Run the Pipeline

After a successful setup, you are ready to run the extractor. If you are in a new terminal session, remember to activate the virtual environment first.

```bash
source venv/bin/activate
```

1.  **Run the Full Pipeline:**
    To execute all steps from start to finish, run the main script:
    ```bash
    python run_extractor.py
    ```

2.  **Run Specific Steps:**
    You can run any combination of steps using the `--steps` argument. This is useful for debugging or re-running a specific part of the process.

    * **Run only data capture (Step 1):**
        ```bash
        python run_extractor.py --steps 1
        ```
    * **Run only the OCR analysis on existing images (Step 3):**
        ```bash
        python run_extractor.py --steps 3
        ```
    * **Run data capture and then OCR, skipping image processing (Steps 1 and 3):**
        ```bash
        python run_extractor.py --steps 1 3
        ```

## 📂 Project Structure

The project uses a clean, modular structure to separate concerns.

```
flippingbook_pipeline/
├── data/              # Stores all generated output from the pipeline
│   ├── 1_pager/       # Raw catalog structure JSON
│   ├── 2_pages/       # Page layout JSON files
│   ├── 3_images/      # Cropped product images
│   └── 4_products/    # Final structured product JSON files
├── src/               # Contains all the source code for the application
│   ├── delegates/     # Handles specific, low-level tasks (e.g., file I/O)
│   ├── models/        # Defines the data structures
│   ├── pipeline/      # Contains the high-level logic for each step
│   ├── main.py        # The main orchestrator that calls the steps
│   └── config.py      # Central configuration for the pipeline
├── .gitignore         # Tells Git which files to ignore
├── run_extractor.py   # The main entry point script you execute
├── requirements.txt   # Lists all Python package dependencies
└── setup.sh           # Automates the installation process
```

## 📊 Output

The final, structured data for each extracted product will be saved as a separate JSON file in the `data/4_products/` directory. Each file will contain detailed information such as the product URL, name, and any prices or SKUs found via OCR.
