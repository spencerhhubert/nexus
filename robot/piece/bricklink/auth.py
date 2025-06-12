import os
from typing import Optional
from requests_oauthlib import OAuth1


def mkAuth() -> OAuth1:
    consumer_key = os.environ.get('BL_CONSUMER_KEY')
    consumer_secret = os.environ.get('BL_CONSUMER_SECRET')
    token_value = os.environ.get('BL_TOKEN_VALUE')
    token_secret = os.environ.get('BL_TOKEN_SECRET')

    missing_vars = []
    if not consumer_key:
        missing_vars.append('BL_CONSUMER_KEY')
    if not consumer_secret:
        missing_vars.append('BL_CONSUMER_SECRET')
    if not token_value:
        missing_vars.append('BL_TOKEN_VALUE')
    if not token_secret:
        missing_vars.append('BL_TOKEN_SECRET')

    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

    return OAuth1(
        client_key=consumer_key,
        client_secret=consumer_secret,
        resource_owner_key=token_value,
        resource_owner_secret=token_secret,
    )
