"""
FlexiGrid optimizer.
Day-ahead scheduling of consecutive-block flexible devices to MINIMIZE the feeder peak
(net of solar). Uses PuLP/CBC MILP when available, otherwise a deterministic greedy.
"""
from __future__ import annotations


def optimize_schedule(devices, base_blocks, solar_blocks, start_block_floor=0):
    """
    devices: list of dicts {id, power_kw, n_blocks, win:(a,b)}  (window in 30-min block idx, b exclusive)
    base_blocks / solar_blocks: list[48] float kW
    returns {device_id: start_block}
    """
    devs = []
    for d in devices:
        a = max(d["win"][0], start_block_floor)
        b = max(a + d["n_blocks"], d["win"][1])
        devs.append({**d, "win": (a, b)})

    try:
        return _milp(devs, base_blocks, solar_blocks)
    except Exception:
        return _greedy(devs, base_blocks, solar_blocks)


def _milp(devs, base, solar):
    import pulp as pl

    B = len(base)
    starts = {}   # device -> list of feasible start indices
    y = {}
    prob = pl.LpProblem("flexigrid", pl.LpMinimize)

    for d in devs:
        a, b = d["win"]
        feas = [s for s in range(a, max(a + 1, b - d["n_blocks"] + 1))]
        if not feas:
            feas = [a]
        starts[d["id"]] = feas
        for s in feas:
            y[(d["id"], s)] = pl.LpVariable(f"y_{d['id']}_{s}", cat="Binary")

    for d in devs:
        prob += pl.lpSum(y[(d["id"], s)] for s in starts[d["id"]]) == 1

    P = pl.LpVariable("P", lowBound=0)
    prob += P + 0.02 * pl.lpSum(
        y[(d["id"], s)] * s for d in devs for s in starts[d["id"]]
    )  # tiny tie-break: prefer earlier

    for blk in range(B):
        load_here = base[blk] - solar[blk]
        contrib = []
        for d in devs:
            for s in starts[d["id"]]:
                if s <= blk < s + d["n_blocks"]:
                    contrib.append(d["power_kw"] * y[(d["id"], s)])
        prob += load_here + pl.lpSum(contrib) <= P

    prob.solve(pl.PULP_CBC_CMD(msg=0, timeLimit=15))
    out = {}
    for d in devs:
        best, bestv = starts[d["id"]][0], -1
        for s in starts[d["id"]]:
            v = pl.value(y[(d["id"], s)]) or 0
            if v > bestv:
                best, bestv = s, v
        out[d["id"]] = best
    return out


def _greedy(devs, base, solar):
    order = sorted(devs, key=lambda d: -(d["power_kw"] * d["n_blocks"]))
    agg = [base[i] - solar[i] for i in range(len(base))]
    out = {}
    for d in order:
        a, b = d["win"]
        best_s, best_cost = a, float("inf")
        for s in range(a, max(a + 1, b - d["n_blocks"] + 1)):
            window = agg[s:s + d["n_blocks"]]
            if len(window) < d["n_blocks"]:
                continue
            cost = max(w + d["power_kw"] for w in window)
            if cost < best_cost:
                best_cost, best_s = cost, s
        out[d["id"]] = best_s
        for i in range(best_s, best_s + d["n_blocks"]):
            agg[i] += d["power_kw"]
    return out


def place_remaining(dev_spec, need_blocks, now_block, agg_after_solar):
    """Real-time re-placement of remaining blocks into cheapest future slots of the window.
    dev_spec: {win:(a,b)} ; agg_after_solar: list[48] current aggregate curve.
    Returns list of block indices."""
    a, b = dev_spec["win"]
    a = max(a, now_block)
    if a >= b or need_blocks <= 0:
        return []
    scored = sorted(range(a, b), key=lambda i: agg_after_solar[i])
    chosen = sorted(scored[:need_blocks])
    return [i for i in chosen if i < b]
