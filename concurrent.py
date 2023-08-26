# Simple to use multi-threaded concurrent executor.
# Similar to what GNU parallel does.

from queue import Queue
from typing import Callable, Iterator, TypeVar
from threading import Thread

T, S = TypeVar("T"), TypeVar("S")


def concurrent(
    fn: Callable[[T], S],
    args: Iterator[T],
    max_threads: int,
) -> Iterator[S]:
    """
    Run a function concurrently on a list of arguments.
    """

    end_marker = object()

    input_q = Queue(maxsize=1)
    output_q = Queue(maxsize=1)

    def reader():
        for arg in args:
            input_q.put(arg)
        for _ in range(max_threads):
            input_q.put(end_marker)

    reader_thread = Thread(target=reader, daemon=True)
    reader_thread.start()

    def worker():
        while True:
            arg: T | end_marker = input_q.get()
            if arg is end_marker:
                return
            try:
                result = fn(arg)
            except BaseException as e:
                result = e
            output_q.put(result)

    worker_threads = [Thread(target=worker, daemon=True) for _ in range(max_threads)]
    for t in worker_threads:
        t.start()

    def waiter():
        for t in worker_threads:
            t.join()
        output_q.put(end_marker)

    waiter_thread = Thread(target=waiter, daemon=True)
    waiter_thread.start()

    while True:
        v: S | BaseException | end_marker = output_q.get()
        if v is end_marker:
            return
        if isinstance(v, BaseException):
            raise v
        yield v
