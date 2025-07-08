import os
import re
import random
import traceback
import numpy as np
from datetime import datetime
from xml_logging import XML_Logger
from pandas import read_csv,DataFrame
from electoral_votes import electoral_votes
CURRENT_DIRECTORY:str = os.getcwd()

class State_Election_Simulation:
    def __init__(self,voter_data:np.ndarray,baseline_popularity_data:np.ndarray,popularity_changes:list[float],turnout:float,round:int):
        self.round:int = round
        self.votes_to_cast:int = self._get_number_of_votes_to_cast(voter_data,turnout)
        self.total_votes:int = 0
        self.dem_popularity:float = baseline_popularity_data[2]+popularity_changes[1]
        self.dem_votes:int = 0
        self.dem_votes_pct:float = 0
        self.rep_popularity:float = baseline_popularity_data[1]+popularity_changes[0]
        self.rep_votes:int = 0
        self.rep_votes_pct:float = 0
        self.ind_popularity:float = baseline_popularity_data[3]+popularity_changes[2]
        self.ind_votes:int = 0
        self.ind_votes_pct:float = 0
        self.state:str = voter_data[0]
        self.total_num_voters:int = voter_data[1]
        self.year = voter_data[-1]
        self._adjusted_party_popularity()

    def _adjusted_party_popularity(self) -> None:
        if(
            (self.rep_popularity >= 0)and
            (self.dem_popularity >= 0)and
            (self.ind_popularity >= 0)  
          ):
            return None
        
        elif(
            (self.rep_popularity >= 0)and
            (self.dem_popularity >= 0)and
            (self.ind_popularity < 0)  
          ):
            rep_increase:float = ((self.ind_popularity*-1)*self.rep_popularity)
            self.rep_popularity -= rep_increase
            self.ind_popularity += rep_increase
            self.dem_popularity -= (self.ind_popularity*-1)
            self.ind_popularity = 0

        elif(
            (self.rep_popularity >= 0)and
            (self.dem_popularity < 0)and
            (self.ind_popularity >= 0)  
          ):
            rep_increase:float = ((self.dem_popularity*-1)*self.rep_popularity)
            self.rep_popularity -= rep_increase
            self.dem_popularity += rep_increase
            self.ind_popularity -= (self.dem_popularity*-1)
            self.dem_popularity = 0

        elif(
            (self.rep_popularity < 0)and
            (self.dem_popularity >= 0)and
            (self.ind_popularity >= 0)  
          ):
            dem_increase:float = (self.rep_popularity*-1)*self.dem_popularity
            self.dem_popularity -= dem_increase
            self.rep_popularity += dem_increase
            self.ind_popularity -= (self.rep_popularity*-1)
            self.rep_popularity = 0
        
        elif(
            (self.rep_popularity >= 0)and
            (self.dem_popularity < 0)and
            (self.ind_popularity < 0)  
          ):
            self.rep_popularity = 1
            self.ind_popularity = 0
            self.dem_popularity = 0

        elif(
            (self.rep_popularity < 0)and
            (self.dem_popularity >= 0)and
            (self.ind_popularity < 0)  
          ):
            self.rep_popularity = 0
            self.ind_popularity = 0
            self.dem_popularity = 1
        
        elif(
            (self.rep_popularity < 0)and
            (self.dem_popularity < 0)and
            (self.ind_popularity >= 0)  
          ):
            self.rep_popularity = 0
            self.ind_popularity = 1
            self.dem_popularity = 0

    def _get_number_of_votes_to_cast(self,voter_data:np.ndarray,turnout:float):
        total_votes:int = 0
        for _ in range(voter_data[1]):
            is_vote:float = random.random()
            if is_vote < turnout:
                total_votes += 1
        return total_votes

    def _get_winner(self):
        if(self.rep_votes > self.dem_votes and self.rep_votes > self.ind_votes):
            return "Republican"
        if(self.dem_votes > self.rep_votes and self.dem_votes > self.ind_votes):
            return "Democrat"
        if(self.ind_votes > self.dem_votes and self.ind_votes > self.rep_votes):
            return "Independent"

    def cast_vote(self):
        is_voting:float = random.random()
        vote:float = random.random()
        if is_voting > 0.98:
            return -1 # No vote cast 2% of the time
        self.total_votes += 1
        if vote < self.rep_popularity:
            self.rep_votes += 1
            return 0 # Republican vote
        if vote >= self.rep_popularity+self.dem_popularity:
            self.ind_votes += 1
            return 2 # Independent vote
        self.dem_votes += 1
        return 1 # Democrat vote
        
    def simulate_election(self):
        for vote in range(self.votes_to_cast):
            self.cast_vote()
        self.rep_votes_pct = self.rep_votes/self.total_votes
        self.dem_votes_pct = self.dem_votes/self.total_votes
        self.ind_votes_pct = self.ind_votes/self.total_votes

    def save_to_csv(self):
        data:dict[str,int|float] = {
                "Round": [self.round],
                "State": [self.state],
                "Electoral Votes": [electoral_votes[self.state]],
                "Winner": [self._get_winner()],
                "Total Votes": [self.total_votes],
                "Republican Votes": [self.rep_votes],
                "Republican Vote Percent": [self.rep_votes_pct],
                "Democrat Votes": [self.dem_votes],
                "Democrat Vote Percent": [self.dem_votes_pct],
                "Independent Votes": [self.ind_votes],
                "Independent Vote Percent": [self.ind_votes_pct]
            }
        DataFrame(data).to_csv(
                                "State_Results.csv", 
                                mode="w" if self.round==1 and self.state=="Alabama" else "a", 
                                encoding='utf-8', 
                                index=False, 
                                header=True if self.round==1 and self.state=="Alabama" else False,
                                float_format='{:,.4f}'.format
                               )

class Federal_Election_Simulation:
    def __init__(self,state_data:list[State_Election_Simulation],round:int,turnout:float):
        self.turnout:float = turnout
        self.round:int = round
        self.total_votes:int = 0
        self.rep_votes:int = 0
        self.rep_electoral_votes:int = 0
        self.rep_votes_pct:float = 0
        self.dem_votes:int = 0
        self.dem_electoral_votes:int = 0
        self.dem_votes_pct:float= 0
        self.ind_votes:int = 0
        self.ind_electoral_votes:int = 0
        self.ind_votes_pct:float = 0
        self._get_total_votes(state_data)
        self._get_electoral_votes(state_data)

    def _get_total_votes(self,state_data:list[State_Election_Simulation]):
        for state in state_data:
            self.total_votes += state.total_votes
            self.rep_votes += state.rep_votes
            self.dem_votes += state.dem_votes
            self.ind_votes += state.ind_votes
        self.rep_votes_pct = self.rep_votes/self.total_votes
        self.dem_votes_pct = self.dem_votes/self.total_votes
        self.ind_votes_pct = self.ind_votes/self.total_votes
    
    def _get_electoral_votes(self,state_data:list[State_Election_Simulation]):
        for state in state_data:
            state_votes:list[int] = [state.rep_votes,state.dem_votes,state.ind_votes]
            num_electoral_votes:int = electoral_votes[state.state]
            if max(state_votes)==state_votes[0]:
                self.rep_electoral_votes += num_electoral_votes
            elif max(state_votes)==state_votes[1]:
                self.dem_electoral_votes += num_electoral_votes
            else:
                self.ind_electoral_votes += num_electoral_votes

    def save_to_csv(self):
        data:dict[str,int|float] = {
                "Round": [self.round],
                "Turnout Percent": [self.turnout],
                "Total Votes": [self.total_votes],
                "Republican Votes": [self.rep_votes],
                "Republican Electoral Votes": [self.rep_electoral_votes],
                "Republican Vote Percent": [self.rep_votes_pct],
                "Democrat Votes": [self.dem_votes],
                "Democrat Electoral Votes": [self.dem_electoral_votes],
                "Democrat Vote Percent": [self.dem_votes_pct],
                "Independent Votes": [self.ind_votes],
                "Independent Electoral Votes": [self.ind_electoral_votes],
                "Independent Vote Percent": [self.ind_votes_pct]
            }
        DataFrame(data).to_csv(
                                "National_Results.csv", 
                                mode="w" if self.round==1 else "a", 
                                encoding='utf-8', 
                                index=False, 
                                header=True if self.round==1 else False,
                                float_format='{:,.4f}'.format
                               )

def get_voter_data(file_name:str,logger:XML_Logger,year:int) -> np.ndarray|None:
    try:
        df:DataFrame = read_csv(file_name)
        df:DataFrame = df[df["Year"]==year]
        return df.to_numpy()
    except Exception as e:
        logger.log_to_xml(message=f"Failed to get data from {file_name}. Terminating program. Official error: {traceback.format_exc()}",basepath=logger.base_dir,status="CRITICAL")
        return None
    
def get_party_popularity_data(file_name:str,logger:XML_Logger) -> np.ndarray|None:
    try:
        df:DataFrame = read_csv(file_name)
        return df.to_numpy()
    except Exception as e:
        logger.log_to_xml(message=f"Failed to get data from {file_name}. Terminating program. Official error: {traceback.format_exc()}",basepath=logger.base_dir,status="CRITICAL")
        return None

def get_popularity_changes() -> list[float]:
    net_rep_change:float = 0
    net_dem_change:float = 0
    net_ind_change:float = 0

    rep_to_ind:float = random.uniform(0,0.1)
    rep_to_dem:float = random.uniform(0,0.05)
    net_rep_change -= (rep_to_dem+rep_to_ind)
    net_dem_change += rep_to_dem
    net_ind_change += rep_to_ind

    dem_to_ind:float = random.uniform(0,0.1)
    dem_to_rep:float = random.uniform(0,0.05)
    net_dem_change -= (dem_to_ind+dem_to_rep)
    net_rep_change += dem_to_rep
    net_ind_change += dem_to_ind

    ind_to_dem:float = random.uniform(0,0.1)
    ind_to_rep:float = random.uniform(0,0.1)
    net_ind_change -= (ind_to_dem+ind_to_rep)
    net_rep_change += ind_to_rep
    net_dem_change += ind_to_dem

    return [net_rep_change,net_dem_change,net_ind_change]

def main():
    logger:XML_Logger = XML_Logger("simulator_logger","archive",log_retention_days=7,base_dir=CURRENT_DIRECTORY)
    voter_data:np.ndarray = get_voter_data(file_name="data/Combined_Data.csv",logger=logger,year=2028)
    party_popularity_data:np.ndarray = get_party_popularity_data(file_name="data/Baseline_Popularity.csv",logger=logger)

    for round in range(1,1_000_001):
        logger.log_to_xml(message=f"Beginning election round {round}",basepath=logger.base_dir,status="INFO")
        print(f"Beginning election round {round} at {datetime.now()}")
        state_elections:list[State_Election_Simulation] = []
        popularity_changes:list[float] = get_popularity_changes()
        turnout:float = random.uniform(0.6,0.9)
        for state_voter_data,state_party_popularity_data in zip(voter_data,party_popularity_data):
            state_simulation:State_Election_Simulation = State_Election_Simulation(state_voter_data,state_party_popularity_data,popularity_changes,turnout,round)
            state_simulation.simulate_election()
            state_simulation.save_to_csv()
            state_elections.append(state_simulation)
        federal_election:Federal_Election_Simulation = Federal_Election_Simulation(state_elections,round=round,turnout=turnout)
        federal_election.save_to_csv()
        del state_elections

    logger.save_variable_info(locals_dict=locals(),variable_save_path=os.path.join(CURRENT_DIRECTORY,'simulator_variables.json'))

if __name__ == "__main__":
    main()