import heapq
import traceback


class Heap(object):
    def __init__(self, initial=None, key=lambda x: x):
        self.key = key
        if initial:
            self._data = [(key(item), item) for item in initial]
            heapq.heapify(self._data)
        else:
            self._data = []

    def push(self, item):
        heapq.heappush(self._data, (self.key(item), item))

    def pop(self):
        return heapq.heappop(self._data)[1]

    def top(self):
        if len(self._data) == 0:
            return None
        item = heapq.heappop(self._data)[1]
        heapq.heappush(self._data, (self.key(item), item))
        return item


def to_string(*args, key="NOKEY"):
    res = key if key is not None else ""
    merged = "__".join(map(str, args))
    return f"{res}__{merged}"


def parse_string(s, delim="__", nokey=False):
    res = s.split(delim)
    if nokey:
        res = res[1:]
    return res


def error_handler(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print("error:", e)
            traceback.print_exc()

    return wrapper


if __name__ == "__main__":
    heap = Heap([])
    heap.push(0)
    print(heap.pop(), heap.pop())
