import traceback
import numpy as np
from xml_logging import XML_Logger
from configuration import load_configuration
from sklearn.linear_model import LinearRegression
from pandas import read_csv,DataFrame,concat,Series

def get_census_data(configuration:dict[str,str|int],logger:XML_Logger) -> DataFrame|None:
    try:
        df:DataFrame = read_csv(configuration["Census_Data_File"])
        df_long:DataFrame = df.melt(id_vars='Geographic Area', var_name='Year', value_name='Population')
        df_long['Year'] = df_long['Year'].astype(int)
        return df_long
    except Exception as e:
        logger.log_to_xml(message=f"Error loading census data. Terminating program. Official error: {traceback.format_exc()}",status="ERROR",basepath=logger.base_dir)
        return None

def _make_population_prediction(area:str,group:DataFrame,future_years:np.ndarray,logger:XML_Logger,model=LinearRegression()) -> DataFrame|None:
    try:
        X:DataFrame = group[['Year']]
        y:Series = group['Population']
        
        model.fit(X, y)
        
        future_X:DataFrame = DataFrame({'Year': future_years})
        future_y:np.ndarray = model.predict(future_X)
        
        pred_df:DataFrame = DataFrame(
                {
                    'Geographic Area': area,
                    'Year': future_years,
                    'Predicted Population': future_y.astype(int)
                }
            )
        return pred_df
    except Exception as e:
        logger.log_to_xml(message=f"Failed to make population from {area} for {future_years}. Official error: {traceback.format_exc()}",status="ERROR",basepath=logger.base_dir)
        return None

def predict_populations(df:DataFrame,future_years:np.ndarray,logger:XML_Logger) -> list[DataFrame]|None:
    try:
        predictions:list[DataFrame] = []
        # Forecast for each geographic area
        for area, group in df.groupby('Geographic Area'):
            pred_df:DataFrame = _make_population_prediction(area=area,group=group,future_years=future_years,logger=logger)
            if pred_df is not None:
                predictions.append(pred_df)
        return predictions
    except Exception as e:
        logger.log_to_xml(message=f"Error predicting future populations. Official error: {traceback.format_exc()}",status="ERROR",basepath=logger.base_dir)
        return None
    
def merge_historical_and_future_data(predictions:list[DataFrame],historical_pivot:DataFrame,logger:XML_Logger) -> DataFrame|None:
    """
    Concatenates historical population data with future predictions into a unified DataFrame.

    Args:
        predictions (list of pandas.DataFrame): List of DataFrames with forecasted values.
        historical_pivot (pandas.DataFrame): Pivoted DataFrame of historical values.
        logger (XML_Logger): Logger for process reporting and diagnostics.

    Returns
    -------
        pandas.DataFrame or None: Combined DataFrame of historical and predicted values, or None if an error occurs.
    """
    try:
        future_df:DataFrame = concat(predictions, ignore_index=True)
        future_pivot:DataFrame = future_df.pivot(index='Geographic Area', columns='Year', values='Predicted Population')
        final_df:DataFrame = concat([historical_pivot, future_pivot], axis=1)
        final_df:DataFrame = final_df[sorted(final_df.columns)]
        final_df.reset_index(drop=True)
        return final_df
    except Exception as e:
        logger.log_to_xml(f"Error merging historical data with predicted future data. Terminating program. Official error: {traceback.format_exc()}",status="CRITICAL",basepath=logger.base_dir)
        return None

def main() -> None:
    configuration:dict[str,str|int]|None = load_configuration()
    if configuration is None:
        return None
    logger:XML_Logger = XML_Logger(log_file="predict_population",log_retention_days=7,base_dir=configuration["Absolute_Working_Directory"])
    logger.log_to_xml(message=f"Begin predicting future populations for all states",status="INFO",basepath=logger.base_dir)    
    df:DataFrame|None = get_census_data(configuration=configuration,logger=logger)
    if df is None:
        return None
    
    future_years:np.ndarray = np.arange(configuration["Future_Year_Start"],configuration["Future_Year_End"]+1)
    historical_pivot:DataFrame = df.pivot(index='Geographic Area', columns='Year', values='Population')
    predictions:list[DataFrame]|None = predict_populations(df=df,future_years=future_years,logger=logger)
    if predictions is None:
        return None
    
    final_df:DataFrame|None = merge_historical_and_future_data(predictions=predictions,historical_pivot=historical_pivot,logger=logger)
    if final_df is None:
        return None
    
    final_df.to_csv("Predicted_Population.csv",index=True)
    logger.log_to_xml(f"Successfully predicted future populations for all states and saved to csv. Closing Program.",status="SUCCESS",basepath=logger.base_dir)
    logger.save_variable_info(locals_dict=locals(),variable_save_path="predict_population_variables.json")

if __name__ == "__main__":
    main()