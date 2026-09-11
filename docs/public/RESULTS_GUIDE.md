# Public results interpretation

Model results are separated into summary values and provenance. `source_runs` identifies canonical run IDs without distributing raw traces, environment files, or machine-specific paths.

- **Performance:** PP/TG microbenchmark
- **Server-performance:** aggregate and per-request throughput, latency, and failure rate by concurrency
- **Knowledge:** total, correct, accuracy, and category summaries
- **Coding:** passed, pass rate, and failure type
- **Tool-call:** selection, argument, and execution metrics
- **Agent-single:** pass rate, steps, and tool calls
- **Agent-multi:** pass rate, handoffs, role participation, steps, and tool calls

Results from different MTP conditions, `llama.cpp` commits, hardware, or evaluator versions must not be directly combined or treated as a single ranking without stating those differences.
