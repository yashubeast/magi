from typing import TypedDict
from typing import cast
import threading
import requests
import random

url = "http://localhost:8072/equity/"

eval = "/eval"
balance = "/balance"
pay = "/pay"

timeout = 7

datas: dict[str, dict[str, str | int]] = {
  "eval": {
    "platform_id": "",
    "message_length": 0
  },
  "balance": {
    "platform_id": ""
  },
  "pay": {
    "sender_platform_id": "",
    "receiver_platform_id": "",
    "amount": 0,
  }
}

# color Codes, green, red, yellow
G = '\033[92m'
R = '\033[91m'
Y = '\033[93m'
E = '\033[0m'
NETWORK_ERROR = f"{R}NETWORK ERROR{E}"

class Response(TypedDict):
  success: bool
  reason: str
  result: int

outputs_lock = threading.Lock()

outputs: dict[str, list[int]] = {
  'total_attempts': [],
  'total_successes': [],
  'total_failures': [],
  'eval_attempts': [],
  'eval_successes': [],
  'eval_failures': [],
  'balance_attempts': [],
  'balance_successes': [],
  'balance_failures': [],
  'pay_attempts': [],
  'pay_successes': [],
  'pay_failures': []
}

def Eval(i: int, p: str ,pid: str, mlen: tuple[int, int], iwidth: int) -> bool:

  # update unique data
  data: dict[str, str | int] = datas["eval"]
  data["platform_id"] = pid
  data["message_length"] = int(random.randint(*mlen))

  try:
    response = requests.post(f"{url}{p}{eval}", json=data, timeout=timeout)
    status = response.status_code
    res: Response = cast(Response, response.json())

    colored_status = get_color_for_status(status)

    gain_color = E
    res_result = 0
    symbol = "+"
    res_reason: str = res.get("reason", "")

    if response.status_code == 200:
      result = True

      if res['success']:
        res_result: int = res["result"]

        if res_result > 0:
          gain_color = G
        else:
          symbol = ""
          gain_color = R

      else:
        symbol = ""
        gain_color = R

    else:
      result = False

    _print(pid, i, iwidth, 'Eval', colored_status, gain_color, symbol, res_result, res_reason)
    return result

  except requests.exceptions.RequestException as e:
    print(f"{pid} {i:0{iwidth}} Eval {R}NETWORK ERROR{E}: {e}")
    _print(pid, i, iwidth, 'Eval', NETWORK_ERROR, str(e))
    return False

def Balance(i: int, p: str, pid: str, iwidth: int) -> int | None:

  # update unique data
  data: dict[str, str | int] = datas["balance"]
  data["platform_id"] = pid

  try:
    response = requests.get(f"{url}{p}{balance}", json=data, timeout=timeout)
    status = response.status_code
    res: Response = cast(Response, response.json())

    colored_status = get_color_for_status(status)

    result = None
    res_reason: str = ''
    res_result: int = 0

    if response.status_code == 200:

      if res['success']:
        res_result = res.get("result", 0)
        result = res_result
      else:
        res_reason = f"{R}{res['reason']}{E}"

    else:
      res_reason = f"{R}{res['reason']}{E}"

    _print(pid, i, iwidth, 'Bal ', colored_status, _res_result = res_result, _res_reason = res_reason)
    return result

  except requests.exceptions.RequestException as e:
    _print(pid, i, iwidth, 'Bal ', NETWORK_ERROR, str(e))
    return False

def Pay(i: int, p: str, pids: list[str], pid: str, user_balance: int, iwidth: int) -> bool:

  # random platformid other than the one currently chosen
  other_pids = [idx for idx in pids if idx != pid]

  # update unique data
  data: dict[str, str | int] = datas["pay"]
  data["sender_platform_id"] = pid
  data["receiver_platform_id"] = random.choice(other_pids)
  data["amount"] = int(user_balance / 10)

  try:
    response = requests.post(f"{url}{p}{pay}", json=data, timeout=timeout)
    status = response.status_code
    res: Response = cast(Response, response.json())

    colored_status = get_color_for_status(status)

    result = None
    res_reason = None

    if response.status_code == 200 and res['success']:

      res_reason = f"{G}{res['reason']}{E}"
      result = True

    else:

      res_reason = f"{R}{res['reason']}{E}"
      result = False

    _print(pid, i, iwidth, 'Pay ', colored_status, res_reason)
    return result

  except requests.exceptions.RequestException as e:
    _print(pid, i, iwidth, 'Pay ', NETWORK_ERROR, str(e))
    return False

def get_color_for_status(status_code: int) -> str:
  if status_code == 200:
    color = G
  elif 400 <= status_code < 500:
    color = Y
  elif 500 <= status_code < 600:
    color = R
  else:
    color = E

  return f"{color}{status_code}{E}"

def _print(
  _pid: str,
  _i: int,
  _iwidth: int,
  _txt: str,
  _colored_status: str,
  _gain_color: str | None = '',
  _symbol: str | None = '',
  _res_result: int | None = None,
  _res_reason: str | None = ''
) -> None:
  print(f"{_pid} {_i:0{_iwidth}} {_txt} {_colored_status}: {_gain_color}{_symbol}{_res_result}{', ' if _res_reason != '' else ''}{_res_reason or ''}{E}")
