import os
from requests_oauthlib import OAuth1

# need to get these from
# https://www.bricklink.com/v2/api/register_consumer.page
# https://www.bricklink.com/v3/api.page
ConsumerKey = os.environ.get("BL_CONSUMER_KEY")
ConsumerSecret = os.environ.get("BL_CONSUMER_SECRET")
TokenValue = os.environ.get("BL_TOKEN_VALUE")
TokenSecret = os.environ.get("BL_TOKEN_SECRET")

oauth = OAuth1(
    client_key=ConsumerKey,
    client_secret=ConsumerSecret,
    resource_owner_key=TokenValue,
    resource_owner_secret=TokenSecret,
)
