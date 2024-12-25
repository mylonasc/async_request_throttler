import asyncio
from collections import deque
from asyncio import Queue
import aiohttp

class RequestWrapper:
    def __init__(self, url, callback=None):
        """
        Initialize a RequestWrapper.

        :param url: The URL to fetch.
        :param callback: A function to execute when the request finishes, with the response data as an argument.
        """
        self.url = url
        self.callback = callback

    async def handle_response(self, response):
        """
        Handle the response and execute the callback if provided.

        :param response: The aiohttp response object.
        """
        data = await response.text()
        if self.callback:
            self.callback(data)

class AsyncThrottler:
    def __init__(self, max_requests: int, time_window: float):
        """
        Initialize the AsyncThrottler.

        :param max_requests: Maximum number of requests allowed in the time window.
        :param time_window: Time window in seconds.
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.request_times = deque()
        self.queue = Queue()
        self.stop_signal_received = False

    async def throttle(self):
        """
        Enforce throttling logic to ensure rate limits are respected.
        """
        current_time = asyncio.get_event_loop().time()

        # Remove timestamps outside the time window
        while self.request_times and current_time - self.request_times[0] >= self.time_window:
            self.request_times.popleft()

        if len(self.request_times) >= self.max_requests:
            time_to_wait = self.time_window - (current_time - self.request_times[0])
            await asyncio.sleep(max(0, time_to_wait))

        self.request_times.append(current_time)

    async def add_request(self, request):
        """
        Add a request to the queue to be processed.

        :param request: A RequestWrapper object.
        """
        await self.queue.put(request)

    async def process_requests(self):
        """
        Continuously process requests from the queue with throttling.
        """
        async with aiohttp.ClientSession() as session:
            while not self.stop_signal_received or not self.queue.empty():
                request = await self.queue.get()

                if request == "STOP":
                    self.stop_signal_received = True
                    print("Stopping request processing.")
                    self.queue.task_done()
                    continue

                # Throttle before processing the request
                await self.throttle()

                # Process the request
                await self.make_request(session, request)

                # Mark the task as done
                self.queue.task_done()

    async def make_request(self, session, request_wrapper):
        """
        Perform an HTTP GET request using aiohttp.

        :param session: aiohttp ClientSession.
        :param request_wrapper: A RequestWrapper object containing the URL and optional callback.
        """
        try:
            async with session.get(request_wrapper.url) as response:
                await request_wrapper.handle_response(response)
                print(f"Request to {request_wrapper.url} completed with status {response.status}")
        except Exception as e:
            print(f"Error fetching {request_wrapper.url}: {e}")

# Example usage
def response_callback(data):
    print(f"Callback received data: {data[:50]}...")

async def main():
    throttler = AsyncThrottler(max_requests=5, time_window=1)

    # Start the request processor in the background
    processor_task = asyncio.create_task(throttler.process_requests())

    # Dynamically add requests
    urls = [
        "https://httpbin.org/get", 
        "https://httpbin.org/delay/1", 
        "https://httpbin.org/uuid", 
        "https://httpbin.org/ip", 
        "https://httpbin.org/headers"
    ]
    for url in urls:
        request = RequestWrapper(url, callback=response_callback)
        await throttler.add_request(request)
        await asyncio.sleep(0.1)  # Simulate requests coming in at irregular intervals

    # Signal to stop the processor
    await throttler.add_request("STOP")

    # Wait for all requests to be processed
    await processor_task

# Run the example
if __name__ == "__main__":
    asyncio.run(main())

