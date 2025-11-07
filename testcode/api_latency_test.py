#!/usr/bin/env python3
"""
测量 OpenRouter (OpenAI client) 接口的平均响应时间。

使用方法：
  python testcode/api_latency_test.py \
    --model qwen/qwen3-235b-a22b-thinking-2507 \
    --n 5 \
    --max_tokens 64 \
    --temperature 0.2

可选：
  --base_url https://openrouter.ai/api/v1
  --api_key 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
  --include_reasoning 
  --out_json 
  --out_csv  

备注：
- 为避免服务端缓存影响，脚本会在每次请求的用户消息中附加随机tag。
- 若需要更稳定或更短的响应时间测量，可将 max_tokens 调小（例如16）。
"""

import argparse
import os
import sys
import time
import statistics
import random
import string
import json
from typing import List, Dict, Any


def gen_random_tag(length: int = 8) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(random.choice(alphabet) for _ in range(length))


def run_once(client, model: str, system_prompt: str, user_message: str,
             temperature: float, max_tokens: int,
             include_reasoning: bool) -> Dict[str, Any]:
    start = time.perf_counter()
    try:
        extra_body = None
        if include_reasoning:
            extra_body = {"reasoning": {"enabled": True}, "include_reasoning": True}

        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0,
            extra_body=extra_body,
        )
        end = time.perf_counter()
        msg = resp.choices[0].message
        content = getattr(msg, "content", "") or ""
        reasoning = getattr(msg, "reasoning", None)
        return {
            "ok": True,
            "elapsed": end - start,
            "content_preview": content[:200],
            "reasoning_present": reasoning is not None,
            "model": getattr(resp, "model", model),
        }
    except Exception as e:
        end = time.perf_counter()
        return {"ok": False, "elapsed": end - start, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="测量API回复的平均时间")
    parser.add_argument("--model", type=str, default=os.getenv("DEFAULT_MODEL", "qwen/qwen3-235b-a22b-thinking-2507"), help="模型名称")
    parser.add_argument("--n", type=int, default=5, help="请求次数")
    parser.add_argument("--temperature", type=float, default=0.2, help="温度")
    parser.add_argument("--max_tokens", type=int, default=64, help="最大生成token数")
    parser.add_argument("--base_url", type=str, default=os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1"), help="API基地址")
    parser.add_argument("--api_key", type=str, default=os.getenv("OPENAI_API_KEY", ""), help="API Key，不填则用环境变量")
    parser.add_argument("--include_reasoning", action="store_true", help="启用 reasoning tokens（部分模型支持）")
    parser.add_argument("--system_prompt", type=str, default="You are a helpful assistant.", help="系统提示")
    parser.add_argument("--user_message", type=str, default="Return a short reply 'OK'.", help="用户消息基础文本")
    parser.add_argument("--out_json", type=str, default="", help="输出结果到JSON文件路径")
    parser.add_argument("--out_csv", type=str, default="", help="输出每次耗时到CSV文件路径")
    args = parser.parse_args()

    try:
        from openai import OpenAI
    except Exception as e:
        print("❌ 需要安装 openai 库：pip install openai")
        print(f"错误: {e}")
        sys.exit(1)

    if not args.api_key:
        print("⚠️ 未提供 API Key，将尝试使用环境变量 OPENAI_API_KEY")

    client = OpenAI(api_key=args.api_key or os.getenv("OPENAI_API_KEY", ""), base_url=args.base_url)

    print("🚀 开始测量 API 响应时间")
    print(f"   模型: {args.model}")
    print(f"   次数: {args.n}")
    print(f"   max_tokens: {args.max_tokens}, temperature: {args.temperature}")
    print(f"   reasoning: {'ON' if args.include_reasoning else 'OFF'}")

    results: List[Dict[str, Any]] = []
    for i in range(args.n):
        tag = gen_random_tag(8)
        user_msg = f"{args.user_message} [req={i}, tag={tag}]"
        r = run_once(client, args.model, args.system_prompt, user_msg,
                     args.temperature, args.max_tokens, args.include_reasoning)
        results.append(r)
        if r["ok"]:
            print(f"✅ 第{i+1}次: {r['elapsed']:.2f}s, reasoning={r['reasoning_present']}")
        else:
            print(f"❌ 第{i+1}次失败: {r['elapsed']:.2f}s, 错误={r.get('error')}")

    # 统计
    times = [r["elapsed"] for r in results if r.get("elapsed") is not None]
    oks = [r for r in results if r.get("ok")]
    fails = [r for r in results if not r.get("ok")]
    summary = {
        "total": len(results),
        "success": len(oks),
        "failed": len(fails),
        "avg_sec": statistics.mean(times) if times else None,
        "median_sec": statistics.median(times) if times else None,
        "min_sec": min(times) if times else None,
        "max_sec": max(times) if times else None,
        "p95_sec": (sorted(times)[int(0.95 * (len(times)-1))] if times else None),
        "model": args.model,
        "include_reasoning": args.include_reasoning,
        "n": args.n,
        "max_tokens": args.max_tokens,
        "temperature": args.temperature,
    }

    print("\n===== 测量结果 =====")
    print(f"总请求: {summary['total']}, 成功: {summary['success']}, 失败: {summary['failed']}")
    if times:
        print(f"平均: {summary['avg_sec']:.2f}s, 中位数: {summary['median_sec']:.2f}s, p95: {summary['p95_sec']:.2f}s")
        print(f"最小: {summary['min_sec']:.2f}s, 最大: {summary['max_sec']:.2f}s")

    # 保存文件
    if args.out_json:
        payload = {"summary": summary, "samples": results}
        try:
            with open(args.out_json, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            print(f"🧾 JSON 已保存: {args.out_json}")
        except Exception as e:
            print(f"保存 JSON 失败: {e}")

    if args.out_csv:
        try:
            with open(args.out_csv, "w", encoding="utf-8") as f:
                f.write("index,ok,elapsed,reasoning_present,error\n")
                for i, r in enumerate(results):
                    f.write(f"{i},{r.get('ok')},{r.get('elapsed')},{r.get('reasoning_present')},{r.get('error','')}\n")
            print(f"🧾 CSV 已保存: {args.out_csv}")
        except Exception as e:
            print(f"保存 CSV 失败: {e}")


if __name__ == "__main__":
    main()