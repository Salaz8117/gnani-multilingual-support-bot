"""Benchmark script for measuring pipeline performance."""

import asyncio
import time
import statistics
from typing import List, Dict, Any
import json

from app.core.config import get_settings
from app.pipelines.support_bot import SupportBotPipeline
from app.models.schemas import SupportBotRequest
from app.models.enums import Language


async def run_benchmark(
    num_requests: int = 10,
    audio_base64: str = None,
    language: Language = Language.HINGLISH,
) -> Dict[str, Any]:
    """Run benchmark on the pipeline."""
    
    if audio_base64 is None:
        # Generate dummy base64 audio (1 second of silence at 16kHz)
        import base64
        import numpy as np
        import soundfile as sf
        import io
        
        silence = np.zeros(16000, dtype=np.float32)
        buffer = io.BytesIO()
        sf.write(buffer, silence, 16000, format='WAV')
        audio_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    
    pipeline = SupportBotPipeline()
    latencies = {
        "total": [],
        "prisma": [],
        "evon": [],
        "timbre": [],
    }
    errors = 0
    
    print(f"Running benchmark with {num_requests} requests...")
    print(f"Language: {language.value}")
    print("-" * 50)
    
    for i in range(num_requests):
        request = SupportBotRequest(
            audio_base64=audio_base64,
            audio_format="wav",
            language=language,
            session_id=f"bench-{i}",
        )
        
        try:
            start = time.perf_counter()
            response = await pipeline.process(request)
            elapsed = (time.perf_counter() - start) * 1000
            
            latencies["total"].append(response.total_latency_ms)
            latencies["prisma"].append(response.latency_breakdown.get("prisma_ms", 0))
            latencies["evon"].append(response.latency_breakdown.get("evon_ms", 0))
            latencies["timbre"].append(response.latency_breakdown.get("timbre_ms", 0))
            
            print(f"Request {i+1}/{num_requests}: {response.total_latency_ms}ms total "
                  f"(Prisma: {response.latency_breakdown.get('prisma_ms', 0)}ms, "
                  f"Evon: {response.latency_breakdown.get('evon_ms', 0)}ms, "
                  f"Timbre: {response.latency_breakdown.get('timbre_ms', 0)}ms)")
            
        except Exception as e:
            errors += 1
            print(f"Request {i+1}/{num_requests}: FAILED - {e}")
        
        # Small delay between requests
        await asyncio.sleep(0.1)
    
    await pipeline.close()
    
    # Calculate statistics
    results = {
        "num_requests": num_requests,
        "successful": num_requests - errors,
        "errors": errors,
        "latencies_ms": {},
    }
    
    for stage, values in latencies.items():
        if values:
            results["latencies_ms"][stage] = {
                "mean": round(statistics.mean(values), 2),
                "median": round(statistics.median(values), 2),
                "stdev": round(statistics.stdev(values), 2) if len(values) > 1 else 0,
                "min": round(min(values), 2),
                "max": round(max(values), 2),
                "p50": round(statistics.median(values), 2),
                "p95": round(sorted(values)[int(len(values) * 0.95)], 2),
                "p99": round(sorted(values)[int(len(values) * 0.99)], 2),
            }
    
    return results


def print_results(results: Dict[str, Any]):
    """Print benchmark results in a nice format."""
    print("\n" + "=" * 60)
    print("BENCHMARK RESULTS")
    print("=" * 60)
    print(f"Total Requests: {results['num_requests']}")
    print(f"Successful: {results['successful']}")
    print(f"Errors: {results['errors']}")
    print()
    
    for stage, stats in results["latencies_ms"].items():
        print(f"{stage.upper()} Latency:")
        print(f"  Mean:   {stats['mean']}ms")
        print(f"  Median: {stats['median']}ms")
        print(f"  StdDev: {stats['stdev']}ms")
        print(f"  Min:    {stats['min']}ms")
        print(f"  Max:    {stats['max']}ms")
        print(f"  P50:    {stats['p50']}ms")
        print(f"  P95:    {stats['p95']}ms")
        print(f"  P99:    {stats['p99']}ms")
        print()


async def main():
    """Main benchmark entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Benchmark Gnani Support Bot Pipeline")
    parser.add_argument("-n", "--num-requests", type=int, default=10, help="Number of requests")
    parser.add_argument("-l", "--language", type=str, default="hi-en-IN", help="Language code")
    parser.add_argument("-o", "--output", type=str, help="Output JSON file")
    parser.add_argument("--audio-file", type=str, help="Path to audio file for testing")
    
    args = parser.parse_args()
    
    # Load audio if provided
    audio_base64 = None
    if args.audio_file:
        import base64
        with open(args.audio_file, "rb") as f:
            audio_base64 = base64.b64encode(f.read()).decode("utf-8")
    
    language = Language(args.language)
    
    results = await run_benchmark(
        num_requests=args.num_requests,
        audio_base64=audio_base64,
        language=language,
    )
    
    print_results(results)
    
    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"Results saved to {args.output}")


if __name__ == "__main__":
    asyncio.run(main())