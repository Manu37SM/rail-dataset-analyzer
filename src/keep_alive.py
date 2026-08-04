import time
import requests
from datetime import datetime

URL = "https://raillens-train-db.onrender.com/actuator/health"
INTERVAL = 300  # 5 minutes


def ping():
    try:
        response = requests.get(URL, timeout=10)

        print(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
            f"Status: {response.status_code} | "
            f"Response: {response.text}"
        )

    except requests.RequestException as e:
        print(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
            f"ERROR: {e}"
        )


def main():
    print("Starting Railens Keep Alive Service...")
    print(f"Pinging {URL} every {INTERVAL // 60} minutes.\n")

    while True:
        ping()
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()