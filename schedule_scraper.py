import schedule
import time
import subprocess

def job():
    print("Executando scraping...")
    subprocess.run(["python", "scraper.py"])

schedule.every().day.at("08:00").do(job)

while True:
    schedule.run_pending()
    time.sleep(1)
