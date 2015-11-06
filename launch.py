import random
from time import sleep
import pprint

import requests

from construct import ApiConnector, get_json

pretty = pprint.PrettyPrinter(indent=2)

API_V1 = '/api/v1/scheduler'
ACCEPT_JSON = "./resources/accept.json"
TASK_RESOURCES_JSON = "./resources/task_resources.json"

class Launcher:
    def __init__(self, master_url):
        self.conn = None
        self.background_thread = None
        self.master_url = master_url
        self.api_url = '{}/{}'.format(master_url, API_V1)
        self.task_count = 0

    def connect(self):
        r = requests.get("{}/state.json".format(self.master_url))
        self.conn = ApiConnector(self.master_url)
        self.background_thread = self.conn.register_framework()

    def wait_for_offers(self):
        count = 0
        while not self.conn.framework_id and count < 10:
            sleep(3)
            print('.')
            count += 1

        if not self.conn.framework_id:
            print("Failed to register, terminating Framework")
            self.background_thread.cancel()
        else:
            count = 0
            while not self.conn.offers and count < 10:
                print('.')
                sleep(3)
                count += 1

            if not self.conn.offers:
                print("Failed to obtain resources, terminating Framework")
                self.conn.terminate_framework(self.conn.framework_id)
                self.background_thread.cancel()
            else:
                print("Got offers:")
                pretty.pprint(self.conn.offers)

    def launch(self):
        if not isinstance(self.conn.offers, dict):
            return

        my_offers = self.conn.offers.get('offers')
        accept_json = get_json(ACCEPT_JSON)
        for i in range(0, len(my_offers)):
            print("Starting offer ", i + 1, " of ", len(my_offers))
            offer = my_offers[i]

            self.task_count += 1
            task_id = self.task_count

            accept_json["accept"]["offer_ids"].append(offer["id"])
            accept_json["framework_id"]["value"] = self.conn.framework_id

            task_infos = accept_json["accept"]["operations"][0]["launch"]["task_infos"][0]
            task_infos["agent_id"]["value"] = offer['agent_id']['value']
            task_infos["task_id"]["value"] = str(task_id)
            task_infos["resources"] = get_json(TASK_RESOURCES_JSON)

            if task_infos["command"]["value"]:
                task_infos["command"]["value"] = "/usr/bin/python -m SimpleHTTPServer 9000"

            print("Sending ACCEPT message, launching a " + task_infos["name"])
            pretty.pprint(accept_json)

            try:
                r = self.conn.post(self.api_url, accept_json)
                print("Result: {}".format(r.status_code))
                if r.text:
                    print(r.text)
                if 200 <= r.status_code < 300:
                    print("Successfully launched task {} on Agent [{}]".format(task_id, self.conn.offers.get('offers')[0]["agent_id"]["value"]))
            except ValueError, err:
                print("Request failed: {}".format(err))

def main():
    launcher = Launcher("http://172.17.0.41:5050")
    launcher.connect()
    launcher.wait_for_offers()
    if launcher.conn.offers:
        launcher.launch()
        launcher.background_thread.join()

if __name__ == '__main__':
    main()