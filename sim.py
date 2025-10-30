import threading
import random
import time

from var import outputs
from var import outputs_lock
from var import Eval
from var import Balance
from var import Pay
from var import G, R, E

amt = 1
platforms = ['discord']
# platform_ids = []
platform_ids = ['1']
message_lengths = (20, 150)

iwidth = len(str(amt))
char = ord('a')

if len(platform_ids) == 0:
  for i in range (26):
    letter = chr(char + i)
    platform_ids.append(letter)

def process(p: str, pid: str):

  _eval_attempts = 0
  _eval_successes = 0
  _eval_failures = 0

  _balance_attempts = 0
  _balance_successes = 0
  _balance_failures = 0

  _pay_attempts = 0
  _pay_successes = 0
  _pay_failures = 0

  i = 0

  # actual process
  while _eval_attempts < amt:

    i += 1
    roll = random.random()
    roll2 = random.random()

    # eval
    _eval_attempts += 1
    if Eval(i, p, pid, message_lengths, iwidth):
      _eval_successes += 1
    else:
      _eval_failures += 1

    # 20%
    if roll <= 0.20:

      # balance
      _balance_attempts += 1
      _balance = Balance(i, p, pid, iwidth)
      if _balance is not None:
        _balance_successes += 1

        # 10%
        if roll2 <= 0.50:
          _pay_attempts += 1
          if Pay(i, p, platform_ids, pid, _balance, iwidth):
            _pay_successes += 1
          else:
            _pay_failures += 1


      else:
        _balance_failures += 1

  # finish

  _total_attempts = _eval_attempts + _balance_attempts + _pay_attempts
  _total_successes = _eval_successes + _balance_successes + _pay_successes
  _total_failures = _eval_failures + _balance_failures + _pay_failures

  with outputs_lock:
    outputs['total_attempts'].append(_total_attempts)
    outputs['total_successes'].append(_total_successes)
    outputs['total_failures'].append(_total_failures)
    outputs['eval_attempts'].append(_eval_attempts)
    outputs['eval_successes'].append(_eval_successes)
    outputs['eval_failures'].append(_eval_failures)
    outputs['balance_attempts'].append(_balance_attempts)
    outputs['balance_successes'].append(_balance_successes)
    outputs['balance_failures'].append(_balance_failures)
    outputs['pay_attempts'].append(_pay_attempts)
    outputs['pay_successes'].append(_pay_successes)
    outputs['pay_failures'].append(_pay_failures)

if __name__ == "__main__":

  start_time = time.perf_counter()

  threads: list[threading.Thread] = []

  for p in platforms:
    for pid in platform_ids:

      t = threading.Thread(
        target = process,
        args = (p, pid,)
      )

      threads.append(t)

      t.start()

  for t in threads:
    t.join()

  total_attempts = sum(outputs['total_attempts'])
  total_successes = sum(outputs['total_successes'])
  total_failures = sum(outputs['total_failures'])
  eval_attempts = sum(outputs['eval_attempts'])
  eval_successes = sum(outputs['eval_successes'])
  eval_failures = sum(outputs['eval_failures'])
  balance_attempts = sum(outputs['balance_attempts'])
  balance_successes = sum(outputs['balance_successes'])
  balance_failures = sum(outputs['balance_failures'])
  pay_attempts = sum(outputs['pay_attempts'])
  pay_successes = sum(outputs['pay_successes'])
  pay_failures = sum(outputs['pay_failures'])

  end_time = time.perf_counter()
  total_time = end_time - start_time

  print("\n--- Simulation Results ---")
  print(f"Reqs:  {total_attempts} | {G}{total_successes}{E}/{R}{total_failures}{E}")
  print(f"Eval:  {eval_attempts} | {G}{eval_successes}{E}/{R}{eval_failures}{E}")
  print(f"Bal :  {balance_attempts} | {G}{balance_successes}{E}/{R}{balance_failures}{E}")
  print(f"Pay :  {pay_attempts} | {G}{pay_successes}{E}/{R}{pay_failures}{E}")
  print(f"Time:  {total_time:.2f} seconds")
  print(f"Req/s: {total_attempts / total_time:.2f}")
