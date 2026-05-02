from apscheduler.schedulers.background import BackgroundScheduler
from utils.coefficients import calculate_monthly_coefficients
import datetime

sched = BackgroundScheduler()
sched.add_job(calculate_monthly_coefficients, 'cron', day=1, hour=2)
sched.start()