# Domain Methods & Reference Knowledge

Authoritative methods used by the automation-grid-game-design harness for
Automation-Game Grid Logistics & Throughput Optimization. This file grounds
the agent (RAG / prompt base) so every numeric claim is method-backed.

## 1. Recipe-graph ratio solving (reverse demand propagation)

For a target output rate `R` (items/sec) of item `i` crafted by recipe `r`:
```
per_machine_rate = (out_qty_i / craft_time) * craft_speed * (1 + productivity_bonus)
machine_count    = R / per_machine_rate
machine_count_rounded = ceil(machine_count)
utilization      = machine_count / machine_count_rounded
```
Each stage's input demand `(qty / craft_time) * count_rounded * eff_speed`
becomes the child stage's target rate. Exact integer ratios use the LCM
across stages.

## 2. Throughput & bottlenecks (Little's Law)

`L = lambda * W` - expected items in system = throughput * mean residence time.
The bottleneck is the stage with the highest utilization; its capacity bounds
the whole line: `throughput_cap = stage_rate / utilization`. Recommend a
buffer of `>= L` items at the bottleneck to absorb jitter.

Reference: Little, J. D. C. (1961), Oper. Res. 9(3), `10.1287/opre.9.3.383`.

## 3. Belt / logistics balancing

Belt throughput (items/sec):
- Factorio: yellow 15, red 30, blue 45.
- Satisfactory Mk1..Mk6: 1, 2, 4.5, 8, 13, 20.

`belts_required = ceil(rate / belt_capacity)`. Throughput-balanced n:n
balancers exist for power-of-two n and use `n-1` splitters (splitter tree).
Non-PoT n:m uses the nearest PoT balancer + lane merge/split; add lane
balancers when exact throughput is required.

## 4. Power / pollution / space tradeoffs

`power_total = sum(machine_power * count)`, `pollution_total = sum(pollution * count)`.
Module effects: speed modules raise throughput AND power; productivity modules
raise output AND pollution; efficiency modules cut power. Spatial footprint
scales with machine count + belt length - prefer compact modular blueprints at
the bottleneck.

## 5. Flow-shop scheduling (academic grounding)

Production chains are flow-shop scheduling problems. Reference review:
Framinan et al. (2004), Eur. J. Oper. Res., `10.1016/S0377-2217(03)00358-8`.

## 6. Evidence hierarchy (this domain)

- Tier 1: Systematic review / meta-analysis / official standard
- Tier 2: Peer-reviewed academic paper / RCT
- Tier 3: Industry report / professional association guideline
- Tier 4: News / blog / vendor material