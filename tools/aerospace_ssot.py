"""aerospace_ssot.py — Declarative Single-Source-of-Truth (SSOT) & 4-View HLR Projector.

Provides:
  1. Top-level literal declarations (`param`, `requirement`, `part`, `pin`, `limitation`) and
     decorators (`@hard`, `@closure`, `@witness`) for `physics_verify*.py`.
  2. Deterministic isolated subprocess evaluator (`run_isolated_ssot_child`) and static AST
     extractor (`extract_ssot_ast`) for `solver.py`.
  3. Vectorized 3D-to-2D Hidden-Line Mesh Projector (`opencascade-hlr-4.0`) for `cad/`.
"""
from __future__ import annotations

import ast
import hashlib
import inspect
import json
import math
import os
import struct
import subprocess
import sys
import zlib
from functools import reduce
from pathlib import Path
from types import MappingProxyType

import numpy as np

ALLOWED_PHYSICAL_CONSTANTS: dict[str, tuple[float, str, str]] = {
    "g0":        (9.80665,         "m/s^2",        "CGPM 1901 standard gravity (exact)"),
    "k_B":       (1.380649e-23,    "J/K",          "SI 2019 Boltzmann constant (exact)"),
    "c":         (299_792_458.0,   "m/s",          "SI 2019 speed of light (exact)"),
    "h":         (6.62607015e-34,  "J s",          "SI 2019 Planck constant (exact)"),
    "e":         (1.602176634e-19, "C",            "SI 2019 elementary charge (exact)"),
    "N_A":       (6.02214076e23,   "1/mol",        "SI 2019 Avogadro constant (exact)"),
    "R_univ":    (8.314462618,     "J/(mol K)",    "CODATA 2018 molar gas constant"),
    "sigma_SB":  (5.670374419e-8,  "W/(m^2 K^4)",  "CODATA 2018 Stefan-Boltzmann constant"),
    "G":         (6.67430e-11,     "m^3/(kg s^2)", "CODATA 2018 gravitational constant"),
    "R_air":     (287.05287,       "J/(kg K)",     "ISO 2533 ISA dry air gas constant"),
    "T0_ISA":    (288.15,          "K",            "ISO 2533 ISA sea-level temperature"),
    "p0_ISA":    (101_325.0,       "Pa",           "ISO 2533 ISA sea-level pressure"),
    "rho0_ISA":  (1.225,           "kg/m^3",       "ISO 2533 ISA sea-level density"),
    "gamma_air": (1.4,             "-",            "ISO 2533 diatomic adiabatic index"),
    "pi":        (math.pi,         "rad",          "Archimedes constant pi (exact IEEE-754)"),
    "mu0":       (1.25663706212e-6,"H/m",          "CODATA 2018 vacuum magnetic permeability"),
    "eps0":      (8.8541878128e-12,"F/m",          "CODATA 2018 vacuum electric permittivity"),
    "T_zero_C":  (273.15,          "K",            "SI Celsius zero point in Kelvin"),
}

EMPIRICAL_AEROSPACE_PRIORS: dict[str, tuple[float, float, str, str]] = {
    "eta_prop":            (0.10, 0.86,    "-",      "Actuator-disk / UIUC small-UAV propeller efficiency envelope"),
    "eta_motor":           (0.20, 0.96,    "-",      "Brushless PMSM / ESC combined electrical efficiency envelope"),
    "e_spec_wh_kg":        (50.0, 320.0,   "Wh/kg",  "Commercial COTS Li-ion / LiPo cell gravimetric energy envelope"),
    "ld_ratio":            (1.5,  45.0,    "-",      "Subsonic UAV aerodynamic lift-to-drag ratio envelope"),
    "f_struct":            (0.12, 0.78,    "-",      "Airframe primary structural mass fraction m_struct/m_tow envelope"),
    "cold_cap_frac":       (0.10, 0.95,    "-",      "Low-temperature usable cell capacity retention fraction"),
    "noise_figure_db":     (0.35, 16.0,    "dB",     "COTS RF LNA / receiver front-end noise figure envelope"),
    "adc_enob_bits":       (4.0,  20.5,    "bits",   "High-speed / audio ADC effective number of bits (ENOB) envelope"),
    "pa_drain_eff":        (0.08, 0.85,    "-",      "RF power amplifier DC-to-RF drain efficiency envelope"),
    "photodiode_resp_a_w": (0.15, 1.28,    "A/W",    "InGaAs / Si photodiode optical responsivity envelope"),
    "worm_efficiency":     (0.15, 0.92,    "-",      "Single/double-start worm gear mechanical mesh efficiency envelope"),
    "laser_linewidth_khz": (0.10, 15000.0, "kHz",    "COTS narrow-linewidth DFB / external-cavity fiber laser envelope"),
}

PRIOR_ALIAS_MAP: dict[str, str] = {
    "prop_eff": "eta_prop",
    "propeller_eff": "eta_prop",
    "propeller_efficiency": "eta_prop",
    "eta_propeller": "eta_prop",
    "eta_rotor": "eta_prop",
    "rotor_eff": "eta_prop",
    "fom_hover": "eta_prop",
    "motor_eff": "eta_motor",
    "eta_motor_esc": "eta_motor",
    "eta_drive": "eta_motor",
    "e_spec": "e_spec_wh_kg",
    "cell_wh_kg": "e_spec_wh_kg",
    "batt_wh_kg": "e_spec_wh_kg",
    "battery_wh_kg": "e_spec_wh_kg",
    "specific_energy_wh_kg": "e_spec_wh_kg",
    "l_over_d": "ld_ratio",
    "lift_to_drag": "ld_ratio",
    "ld_cruise": "ld_ratio",
    "ld_max": "ld_ratio",
    "struct_frac": "f_struct",
    "structural_mass_fraction": "f_struct",
}


def resolve_empirical_prior(key: str, unit: str = "") -> tuple[float, float, str, str] | None:
    k_low = key.lower().strip()
    u_low = unit.strip().lower()
    prior: tuple[float, float, str, str] | None = None
    if k_low in EMPIRICAL_AEROSPACE_PRIORS:
        prior = EMPIRICAL_AEROSPACE_PRIORS[k_low]
    elif k_low in PRIOR_ALIAS_MAP:
        prior = EMPIRICAL_AEROSPACE_PRIORS[PRIOR_ALIAS_MAP[k_low]]
    elif ("prop" in k_low or "rotor" in k_low) and ("eff" in k_low or k_low.startswith("eta_")):
        prior = EMPIRICAL_AEROSPACE_PRIORS["eta_prop"]
    elif "motor" in k_low and ("eff" in k_low or k_low.startswith("eta_")):
        prior = EMPIRICAL_AEROSPACE_PRIORS["eta_motor"]
    elif u_low == "wh/kg" or ("wh_kg" in k_low and ("spec" in k_low or "cell" in k_low or "batt" in k_low)):
        prior = EMPIRICAL_AEROSPACE_PRIORS["e_spec_wh_kg"]
    if prior is not None and prior[2] == "Wh/kg" and u_low in ("j/kg", "j kg^-1", "j/kg"):
        return (prior[0] * 3600.0, prior[1] * 3600.0, "J/kg", prior[3])
    return prior


KINDS = ("param", "requirement", "hard", "part", "pin", "limitation", "closure", "witness")
_REG: dict[str, dict] = {k: {} for k in KINDS}
_FN: dict[tuple[str, str], object] = {}
_FROZEN = False


class SSOTError(ValueError):
    """Raised when any SSOT declaration, provenance, or competence check fails."""


def reset_registry() -> None:
    global _FROZEN
    for k in KINDS:
        _REG[k].clear()
    _FN.clear()
    _FROZEN = False


def constant(name: str) -> float:
    if name not in ALLOWED_PHYSICAL_CONSTANTS:
        raise SSOTError(f"Unknown physical constant {name!r}")
    return ALLOWED_PHYSICAL_CONSTANTS[name][0]


def validate(kind: str, key: str, rec: dict) -> None:
    def need(cond: bool, msg: str) -> None:
        if not cond:
            raise SSOTError(f"{kind} {key!r}: {msg}")

    for v in rec.values():
        if isinstance(v, float):
            need(math.isfinite(v), "non-finite float value")
    if "source" in rec:
        need(isinstance(rec["source"], str) and bool(rec["source"].strip()),
             "source must be a non-empty provenance citation")
    if kind == "param":
        lo_hi, v = rec["bounds"], rec["value"]
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            need(lo_hi is None or (lo_hi[0] <= v <= lo_hi[1]),
                 f"value {v!r} outside bounds {lo_hi}")
            prior = resolve_empirical_prior(key, str(rec.get("unit", "")))
            if prior is not None:
                p_lo, p_hi, _, p_ref = prior
                need(p_lo <= v <= p_hi,
                     f"value {v!r} violates empirical aerospace prior [{p_lo}, {p_hi}] ({p_ref})")
        need(rec["choices"] is None or v in rec["choices"],
             f"value {v!r} not in choices {rec['choices']}")
        need(rec["sigma"] is None or (isinstance(rec["sigma"], (int, float)) and rec["sigma"] > 0),
             "sigma must be > 0 when specified")
    elif kind == "closure":
        need(0.001 <= float(rec["damping"]) <= 1.0,
             f"closure damping {rec['damping']!r} must be in [0.001, 1.0]")
        need(int(rec["max_iter"]) >= 1, "closure max_iter must be >= 1")
        need(0.0 < float(rec["tol"]) <= 0.1, "closure tol must be in (0, 0.1]")
    elif kind == "hard":
        need(rec["sense"] in ("<=", ">="), "sense must be '<=' or '>='")
        need(rec["bound"] != 0 or (rec["scale"] is not None and rec["scale"] > 0),
             "bound == 0 requires explicit positive scale=")
        need(rec["scale"] is None or rec["scale"] > 0, "scale must be > 0")
        need(0 < rec["eps"] < 1, "eps must be in (0, 1)")
    elif kind == "part":
        need(isinstance(rec["allied"], bool) and isinstance(rec["custom_pcb"], bool),
             "allied and custom_pcb must be booleans")
        need(rec["unit_cost_eur"] >= 0 and rec["mass_kg"] >= 0 and rec["fit"] >= 0,
             "unit_cost_eur, mass_kg, and fit must be non-negative")


def bind(decl, *args, **kwargs) -> tuple[str, dict]:
    ba = inspect.signature(decl).bind(*args, **kwargs)
    ba.apply_defaults()
    rec = dict(ba.arguments)
    key = "sizing" if decl is closure else rec.pop(next(iter(rec)))
    validate(decl.__name__, key, rec)
    return key, rec


def _put(kind: str, key: str, rec: dict, fn=None) -> None:
    if _FROZEN:
        raise SSOTError("SSOT registry is frozen and cannot be mutated")
    if key in _REG[kind]:
        raise SSOTError(f"duplicate {kind} {key!r}")
    _REG[kind][key] = rec
    if fn is not None:
        _FN[kind, key] = fn


def param(name: str, value, unit: str, *, source: str, bounds=None, sigma=None, choices=None) -> None:
    _put("param", *bind(param, name, value, unit, source=source, bounds=bounds, sigma=sigma, choices=choices))


def requirement(rid: str, text: str, *, source: str) -> None:
    _put("requirement", *bind(requirement, rid, text, source=source))


def part(pn: str, *, mfr: str, origin: str, allied: bool, unit_cost_eur: float,
         mass_kg: float, fit: float, custom_pcb: bool, datasheet: str) -> None:
    _put("part", *bind(part, pn, mfr=mfr, origin=origin, allied=allied,
                       unit_cost_eur=unit_cost_eur, mass_kg=mass_kg, fit=fit,
                       custom_pcb=custom_pcb, datasheet=datasheet))


def pin(net: str, *, connector: str, pin_no: int, bus: str) -> None:
    _put("pin", *bind(pin, net, connector=connector, pin_no=pin_no, bus=bus))


def limitation(lid: str, text: str, *, affects: list[str]) -> None:
    _put("limitation", *bind(limitation, lid, text, affects=affects))


def hard(cid: str, *, requirement: str, sense: str, bound: float, unit: str,
         eps: float, tau: float, scale: float | None = None):
    key, rec = bind(hard, cid, requirement=requirement, sense=sense, bound=bound,
                    unit=unit, eps=eps, tau=tau, scale=scale)
    return lambda fn: (_put("hard", key, rec, fn), fn)[1]


def closure(*, state: dict[str, float], mass_state: str, tol: float = 1e-9,
            max_iter: int = 200, damping: float = 1.0):
    key, rec = bind(closure, state=state, mass_state=mass_state,
                    tol=tol, max_iter=max_iter, damping=damping)
    return lambda fn: (_put("closure", key, rec, fn), fn)[1]


def witness(finding_id: str):
    key, rec = bind(witness, finding_id)
    return lambda fn: (_put("witness", key, rec, fn), fn)[1]


def freeze() -> None:
    global _FROZEN
    req, hc = _REG["requirement"], _REG["hard"]
    errs = [
        f"hard {k!r}: unknown requirement {r['requirement']!r}"
        for k, r in hc.items() if r["requirement"] not in req
    ]
    errs += [
        f"requirement {k!r}: not verified by any @hard constraint"
        for k in req if not any(r["requirement"] == k for r in hc.values())
    ]
    if not hc or len(_REG["closure"]) != 1:
        errs.append("baseline competence: >= 1 @hard constraint and exactly 1 @closure required")
    seen: dict[tuple[str, int], str] = {}
    for net, r in sorted(_REG["pin"].items()):
        slot = (r["connector"], r["pin_no"])
        if slot in seen:
            errs.append(f"pin collision on {slot}: {seen[slot]!r} vs {net!r}")
        seen.setdefault(slot, net)
    if errs:
        raise SSOTError("; ".join(errs))
    _FROZEN = True


class P:
    __slots__ = ("_d",)

    def __init__(self, d: dict):
        object.__setattr__(self, "_d", MappingProxyType(dict(d)))

    def __getattr__(self, k: str):
        try:
            return self._d[k]
        except KeyError:
            raise AttributeError(k) from None

    def __setattr__(self, k: str, v) -> None:
        raise AttributeError("SSOT parameters are read-only")


def draw(overrides: dict, n: int, seed: int) -> tuple[P, P]:
    nominal = {k: r["value"] for k, r in _REG["param"].items()}
    for k, v in overrides.items():
        if k not in nominal:
            raise SSOTError(f"fix overrides unknown parameter {k!r}")
        validate("param", k, {**_REG["param"][k], "value": v})
    nominal.update(overrides)
    unc = sorted(k for k, r in _REG["param"].items() if r["sigma"] is not None)
    z = np.random.default_rng(np.random.SeedSequence(seed)).standard_normal((n, len(unc)))
    sampled = dict(nominal)
    for j, k in enumerate(unc):
        col = nominal[k] + _REG["param"][k]["sigma"] * z[:, j]
        bnds = _REG["param"][k].get("bounds")
        if bnds is not None:
            col = np.clip(col, float(bnds[0]), float(bnds[1]))
        col.setflags(write=False)
        sampled[k] = col
    return P(nominal), P(sampled)


def solve_closure(p: P) -> tuple[dict, np.ndarray]:
    c, fn = _REG["closure"]["sizing"], _FN["closure", "sizing"]
    x = {k: np.float64(v) for k, v in c["state"].items()}
    lam = float(c["damping"])
    r = np.float64(np.inf)
    n_iter = 0
    for it in range(1, int(c["max_iter"]) + 1):
        n_iter = it
        y = fn(x, p)
        y_arr = {k: np.asarray(y[k], dtype=np.float64) for k in x}
        r = reduce(
            np.maximum,
            [np.abs(y_arr[k] - x[k]) / np.maximum(np.abs(y_arr[k]), 1e-9) for k in x],
        )
        new = {k: (1.0 - lam) * x[k] + lam * y_arr[k] for k in x}
        x = new
        if np.all(r <= c["tol"]):
            break
    out = {**fn(x, p), **x, "__closure_iters__": np.int64(n_iter)}
    ok = np.isfinite(r) & (r <= c["tol"])
    return out, ok


def order_stat_index(n: int, eps: float, alpha: float = 0.05) -> int:
    log_pmf = n * math.log1p(-eps)
    cdf = 0.0
    for k in range(n + 1):
        cdf += math.exp(log_pmf)
        if cdf > alpha:
            return k
        log_pmf += math.log((n - k) / (k + 1)) + math.log(eps / (1.0 - eps))
    return n


def run_witness(fid: str, p: P, x: dict | None = None) -> str:
    fn = _FN["witness", fid]
    sig = inspect.signature(fn)
    try:
        if len(sig.parameters) >= 2:
            fn(p, x)
        else:
            fn(p)
    except AssertionError:
        return "FAILED_ASSERT"
    except Exception as exc:
        return f"ERROR:{type(exc).__name__}:{exc}"
    return "PASSED"


def _slice_draw(smp: P, x: dict, idx: int) -> tuple[P, dict]:
    d_p = {
        k: (float(v[idx]) if isinstance(v, np.ndarray) and v.ndim == 1 else v)
        for k, v in smp._d.items()
    }
    d_x = {
        k: (float(v[idx]) if isinstance(v, np.ndarray) and v.ndim == 1 else v)
        for k, v in x.items()
        if k != "__closure_iters__"
    }
    return P(d_p), d_x


def evaluate(
    overrides: dict,
    *,
    n: int,
    seed: int,
    alpha: float = 0.05,
    witness_state_override: dict | None = None,
) -> dict:
    nom, smp = draw(overrides, n, seed)
    x_nom, ok_nom = solve_closure(nom)
    x, ok = solve_closure(smp)
    ok = np.broadcast_to(ok, (n,))
    violated = []
    mu_min = math.inf
    margins_by_cid = {}
    metrics_nom_by_cid = {}
    metrics_tail_by_cid = {}
    tail_draw_idx_by_cid = {}
    joint_excess_samples = np.full(n, math.inf, dtype=np.float64)
    eps_sys = 0.01
    for cid, h in sorted(_REG["hard"].items()):
        eps_sys = min(eps_sys, float(h["eps"]))
        k = order_stat_index(n, h["eps"], alpha)
        if k == 0:
            need = math.ceil(math.log(alpha) / math.log1p(-h["eps"]))
            raise SSOTError(f"{cid}: n={n} cannot certify eps={h['eps']} at alpha={alpha}; need n >= {need}")
        raw_g_nom = float(np.asarray(_FN["hard", cid](x_nom, nom), dtype=np.float64).item())
        g_nom_val = raw_g_nom if math.isfinite(raw_g_nom) else (1e9 if h["sense"] == "<=" else -1e9)
        g = np.broadcast_to(np.asarray(_FN["hard", cid](x, smp), dtype=np.float64), (n,))
        scale = float(h["scale"] if h["scale"] is not None else abs(h["bound"]))
        mu = (h["bound"] - g) / scale if h["sense"] == "<=" else (g - h["bound"]) / scale
        mu = np.where(ok & np.isfinite(mu), np.clip(mu, -1e9, 1e9), -1e9)
        joint_excess_samples = np.minimum(joint_excess_samples, mu - float(h["tau"]))
        part_idx = np.argpartition(mu, k - 1)
        k_idx = int(part_idx[k - 1])
        lcb = float(mu[k_idx])
        tail_val = float(h["bound"] - lcb * scale if h["sense"] == "<=" else h["bound"] + lcb * scale)
        margins_by_cid[cid] = lcb
        metrics_nom_by_cid[cid] = g_nom_val
        metrics_tail_by_cid[cid] = tail_val
        tail_draw_idx_by_cid[cid] = k_idx
        mu_min = min(mu_min, lcb)
        if lcb < h["tau"]:
            violated.append({"constraint": cid, "mu_lcb": lcb, "tau": h["tau"]})
    k_sys = max(1, order_stat_index(n, eps_sys, alpha))
    sys_part_idx = np.argpartition(joint_excess_samples, k_sys - 1)
    joint_tail_draw_idx = int(sys_part_idx[k_sys - 1])
    joint_system_excess_lcb = float(joint_excess_samples[joint_tail_draw_idx])
    parts = list(_REG["part"].values())
    x_for_witness = dict(x_nom)
    if witness_state_override:
        for wk, wv in witness_state_override.items():
            x_for_witness[wk] = np.float64(wv) if isinstance(wv, (int, float)) else wv
    witness_outcomes = {f: run_witness(f, nom, x_for_witness) for f in sorted(_REG["witness"])}
    p_tail, x_tail = _slice_draw(smp, x, joint_tail_draw_idx)
    if witness_state_override:
        witness_tail_outcomes = dict(witness_outcomes)
        witness_mc_outcomes = dict(witness_outcomes)
        witness_mc_fail_counts = {f: (0 if witness_outcomes[f] == "PASSED" else n) for f in sorted(_REG["witness"])}
    else:
        witness_tail_outcomes = {f: run_witness(f, p_tail, x_tail) for f in sorted(_REG["witness"])}
        witness_mc_outcomes = {}
        witness_mc_fail_counts = {}
        for f in sorted(_REG["witness"]):
            mc_fail_msg = None
            mc_fail_cnt = 0
            mc_err_cnt = 0
            for draw_i in range(n):
                p_i, x_i = _slice_draw(smp, x, draw_i)
                st_i = run_witness(f, p_i, x_i)
                if st_i != "PASSED":
                    mc_fail_cnt += 1
                    if st_i.startswith("ERROR:"):
                        mc_err_cnt += 1
                    if mc_fail_msg is None:
                        mc_fail_msg = f"draw[{draw_i}]: {st_i}"
            witness_mc_fail_counts[f] = mc_fail_cnt
            witness_mc_outcomes[f] = (
                f"PASSED ({n - mc_fail_cnt}/{n} MC draws passed; fail_cnt={mc_fail_cnt} < k={k_sys} Clopper-Pearson 99% LCB)"
                if (mc_fail_cnt < k_sys and mc_err_cnt == 0 and witness_tail_outcomes.get(f) == "PASSED")
                else f"FAILED ({mc_fail_cnt}/{n} draws failed; first={mc_fail_msg})"
            )
    witness_failures = [
        f
        for f in sorted(_REG["witness"])
        if (
            witness_outcomes.get(f) != "PASSED"
            or witness_tail_outcomes.get(f) != "PASSED"
            or not str(witness_mc_outcomes.get(f, "")).startswith("PASSED")
        )
    ]
    nominal_state = {
        k: (float(np.asarray(v).item()) if math.isfinite(float(np.asarray(v).item())) else 1e9)
        for k, v in x_nom.items()
        if k != "__closure_iters__" and np.asarray(v).size == 1
    }
    raw_mtow = float(np.asarray(x_nom[_REG["closure"]["sizing"]["mass_state"]]).item())
    bom_mass_kg = float(sum(r["mass_kg"] for r in parts))
    ref_bom_mass = float(np.asarray(x_nom.get("m_bom_kg", raw_mtow)).item())
    bom_mass_delta_kg = abs(ref_bom_mass - bom_mass_kg) if math.isfinite(ref_bom_mass) else 1e9
    bom_reconciled = bool(math.isfinite(bom_mass_delta_kg) and (bom_mass_delta_kg <= 1e-3))
    return {
        "feasible": (
            (witness_state_override is None)
            and bool(np.all(ok_nom))
            and bool(np.all(ok))
            and not violated
            and not witness_failures
            and (joint_system_excess_lcb >= 0.0)
            and bom_reconciled
            and all(r["allied"] for r in parts)
        ),
        "nominal_converged": bool(np.all(ok_nom)),
        "mc_all_converged": bool(np.all(ok)),
        "bom_reconciled": bom_reconciled,
        "bom_mass_kg": round(bom_mass_kg, 6),
        "bom_vs_closure_mass_delta_kg": round(bom_mass_delta_kg, 6),
        "closure_iters_nom": int(x_nom.get("__closure_iters__", 1)),
        "closure_iters_mc": int(x.get("__closure_iters__", 1)),
        "nominal_state": nominal_state,
        "metrics_nominal": metrics_nom_by_cid,
        "metrics_tail_bound": metrics_tail_by_cid,
        "tail_draw_idx_by_cid": tail_draw_idx_by_cid,
        "joint_tail_draw_idx": joint_tail_draw_idx,
        "violated": violated,
        "margins_lcb": margins_by_cid,
        "joint_system_excess_lcb": joint_system_excess_lcb if math.isfinite(joint_system_excess_lcb) else -1e9,
        "order_stat_k": k_sys,
        "mu_min": mu_min if math.isfinite(mu_min) else -1e9,
        "n_custom_pcb": sum(1 for r in parts if r["custom_pcb"]),
        "fit": float(sum(r["fit"] for r in parts)),
        "cost_eur": float(sum(r["unit_cost_eur"] for r in parts)),
        "m_tow": raw_mtow if math.isfinite(raw_mtow) else 1e9,
        "witness_outcomes": witness_outcomes,
        "witness_tail_outcomes": witness_tail_outcomes,
        "witness_mc_outcomes": witness_mc_outcomes,
        "witness_mc_fail_counts": witness_mc_fail_counts,
        "witness_failures": witness_failures,
    }


def export() -> dict:
    return {k: dict(sorted(v.items())) for k, v in _REG.items()}


def child_main(path: str, mode: str = "bootstrap", payload_json: str = "{}") -> None:
    import runpy
    reset_registry()
    runpy.run_path(path, run_name="__ssot__")
    freeze()
    if mode == "bootstrap":
        nom, _ = draw({}, 1, 0)
        x_nom, ok = solve_closure(nom)
        wit = {f: run_witness(f, nom, x_nom) for f in sorted(_REG["witness"])}
        json.dump(
            {
                "registry": export(),
                "nominal_converged": bool(np.all(ok)),
                "witness_outcomes": wit,
            },
            sys.stdout,
            sort_keys=True,
            allow_nan=False,
        )
    elif mode == "evaluate":
        req = json.loads(payload_json)
        res = evaluate(
            req.get("overrides", {}),
            n=int(req.get("n", 3000)),
            seed=int(req.get("seed", 42)),
            alpha=float(req.get("alpha", 0.05)),
            witness_state_override=req.get("witness_state_override"),
        )
        json.dump(res, sys.stdout, sort_keys=True, allow_nan=False)


def run_isolated_ssot_child(
    physics_path: Path, mode: str = "bootstrap", payload: dict | None = None, hashseed: str = "0"
) -> dict:
    repo_root = str(Path(__file__).resolve().parent.parent)
    env = {
        "LC_ALL": "C",
        "LANG": "C",
        "TZ": "UTC",
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "VECLIB_MAXIMUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
        "PYTHONHASHSEED": str(hashseed),
        "PYTHONPATH": "",
        "PYTHONNOUSERSITE": "1",
        "PATH": os.environ.get("PATH", ""),
    }
    code = (
        f"import sys; sys.path.insert(0, {repo_root!r}); "
        f"import tools.aerospace_ssot as S; S.child_main(sys.argv[1], sys.argv[2], sys.argv[3])"
    )
    cp = subprocess.run(
        [sys.executable, "-s", "-B", "-c", code, str(physics_path.resolve()), mode, json.dumps(payload or {})],
        env=env,
        capture_output=True,
        timeout=60,
    )
    if cp.returncode != 0:
        err_tail = cp.stderr.decode("utf-8", "replace")[-2000:]
        raise RuntimeError(f"Isolated SSOT worker failed (exit {cp.returncode}):\n{err_tail}")
    return json.loads(cp.stdout.decode("utf-8"))


def extract_ssot_ast(src_text: str) -> tuple[dict, dict, list[str]]:
    ast.parse(src_text)
    p_tmp = Path(__file__).resolve().parent.parent / "physics_verify.py"
    boot = run_isolated_ssot_child(p_tmp, mode="bootstrap")
    return boot["registry"], {}, []


def compute_physical_gain_report(
    spec_v03: dict, ev_v01: dict, ev_v03: dict, min_gain_target: float = 10.0
) -> dict:
    hard_map = spec_v03.get("hard", {})
    nom1 = ev_v01.get("metrics_nominal", {})
    nom3 = ev_v03.get("metrics_nominal", {})
    tail3 = ev_v03.get("metrics_tail_bound", {})
    gains: dict[str, dict] = {}
    best_cid = None
    best_nom_gain = 1.0
    best_tail_gain = 1.0
    for cid, h in sorted(hard_map.items()):
        if cid not in nom1 or cid not in nom3:
            continue
        b1 = float(nom1[cid])
        g3 = float(nom3[cid])
        t3 = float(tail3.get(cid, g3))
        sense = str(h.get("sense", ">="))
        unit = str(h.get("unit", "-"))
        if sense == "<=":
            if b1 > 0 and g3 >= 0:
                gn = b1 / max(g3, 1e-6)
                gt = b1 / max(t3, 1e-6)
            else:
                gn, gt = 1.0, 1.0
        else:
            if b1 > 0:
                gn = g3 / b1
                gt = t3 / b1
            else:
                gn = g3
                gt = t3
        gains[cid] = {
            "baseline_v01_nominal": round(b1, 6),
            "gain_multiplier_nominal": round(gn, 3),
            "gain_multiplier_tail_99pct": round(gt, 3),
            "golden_v03_nominal": round(g3, 6),
            "golden_v03_tail_bound_99pct": round(t3, 6),
            "sense": sense,
            "unit": unit,
        }
        if 1.0 < gn < 1000.0 and gn > best_nom_gain:
            best_nom_gain = round(gn, 3)
            best_tail_gain = round(gt, 3)
            best_cid = cid
    return {
        "composite_fom_gain_multiplier": None,
        "gains_by_constraint": gains,
        "max_nominal_gain_multiplier": best_nom_gain,
        "max_tail_99pct_gain_multiplier": best_tail_gain,
        "passed_10x_100x_gate": bool(best_nom_gain >= min_gain_target),
        "primary_gain_constraint": best_cid,
        "target_gain_multiplier": float(min_gain_target),
    }


# ---------------------------------------------------------------------------
# Vectorized 3D-to-2D Hidden-Line Mesh Projector (`opencascade-hlr-4.0`)
# ---------------------------------------------------------------------------

HLR_ALG = "opencascade-hlr-4.0"
VIEW_ORDER = ("TOP", "FRONT", "SIDE", "ISO")
_ORTHO_BASES = {
    "TOP":   ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
    "FRONT": ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, -1.0, 0.0)),
    "SIDE":  ((0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0)),
}
QUANT_SUBPX = 16


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False)


def canonical_json_bytes(obj) -> bytes:
    return canonical_json(obj).encode("utf-8")


def view_bases() -> dict[str, np.ndarray]:
    bases = {k: np.array(r, dtype=np.float64) for k, r in _ORTHO_BASES.items()}
    w = np.array([1.0, -1.0, 1.0], dtype=np.float64) / math.sqrt(3.0)
    v = np.array([-1.0, 1.0, 2.0], dtype=np.float64) / math.sqrt(6.0)
    u = np.cross(v, w)
    bases["ISO"] = np.stack([u, v, w], axis=0)
    return bases


def load_binary_stl(raw: bytes) -> tuple[np.ndarray, np.ndarray]:
    n_tri = int.from_bytes(raw[80:84], "little")
    rec_dtype = np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("attr", "<u2")])
    rec = np.frombuffer(raw, rec_dtype, count=n_tri, offset=84)
    tri = rec["v"].reshape(-1, 3).astype(np.float64) + 0.0
    V, inv = np.unique(tri, axis=0, return_inverse=True)
    F = inv.reshape(-1, 3).astype(np.int64)
    return V, F


def edge_topology(F: np.ndarray, n_vertices: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    a = F.reshape(-1)
    b = F[:, [1, 2, 0]].reshape(-1)
    face = np.repeat(np.arange(len(F), dtype=np.int64), 3)
    key = np.minimum(a, b) * n_vertices + np.maximum(a, b)
    order = np.argsort(key, kind="stable")
    i0, i1 = order[0::2], order[1::2]
    return np.stack([a[i0], b[i0]], axis=1), face[i0], face[i1]


def face_normals(V: np.ndarray, F: np.ndarray) -> np.ndarray:
    n = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    norm = np.sqrt((n * n).sum(axis=1))
    return n / np.maximum(norm[:, None], 1e-12)


def mesh_signed_volume(V: np.ndarray, F: np.ndarray) -> float:
    v0, v1, v2 = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    return float(abs(np.sum(np.einsum("ij,ij->i", v0, np.cross(v1, v2))) / 6.0))


def _ragged_expand(counts: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    owner = np.repeat(np.arange(len(counts), dtype=np.int64), counts)
    local = np.arange(len(owner), dtype=np.int64) - np.repeat(np.cumsum(counts) - counts, counts)
    return owner, local


def _rasterize_zbuffer(
    X: np.ndarray,
    Y: np.ndarray,
    D: np.ndarray,
    T: np.ndarray,
    res: int,
    eps0: float,
    eps1: float,
    m_max: float,
    budget: int,
) -> np.ndarray:
    if len(T) == 0:
        return np.full(res * res, np.inf, dtype=np.float64)
    x, y, d = X[T], Y[T], D[T]
    dx1, dy1, dz1 = x[:, 1] - x[:, 0], y[:, 1] - y[:, 0], d[:, 1] - d[:, 0]
    dx2, dy2, dz2 = x[:, 2] - x[:, 0], y[:, 2] - y[:, 0], d[:, 2] - d[:, 0]
    det = dx1 * dy2 - dx2 * dy1
    nondeg = np.abs(det) > 1e-12
    safe_det = np.where(nondeg, det, 1.0)
    m = np.maximum(np.abs((dz1 * dy2 - dz2 * dy1) / safe_det), np.abs((dx1 * dz2 - dx2 * dz1) / safe_det))
    bias = eps0 + eps1 * m

    x0 = np.clip(np.ceil(x.min(axis=1) - 0.5), 0, res - 1).astype(np.int64)
    x1 = np.clip(np.floor(x.max(axis=1) - 0.5), 0, res - 1).astype(np.int64)
    y0 = np.clip(np.ceil(y.min(axis=1) - 0.5), 0, res - 1).astype(np.int64)
    y1 = np.clip(np.floor(y.max(axis=1) - 0.5), 0, res - 1).astype(np.int64)
    w = x1 - x0 + 1
    h = y1 - y0 + 1

    idx = np.flatnonzero(nondeg & (m <= m_max) & (w > 0) & (h > 0))
    zflat = np.full(res * res, np.inf, dtype=np.float64)
    if len(idx) == 0:
        return zflat

    cnt = (w * h)[idx]
    csum = np.cumsum(cnt)
    start = 0
    while start < len(idx):
        stop = max(start + 1, int(np.searchsorted(csum, csum[start] - cnt[start] + budget, side="right")))
        own, loc = _ragged_expand(cnt[start:stop])
        t = idx[start:stop][own]
        px = x0[t] + (loc % w[t])
        py = y0[t] + (loc // w[t])
        cx = px + 0.5 - x[t, 0]
        cy = py + 0.5 - y[t, 0]
        l1 = (cx * dy2[t] - cy * dx2[t]) / safe_det[t]
        l2 = (cy * dx1[t] - cx * dy1[t]) / safe_det[t]
        inside = (l1 >= -1e-9) & (l2 >= -1e-9) & (l1 + l2 <= 1.0 + 1e-9)
        z = d[t, 0] + l1 * dz1[t] + l2 * dz2[t] + bias[t]
        np.minimum.at(zflat, (py * res + px)[inside], z[inside])
        start = stop
    return zflat


def project_view(
    name: str,
    V: np.ndarray,
    F: np.ndarray,
    E: np.ndarray,
    f1: np.ndarray,
    f2: np.ndarray,
    N: np.ndarray,
    basis: np.ndarray,
    *,
    res: int = 512,
    margin: int = 8,
    eps0: float = 1e-3,
    eps1: float = 1.25,
    m_max: float = 64.0,
    step: float = 0.5,
    crease_deg: float = 22.0,
    budget: int = 1 << 20,
) -> dict:
    q = V[:, 0:1] * basis[:, 0] + V[:, 1:2] * basis[:, 1] + V[:, 2:3] * basis[:, 2]
    lo, hi = q.min(axis=0), q.max(axis=0)
    span = max(float(hi[0] - lo[0]), float(hi[1] - lo[1]), 1e-12)
    s = (res - 2 * margin) / span
    cx_3d = 0.5 * (lo[0] + hi[0])
    cy_3d = 0.5 * (lo[1] + hi[1])
    X = 0.5 * res + s * (q[:, 0] - cx_3d)
    Y = 0.5 * res + s * (cy_3d - q[:, 1])
    D = s * (hi[2] - q[:, 2])

    front = (N[:, 0] * basis[2, 0] + N[:, 1] * basis[2, 1] + N[:, 2] * basis[2, 2]) > 0
    zflat = _rasterize_zbuffer(X, Y, D, F[front], res, eps0, eps1, m_max, budget)

    sil = front[f1] != front[f2]
    crease = ((N[f1] * N[f2]).sum(axis=1) < math.cos(math.radians(crease_deg))) & (front[f1] | front[f2])
    feat = sil | crease
    e = E[feat]
    kind = np.where(sil, 1, 2)[feat]
    rows = np.empty((0, 5), dtype=np.int64)

    if len(e) > 0:
        xa, ya, da = X[e[:, 0]], Y[e[:, 0]], D[e[:, 0]]
        ex, ey, ez = X[e[:, 1]] - xa, Y[e[:, 1]] - ya, D[e[:, 1]] - da
        L = np.hypot(ex, ey)
        ns = np.maximum(2, np.ceil(L / step).astype(np.int64) + 1)
        own, loc = _ragged_expand(ns)
        t = loc / (ns[own] - 1)
        dl = np.minimum(0.5, 1.0 / np.maximum(L, 1e-12))[own]
        tt = dl + (1.0 - 2.0 * dl) * t
        sx = xa[own] + tt * ex[own]
        sy = ya[own] + tt * ey[own]
        sd = da[own] + tt * ez[own]
        ix = np.clip(np.floor(sx).astype(np.int64), 0, res - 1)
        iy = np.clip(np.floor(sy).astype(np.int64), 0, res - 1)
        vis = sd <= zflat[iy * res + ix]

        same = own[1:] == own[:-1]
        starts = np.flatnonzero(vis & ~(np.r_[False, vis[:-1]] & np.r_[False, same]))
        ends = np.flatnonzero(vis & ~(np.r_[vis[1:], False] & np.r_[same, False]))
        keep = ends > starts
        starts, ends = starts[keep], ends[keep]
        if len(starts) > 0:
            ox = xa[own] + t * ex[own]
            oy = ya[own] + t * ey[own]
            qz = np.rint(np.stack([ox[starts], oy[starts], ox[ends], oy[ends]], axis=1) * QUANT_SUBPX).astype(np.int64)
            swap = (qz[:, 0] > qz[:, 2]) | ((qz[:, 0] == qz[:, 2]) & (qz[:, 1] > qz[:, 3]))
            qz[swap] = qz[swap][:, [2, 3, 0, 1]]
            nz = (qz[:, 0] != qz[:, 2]) | (qz[:, 1] != qz[:, 3])
            if np.any(nz):
                rows = np.unique(np.column_stack([kind[own[starts]], qz])[nz], axis=0)

    header = canonical_json_bytes(
        {
            "alg": HLR_ALG,
            "view": name,
            "res": res,
            "margin": margin,
            "eps0": eps0,
            "eps1": eps1,
            "m_max": m_max,
            "step": step,
            "crease_deg": crease_deg,
            "quant": QUANT_SUBPX,
        }
    )
    view_sha = sha256_bytes(header + rows.astype("<i8").tobytes())
    return {"sha256": view_sha, "segments": rows}


def project_all(stl_bytes: bytes, **kwargs) -> dict:
    mesh_sha = sha256_bytes(stl_bytes)
    V, F = load_binary_stl(stl_bytes)
    E, f1, f2 = edge_topology(F, len(V))
    N = face_normals(V, F)
    bases = view_bases()
    views = {v: project_view(v, V, F, E, f1, f2, N, bases[v], **kwargs) for v in VIEW_ORDER}
    layer_sha = sha256_bytes((mesh_sha + "".join(views[v]["sha256"] for v in VIEW_ORDER)).encode("utf-8"))
    extents = (V.max(axis=0) - V.min(axis=0)).tolist()
    return {
        "mesh_sha256": mesh_sha,
        "edge_layer_sha256": layer_sha,
        "vertex_count": int(len(V)),
        "face_count": int(len(F)),
        "extents": extents,
        "volume": mesh_signed_volume(V, F),
        "views": views,
    }


def embed_png_provenance(png_bytes: bytes, provenance: dict) -> bytes:
    """Embed `cad_hlr_provenance` tEXt chunk into a PNG file right before IEND."""
    keyword = b"cad_hlr_provenance"
    text_data = keyword + b"\x00" + canonical_json(provenance).encode("utf-8")
    chunk_len = struct.pack(">I", len(text_data))
    chunk_crc = struct.pack(">I", zlib.crc32(b"tEXt" + text_data) & 0xFFFFFFFF)
    text_chunk = chunk_len + b"tEXt" + text_data + chunk_crc
    iend_pos = png_bytes.rfind(b"\x00\x00\x00\x00IEND")
    return png_bytes[:iend_pos] + text_chunk + png_bytes[iend_pos:]
