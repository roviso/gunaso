import json
from typing import List

from djangorestframework_camel_case.render import CamelCaseJSONRenderer
from djangorestframework_camel_case.util import underscoreize


def get_camelized_json(data):
    """Utility function that returns CamelizedJSON of snake_cased_json

    Args:
        data (json): Snaked Case data

    Returns:
        json: Camelized data
    """
    camalized_data = json.loads(CamelCaseJSONRenderer().render(data).decode())
    return camalized_data


def get_underscoreize_json(data):
    """Utility function that returns snake_cased_json of a CamelizedJSON

    Args:
        data (json): Camelized data

    Returns:
        json: Snaked Case data
    """
    underscoreize_data = underscoreize(data)
    return underscoreize_data


def get_pclaim(user):
    try:
        claim = user.password[-10:]
        bclaim = claim.encode("utf-8")
        pclaim = str(int.from_bytes(bclaim, "big"))
        return pclaim
    except Exception as e:
        print(e)
        return None


def has_role(user, role: List[str]):
    if hasattr(user, "profile") and user.profile and user.profile.role in role:
        return True
    return False


def get_key_from_dict(my_dict, val):
    """Function to get key from a dictionary by its value

    Args:
        my_dict (dict): The dictionary from which a key is to be extracted
        val (any): A value that is inside the value

    Returns:
        any: Returns a key if found. Else returns None
    """
    for key, value in my_dict.items():
        if val == value:
            return key

    return None
