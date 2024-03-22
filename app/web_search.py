from duckduckgo_search import DDGS,AsyncDDGS
import asyncio
import sys
import argparse
import json

def get_web_text(query):
    print("web検索:",query, file=sys.stderr)
    results = asyncio.run(async_get_web_text(query))
    results_text = json.dumps(results,ensure_ascii=False)
    print("results_text:",results_text,file=sys.stderr)
    return results_text

async def async_get_web_text(query):
    results = await AsyncDDGS().text(query, max_results=5,region='jp-jp') 
    return results

async def async_get_web_news(query):
    results = await AsyncDDGS().news(query, max_results=5,region='jp-jp')
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Search DuckDuckGo for a query.")
    parser.add_argument("query", type=str, help="The search query.")
    args = parser.parse_args()

    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    print("------ text ------")
    results = get_web_text(args.query)
    print(results)
    print("------async text ------")
    results = asyncio.run(async_get_web_text(args.query))
    for result in results:
        print(result)

    print("------ news ------")
    results = asyncio.run(async_get_web_news(args.query))
    for result in results:
        print(result)
