from typing import TypedDict
from typing import cast
import threading
import requests
import random
import time

url = "localhost:8072/equity"
eval_endpoint = "/discord/eval"
balance_endpoint = "/discord/balance"
pay_endpoint = "/discord/pay"

amt = 100
# platforms = ["discord"] # alternates randomly
platform_ids = ["yasu", "shen"]
message_length_range = (10, 100) # random choice

eval_data = {
	"platform_id": "",
	"message_length": 0
}

balance_data = {
	"platform_id": ""
}

pay_data = {
	"sender_platform_id": "",
	"receiver_platform_id": "",
	"amount": 0,
}

# color Codes
G = '\033[92m'
R = '\033[91m'
Y = '\033[93m'
E = '\033[0m'

api_urls = {
	"eval": f"http://{url}{eval_endpoint}",
	"balance": f"http://{url}{balance_endpoint}",
	"pay": f"http://{url}{pay_endpoint}"
}

# padding of zeros for attempt numbers
padding_width = len(str(amt))

outputs_lock = threading.Lock()

class Response(TypedDict):
	success: bool
	reason: str | None
	result: int | None

outputs: dict[str, list[int]] = {
	'total_attempts': [],
	'total_successes': [],
	'total_failures': [],
	'eval_attempts': [],
	'eval_successes': [],
	'eval_failures': [],
	'balance_attempts': [],
	'balance_successes': [],
	'balance_failures': []
}

def process(platformid: str):

	_eval_attempts = 0
	_eval_successes = 0
	_eval_failures = 0

	_balance_attempts = 0
	_balance_successes = 0
	_balance_failures = 0

	i = 0

	# actual process
	# for i in range(1, amt + 1):
	while _eval_attempts < amt:

		i += 1
		roll = random.random()
		roll2 = random.random()

		# eval
		_eval_attempts += 1
		if eval(i, platformid):
			_eval_successes += 1
		else:
			_eval_failures += 1

		# 20%
		if roll <= 0.20:

			# balance
			_balance_attempts += 1
			_balance = balance(i, platformid)
			if _balance is not None:
				_balance_successes += 1

				# 10%
				if roll2 <= 0.50:
					_ = pay(i, platformid, _balance)

			else:
				_balance_failures += 1

	# finish

	_total_attempts = _eval_attempts + _balance_attempts
	_total_successes = _eval_successes + _balance_successes
	_total_failures = _eval_failures + _balance_failures

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

def eval(i: int, pid: str):
	# update unique data
	data = eval_data.copy()
	data["platform_id"] = pid
	data["message_length"] = int(random.randint(*message_length_range))

	try:
		response = requests.post(api_urls["eval"], json=data, timeout=5)
		status = response.status_code
		res: Response = cast(Response, response.json())

		color = get_color_for_status(status)

		gain_color = None
		res_result = 0
		symbol = "+"

		if response.status_code == 200:
			result = True
			if res['success']:
				res_result = res.get("result", 0)
				if res_result is None:
					res_result = 0
				if res_result > 99:
					gain_color = G
				elif res_result > 0:
					gain_color = Y
				else:
					symbol = "-"
					if res_result < 0:
						res_result = int(str(res_result)[1:])
					gain_color = R
			else:
				symbol = ""
				res_result = f"{res['reason']}, {res['result']}"
				gain_color = R
		else:
			result = False

		print(f"{pid} {i:0{padding_width}} Eval {color}{status}{E}: {symbol}{gain_color}{res_result}{E}")
		return result

	except requests.exceptions.RequestException as e:
		print(f"{pid} {i:0{padding_width}} Eval {R}NETWORK ERROR{E}: {e}")
		return False

def balance(i: int, pid: str) -> int | None:
	# update unique data
	data = balance_data.copy()
	data["platform_id"] = pid

	try:
		response = requests.get(api_urls["balance"], json=data, timeout=5)
		status = response.status_code
		res: Response = cast(Response, response.json())

		color = get_color_for_status(status)

		result = None

		if response.status_code == 200:
			if res['success']:
				res_result = res.get("result", 0)
				res_result = int(res_result) if res_result is not None else 0
				result = res_result
			else:
				res_result = f"{R}{res['reason']}{E}"
		else:
			res_result = f"{R}{res['reason']}{E}"

		print(f"{pid} {i:0{padding_width}} Bal  {color}{status}{E}: {res_result}")
		return result

	except requests.exceptions.RequestException as e:
		print(f"{pid} {i:0{padding_width}} Bal  {R}NETWORK ERROR{E}: {e}")
		return False

def pay(i: int, pid: str, user_balance: int):

	# random platformid other than the one currently chosen
	other_pids = [idx for idx in platform_ids if idx != pid]

	# update unique data
	data = pay_data.copy()
	data["sender_platform_id"] = pid
	data["receiver_platform_id"] = random.choice(other_pids)
	data["amount"] = int(user_balance / 10)

	try:
		response = requests.post(api_urls["pay"], json=data, timeout=5)
		status = response.status_code
		res: Response = cast(Response, response.json())

		color = get_color_for_status(status)

		result = None
		res_result = None

		if response.status_code == 200 and res['success']:
			res_result = f"{G}{res['reason']}{E}"
			result = True
		else:
			res_result = f"{R}{res['reason']}{E}"
			result = False

		print(f"{pid} {i:0{padding_width}} Pay  {color}{status}{E}: {res_result}")
		return result

	except requests.exceptions.RequestException as e:
		print(f"{pid} {i:0{padding_width}} Pay  {R}NETWORK ERROR{E}: {e}")
		return False

def get_color_for_status(status_code: int) -> str:
	if status_code == 200:
		return G
	elif 400 <= status_code < 500:
		return Y
	elif 500 <= status_code < 600:
		return R
	return E # default for other codes

if __name__ == "__main__":

	start_time = time.perf_counter()

	threads: list[threading.Thread] = []

	for platformID in platform_ids:

		t = threading.Thread(
			target = process,
			args = (platformID,)
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

	end_time = time.perf_counter()
	total_time = end_time - start_time

	print("\n--- Simulation Results ---")
	print(f"Reqs:  {total_attempts} | {G}{total_successes}{E}/{R}{total_failures}{E}")
	print(f"Eval:  {eval_attempts} | {G}{eval_successes}{E}/{R}{eval_failures}{E}")
	print(f"Bal:   {balance_attempts} | {G}{balance_successes}{E}/{R}{balance_failures}{E}")
	print(f"Time:  {total_time:.2f} seconds")
	print(f"Req/s: {total_attempts / total_time:.2f}")
