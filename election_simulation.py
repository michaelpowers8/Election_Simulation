import os
import json
import random
import requests
import traceback
from xml_logging import XML_Logger
from numpy import ndarray
from bs4 import BeautifulSoup
from bs4.element import Comment
from pandas import read_csv,read_html,DataFrame,set_option

def _verify_configuration(configuration:dict[str,str|int],logger:XML_Logger) -> bool:
    required_keys:list[str] = ["Voter_Rolls_Data_File_Path","Past_Election_Results_Data_File_Path"]
    missing_keys:list[str] = []

    for key in required_keys:
        if key not in configuration.keys():
            missing_keys.append(key)

    if len(missing_keys) > 0:
        logger.log_to_xml(message=f"Configuration missing {','.join(missing_keys)} keys. Terminating program.",status='CRITICAL')
        return False
    return True

def load_configuration(logger:XML_Logger) -> dict[str,str|int]|None:
    # Safely construct the full path to Configuration.json
    config_path:str = os.path.join(logger.base_dir, "configuration.json")
    with open(config_path,"rb") as file:
        configuration:dict[str,str|int] = json.load(file)
    if not(_verify_configuration(configuration=configuration,logger=logger)):
        return None
    return configuration

def convert_str_to_int(value:str,logger:XML_Logger) -> int|str:
    try:
        return int(value.replace(",","").strip())
    except Exception as e:
        logger.log_to_xml(f"Failed to convert {value} to integer. Official error thrown: {traceback.format_exc()}",status="ERROR")
        return value

def convert_str_percent_to_float(value:str,logger:XML_Logger) -> float|str:
    try:
        return round(float(value.replace(",","").replace("%","").strip())/100,5)
    except Exception as e:
        logger.log_to_xml(f"Failed to convert {value} to integer. Official error thrown: {traceback.format_exc()}",status="ERROR")
        return value

def get_voter_rolls_data(configuration:dict[str,str|int],logger:XML_Logger) -> ndarray|None:
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
        logger.log_to_xml(f"Failed to get raw data from {configuration['Voter_Rolls_Data_File_Path']}. Terminating program. Official error thrown: {traceback.format_exc()}",status="CRITICAL")
        return None
    
def get_election_results_data(configuration:dict[str,str|int],logger:XML_Logger) -> ndarray|None:
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
        logger.log_to_xml(f"Failed to get raw data from {configuration['Past_Election_Results_Data_File_Path']}. Terminating program. Official error thrown: {traceback.format_exc()}",status="CRITICAL")
        return None

def _verify_castable_vote(state:str,state_voter_rolls_data:ndarray,state_past_election_results:ndarray) -> bool:
    if(not(isinstance(state,str))):
        return False
    if(not(isinstance(state_voter_rolls_data,ndarray))):
        return False
    if(not(isinstance(state_past_election_results,ndarray))):
        return False
    if(
        (not(state == state_voter_rolls_data[0]))or # If the state name provided is not the same as the state found in the voter roll data
        (
            not(
                (state in ["Maine","Nebraska"])and 
                (state_voter_rolls_data[0] in ["Maine","Nebraska"])and
                (state_past_election_results[0] in ["Maine","Nebraska","CD-1","CD-2","CD-3"])
            )
        )
      ):
        return False
    if(state=="Maine" and state_past_election_results[0] == "CD-3"):
        return False
    if((state == "Maine" and state_past_election_results[0] in ["Maine","CD-1","CD-2"]) and (state == state_voter_rolls_data[0])):
        return True
    if((state == "Nebraska" and state_past_election_results[0] in ["Nebraska","CD-1","CD-2","CD-3"]) and (state == state_voter_rolls_data[0])):
        return True
    if((state == state_past_election_results[0]) and (state == state_voter_rolls_data[0])):
        return True

def cast_vote(state:str,state_voter_rolls_data:ndarray,state_past_election_results:ndarray,logger:XML_Logger) -> str|None:
    if(not(_verify_castable_vote(state=state,state_voter_rolls_data=state_voter_rolls_data,state_past_election_results=state_past_election_results))):
        logger.log_to_xml(f"Invalid parameters past. Parameters passed: {state}, {state_voter_rolls_data}, {state_past_election_results}. No vote being cast.")
        return None
    number_of_registered_voters:int = state_voter_rolls_data[1]
    return ""

def main():
    logger:XML_Logger = XML_Logger(log_file="Election_Simulation_Logger.xml",log_retention_days=7)
    configuration:dict[str,str|int] = load_configuration(logger=logger)
    if configuration is None:
        return
    voter_rolls_data:ndarray|None = get_voter_rolls_data(configuration=configuration,logger=logger)
    past_election_results_data:ndarray|None = get_election_results_data(configuration=configuration,logger=logger)
    if voter_rolls_data is None or past_election_results_data is None:
        return
    logger.save_variable_info(locals_dict=locals())

if __name__ == "__main__":
    main()