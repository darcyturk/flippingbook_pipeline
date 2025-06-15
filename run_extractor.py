# run_extractor.py

# Import necessary libraries
import asyncio  # For running our asynchronous code (like web browsing)
import argparse # For creating command-line arguments (like --steps)
import logging  # For creating structured, professional log messages instead of just print()
import sys      # Needed to tell the logger to also print to the console

# Import our main pipeline function from the 'src' package
from src.main import main as run_pipeline

# This is a standard Python construct. It checks if this script is being run directly
# by the user (e.g., 'python run_extractor.py'). If it is, the code inside this block will execute.
# If this file were imported by another file, this code would NOT run.
if __name__ == "__main__":
    
    # --- Central Logging Configuration ---
    # This sets up the logging for the entire application, one time.
    logging.basicConfig(
        level=logging.INFO,  # Set the minimum level of messages to show (e.g., INFO, WARNING, ERROR)
        
        # Define the format for every log message.
        # asctime = timestamp, levelname = INFO/ERROR, name = filename, message = the log text
        format="%(asctime)s - %(levelname)-8s - %(name)-25s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S", # The format for the timestamp
        
        # Define where the logs should go.
        handlers=[
            logging.FileHandler("pipeline.log"), # Save all logs to a file named 'pipeline.log'
            logging.StreamHandler(sys.stdout),   # Also print all logs to the console/terminal
        ]
    )

    # --- Argument Parsing Setup ---
    # This creates the system that understands command-line arguments.
    parser = argparse.ArgumentParser(
        description="Run the FlippingBook data extraction pipeline.",
        formatter_class=argparse.RawTextHelpFormatter # Helps format the help text nicely
    )
    
    # Define the '--steps' argument.
    parser.add_argument(
        '--steps',
        nargs='+',              # Allows one or more values (e.g., --steps 1 2)
        type=int,               # Expects the values to be integers
        choices=[1, 2, 3],      # Only allows the numbers 1, 2, or 3
        default=[1, 2, 3],      # If the user provides no --steps argument, run all steps by default
        help="""Specify which pipeline steps to run.
    1: Capture Pager Data
    2: Process Pages and Generate Images/Tasks
    3: Perform OCR on Product Images
Example: python run_extractor.py --steps 1 3
"""
    )
    # Parse the arguments provided by the user in the terminal.
    args = parser.parse_args()

    # --- Pipeline Execution ---
    logging.info("=" * 60)
    logging.info("FlippingBook Product Extraction Pipeline Starting...")
    logging.info("Running steps: %s", args.steps) # Log which steps are being run
    logging.info("=" * 60)

    try:
        # This is where the magic happens. We call our main pipeline function and pass it
        # the list of steps the user wants to run.
        # asyncio.run() starts the asynchronous event loop.
        asyncio.run(run_pipeline(steps_to_run=args.steps))
        
    except KeyboardInterrupt:
        # A user-friendly message if the user stops the script with Ctrl+C
        logging.warning("Pipeline interrupted by user.")
    except Exception as e:
        # A catch-all for any unexpected errors, so the program doesn't just crash silently.
        # 'exc_info=True' adds a detailed traceback to the log file for debugging.
        logging.critical("An unexpected error occurred: %s", e, exc_info=True)
    finally:
        # This block will always run, whether the script succeeded or failed.
        logging.info("=" * 60)
        logging.info("Pipeline execution finished.")
