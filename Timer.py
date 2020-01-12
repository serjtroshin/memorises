from utils import Heap
from time import time

class Activity:
    def __init__(self, flash_card, time):
        self.time = time
        self.flash_card = flash_card




TIMES = [60, 60 * 4, 60 * 10, 3600, 3600 * 24 * 1, 3600 * 24 * 5, 3600 * 24 * 24, 3600 * 24 * 360]
class Timer:
    def __init__(self):
        pass

    def add_card(self, flash_card):
        global activities
        for time_i in TIMES:
            activities.push(Activity(flash_card, time_i + flash_card.time_added))

    def update(self):
        global activities
        cur_time = time()
        acts = []
        while activities.top() is not None and activities.top() < cur_time:
            act = activities.pop()
            acts.append(act)
        return acts
