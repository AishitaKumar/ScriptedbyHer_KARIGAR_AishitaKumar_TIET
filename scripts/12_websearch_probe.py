import sys, asyncio, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace"); sys.path.insert(0, ".")
from dotenv import load_dotenv; load_dotenv()
from app.llm import client

async def main():
    t = time.perf_counter()
    try:
        r = await client().responses.create(
            model="gpt-4o",
            tools=[{"type": "web_search_preview"}],
            input="Search the web: what is the typical selling price range in INR for a "
                  "handmade Madhubani painting (unframed, ~12x18 inch) on Meesho.com right now? "
                  "Reply with just a low-high rupee range and one source.",
        )
        print("OK web_search, %.1fs" % (time.perf_counter()-t))
        print(r.output_text[:600])
    except Exception as e:
        print("web_search FAILED:", type(e).__name__, str(e)[:200])
asyncio.run(main())
