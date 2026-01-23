
from redis import Redis
from rq import Queue

# Need to set environment variable for config path if needed
# os.environ["AI_BOX_CONFIG_PATH"] = "/Users/daniel/GitHub/AI-Box/config/config.json"

redis_conn = Redis(host="localhost", port=6379, db=0)
kg_q = Queue("kg_extraction", connection=redis_conn)

print("Queue: kg_extraction")
print(f"Jobs in queue: {len(kg_q.jobs)}")
for job in kg_q.jobs:
    print(f"Job ID: {job.id}, Status: {job.get_status()}, Created: {job.created_at}")

failed_q = Queue("failed", connection=redis_conn)
print(f"\nFailed Jobs: {len(failed_q.jobs)}")
for job in failed_q.jobs[:10]:  # Just show last 10
    print(f"Job ID: {job.id}, Status: {job.get_status()}")
    if job.exc_info:
        print(f"Error: {job.exc_info[-500:]}")  # Show last 500 chars
