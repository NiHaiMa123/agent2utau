import numpy as np

fcpe = np.load("runs/production/zuihouyiye-from-scratch-20261027/observation/fcpe.npz")
times, f0 = fcpe["times"], fcpe["f0_hz"]
cents = np.where(f0 > 50.0, 6900.0 + 1200.0 * np.log2(np.maximum(f0, 1e-6) / 440.0), np.nan)

def print_pitch(t0, t1, label):
    mask = (times >= t0) & (times <= t1) & np.isfinite(cents)
    sub_t = times[mask]
    sub_c = cents[mask]
    print(f"=== {label} [{t0:.2f}s - {t1:.2f}s] ===")
    if len(sub_c) == 0:
        print("  No voiced pitch")
        return
    print(f"  Min: {np.min(sub_c):.1f}c, Max: {np.max(sub_c):.1f}c, Mean: {np.mean(sub_c):.1f}c, Span: {np.ptp(sub_c):.1f}c")
    for t, c in zip(sub_t[::2], sub_c[::2]):
        print(f"    {t:6.3f}s: {c:6.1f}c ({c/100.0:.2f})")

print_pitch(75.15, 76.40, "Part 10 '身体里面' (75.15-76.40s)")
print_pitch(81.50, 83.00, "Part 12 '那颗没落' (81.50-83.00s)")
