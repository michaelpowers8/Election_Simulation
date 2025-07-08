import os
import re
import traceback
from time import time
from numpy import array,ndarray,arange
from xml_logging import XML_Logger
from pandas import DataFrame,read_csv,concat
from sklearn.linear_model import LinearRegression
CURRENT_DIRECTORY:str = os.getcwd()

def get_csv(file_name:str,logger:XML_Logger) -> DataFrame|None:
    try:
        df:DataFrame|None = None
        lines_to_skip:int = 0
        with open(file_name,'r') as file:
            lines:list[str] = file.readlines()
            for line in lines:
                if("Timeframe:" in line):
                    year:int = int(re.search(r"\d+",line).group())
                    num_lines:int = len(lines)
        while((df is None)and(lines_to_skip < num_lines)):
            try:
                df:DataFrame|None = read_csv(file_name,skiprows=lines_to_skip)
                if("Location" in df.columns):
                    df["Year"] = year
                    return df
                else:
                    raise Exception
            except Exception as e:
                df:DataFrame|None = None
                lines_to_skip += 1
        return None
    except Exception as e:
        logger.log_to_xml(message=f"Failed to get data from {file_name}. Official error: {traceback.format_exc()}",basepath=logger.base_dir,status="ERROR")
        return None

def get_all_csvs(data_folder:str,logger:XML_Logger) -> ndarray|None:
    try:
        dfs:list[DataFrame] = []
        for file in os.scandir(data_folder):
            if file.is_file() and file.name.endswith('.csv') and not('Combine' in file.name):
                df:DataFrame|None = get_csv(file_name=os.path.join(data_folder,file.name),logger=logger)
                if df is not None:
                    dfs.append(df.iloc[1:-6])
        return concat(dfs).to_numpy()
    except Exception as e:
        logger.log_to_xml(message=f"Error getting all CSV data in {data_folder}. Terminating program. Official error: {traceback.format_exc()}",basepath=logger.base_dir,status="CRITICAL")
        return None

def convert_data_to_dict(data:ndarray,logger:XML_Logger) -> dict[str,dict[str,list[int|float]]]|None:
    try:
        states:dict[str,dict[str,list[int|float]]] = {}
        for row in data:
            current_state:str = row[0]
            if current_state not in states:
                states[current_state] = {'year': [], 'num_registered_voters': [], 'pct_registered_voters': [], 'num_votes_cast': [], 'pct_votes_cast': []}
            states[current_state]['year'].append(row[-1])
            states[current_state]['num_registered_voters'].append(float(row[1].replace(',','')) if isinstance(row[1], str) else row[1])
            states[current_state]['num_votes_cast'].append(float(row[3].replace(',','')) if isinstance(row[3], str) else row[3])
            states[current_state]['pct_registered_voters'].append(row[2])
            states[current_state]['pct_votes_cast'].append(row[4])
        return states
    except Exception as e:
        logger.log_to_xml(message=f"Failed to convert data to dictionary. Official error: {traceback.format_exc()}",basepath=logger.base_dir,status="ERROR")
        return None

def predict_future(states:dict[str,dict[str,list[int|float]]], future_years:list[int]|ndarray, logger:XML_Logger) -> dict[str,dict[str,list[int|float]]]:
    try:
        for state in states:
            years = array(states[state]['year']).reshape(-1, 1)
            for key in ['num_registered_voters', 'num_votes_cast', 'pct_registered_voters', 'pct_votes_cast']:
                values = array(states[state][key])
                model = LinearRegression()
                model.fit(years, values)
                predictions = model.predict(array(future_years).reshape(-1, 1))
                states[state][key].extend(predictions)
                states[state]['year'].extend(future_years)
        return states
    except Exception as e:
        logger.log_to_xml(message=f"Failed to make future data. Official error: {traceback.format_exc()}",basepath=logger.base_dir,status="ERROR")
        return states

def convert_dict_to_data(states:dict[str,dict[str,list[int|float]]], logger:XML_Logger) -> ndarray|None:
    try:
        # Define the dtype for our structured array
        dtype = [
                ('state', 'U50'),      # String (Unicode) for state names
                ('num_registered_voters', 'i8'),      # 64-bit integer
                ('pct_registered_voters', 'f8'),      # 64-bit float
                ('num_votes_cast', 'i8'),             # 64-bit integer
                ('pct_votes_cast', 'f8'),             # 64-bit float
                ('year', 'i4')                       # 32-bit integer
            ]
        
        # Create a list of tuples with the correct data types
        data_tuples = []
        for state in states:
            for i, year in enumerate(states[state]['year']):
                if i >= len(states[state]['num_registered_voters']):
                    break
                data_tuples.append((
                        state,
                        int(round(states[state]['num_registered_voters'][i]))*1000,
                        float(round(states[state]['pct_registered_voters'][i], 3)),
                        int(round(states[state]['num_votes_cast'][i]))*1000,
                        float(round(states[state]['pct_votes_cast'][i], 3)),
                        int(year)
                    ))
        
        # Sort the data by state and year
        data_tuples_sorted = sorted(data_tuples, key=lambda x: (x[0], x[-1]))
        
        # Create and return the structured array
        return array(data_tuples_sorted, dtype=dtype)
    except Exception as e:
        logger.log_to_xml(message=f"Failed to convert dictionary back to list. Official error: {traceback.format_exc()}",basepath=logger.base_dir,status="ERROR")
        return None

def main():
    logger:XML_Logger = XML_Logger("voter_registration_kff_merge","archive",log_retention_days=7,base_dir=CURRENT_DIRECTORY)
    future_years:ndarray = arange(2025,2033)
    data:ndarray|None = get_all_csvs(data_folder=os.path.join(CURRENT_DIRECTORY,'data'),logger=logger)
    if data is None:
        return
    data:dict[str,dict[str,list[int|float]]]|None = convert_data_to_dict(data=data,logger=logger)
    if data is None:
        return
    data:dict[str,dict[str,list[int|float]]]|None = predict_future(states=data,future_years=future_years,logger=logger)
    if data is None:
        return
    data:ndarray|None = convert_dict_to_data(states=data,logger=logger)
    if data is None:
        return
    df:DataFrame = DataFrame(data)
    df.columns = ['State','Number of Registered Voters','Percent of Voters to Total Population', 'Number of Votes Cast', 'Percent of Votes Cast to Total Population', 'Year']
    df.to_csv("data/Combined_Data.csv",index=False)
    logger.save_variable_info(locals_dict=locals(),variable_save_path=os.path.join(CURRENT_DIRECTORY,'voter_registration_kff_merge_variables.json'))
if __name__ == "__main__":
    main()
    