from models import User, TavusJob, db
from video_content import get_top_trending_topics, generate_video_title_and_description
from openai_client import generate_script
from tavus_client import create_tavus_video
# ... other imports

def process_user_videos():
    users = User.query.all()
    topics = get_top_trending_topics()
    for user in users:
        for topic in topics[:user.frequency]:
            title, description = generate_video_title_and_description(topic)
            script = generate_script(topic)  # <--- Now uses ChatGPT!
            tavus_result = create_tavus_video(script, title, description)
            job = TavusJob(
                user_id=user.id,
                topic=topic,
                title=title,
                description=description,
                script=script,
                tavus_job_id=tavus_result.get("job_id") if tavus_result else None,
                status="pending"
            )
            db.session.add(job)
    db.session.commit()
