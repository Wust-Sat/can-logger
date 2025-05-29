import asyncio

from life_guard.life_center import Dummy


# Usage
async def main():
    nodes = [Dummy(node_id=1), Dummy(node_id=2), Dummy(node_id=3)]
    tasks = [asyncio.create_task(node.start()) for node in nodes]

    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        print("\nShutting down nodes...")
        await asyncio.gather(*[node.stop() for node in nodes])
    finally:
        print("Clean shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nForced exit")
    finally:
        print("Program terminated")
