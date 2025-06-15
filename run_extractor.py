# run_extractor.py
import asyncio
import argparse
import logging
import sys
from pathlib import Path

# Import RichHandler here for centralized logging
from rich.logging import RichHandler
from rich.console import Console # Useful for rich.print and general console operations

# Import your main pipeline entry point
from src.main import main as run_pipeline

# Import the new HAR generation utility
from src.utils.har_generator import generate_har

if __name__ == "__main__":
    # --- Centralized Logging Configuration ---
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO) # Default level

    formatter = logging.Formatter(
        fmt="%(asctime)s - %(levelname)-8s - %(name)-25s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    log_file_path = Path("pipeline.log")
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(logging.DEBUG) # Log all debug messages to file
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    rich_handler = RichHandler(
        level=logging.DEBUG, # Set to DEBUG for detailed console output during development
        show_time=True,
        show_level=True,
        show_path=False,
    )
    root_logger.addHandler(rich_handler)

    # --- Argument Parsing ---
    parser = argparse.ArgumentParser(
        description="Run the FlippingBook data extraction pipeline.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        '--steps',
        nargs='+',
        type=int,
        choices=[1, 2],
        default=[1, 2],
        help="""Specify which pipeline steps to run.
    1: Capture Page HTML and Extract Publication Model
    2: Extract Product Data from XML
Example: python run_extractor.py --steps 2
"""
    )
    parser.add_argument(
        '--generate-har',
        action='store_true', # This makes it a boolean flag
        help="Generate a HAR file for analysis instead of running the pipeline."
    )
    parser.add_argument(
        '--har-url',
        type=str,
        default="https://online.flippingbook.com/view/890674106/", # Default target URL for HAR
        help="URL to generate HAR for (used with --generate-har)."
    )
    parser.add_argument(
        '--har-output',
        type=str,
        default="har_analysis_output.har", # Default HAR output file name
        help="Output filename for the generated HAR file (used with --generate-har)."
    )

    args = parser.parse_args()

    # --- Conditional Execution based on Arguments ---
    if args.generate_har:
        logging.info("--- HAR Generation Mode ---")
        har_output_path = Path(args.har_output)
        # Ensure the directory for the HAR file exists if it's not in the current dir
        if har_output_path.parent:
            har_output_path.parent.mkdir(parents=True, exist_ok=True)
            
        try:
            # Run the HAR generation utility
            asyncio.run(generate_har(args.har_url, har_output_path, timeout_ms=60000)) # 60 sec timeout for HAR gen
        except Exception as e:
            logging.critical("An error occurred during HAR file generation: %s", e, exc_info=True)
        finally:
            logging.info("--- HAR Generation Finished ---")
        sys.exit(0) # Exit after generating HAR

    # --- Normal Pipeline Execution (if --generate-har is not used) ---
    logging.info("=" * 60)
    logging.info("FlippingBook Product Extraction Pipeline Starting...")
    logging.info("Running steps: %s", args.steps)
    logging.info("=" * 60)

    try:
        asyncio.run(run_pipeline(steps_to_run=args.steps))
    except KeyboardInterrupt:
        logging.warning("Pipeline interrupted by user.")
    except Exception as e:
        logging.critical("An unexpected error occurred: %s", e, exc_info=True)
    finally:
        logging.info("=" * 60)
        logging.info("Pipeline execution finished.")
