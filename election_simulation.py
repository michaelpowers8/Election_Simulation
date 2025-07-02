import os
import sys
import json
import shutil
import random
import hashlib
import requests
import traceback
from typing import Any
from numpy import ndarray
from bs4 import BeautifulSoup
from bs4.element import Comment
from datetime import datetime,timedelta
from xml.etree import ElementTree as ET
from pandas import read_csv,read_html,DataFrame,set_option

LOG_FILE = "Election_Simulation_Log.xml"
ARCHIVE_FOLDER = "archive"
LOG_RETENTION_DAYS = 30  
BASE_DIR:str = os.path.dirname(os.path.abspath(__file__))

def save_variable_info(locals_dict:dict[str,Any]) -> None:
    # Get the current global and local variables
    globals_dict:dict[str,Any] = globals()
    
    # Combine them, prioritizing locals (to avoid duplicates)
    all_vars:dict[str,Any] = {**globals_dict, **locals_dict}
    
    # Filter out modules, functions, and built-ins
    variable_info:list[dict[str,str|int|float|list|set|dict|bytes]] = []
    for name, value in all_vars.items():
        # Skip special variables, modules, and callables
        if name.startswith('__') and name.endswith('__'):
            continue
        if callable(value):
            continue
        if isinstance(value, type(sys)):  # Skip modules
            continue
            
        # Get variable details
        var_type:str = type(value).__name__
        try:
            var_hash:str = hashlib.sha256(str(value).encode('utf-8')).hexdigest()
        except Exception:
            var_hash:str = "Unhashable"
        
        var_size:int = sys.getsizeof(value)
        
        variable_info.append({
            "Variable Name": name,
            "Type": var_type,
            "Hash": var_hash,
            "Size (bytes)": var_size
        })
    
    # Convert to a DataFrame for nice tabular output
    df:DataFrame = DataFrame(variable_info)
    df.to_json(os.path.join(BASE_DIR,"Election_Simulation_End_Variables.json"),orient='table',indent=4)

def get_current_log_filename(basepath:str) -> str:
    """Generates a log filename based on the current date."""
    return f"{basepath}/{LOG_FILE}_{datetime.now().strftime('%Y%m%d')}.xml"

def rotate_logs():
    """Checks if the log file date has changed and archives it if needed."""
    current_date = datetime.now().strftime("%Y%m%d")
    
    # Get the last modified date of the existing log file
    if os.path.exists(LOG_FILE):
        modified_time = datetime.fromtimestamp(os.path.getmtime(LOG_FILE)).strftime("%Y%m%d")

        if modified_time != current_date:  # If the log is from a previous day, archive it
            # Ensure archive folder exists
            if not os.path.exists(ARCHIVE_FOLDER):
                os.makedirs(ARCHIVE_FOLDER)

            # Move the old log file to archive with a date-based name
            archive_filename = f"{ARCHIVE_FOLDER}/{LOG_FILE}_{modified_time}.xml"
            shutil.move(LOG_FILE, archive_filename)

            # Perform cleanup of old logs
            delete_old_logs()

def delete_old_logs():
    """Deletes logs that are older than LOG_RETENTION_DAYS."""
    cutoff_date:datetime = datetime.now() - timedelta(days=LOG_RETENTION_DAYS)

    if not os.path.exists(ARCHIVE_FOLDER):
        return  # No logs to delete

    for filename in os.listdir(ARCHIVE_FOLDER):
        if filename.startswith(f"{LOG_FILE}") and filename.endswith(".xml"):
            try:
                # Extract date from filename
                date_str:str = filename.replace(f"{LOG_FILE}", "").replace(".xml", "")
                log_date:datetime = datetime.strptime(date_str, "%Y%m%d")

                # Delete files older than retention period
                if log_date < cutoff_date:
                    file_path:str = os.path.join(ARCHIVE_FOLDER, filename)
                    os.remove(file_path)

            except ValueError:
                # Ignore files that don't match the expected date format
                pass

def log_to_xml(message:str, status="INFO", basepath=os.path.dirname(os.path.realpath(__file__))):
    """
    Logs a message to an XML file, ensuring daily log rotation and old log cleanup.
    """
    rotate_logs()  # Check if the date has changed and archive if necessary

    # Get the correct filename for today's log
    current_log_file = get_current_log_filename(basepath=basepath)

    # Create file if it does not exist
    if not os.path.exists(current_log_file):
        root = ET.Element("logs")
        tree = ET.ElementTree(root)
        tree.write(current_log_file)

    # Load existing XML file
    tree = ET.parse(current_log_file)
    root = tree.getroot()

    # Create log entry
    log_entry = ET.SubElement(root, "log")
    log_entry.set("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    log_entry.set("status", status)

    message_element = ET.SubElement(log_entry, "message")
    message_element.text = message

    # Write changes back to the file
    tree.write(current_log_file)

def _verify_configuration(configuration:dict[str,str|int]) -> bool:
    required_keys:list[str] = ["Voter_Rolls_Data_File_Path","Past_Election_Results_Data_File_Path"]
    missing_keys:list[str] = []

    for key in required_keys:
        if key not in configuration.keys():
            missing_keys.append(key)

    if len(missing_keys) > 0:
        log_to_xml(message=f"Configuration missing {','.join(missing_keys)} keys. Terminating program.",status='CRITICAL')
        return False
    return True

def load_configuration() -> dict[str,str|int]|None:
    # Safely construct the full path to Configuration.json
    config_path:str = os.path.join(BASE_DIR, "configuration.json")
    with open(config_path,"rb") as file:
        configuration:dict[str,str|int] = json.load(file)
    if not(_verify_configuration(configuration=configuration)):
        return None
    return configuration

def convert_str_to_int(value:str) -> int|str:
    try:
        return int(value.replace(",","").strip())
    except Exception as e:
        log_to_xml(f"Failed to convert {value} to integer. Official error thrown: {traceback.format_exc()}",status="ERROR")
        return value

def convert_str_percent_to_float(value:str) -> float|str:
    try:
        return round(float(value.replace(",","").replace("%","").strip())/100,5)
    except Exception as e:
        log_to_xml(f"Failed to convert {value} to integer. Official error thrown: {traceback.format_exc()}",status="ERROR")
        return value

def get_voter_rolls_data(configuration:dict[str,str|int]) -> ndarray|None:
    try:
        set_option('display.max_columns',None)
        df:DataFrame = read_csv(configuration["Voter_Rolls_Data_File_Path"])
        for column in df.columns:
            if " (in thousands)" in column:
                df[column.replace(" (in thousands)","")] = df[column].apply(convert_str_to_int)
                df = df.drop(columns=[column],axis=1)
                df[column.replace(" (in thousands)","")] = df[column.replace(" (in thousands)","")]*1000
            else:
                try:
                    df[column] = df[column].astype(float)
                except:
                    pass
        return df[["Location","Number of Registered Voters","Registered Voters as a Share of the Voter Population","Number of Individuals who Voted","Individuals who Voted as a Share of the Voter Population"]].iloc[1:].to_numpy() # Return only state data. Not the total United States numbers. Will cause redundancy.
    except Exception as e:
        log_to_xml(f"Failed to get raw data from {configuration['Voter_Rolls_Data_File_Path']}. Terminating program. Official error thrown: {traceback.format_exc()}",status="CRITICAL")
        return None
    
def get_election_results_data(configuration:dict[str,str|int]) -> ndarray|None:
    try:
        set_option('display.max_columns',None)
        df:DataFrame = read_csv(configuration["Past_Election_Results_Data_File_Path"])
        for column in df.columns:
            if "%" in column:
                df[column] = df[column].apply(convert_str_percent_to_float)
                df[column] = df[column]
            else:
                try:
                    df[column] = df[column].fillna(0)
                    df[column] = df[column].astype(int)
                except:
                    pass
        return df.to_numpy() # Return only state data. Not the total United States numbers. Will cause redundancy.
    except Exception as e:
        log_to_xml(f"Failed to get raw data from {configuration['Past_Election_Results_Data_File_Path']}. Terminating program. Official error thrown: {traceback.format_exc()}",status="CRITICAL")
        return None

def cast_vote(state:str,state_voter_rolls_data:ndarray,state_past_election_results:ndarray) -> str|None:
    if(
        (not(state == state_voter_rolls_data[0]))or
        (
            not(
                (state in ["Maine","Nebraska"])and 
                (state_voter_rolls_data[0] in ["Maine","Nebraska"])and
                (state_past_election_results[0] in ["Maine","Nebraska","CD-1","CD-2","CD-3"])
            )
        )
      ):
        log_to_xml(f"Invalid parameters past. Parameters passed: {state}, {state_voter_rolls_data}, {state_past_election_results}. No vote being cast.")
        return None
    return ""

def main():
    configuration:dict[str,str|int] = load_configuration()
    if configuration is None:
        return
    voter_rolls_data:ndarray|None = get_voter_rolls_data(configuration=configuration)
    past_election_results_data:ndarray|None = get_election_results_data(configuration=configuration)
    if voter_rolls_data is None or past_election_results_data is None:
        return
    save_variable_info(locals_dict=locals())

if __name__ == "__main__":
    main()