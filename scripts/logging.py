import os
import re
from datetime import datetime

def parse_logs(start_date: str, end_date: str, log_dir: str = "."):
    """
    Parse log files in a given directory and count successes and failures 
    for a specified date range.
    
    Args:
        start_date (str): Start date in the format "dd_mm_yyyy".
        end_date (str): End date in the format "dd_mm_yyyy".
        log_dir (str): Directory where log files are stored.
    
    Returns:
        dict: Counts of successes and failures.
    """
    # Convert date strings to datetime objects
    start_date_obj = datetime.strptime(start_date, "%d_%m_%Y")
    end_date_obj = datetime.strptime(end_date, "%d_%m_%Y")
    
    success_count = 0
    failure_count = 0

    # Regex to match log filenames
    log_pattern = re.compile(r"log_(\d{2}_\d{2}_\d{4})\.log")

    # Iterate through files in the directory
    for file_name in os.listdir(log_dir):
        match = log_pattern.match(file_name)
        if match:
            log_date_str = match.group(1)
            log_date_obj = datetime.strptime(log_date_str, "%d_%m_%Y")
            
            # Check if the log file falls within the date range
            if start_date_obj <= log_date_obj <= end_date_obj:
                log_path = os.path.join(log_dir, file_name)
                
                # Read and parse the log file
                with open(log_path, "r") as log_file:
                    for line in log_file:
                        if "Éxito en Ejecución" in line:
                            success_count += 1
                        elif "Error en Ejecución" in line:
                            failure_count += 1

    return {
        "successes": success_count,
        "failures": failure_count,
    }

# Example usage
if __name__ == "__main__":
    # Define the date range
    start_date = "01_12_2024"
    end_date = "03_12_2024"
    
    # Parse logs and count successes and failures
    log_counts = parse_logs(start_date, end_date, log_dir="../logs")
    
    # Print results
    print(f"Successes: {log_counts['successes']}")
    print(f"Failures: {log_counts['failures']}")