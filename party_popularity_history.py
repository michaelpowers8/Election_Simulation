import os
import re
import csv
import requests
import traceback
from bs4 import BeautifulSoup
from xml_logging import XML_Logger
CURRENT_DIRECTORY:str = os.getcwd()

def _get_website_text(state:str,logger:XML_Logger) -> str|None:
    try:
        response:requests.Response = requests.get(f"https://www.270towin.com/states/{state}")
        html_content:str = response.text

        soup:BeautifulSoup = BeautifulSoup(html_content, 'html.parser')
        visible_text:str = soup.get_text()
        cleaned_text:list[str] = []
        for line in visible_text.splitlines():
            if len(line.strip()) > 0:
                cleaned_text.append(f"{line.strip()}")
        return '\n'.join(cleaned_text)
    except Exception as e:
        logger.log_to_xml(message=f"Failed to get website text. Terminating program. Official error: {traceback.format_exc()}",basepath=logger.base_dir,status="CRITICAL")
        return None

def pct_to_float(value:str,logger:XML_Logger) -> str:
    try:
        return float(value.strip().replace('%',''))/100
    except Exception as e:
        logger.log_to_xml(message=f"Failed to convert the percent to a float. Official error: {traceback.format_exc()}",basepath=logger.base_dir,status="WARN")
        return value

def past_election_results(state:str,logger:XML_Logger) -> list[list[int|float]]|None:
    try:
        webpage:str|None = _get_website_text(state=state,logger=logger)
        if webpage is None:
            return None
        lines:list[str] = webpage.splitlines()
        recent_presidential_elections_found:bool = False
        past_results:list[list[int|float]] = []
        past_results_row:list[int|float] = []
        for line in lines:
            if("Recent Presidential Elections" in line):
                recent_presidential_elections_found = True
                continue
            if((line.startswith("Show:")) and (lines[lines.index(line)+1].strip()=='7')):
                break
            if(not(recent_presidential_elections_found)):
                continue
            if(re.match(r"^[0-9]{4}$",line.strip())):
                if(len(past_results_row)>0):
                    past_results.append(past_results_row.copy())
                    past_results_row:list[int|float] = []
                past_results_row.append(int(line.strip()))
            elif(re.match(r"^[0-9\.]{2,}\%$",line.strip())):
                past_results_row.append(round(float(pct_to_float(line.strip(),logger=logger)),4))
        return past_results
    except Exception as e:
        logger.log_to_xml(message=f"Failed to get past election results. Terminating program. Official error: {traceback.format_exc()}",basepath=logger.base_dir,status="CRITICAL")
        return None

def baseline_republican_popularity(past_results:list[list[int|float]],logger:XML_Logger) -> float|None:
    try:
        total_popularity:float = 0
        for row in past_results:
            total_popularity += row[2]
        return round(total_popularity/len(past_results),10)
    except Exception as e:
            logger.log_to_xml(message=f"Failed to get past baseline popularity for republicans. Official error: {traceback.format_exc()}",basepath=logger.base_dir,status="ERROR")
            return None

def baseline_democratic_popularity(past_results:list[list[int|float]],logger:XML_Logger) -> float|None:
    try:
        total_popularity:float = 0
        for row in past_results:
            total_popularity += row[1]
        return round(total_popularity/len(past_results),10)
    except Exception as e:
        logger.log_to_xml(message=f"Failed to get past baseline popularity for democrats. Official error: {traceback.format_exc()}",basepath=logger.base_dir,status="ERROR")
        return None

def baseline_independent_popularity(past_results:list[list[int|float]],logger:XML_Logger) -> float|None:
    try:
        total_popularity:float = 0
        for row in past_results:
            total_popularity += (row[1]+row[2])
        return round(1-(total_popularity/len(past_results)),10)
    except Exception as e:
        logger.log_to_xml(message=f"Failed to get past baseline popularity for independents. Official error: {traceback.format_exc()}",basepath=logger.base_dir,status="ERROR")
        return None

def save_popularity_to_csv(data:dict[str,list[float]],logger:XML_Logger) -> None:
    try:
        # Define the CSV file name
        csv_file = "data/Baseline_Popularity.csv"

        # Write to CSV
        with open(csv_file, mode='w', newline='') as file:
            writer = csv.writer(file)
            
            # Write header
            writer.writerow(["State", "Republican", "Democrat", "Independent"])
            
            # Write each state's data
            for state, percentages in data.items():
                writer.writerow([state.title().capitalize().replace("-"," ")] + percentages)
    except Exception as e:
        logger.log_to_xml(message=f"Failed to save popularity to CSV. Official error: {traceback.format_exc()}",basepath=logger.base_dir,status="ERROR")
        return None

def main():
    try:
        logger:XML_Logger = XML_Logger("party_popularity_history_logger","archive",log_retention_days=7,base_dir=CURRENT_DIRECTORY)
        logger.log_to_xml(message=f"Begin getting baseline popularity for each major political party.",basepath=logger.base_dir,status="INFO")
        states:list[str] = [
                "alabama", "alaska", "arizona", "arkansas", "california",
                "colorado", "connecticut", "delaware", "district-of-columbia", "florida", "georgia",
                "hawaii", "idaho", "illinois", "indiana", "iowa",
                "kansas", "kentucky", "louisiana", "maine", "maryland",
                "massachusetts", "michigan", "minnesota", "mississippi", "missouri",
                "montana", "nebraska", "nevada", "new-hampshire", "new-jersey",
                "new-mexico", "new-york", "north-carolina", "north-dakota", "ohio",
                "oklahoma", "oregon", "pennsylvania", "rhode-island", "south-carolina",
                "south-dakota", "tennessee", "texas", "utah", "vermont",
                "virginia", "washington", "west-virginia", "wisconsin", "wyoming"
            ]
        baseline_popularity:dict[str,list[float]] = {}
        for state in states:
            past_results:list[list[int|float]] = past_election_results(state=state,logger=logger)
            if past_results is None:
                continue
            baseline_popularity[state] = [baseline_republican_popularity(past_results,logger),baseline_democratic_popularity(past_results,logger),baseline_independent_popularity(past_results,logger)]
        save_popularity_to_csv(data=baseline_popularity,logger=logger)
        logger.save_variable_info(locals_dict=locals(),variable_save_path=os.path.join(CURRENT_DIRECTORY,'party_popularity_history_variables.json'))
        logger.log_to_xml(message=f"Successfully got baseline popularity for each major political party and saved to CSV.",basepath=logger.base_dir,status="SUCCESS")
    except Exception as e:
        if('logger' in locals()):
            logger.log_to_xml(message=f"Error getting baseline popularity for each political party. Terminating program. Official error: {traceback.format_exc()}",basepath=logger.base_dir,status="CRITICAL")
        else:
            print(f"Error getting baseline popularity for each political party. Terminating program. Official error: {traceback.format_exc()}")
        return None
    
if __name__ == "__main__":
    main()