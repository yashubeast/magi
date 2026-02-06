import threading
import random
import time
import requests
from concurrent.futures import ThreadPoolExecutor
from typing import TypedDict, Optional, List

##### constants & Types ########################################################
G, R, Y, E = '\033[92m', '\033[91m', '\033[93m', '\033[0m'

class APIResponse(TypedDict):
  success: bool
  reason: str | None
  result: int | None

class APISpammer:
  def __init__(
    self,
    base_url: str,
    platforms: List[str],
    platform_ids: List[str]
  ):
    self.base_url = base_url.rstrip('/')
    self.platforms = platforms
    self.platform_ids = platform_ids if platform_ids else [
      chr(97 + i) for i in range(26)
    ]

    # statistics tracking
    self.stats = {
      'attempts': 0,
      'success': 0,
      'failure': 0,
      'start_time': 0.0
    }
    self._lock = threading.Lock()

  @staticmethod
  def _get_status_color(code: int) -> str:
    if 200 <= code < 300: return G
    if 400 <= code < 500: return Y
    return R

  def log(self, pid: str, action: str, code: str, detail: str = ""):
    """Thread-safe logging to console."""
    with self._lock:
      print(f"[{pid}] {action.ljust(8)} | Status: {code} | {detail}")

  def run_eval(self, platform: str, pid: str) -> bool:
    payload = {
      "platform_id": pid,
      "message_length": random.randint(20, 150)
    }
    try:
      resp = requests.post(
        f"{self.base_url}/{platform}/eval",
        json=payload,
        timeout=5
      )
      data: APIResponse = resp.json()
      color = self._get_status_color(resp.status_code)

      self.log(
        pid,
        "EVAL",
        f"{color}{resp.status_code}{E}"
      )
      return resp.status_code == 200 and data.get('success')
    except Exception as e:
      self.log(pid, "EVAL", f"{R}ERR{E}", str(e))
      return False

  def run_balance(self, platform: str, pid: str) -> Optional[int]:
    try:
      resp = requests.get(
        f"{self.base_url}/{platform}/balance",
        json={"platform_id": pid},
        timeout=5
      )
      data: APIResponse = resp.json()
      if resp.status_code == 200 and data.get('success'):
        self.log(
          pid,
          "BAL",
          f"{G}200{E}",
          f"{data.get('result')}"
        )
        return data.get('result')
      return None
    except Exception:
      return None

  def run_pay(self, platform: str, pid: str, balance: int):
    target = random.choice([i for i in self.platform_ids if i != pid])
    payload = {
      "sender_platform_id": pid,
      "receiver_platform_id": target,
      "amount": balance // 10
    }
    try:
      resp = requests.post(
        f"{self.base_url}/{platform}/pay",
        json=payload,
        timeout=5
      )
      data: APIResponse = resp.json()
      self.log(
        pid,
        "PAY",
        f"{self._get_status_color(resp.status_code)}{resp.status_code}{E}",
        f"{data.get('reason')}"
      )
    except Exception:
      pass

  def worker_loop(self, platform: str, pid: str, iterations: int):
    """The logic for a single worker thread."""
    for _ in range(iterations):
      success = self.run_eval(platform, pid)

      with self._lock:
        self.stats['attempts'] += 1
        if success:
          self.stats['success'] += 1
        else:
          self.stats['failure'] += 1

      # Logic branches
      if success and random.random() < 0.20:
        bal = self.run_balance(platform, pid)
        if bal and random.random() < 0.50:
          self.run_pay(platform, pid, bal)

  def spam(self, iterations_per_id: int, max_workers: int = 10):
    self.stats['start_time'] = time.perf_counter()

    print(f"{Y}Starting spammer with {max_workers} workers...{E}\n")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
      for p in self.platforms:
        for pid in self.platform_ids:
          executor.submit(self.worker_loop, p, pid, iterations_per_id)

    self.report()

  def report(self):
    duration = time.perf_counter() - self.stats['start_time']
    total = self.stats['attempts']
    print("\n" + "=" * 30)
    print(f"TEST COMPLETE in {duration:.2f}s")
    print(f"total requests: {total}")
    print(f"successes: {G}{self.stats['success']}{E}")
    print(f"failures:  {R}{self.stats['failure']}{E}")
    print(f"throughput: {total / duration:.2f} req/s")
    print("=" * 30)


##### execution ################################################################

if __name__ == "__main__":
  spammer = APISpammer(
    base_url="http://localhost:8072/equity",
    platforms=["discord"],
    platform_ids=["1", "2", "3"]  # Or leave empty [] for a-z
  )

  # run 50 iterations for every platform_id combined
  spammer.spam(iterations_per_id=500, max_workers=15)