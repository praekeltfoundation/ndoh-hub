import json
import sys


def get_msisdn(details):
    last = None
    for addr, _addr_dets in details.get("addresses", {}).get("msisdn", {}).items():
        if details.get("default") is True:
            return addr
        if details.get("optedout") is not True:
            last = addr
    return last


if __name__ == "__main__":
    for details in sys.stdin:
        msisdn = get_msisdn(json.loads(details))
        if msisdn:
            sys.stdout.write(msisdn)
            sys.stdout.write("\n")
