FUNCTION_CALLING_SYS_PROMPT = {
    "role": "system",
    "content": """
# Instructions
You are a highly detailed researcher, who is trying to extract information from a large dataset.

You will be provided with high level instructions of what data to extract, and you are responsible
for creating JSON schema definitions for functions to extract the information you need.
""",
}


FUNCTION_CALLING_FEW_SHOTS_DICT = [
    {"role": "user", "content": "I need to extract the total population of all countries."},
    {
        "role": "assistant",
        "content": "{'properties': {'country': {'title': 'Country', 'type': 'string'}, 'population': {'title': 'Population', 'type': 'integer'}}, 'required': ['country', 'population'], 'title': 'CountryPopulation', 'type': 'object'}",
    },
    {
        "role": "user",
        "content": "I need to extract information about users. I want their id, name, signup timestamp and friends. Default name can be John Doe",
    },
    {
        "role": "assistant",
        "content": "{'properties': {'id': {'title': 'Id', 'type': 'integer'}, 'name': {'default': 'John Doe', 'title': 'Name', 'type': 'string'}, 'signup_ts': {'default': None, 'format': 'date-time', 'title': 'Signup Ts', 'type': 'string'}, 'friends': {'default': [], 'items': {'type': 'integer'}, 'title': 'Friends', 'type': 'array'}}, 'required': ['id'], 'title': 'User', 'type': 'object'}}",
    },
    {
        "role": "user",
        "content": "I need to extract information about survey responses, I want to extract a user name, their phone number if present, their satisfaction score, their criticisms. Make sure their satisfaction score is 1<=score<=10",
    },
    {
        "role": "assistant",
        "content": "{'properties': {'user_name': {'title': 'User Name', 'type': 'string'}, 'phone_number': {'default': None, 'title': 'Phone Number', 'type': 'string'}, 'satisfaction_score': {'title': 'Satisfaction Score', 'type': 'integer'}, 'criticisms': {'items': {'type': 'string'}, 'title': 'Criticisms', 'type': 'array'}}, 'required': ['user_name', 'satisfaction_score', 'criticisms'], 'title': 'SurveyResponse', 'type': 'object'}",
    },
]
