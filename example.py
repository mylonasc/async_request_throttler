from src.async_throttler import async_throttler

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

