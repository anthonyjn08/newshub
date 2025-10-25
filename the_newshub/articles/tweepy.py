import os
import tweepy
from dotenv import load_dotenv

load_dotenv()


def get_twitter_client():
    """
    Authenticate tweepy.
    """
    api_key = os.getenv("TWITTER_API_KEY")
    api_secret = os.getenv("TWITTER_API_SECRET")
    access_token = os.getenv("TWITTER_ACCESS_TOKEN")
    access_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

    if not all([api_key, api_secret, access_token, access_secret]):
        print("⚠️ Twitter API keys are missing. Tweet not sent.")
        return None

    try:
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_secret,
        )
        return client
    except Exception as e:
        print(f"⚠️ Failed to connect to Twitter API: {e}")
        return None


def tweet_article(article):
    """
    Send a tweet when an article or newsletter is published.
    """
    client = get_twitter_client()
    if not client:
        return

    tweet_text = (f"{article.title} by {article.author.full_name}"
                  f"\nRead more on The Newshub 📰")

    try:
        response = client.create_tweet(text=tweet_text)
        print(f"✅ Tweet sent for article: ({response.data})")
        return response
    except Exception as e:
        print(f"⚠️ Error tweeting article: {e}")
        return None
