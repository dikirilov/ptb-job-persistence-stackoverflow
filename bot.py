import random
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import sys
from apscheduler.events import EVENT_JOB_REMOVED, EVENT_JOB_ADDED, JobEvent
from loguru import logger
from job_serialization import save_jobs_to_file, restore_jobs_from_file
import os

TOKEN = os.getenv("TOKEN")
FILENAME = "jobs.pkl"
job_queue = None
logger.remove()
logger.add(sys.stdout, level="DEBUG", format="<green>{time}</green> | <blue>{module}</blue> | <lvl>{level}</lvl> | {message}", serialize=False)


async def tick(context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_message(
        chat_id=context.job.chat_id,
        text=f"Tick from {context.job.name}"
    )


async def add_ticker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(f"Starting ticking")
    num = len(context.job_queue.jobs())
    seconds = random.randint(5, 15)
    msg = f"Scheduling job-{num} every {seconds} seconds"
    logger.info(msg)
    context.job_queue.run_repeating(tick, seconds, chat_id=update.message.chat_id,
                                    name=f"job-{num}")
    await context.bot.send_message(
        chat_id=update.message.chat_id,
        text=msg,
    )


async def remove_ticker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(f"Stopping ticking")
    job = context.job_queue.jobs()[-1]
    name = job.name
    job.schedule_removal()
    msg = f"Removed {name}"
    logger.info(msg)
    await context.bot.send_message(
        chat_id=update.message.chat_id,
        text=msg,
    )


def scheduler_event_catcher(event: JobEvent):
    logger.debug(f"Scheduler event: {event}, job id: {event.job_id}, jobstore name: {event.jobstore}, current job queue: {job_queue}")
    if job_queue:
        logger.info(f"job queue is defined, saving jobs to {FILENAME}")
        save_jobs_to_file(job_queue, FILENAME)
    else:
        logger.warning(f"job queue is not defined")


def main():
    if TOKEN is None:
        logger.error(f"No token configured for bot")
        return
    app = ApplicationBuilder().token(TOKEN).build()
    app.job_queue.scheduler.add_listener(scheduler_event_catcher, EVENT_JOB_REMOVED | EVENT_JOB_ADDED)
    app.add_handler(CommandHandler("add_ticker", add_ticker))
    app.add_handler(CommandHandler("remove_ticker", remove_ticker))
    logger.info('Handlers added')
    global job_queue
    job_queue = app.job_queue
    restore_jobs_from_file(job_queue, FILENAME)

    logger.info('Starting polling...')
    app.run_polling()


if __name__ == '__main__':
    main()
