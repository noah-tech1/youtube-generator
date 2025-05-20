from pytrends.request import TrendReq
import random

def get_trending_topic():
    pytrends = TrendReq(hl='en-US', tz=360)
    pytrends.build_payload(kw_list=[""])
    trending_searches = pytrends.trending_searches(pn="united_states")
    topic = trending_searches.sample(1).iloc[0, 0]
    return topic

def generate_title_and_description():
    topic = get_trending_topic()
    title = f"{topic} - What You Need To Know This Week!"
    description = (
        f"In this video, we discuss {topic} and what it means for you. "
        "Subscribe for more trending news and updates!"
    )
    return title, description
