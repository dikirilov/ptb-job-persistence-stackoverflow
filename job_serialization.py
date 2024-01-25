from loguru import logger
import pickle
import sys
import os
from apscheduler.util import ref_to_obj, obj_to_ref
from apscheduler.job import Job
from telegram.ext import JobQueue as PTBJobQueue, Job as PTBJob


logger.remove()
logger.add(sys.stdout, level="TRACE", format="<green>{time}</green> | <blue>{module}</blue> | <lvl>{level}</lvl> | {message}",
           serialize=False)


def restore_state(job_queue: PTBJobQueue, serialized_job: dict):
    if serialized_job["type"] != "PTB job":
        logger.warning(f"Unsupported job type: {serialized_job['type']}")
        return
    if serialized_job["version"] != 1:
        logger.warning(f"Unsupported job version: {serialized_job['version']}")
        return
    logger.debug(f"Restoring PTB job {serialized_job['name']}")
    callback = ref_to_obj(serialized_job["callback"])
    j = job_queue.run_custom(callback, data=serialized_job["data"], name=serialized_job["name"],
                             chat_id=serialized_job["chat_id"], user_id=serialized_job["user_id"], job_kwargs={})
    job_id = j.job.id
    j.job.__setstate__(serialized_job["state"])
    j.job.id = job_id
    j.job.func = job_queue.job_callback
    j.job.args = (job_queue, j)
    logger.debug(f"Restored PTB job {serialized_job['name']} with {j.job.trigger}")


def retrieve_state(job: Job):
    """
    Retrieve the state of a job and prepare it for serialization.

    Parameters:
        job: The job for which the state is to be retrieved.

    Returns:
        A serializable dictionary containing the necessary job information.
    """
    logger.trace(f"Data for {job.id=} is to be retrieved")
    state = job.__getstate__()
    ptb_job: PTBJob = job.args[1]
    # eliminate extra references that might be restored from other sources
    state['args'] = None
    serializable = {
        "type": "PTB job",
        "version": 1,
        "PTB_deleted": False,
        "callback": obj_to_ref(ptb_job.callback),
        "data": ptb_job.data,
        "name": ptb_job.name,
        "removed": ptb_job.removed,
        "enabled": ptb_job.enabled,
        "chat_id": ptb_job.chat_id,
        "user_id": ptb_job.user_id,
        "state": state
    }
    logger.trace(f"{state=}")
    return serializable


def save_jobs_to_file(job_queue: PTBJobQueue, filename: str) -> bool:
    serialized = [retrieve_state(job.job) for job in job_queue.jobs()]
    logger.debug(f"Saving {len(serialized)} jobs to file {filename}")
    with open(filename, 'wb') as f:
        try:
            pickle.dump(serialized, f)
            logger.debug(f"Saved {len(serialized)} jobs to file {filename}")
        except Exception as e:
            logger.error(f"Failed to save jobs to {filename}: {e}")
    return True


def restore_jobs_from_file(job_queue: PTBJobQueue, filename: str) -> bool:
    if not os.path.exists(filename):
        logger.error(f"File {filename} does not exist")
        return None
    with open(filename, 'rb') as f:
        unpickler = pickle.Unpickler(f)
        try:
            data = unpickler.load()
            logger.info(f"Read {len(data)} jobs from {filename}")
        except EOFError:
            data = None
            logger.info(f"{filename} is empty")
    if not data:
        logger.warning(f"Nothing to restore. If restore information was updated after FileJobStore was created, "
                       f"read_state_from_persistence() must be called first")
        return False
    for job in data:
        restore_state(job_queue, job)
    return True
