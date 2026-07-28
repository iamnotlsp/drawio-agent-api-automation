from time import monotonic, sleep

import pytest


def wait_until(
        fetch_state,
        is_ready,
        *,
        timeout=30,
        interval=1,
        description="异步条件"
):
    deadline = monotonic() + timeout
    last_state = None

    while True:
        last_state = fetch_state()

        if is_ready(last_state):
            return last_state

        remaining = deadline - monotonic()
        if remaining <= 0:
            pytest.fail(
                f"等待{description}超时，"
                f"timeout={timeout}s，最后状态={last_state!r}"
            )

        sleep(min(interval, remaining))
