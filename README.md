# python-telegram-bot jobqueue persistence

This is an example of how to persist scheduled jobs in a file most simply.
The main goal is not to fully persist (e.g. there is no constant lookup to file) but to have a kind of backup, so any bot outages will not make your users suffer and create schedules once again.

## Installation

Copy [job_serialization.py](https://github.com/dikirilov/ptb-job-persistence-stackoverflow/blob/main/job_serialization.py) to your project

## Usage

An example of usage you can find in [bot.py](https://github.com/dikirilov/ptb-job-persistence-stackoverflow/blob/main/bot.py)

There are several things to do:

```python
# import functions from copied script:
from job_serialization import save_jobs_to_file, restore_jobs_from_file
# import event types you will catch 
from apscheduler.events import EVENT_JOB_REMOVED, EVENT_JOB_ADDED, JobEvent
...

# create job_queue variable that will be global for that module 
job_queue = None
# define FILENAME where all the jobs will be saved
FILENAME = "jobs.pkl"
...

# create event catcher to leverage save script so jobs will be persisted
def scheduler_event_catcher(event: JobEvent):
    logger.debug(f"Scheduler event: {event}, job id: {event.job_id}, ",
          f"jobstore name: {event.jobstore}, current job queue: {job_queue}")
    if job_queue:
        logger.info(f"job queue is defined, saving jobs to {FILENAME}")
        save_jobs_to_file(job_queue, FILENAME)
    else:
        logger.warning(f"job queue is not defined")
...

# during bot initialization phase add listener and check persistence to restore jobs if any
app = ApplicationBuilder().token(TOKEN).build()
app.job_queue.scheduler.add_listener(scheduler_event_catcher,
  EVENT_JOB_REMOVED | EVENT_JOB_ADDED)
restore_jobs_from_file(app.job_queue, FILENAME)
# during the same initialization phase define job queue as a global and assign
# current instance of it, so event catcher will be able to use it
global job_queue
job_queue = app.job_queue

```

## Caution
The provided example is something quick to implement and fits the best to MVP / small bots with up to ~100s of scheduled jobs. 
The mechanism is to lookup into jobqueue to retrieve all the jobs and save them as a current state of the jobqueue.
Given that PTB leverages APSheduler in a way that every scheduled job execution leads to APS jobstore adjustment, it could lead to overwhelming file usage. 

In case you are building bot that will scale bigger, please consider other approaches, e.g.:
1. Create a technical schedule that will lookup into jobqueue and save it regularly.
2. Create a separate admin bot command that will lookup into jobqueue and save it.
3. Use not file, but a fully-featured persistence (PostgreSQL, MongoDB, Redis, etc) - check what is relevant for you among what [APScheduler provides](https://github.com/agronholm/apscheduler/tree/master/src/apscheduler/datastores)
