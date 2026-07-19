import sys, asyncio, json
sys.stdout.reconfigure(encoding="utf-8", errors="replace"); sys.path.insert(0, ".")
from dotenv import load_dotenv; load_dotenv()
from app.db.client import db
from app.flows.common import validate_answer
from app.flows.operations import _craft_label
from app.llm import chat_json, load_prompt

cols = db().table("listings").select("*").limit(1).execute().data
print("listings.dimensions column present:", (not cols) or ("dimensions" in cols[0]))

async def main():
    print("\n-- input validation (name) --")
    for txt in ["नहीं बताऊंगी", "रामकली देवी", "asdfgh"]:
        r = await validate_answer("name", txt, "hi")
        print(f"  {txt!r} -> valid={r.get('valid')} | {(r.get('message') or '')[:55]}")
    print("\n-- dimensions parse --")
    for txt in ["बारह गुणा अठारह इंच", "12 by 18 inches", "नहीं पता"]:
        r = await chat_json(load_prompt("parse_dimensions"),
                            json.dumps({"answer": txt, "language": "hi"}, ensure_ascii=False), what="t")
        print(f"  {txt!r} -> valid={r.get('valid')} canonical={r.get('canonical')} normalized={r.get('normalized')}")
    print("\n-- craft label --")
    print("  madhubani/hi ->", _craft_label("madhubani", "hi"))
    print("  warli/en ->", _craft_label("warli", "en"))
    print("  unknown/hi ->", _craft_label("random craft", "hi"))
asyncio.run(main())
