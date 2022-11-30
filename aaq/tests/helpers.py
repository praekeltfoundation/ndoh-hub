import json


class FakeAaqCoreApi:
    def post_inbound_check(self, request):
        payload = json.loads(request.body)
        print("payload:", payload)
        resp_body = {
            "top_responses": [
                [
                    "21",
                    "short of breath",
                    "*Yes, pregnancy can affect your breathing",
                ],
                [
                    "26",
                    "Fainting in pregnancy",
                    "*Fainting could mean anemia – visit the clinic to find out",
                ],
                [
                    "114",
                    "Bleeding in pregnancy",
                    "*Bleeding during pregnancy*\r\n \r\n*Early pregnancy",
                ],
                [
                    "111",
                    "Sleep in pregnancy",
                    "*Get good sleep during pregnancy*\r\n\r\nGood sleep is good",
                ],
                [
                    "150",
                    "Breast pain",
                    "*Sometimes breast pain needs to be checked at the clinic",
                ],
            ],
            "feedback_secret_key": "xxx",
            "inbound_secret_key": "yyy",
            "inbound_id": "iii",
            "next_page_url": "/inbound/iii/ppp?inbound_secret_key=zzz",
        }

        return (200, {}, json.dumps(resp_body))

    def post_inbound_check_return_empty(self, request):
        payload = json.loads(request.body)
        print("payload:", payload)
        resp_body = {
            "top_responses": [],
            "feedback_secret_key": "xxx",
            "inbound_secret_key": "yyy",
            "inbound_id": "iii",
        }

        return (200, {}, json.dumps(resp_body))
