import json


class FakeAaqCoreApi:
    def post_inbound_check(self, request):
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
        resp_body = {
            "top_responses": [],
            "feedback_secret_key": "xxx",
            "inbound_secret_key": "yyy",
            "inbound_id": "iii",
        }

        return (200, {}, json.dumps(resp_body))


class FakeAaqUdApi:
    def post_inbound_check_return_one(self, request):
        resp_body = {
            "urgency_score": 1.0,
        }

        return (200, {}, json.dumps(resp_body))

    def post_inbound_check_return_zero(self, request):
        resp_body = {
            "urgency_score": 0.0,
        }

        return (200, {}, json.dumps(resp_body))

class FakeTask:
    def call_add_feedback_task(self, request):
        resp_body = {
            "task_added": "True",
        }
        return (202, {}, json.dumps(resp_body))
