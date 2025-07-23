import asyncio
from typing import Coroutine, Literal, NamedTuple, Any, TypeVar, Optional, TYPE_CHECKING, Callable, Awaitable
import threading



TArg = TypeVar("TArg")
def run_coroutine(coroutine: Callable[[], Awaitable[TArg]]) -> TArg:
    """
    Switch to another thread to run
    """
    current_loop = None
    try:
        current_loop = asyncio.get_running_loop() # Maybe not needed but guard againt error
    except Exception as e:
        print(e)
    result: TArg = None #type:ignore
    def block_task():
        nonlocal result
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(coroutine())
        loop.close()    
    thread = threading.Thread(target=block_task)
    thread.start()
    thread.join()
    asyncio.set_event_loop(current_loop)
    return result #type:ignore