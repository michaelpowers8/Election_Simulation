import json

def _verify_configuration(configuration:dict[str,str|int]) -> bool:
    if "Required_Keys" not in configuration.keys():
        return False
    missing_keys:list[str] = []

    for key in configuration["Required_Keys"]:
        if key not in configuration.keys():
            missing_keys.append(key)

    if len(missing_keys) > 0:
        return False
    return True

def load_configuration() -> dict[str,str|int]|None:
    with open("configuration.json","rb") as file:
        configuration:dict[str,str|int] = json.load(file)
    if not(_verify_configuration(configuration=configuration)):
        return None
    return configuration
