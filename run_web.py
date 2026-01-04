"""Run the AI Dungeon Master web server."""

import uvicorn

if __name__ == "__main__":
    print("=" * 50)
    print("  AI Dungeon Master - Web Server")
    print("  Pathfinder 1st Edition")
    print("=" * 50)
    print()
    print("Starting server at http://localhost:8000")
    print("Connect from your phone using your computer's IP address")
    print()
    print("Press Ctrl+C to stop")
    print()

    uvicorn.run(
        "src.web.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
