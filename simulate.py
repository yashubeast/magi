import requests
import time
import random

url = "localhost:8070"
eval_endpoint = "/equity/eval"
balance_endpoint = "/equity/balance"

amt = 100 # amount of reqs to simulate per platform
platforms = ["discord", "minecraft"]
message_length_range = (10, 100)
timeleap = 60

eval_data = {
	"platform": "1",
	"platform_id": "1",
	"message_id": "test_msg_",
	"message_length": "1",
	"debug_timestamp": f"{int(time.time())}",
}

eval_balance = {
	"platform": "1",
	"platform_id": "1",
}

# color Codes
G = '\033[92m'
R = '\033[91m'
Y = '\033[93m'
E = '\033[0m'

api_urls = {
	"eval": f"http://{url}{eval_endpoint}",
	"balance": f"http://{url}{balance_endpoint}"
}

def process():

	start_time = time.perf_counter()

	eval_attempts = 0
	eval_successes = 0
	eval_failures = 0
	balance_attempts = 0
	balance_successes = 0
	balance_failures = 0

	for i in range(1, amt + 1):

		# eval
		eval_attempts += 1
		if eval(i):
			eval_successes += 1
		else: eval_failures += 1

		# random
		roll = random.random()

		# 20%
		if roll <= 0.20:

			# balance
			balance_attempts += 1
			if balance():
				balance_successes += 1
			else: balance_failures += 1

	# finish
	end_time = time.perf_counter()

	total_attempts = eval_attempts + balance_attempts
	total_successes = eval_successes + balance_successes
	total_failures = eval_failures + balance_failures
	total_time = end_time - start_time

	print("\n--- Simulation Results ---")
	print(f"Reqs:  {total_attempts} | {G}{total_successes}{E}/{R}{total_failures}{E}")
	print(f"Eval:  {eval_attempts} | {G}{eval_successes}{E}/{R}{eval_failures}{E}")
	print(f"Bal:   {balance_attempts} | {G}{balance_successes}{E}/{R}{balance_failures}{E}")
	print(f"Time:  {total_time:.2f} seconds")
	print(f"Req/s: {total_attempts / total_time:.2f}")


def eval(i):
	# update unique data
	data = eval_data.copy()
	data["platform"] = random.choice(platforms)
	data["message_id"] += str(i)
	data["message_length"] = str(random.randint(*message_length_range))
	data["debug_timestamp"] = str(int(data["debug_timestamp"]) + (timeleap * i))

	try:
		response = requests.post(api_urls["eval"], json=data, timeout=5)
		status = response.status_code
		res = response.json()

		color = get_color_for_status(status)

		status_text = f"{color}STATUS {status}{E}"

		if response.status_code == 200:
			result = True
			res_result = res.get("result", 0)
			if res_result > 99:
				status_text += f" | Gained: {G}{res_result}{E}"
			elif res_result > 0:
				status_text += f" | Gained: {Y}{res_result}{E}"
			else:
				status_text += f" | Gained: {R}{res_result}{E}"
		else:
			result = False

		print(f"Request {i:03}: {status_text}")
		return result

	except requests.exceptions.RequestException as e:
		print(f"Request {i:03}: {R}NETWORK ERROR{E} - {e}")
		return False

def balance():
	# update unique data
	data = eval_balance.copy()
	data["platform"] = random.choice(platforms)

	try:
		response = requests.get(api_urls["balance"], json=data, timeout=5)
		status = response.status_code
		res = response.json()

		color = get_color_for_status(status)

		status_text = f"{color}STATUS {status}{E}"

		if response.status_code == 200:
			result = True
			res_result = res.get("result", 0)
			if res_result > 99:
				status_text += f" | Balance: {G}{res_result}{E}"
			elif result > 0:
				status_text += f" | Balance: {Y}{res_result}{E}"
			else:
				status_text += f" | Balance: {R}{res_result}{E}"
		else:
			result = False

		print(f"Request Balance: {status_text}")
		return result

	except requests.exceptions.RequestException as e:
		print(f"Request Balance: {R}NETWORK ERROR{E} - {e}")
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
	process()