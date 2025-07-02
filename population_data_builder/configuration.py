import os
import json
from xml_logging import XML_Logger

def _verify_configuration(configuration:dict[str,str|int],logger:XML_Logger) -> bool:
    if "Required_Keys" not in configuration.keys():
        return False
    missing_keys:list[str] = []

    for key in configuration["Required_Keys"]:
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
