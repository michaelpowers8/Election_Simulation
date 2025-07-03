import os
import json
import random
import traceback
from typing import Any
from numpy import ndarray
from xml_logging import XML_Logger
from electoral_votes import electoral_votes
from pandas import read_csv,DataFrame,concat
from configuration import load_configuration

def convert_str_to_int(value:str) -> int|str:
    try:
        return int(value.replace(',',"").strip())
    except Exception as e:
        return value

def convert_str_percent_to_float(value:str) -> float|str:
    try:
        return round(float(value.replace(',',"").replace("%","").strip())/100,5)
    except Exception as e:
        return value

def get_voter_rolls_data(configuration:dict[str,str|int],logger:XML_Logger) -> ndarray|None:
    try:
        df:DataFrame = read_csv(configuration["Voter_Rolls_Data_File_Path"])
        for column in df.columns:
            if " (in thousands)" in column:
                df[column.replace(' (in thousands)',"")] = df[column].apply(convert_str_to_int)
                df = df.drop(columns=[column],axis=1)
                df[column.replace(' (in thousands)',"")] = df[column.replace(' (in thousands)',"")]*1000
            else:
                try:
                    df[column] = df[column].astype(float)
                except:
                    pass
        return df[["Location","Number of Registered Voters","Registered Voters as a Share of the Voter Population","Number of Individuals who Voted","Individuals who Voted as a Share of the Voter Population"]].iloc[1:].to_numpy() # Return only state data. Not the total United States numbers. Will cause redundancy.
    except Exception as e:
        logger.log_to_xml(message=f'Failed to get raw data from {configuration["Voter_Rolls_Data_File_Path"]}. Terminating program. Official error thrown: {traceback.format_exc()}',status="CRITICAL",basepath=logger.base_dir)
        return None

def get_state_names(configuration:dict[str,str|int],logger:XML_Logger) -> list[str]|None:
    try:
        df:DataFrame = read_csv(configuration["Voter_Rolls_Data_File_Path"])
        return list(df['Location'].values)[1:]
    except Exception as e:
        logger.log_to_xml(message=f'Failed to get states names. Terminating program. Official error thrown: {traceback.format_exc()}',status="CRITICAL",basepath=logger.base_dir)
        return None

def get_election_results_data(configuration:dict[str,str|int],logger:XML_Logger) -> ndarray|None:
    try:
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
        return df.iloc[1:].to_numpy() # Return only state data. Not the total United States numbers. Will cause redundancy.
    except Exception as e:
        logger.log_to_xml(message=f'Failed to get raw data from {configuration["Past_Election_Results_Data_File_Path"]}. Terminating program. Official error thrown: {traceback.format_exc()}',status="CRITICAL",basepath=logger.base_dir)
        return None

def get_future_population_data(configuration:dict[str,str|int],logger:XML_Logger) -> ndarray|None:
    try:
        df:DataFrame = read_csv(configuration["Expected_Population_Data"])
        for column in df.columns:
            try:
                df[column] = df[column].fillna(0)
                df[column] = df[column].astype(int)
            except:
                pass
        return df.iloc[1:].to_numpy() # Return only state data. Not the total United States numbers. Will cause redundancy.
    except Exception as e:
        logger.log_to_xml(message=f'Failed to get future population data from {configuration["Expected_Population_Data"]}. Terminating program. Official error thrown: {traceback.format_exc()}',status="CRITICAL",basepath=logger.base_dir)
        return None
    
def get_future_population_data_columns(configuration:dict[str,str|int],logger:XML_Logger) -> list[str]|None:
    try:
        df:DataFrame = read_csv(configuration["Expected_Population_Data"])
        return list(df.columns) # Return only state data. Not the total United States numbers. Will cause redundancy.
    except Exception as e:
        logger.log_to_xml(message=f'Failed to get future population data columns from {configuration["Expected_Population_Data"]}. Terminating program. Official error thrown: {traceback.format_exc()}',status="CRITICAL",basepath=logger.base_dir)
        return None

def _verify_state_paramters(state:str,state_voter_rolls_data:ndarray,state_past_election_results:ndarray) -> bool:
    if(not(isinstance(state,str))):
        return False
    if(not(isinstance(state_voter_rolls_data,ndarray))):
        return False
    if(not(isinstance(state_past_election_results,ndarray))):
        return False
    if(
        (not(state == state_voter_rolls_data[0]))and # If the state name provided is not the same as the state found in the voter roll data
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

def _process_individual_vote(republican_vote_probability:float,democratic_vote_probability:float,independent_vote_probability:float) -> int:
    total:float = republican_vote_probability + democratic_vote_probability + independent_vote_probability
    vote_cast:float = random.uniform(0,total)
    if(random.random() > 0.98):
        return -1 # No vote cast

    if(vote_cast < republican_vote_probability):
        return 0 # Republican vote
    
    if(vote_cast >= republican_vote_probability+democratic_vote_probability):
        return 2 # Independent vote
    
    return 1 # Democratic vote

def process_state(state:str,state_voter_rolls_data:ndarray,state_past_election_results:ndarray,future_population_data:ndarray,year:int,columns:list[str],logger:XML_Logger,iteration_number=1):
    """"""
    logger.log_to_xml(f'Begin processing round {iteration_number} for {state} for election year {year}.',status="INFO",basepath=logger.base_dir)
    if(not(_verify_state_paramters(state=state,state_voter_rolls_data=state_voter_rolls_data,state_past_election_results=state_past_election_results))):
        logger.log_to_xml(message=f'Invalid parameters passed. Parameters passed: {state}, {state_voter_rolls_data}, {state_past_election_results}. State cannot be processed.',status="ERROR",basepath=logger.base_dir)
        return None
    if year % 4 == 0:
        voter_turnout_percent = random.uniform(0.85,0.95)
    else:
        voter_turnout_percent = random.uniform(0.6,0.8)
    year_column_index:int = columns.index(str(year))
    num_citizens:int = future_population_data[year_column_index]
    registered_voters:int = round((state_voter_rolls_data[2]*random.uniform(0.98,1.02))*num_citizens)
    votes_to_cast:int = round(registered_voters*voter_turnout_percent)

    past_republican_vote_percent:float = state_past_election_results[6]
    actual_republican_votes:int = 0

    past_democratic_vote_percent:float = state_past_election_results[3]
    actual_democratic_votes:int = 0

    past_independent_vote_percent:float = state_past_election_results[9]
    actual_independent_votes:int = 0

    for _ in range(votes_to_cast):
        republican_vote_probability:float = random.uniform(max(past_republican_vote_percent - random.uniform(0.01,0.1),0),past_republican_vote_percent + random.uniform(0.01,0.1))
        democratic_vote_probability:float = random.uniform(max(past_democratic_vote_percent - random.uniform(0.01,0.1),0),past_democratic_vote_percent + random.uniform(0.01,0.1))
        independent_vote_probability:float = random.uniform(max(past_independent_vote_percent - random.uniform(0.001,0.025),0),past_independent_vote_percent + random.uniform(0.001,0.025))
        vote_cast:int = _process_individual_vote(republican_vote_probability,democratic_vote_probability,independent_vote_probability)
        if vote_cast == -1:
            continue
        if vote_cast == 0:
            actual_republican_votes += 1
        elif vote_cast == 1:
            actual_democratic_votes += 1
        else:
            actual_independent_votes += 1
    total_votes:int = actual_republican_votes+actual_democratic_votes+actual_independent_votes
    return {
            "State":state,
            "Electoral Votes":electoral_votes[state],
            "Total Votes":f'{total_votes:,.0f}',
            "Republicans Votes":f'{actual_republican_votes:,.0f}',
            "Republicans Percent":f'{(actual_republican_votes/total_votes)*100:,.4f}',
            "Republican Electoral Votes": electoral_votes[state] if actual_republican_votes == max([actual_republican_votes,actual_democratic_votes,actual_independent_votes]) else 0,
            "Democrats Votes":f'{actual_democratic_votes:,.0f}',
            "Democrats Percent":f'{(actual_democratic_votes/total_votes)*100:,.4f}',
            "Democrats Electoral Votes": electoral_votes[state] if actual_democratic_votes == max([actual_republican_votes,actual_democratic_votes,actual_independent_votes]) else 0,
            "Independents Votes":f'{actual_independent_votes:,.0f}',
            "Independents Percent":f'{(actual_independent_votes/total_votes)*100:,.4f}',
            "Independents Electoral Votes": electoral_votes[state] if actual_independent_votes == max([actual_republican_votes,actual_democratic_votes,actual_independent_votes]) else 0,
        }

def process_maine(cd_1:dict[str,Any],cd_2:dict[str,Any]):
    for key,item in cd_1.items():
        try:
            cd_1[key] = convert_str_to_int(item)
        except:
            pass
    for key,item in cd_2.items():
        try:
            cd_2[key] = convert_str_to_int(item)
        except:
            pass
    return {
            "State":"Maine",
            "Electoral Votes": 2,
            "Total Votes":f'{cd_1["Total Votes"]+cd_2["Total Votes"]:,.0f}',
            "Republicans Votes":f'{cd_1["Republicans Votes"]+cd_2["Republicans Votes"]:,.0f}',
            "Republicans Percent":f'{((cd_1["Republicans Votes"]+cd_2["Republicans Votes"])/(cd_1["Total Votes"]+cd_2["Total Votes"]))*100:,.4f}',
            "Republican Electoral Votes": 2 if cd_1["Republicans Votes"]+cd_2["Republicans Votes"] == max([cd_1["Republicans Votes"]+cd_2["Republicans Votes"],cd_1["Democrats Votes"]+cd_2["Democrats Votes"],cd_1["Independents Votes"]+cd_2["Independents Votes"]]) else 0,
            "Democrats Votes":f'{cd_1["Democrats Votes"]+cd_2["Democrats Votes"]:,.0f}',
            "Democrats Percent":f'{((cd_1["Democrats Votes"]+cd_2["Democrats Votes"])/(cd_1["Total Votes"]+cd_2["Total Votes"]))*100:,.4f}',
            "Democrats Electoral Votes": 2 if cd_1["Democrats Votes"]+cd_2["Democrats Votes"] == max([cd_1["Republicans Votes"]+cd_2["Republicans Votes"],cd_1["Democrats Votes"]+cd_2["Democrats Votes"],cd_1["Independents Votes"]+cd_2["Independents Votes"]]) else 0,
            "Independents Votes":f'{cd_1["Independents Votes"]+cd_2["Independents Votes"]:,.0f}',
            "Independents Percent":f'{((cd_1["Independents Votes"]+cd_2["Independents Votes"])/(cd_1["Total Votes"]+cd_2["Total Votes"]))*100:,.4f}',
            "Independents Electoral Votes": 2 if cd_1["Independents Votes"]+cd_2["Independents Votes"] == max([cd_1["Republicans Votes"]+cd_2["Republicans Votes"],cd_1["Democrats Votes"]+cd_2["Democrats Votes"],cd_1["Independents Votes"]+cd_2["Independents Votes"]]) else 0,
        }

def process_nebraska(cd_1:dict[str,Any],cd_2:dict[str,Any],cd_3:dict[str,Any]):
    for key,item in cd_1.items():
        try:
            cd_1[key] = convert_str_to_int(item)
        except:
            pass
    for key,item in cd_2.items():
        try:
            cd_2[key] = convert_str_to_int(item)
        except:
            pass
    for key,item in cd_3.items():
        try:
            cd_3[key] = convert_str_to_int(item)
        except:
            pass
    return {
            "State":"Nebraska",
            "Electoral Votes": 2,
            "Total Votes":f'{cd_1["Total Votes"]+cd_2["Total Votes"]+cd_3["Total Votes"]:,.0f}',
            "Republicans Votes":f'{cd_1["Republicans Votes"]+cd_2["Republicans Votes"]+cd_3["Republicans Votes"]:,.0f}',
            "Republicans Percent":f'{((cd_1["Republicans Votes"]+cd_2["Republicans Votes"]+cd_3["Republicans Votes"])/(cd_1["Total Votes"]+cd_2["Total Votes"]+cd_3["Total Votes"]))*100:,.4f}',
            "Republican Electoral Votes": 2 if cd_1["Republicans Votes"]+cd_2["Republicans Votes"]+cd_3["Republicans Votes"] == max([cd_1["Republicans Votes"]+cd_2["Republicans Votes"]+cd_3["Republicans Votes"],cd_1["Democrats Votes"]+cd_2["Democrats Votes"]+cd_3["Democrats Votes"],cd_1["Independents Votes"]+cd_2["Independents Votes"]+cd_3["Independents Votes"]]) else 0,
            "Democrats Votes":f'{cd_1["Democrats Votes"]+cd_2["Democrats Votes"]+cd_3["Democrats Votes"]:,.0f}',
            "Democrats Percent":f'{((cd_1["Democrats Votes"]+cd_2["Democrats Votes"]+cd_3["Democrats Votes"])/(cd_1["Total Votes"]+cd_2["Total Votes"]+cd_3["Total Votes"]))*100:,.4f}',
            "Democrats Electoral Votes": 2 if cd_1["Democrats Votes"]+cd_2["Democrats Votes"]+cd_3["Democrats Votes"] == max([cd_1["Republicans Votes"]+cd_2["Republicans Votes"]+cd_3["Republicans Votes"],cd_1["Democrats Votes"]+cd_2["Democrats Votes"]+cd_3["Democrats Votes"],cd_1["Independents Votes"]+cd_2["Independents Votes"]+cd_3["Independents Votes"]]) else 0,
            "Independents Votes":f'{cd_1["Independents Votes"]+cd_2["Independents Votes"]+cd_3["Independents Votes"]:,.0f}',
            "Independents Percent":f'{((cd_1["Independents Votes"]+cd_2["Independents Votes"]+cd_3["Independents Votes"])/(cd_1["Total Votes"]+cd_2["Total Votes"]+cd_3["Total Votes"]))*100:,.4f}',
            "Independents Electoral Votes": 2 if cd_1["Independents Votes"]+cd_2["Independents Votes"]+cd_3["Independents Votes"] == max([cd_1["Republicans Votes"]+cd_2["Republicans Votes"]+cd_3["Republicans Votes"],cd_1["Democrats Votes"]+cd_2["Democrats Votes"]+cd_3["Democrats Votes"],cd_1["Independents Votes"]+cd_2["Independents Votes"]+cd_3["Independents Votes"]]) else 0,
        }

def update_total_vote_counts(total_votes:int,total_rep_votes:int,total_dem_votes:int,total_ind_votes:int,state_data:dict[str,Any]):
    total_votes += convert_str_to_int(state_data["Total Votes"])
    total_rep_votes += convert_str_to_int(state_data["Republicans Votes"])
    total_dem_votes += convert_str_to_int(state_data["Democrats Votes"])
    total_ind_votes += convert_str_to_int(state_data["Independents Votes"])
    return total_votes,total_rep_votes,total_dem_votes,total_ind_votes

def main():
    configuration:dict[str,str|int] = load_configuration()
    if configuration is None:
        return None
    logger:XML_Logger = XML_Logger(log_file="Election_Simulation_Logger",log_retention_days=7,base_dir=configuration["Absolute_Working_Directory"])
    state_names:list[str] = get_state_names(configuration=configuration,logger=logger)
    voter_rolls_data:ndarray|None = get_voter_rolls_data(configuration=configuration,logger=logger)
    past_election_results_data:ndarray|None = get_election_results_data(configuration=configuration,logger=logger)
    future_population_data:ndarray|None = get_future_population_data(configuration=configuration,logger=logger)
    future_population_data_columns:list[str]|None = get_future_population_data_columns(configuration=configuration,logger=logger)
    if any(item is None for item in [state_names,voter_rolls_data,past_election_results_data,future_population_data,future_population_data_columns]):
        return None
    
    all_national_data:list[DataFrame] = []
    all_state_data:list[DataFrame] = []
    simulation_data:list[dict[str,str]] = []
    for election_cycle in range(1,101):
        total_votes:int = 0
        total_rep_votes:int = 0
        total_dem_votes:int = 0
        total_ind_votes:int = 0
        for state,state_voter_roll_data,state_past_election_data,state_future_population_data in zip(state_names,voter_rolls_data,past_election_results_data,future_population_data):
            simulation_data.append(process_state(
                                                    state,
                                                    state_voter_roll_data,
                                                    state_past_election_data,
                                                    state_future_population_data,
                                                    configuration["Election_Year"],
                                                    future_population_data_columns,
                                                    logger,
                                                    election_cycle
                                                )
                                            )
            total_votes,total_rep_votes,total_dem_votes,total_ind_votes = update_total_vote_counts(total_votes,total_rep_votes,total_dem_votes,total_ind_votes,simulation_data[-1])
            if(state == "Maine-CD-2"):
                simulation_data.append(process_maine(simulation_data[-2].copy(),simulation_data[-1].copy()))
            elif(state == "Nebraska-CD-3"):
                simulation_data.append(process_nebraska(simulation_data[-3].copy(),simulation_data[-2].copy(),simulation_data[-1].copy()))
        state_data:DataFrame = DataFrame(simulation_data)
        all_state_data.append(state_data)
        national_data:DataFrame = DataFrame(
                                            {
                                                "Total Votes":f'{total_votes:,.0f}', 
                                                "Republican Electoral Votes":f'{state_data["Republican Electoral Votes"].sum():,.0f}', 
                                                "Republican Votes":f'{total_rep_votes:,.0f}', 
                                                "Republican Percent":f'{(total_rep_votes/total_votes)*100:,.4f}', 
                                                "Democrats Electoral Votes":f'{state_data["Democrats Electoral Votes"].sum():,.0f}', 
                                                "Democrats Votes":f'{total_dem_votes:,.0f}', 
                                                "Democrats Percent":f'{(total_dem_votes/total_votes)*100:,.4f}', 
                                                "Independents Electoral Votes":f'{state_data["Independents Electoral Votes"].sum():,.0f}',
                                                "Independents Votes":f'{total_ind_votes:,.0f}', 
                                                "Independents Percent":f'{(total_ind_votes/total_votes)*100:,.4f}'
                                            }
                                        )
        all_national_data.append(national_data)
        concat(all_state_data).to_csv("All_State_Raw_Results.csv")
        concat(all_national_data).to_csv("All_National_Results.csv")
    all_state_data_df:DataFrame = concat(all_state_data)
    all_state_data_df.groupby("State").median().to_csv("Median_State_Results.csv")
    all_state_data_df.groupby("State").mean().to_csv("Mean_State_Results.csv")

    logger.save_variable_info(locals_dict=locals(),variable_save_path="Election_Simulation_End_Variables.json")

if __name__ == "__main__":
    main()