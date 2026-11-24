"""Generate REPORT.md (and BASELINE.md/NOT_TESTED.md for e05371f) inside a suite result folder."""
from __future__ import annotations

import json
from pathlib import Path
import sys

from common import ACCEPTANCE_DIR


def _read(d: Path, name: str) -> dict | None:
    p = d / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def _rel_link(target: Path, base_dir: Path) -> str:
    try:
        rel = target.resolve().relative_to(base_dir.resolve()).as_posix()
        return f"[{target.name}]({rel})"
    except ValueError:
        return f"[{target.name}](file:///{target.resolve().as_posix()})"


def generate(result_dir: Path, commit: str = "HEAD") -> None:
    hw = _read(result_dir, "hardware.json") or {}
    s1 = _read(result_dir, "s1_retrieval.json")
    s1_lat = _read(result_dir, "s1_latency_http.json")
    s2 = _read(result_dir, "s2_extract_cost.json")
    s3 = _read(result_dir, "s3_forget.json")
    s4 = _read(result_dir, "s4_bridge_pg.json")
    s5 = _read(result_dir, "s5_rule9.json")
    s6 = _read(result_dir, "s6_graph.json")
    s7 = _read(result_dir, "s7_traps.json")
    s8 = _read(result_dir, "s8_places_topics.json")
    s9 = _read(result_dir, "s9_why_story.json")
    s10 = _read(result_dir, "s10_hybrid_ablation.json")

    if not hw and s10 and isinstance(s10.get("hardware"), dict):
        hw = s10["hardware"]

    title = (
        f"# Acceptance Baseline — `temporal_memory` @ `{commit}`"
        if commit == "e05371f"
        else f"# Acceptance Report — `temporal_memory` @ `{commit}`"
    )
    lines: list[str] = [
        title,
        "",
        f"**Run folder:** [{result_dir.name}](file:///{result_dir.resolve().as_posix()})  ",
        f"**Hardware:** {hw.get('cpu', 'unknown')} · {hw.get('cores', '?')}C/{hw.get('threads', '?')}T · {hw.get('ram_gb', '?')} GB RAM · {hw.get('gpu', 'unknown')}  ",
        f"**Postgres:** `{hw.get('postgres', 'unknown')}` · **Python:** `{hw.get('python', '?')}`",
        "",
        "## Suite Summary (vs Plan v1 §6 Gates)",
        "",
        "| Suite | Gate (§6) | Measured Result | Status | Raw Evidence |",
        "|---|---|---|---|---|",
    ]

    def _add_sum(suite: str, gate: str, measured: str, obj: dict | None, fname: str):
        st = obj.get("status", "NOT MEASURED") if obj else "NOT MEASURED"
        lnk = _rel_link(result_dir / fname, result_dir) if (result_dir / fname).exists() else "—"
        lines.append(f"| {suite} | {gate} | {measured} | **{st}** | {lnk} |")

    if s1:
        g_ctx = s1["gold_mode"]["context_pack"]["overall"]
        lat20 = s1["latency_summary"]
        m_s1 = (
            f"Gold ctx top-8/16 `{g_ctx['top8_macro_38']}/{g_ctx['top16_macro_38']}` (sens leaks `{g_ctx['sensitive_leaks_top16']}`); "
            f"20k p95 `{lat20['20k_ctx_p95_ms']} ms` (writer `{lat20['20k_ctx_during_writer_p95_ms']} ms`), "
            f"needle `{lat20['needle_2015']['context_pack']}/{lat20['needle_2015']['http_search']}/{lat20['needle_2015']['mcp_memory_search']}`"
        )
    else:
        m_s1 = "Not measured"
    _add_sum("S1 Retrieval", "top-8 ≥ 0.78, top-16 ≥ 0.85, AR ≥ 0.80, 0 leaks; 20k p95 < 150 ms; needle True", m_s1, s1, "s1_retrieval.json")

    if s2:
        c = s2["cost_per_owner_day"]
        eq = s2["extraction_quality"]
        ch = s2["changes"]
        pr = s2["privacy"]
        m_s2 = (
            f"mean `${c['mean_usd']:.4f}`/day (p95 `${c['p95_usd']:.4f}`, max `${c['max_usd']:.4f}`); "
            f"recall `{eq['fact_recall']:.1%}`, prec `{eq['fact_precision']:.1%}`; "
            f"changes `{ch['superseded_ok']}/{ch['superseded_total']}` sup, `{ch['ended_ok']}/{ch['ended_total']}` end, `{ch['late_ok']}/{ch['late_total']}` late; "
            f"FP `{pr['clean_gold_fp_pct']}%`"
        )
    else:
        m_s2 = "Not measured"
    _add_sum("S2 Extraction & Cost", "mean ≤ $0.0044/day; 8/8+4/4+4/4 changes; 0 leaks; FP ≤ 2%", m_s2, s2, "s2_extract_cost.json")

    if s3:
        surv = s3["direct_forget_source"]["survivors_after_forget"]
        m_s3 = (
            f"bridge fact_id erased=`{s3['bridge_forget_by_fact_id']['response'].get('facts_erased')}`, "
            f"warm_ctx_leak=`{surv['warm_context_f_only']}`, facts_ver_bumped=`{s3['direct_forget_source']['facts_version_bumped']}`, "
            f"stale_subj_cnt=`{surv['subjects_fact_count_stale']}`"
        )
    else:
        m_s3 = "Not measured"
    _add_sum("S3 Forget", "0 survivors across all surfaces, caches, counts; in-flight fenced", m_s3, s3, "s3_forget.json")

    if s4:
        cp = s4.get("http_client_against_postgres") or {}
        if cp:
            ok_cnt = sum(1 for v in cp.values() if v.get("ok"))
            m_s4 = f"{ok_cnt}/{len(cp)} HttpTemporalMemoryClient ops OK; e2e write={s4.get('memory_bridge_http_e2e', {}).get('write_consented', {}).get('ok')}"
        else:
            m_s4 = s4.get("reason") or s4.get("status", "Not measured")
    else:
        m_s4 = "Not measured"
    _add_sum("S4 Bridge on Postgres", "contest-shared HTTP contract passes on Postgres", m_s4, s4, "s4_bridge_pg.json")

    if s5:
        m_s5 = (
            f"5A leaks(people={s5['case_5a_quarantined_fact_leaks']['zeta_in_vault_people']}, "
            f"links={s5['case_5a_quarantined_fact_leaks']['orphan_links_count']}); "
            f"5B place_prov=`{s5['case_5b_autopromoted_place_provenance']['alserkal_vault_provenance']}`"
        )
    else:
        m_s5 = "Not measured"
    _add_sum("S5 Rule 9 Surfaces", "0 sensitive leaks; 0 inferred as user_supplied", m_s5, s5, "s5_rule9.json")

    if s6 and "details" in s6 and "latency_20k" in s6["details"]:
        lat6 = s6["details"]["latency_20k"]
        m_s6 = f"20k p95 subj={lat6['graph_subjects']['p95_ms']}ms ppl={lat6['graph_people']['p95_ms']}ms"
    elif s6 and "probe" in s6:
        m_s6 = f"HTTP {s6['probe']['graph_subjects_status']}"
    elif s6:
        m_s6 = f"status={s6.get('status')}"
    else:
        m_s6 = "Not measured"
    _add_sum("S6 Vault Graph", "/vault/graph p95 < 150 ms; true counts; T1 confirmed only", m_s6, s6, "s6_graph.json")

    if s7:
        traps_link = _rel_link(ACCEPTANCE_DIR / "TRAPS.md", result_dir)
        if "precision" in s7:
            m_s7 = f"prec={s7['precision']}, user_supplied={s7.get('user_supplied_precision')} ({traps_link})"
        else:
            total_items = (s7.get("dataset") or {}).get("total_items", 84)
            m_s7 = f"{total_items} items ready ({traps_link})"
    else:
        m_s7 = "Not measured"
    _add_sum("S7 Live Triples", "≥90%/≥98% prec on 84-item trap set; <50 ms", m_s7, s7, "s7_traps.json")

    if s8:
        p8 = s8["part_8a_restaurant"]
        m_s8 = f"Zuma={p8['by_name']}, DIFC={p8['by_area']}, restaurant={p8['by_word_restaurant']}; 2-visit hyp={s8['part_8b_topic_counter']['hypotheses_after_session_2']}"
    else:
        m_s8 = "Not measured"
    _add_sum("S8 R6 Places & Topics", "restaurant by name/area/'restaurant'; 2-session topic hyp", m_s8, s8, "s8_places_topics.json")

    if s9:
        if "checks" in s9:
            chk = s9["checks"]
            ok_cnt = sum(1 for v in chk.values() if v)
            st_tpl = s9.get("story_template") or {}
            st_inv = s9.get("story_forget_invalidation") or {}
            m_s9 = (
                f"{ok_cnt}/{len(chk)} checks OK; reason_span={chk.get('why_reason_matches_cited_span')}, "
                f"story_cache={st_tpl.get('first_cached')}->{st_tpl.get('second_cached')}, "
                f"forget_inv={chk.get('forget_invalidates_why_and_story_cache')} (why_after={st_inv.get('why_after_status')})"
            )
        else:
            m_s9 = f"reason_field={s9.get('why_with_reason', {}).get('has_reason_field')}, story HTTP {s9.get('story_probe_status')}"
    else:
        m_s9 = "Not measured"
    _add_sum("S9 Why & Story", "cited reason span or unknown; grounded story + cache invalidation", m_s9, s9, "s9_why_story.json")

    if s10:
        hg = s10["gold_hybrid"]["context_pack"]["overall"]
        kp = s10["paraphrase_keyword_only"]["context_pack"]["overall"]
        hp = s10["paraphrase_hybrid"]["context_pack"]["overall"]
        lat_hnsw = s10["scale_20k"]["hnsw_cached_embed"]["context"]["p95_ms"]
        m_s10 = (
            f"gold hyb top-8/16 `{hg['top8_macro_38']}/{hg['top16_macro_38']}` (leaks `{hg['sensitive_leaks_top16']}`); "
            f"para kw->hyb `{kp['top16_macro_38']}->{hp['top16_macro_38']}`; "
            f"20k hnsw cached p95 `{lat_hnsw} ms`, needle `{s10['scale_20k_needle_semantic_hit']}`"
        )
    else:
        m_s10 = "Not measured"
    _add_sum("S10 Hybrid Ablation", "hybrid beats kw on paraphrase; gold top-16 ≥ 0.85; 20k HNSW p95 < 150 ms; needle True", m_s10, s10, "s10_hybrid_ablation.json")

    # S1 Detailed Tables
    if s1:
        lines.extend(["", "## S1 — Retrieval Per-Bucket (40 Gold Probes, 3 HTTP Paths)", ""])
        for mode_label, mode_obj in [("Gold Graph Mode", s1["gold_mode"]), ("Extracted Graph Mode (from S2)", s1.get("extracted_mode"))]:
            if not mode_obj:
                continue
            lines.extend([
                f"### {mode_label}",
                "",
                "| Bucket (n) | `/context` top8 / top16 (leaks16) | `/search` top8 / top16 (leaks16) | MCP `memory_search` top8 / top16 (leaks16) |",
                "|---|---:|---:|---:|",
            ])
            buckets = ["person", "person_alias", "contradiction", "twohop", "arabic", "sensitive", "noise"]
            for b in buckets:
                c_b = mode_obj["context_pack"]["by_bucket"].get(b, {})
                s_b = mode_obj["http_search"]["by_bucket"].get(b, {})
                m_b = mode_obj["mcp_memory_search"]["by_bucket"].get(b, {})
                n = c_b.get("n", 0)
                fmt = lambda d: f"{d.get('top8_raw') if d.get('top8_raw') is not None else '—'} / {d.get('top16_raw') if d.get('top16_raw') is not None else '—'} ({d.get('leaks16', 0)})"
                lines.append(f"| `{b}` ({n}) | {fmt(c_b)} | {fmt(s_b)} | {fmt(m_b)} |")
            ov_c = mode_obj["context_pack"]["overall"]
            ov_s = mode_obj["http_search"]["overall"]
            ov_m = mode_obj["mcp_memory_search"]["overall"]
            lines.append(
                f"| **Macro (38 non-noise)** | **{ov_c['top8_macro_38']} / {ov_c['top16_macro_38']} ({ov_c['leaks_or_noise_fail_top16']} fails)** | "
                f"**{ov_s['top8_macro_38']} / {ov_s['top16_macro_38']} ({ov_s['leaks_or_noise_fail_top16']} fails)** | "
                f"**{ov_m['top8_macro_38']} / {ov_m['top16_macro_38']} ({ov_m['leaks_or_noise_fail_top16']} fails)** |"
            )
            lines.append("")

    if s1_lat:
        lines.extend([
            "### S1 — Authenticated HTTP Latency (`n = 100` per scenario)",
            "",
            f"Raw file: {_rel_link(result_dir / 's1_latency_http.json', result_dir)}",
            "",
            "| Size | `/context` cold | `/context` warm p50 / p95 / p99 | `/search` p50 / p95 / p99 | MCP search p50 / p95 / p99 | Needle (`ctx` / `search` / `MCP`) |",
            "|---:|---:|---:|---:|---:|---|",
        ])
        for sz in ("1000", "5000", "20000"):
            d = s1_lat["sizes"][sz]
            cw, sw, mw = d["context_warm"], d["http_search_warm"], d["mcp_search_warm"]
            nd = d.get("needle_2015")
            nd_str = f"`{nd['context_pack']}` / `{nd['http_search']}` / `{nd['mcp_memory_search']}`" if nd else "—"
            lines.append(
                f"| {int(sz):,} | {d['context_cold_ms']} ms | {cw['p50_ms']} / {cw['p95_ms']} / {cw['p99_ms']} ms | "
                f"{sw['p50_ms']} / {sw['p95_ms']} / {sw['p99_ms']} ms | {mw['p50_ms']} / {mw['p95_ms']} / {mw['p99_ms']} ms | {nd_str} |"
            )
        cdw = s1_lat["sizes"]["20000"]["context_during_writer"]
        lines.append(
            f"\n- **20k `/context` during concurrent writer** (`{cdw['writer_commits']}` commits applied, `{cdw['http_errors']}` HTTP errors): "
            f"p50 **{cdw['p50_ms']} ms**, p95 **{cdw['p95_ms']} ms**, p99 **{cdw['p99_ms']} ms**, max **{cdw['max_ms']} ms**."
        )

    if s2:
        c, eq, ch, pr = s2["cost_per_owner_day"], s2["extraction_quality"], s2["changes"], s2["privacy"]
        lines.extend([
            "",
            "## S2 — Extraction & Cost (`apps/memory` Worker over 31 Owner-Days + Late Packet)",
            "",
            f"Raw files: {_rel_link(result_dir / 's2_extract_cost.json', result_dir)}, {_rel_link(result_dir / 's2_calls.jsonl', result_dir)}, {_rel_link(result_dir / 's2_judge.json', result_dir)}",
            "",
            "| Metric | Value | Gate |",
            "|---|---|---|",
            f"| Model (`model_observed`) | `{', '.join(c['models_observed']) or 'haiku'}` | — |",
            f"| Jobs applied / rejected | {s2['jobs']['applied']} / {s2['jobs']['rejected']} | 0 rejected |",
            f"| Cost / owner-day (mean / p95 / max) | `${c['mean_usd']:.5f}` / `${c['p95_usd']:.5f}` / `${c['max_usd']:.5f}` (total `${c['total_extract_usd']:.4f}`) | mean ≤ `$0.0044` |",
            f"| Fact recall / precision | `{eq['fact_recall']:.1%}` (`{eq['plain_gold_total']}` plain) / `{eq['fact_precision']:.1%}` (`{eq['extracted_true']}T / {eq['extracted_noise']}N / {eq['extracted_wrong']}W`) | — |",
            f"| People found (dups) / relations / edges | `{eq['people_found']}/{eq['people_total']}` (`{eq['people_duplicated']}` dups) / `{eq['relation_correct']}/{eq['people_found']}` / `{eq['edges_found']}/{eq['edges_total']}` | — |",
            f"| Changes (`superseded` / `ended` / `late`) | `{ch['superseded_ok']}/{ch['superseded_total']}` / `{ch['ended_ok']}/{ch['ended_total']}` / `{ch['late_ok']}/{ch['late_total']}` | `8/8 + 4/4 + 4/4` |",
            f"| Privacy leaks / clean gold FP | `{pr['sensitive_leaked']}` leaks / `{pr['clean_gold_fp_count']}` FP (`{pr['clean_gold_fp_pct']}%`) | 0 leaks / ≤ 2% FP |",
        ])

    if s3:
        surv = s3["direct_forget_source"]["survivors_after_forget"]
        lines.extend([
            "",
            "## S3 — Forget Completeness",
            "",
            f"Raw file: {_rel_link(result_dir / 's3_forget.json', result_dir)}",
            "",
            "| Check | Result | Pass? |",
            "|---|---|---|",
            f"| Bridge `POST /forget` by `fact_id` (`f_fact_target`) | `facts_erased={s3['bridge_forget_by_fact_id']['response'].get('facts_erased')}`, survived_in_ctx=`{s3['bridge_forget_by_fact_id']['fact_survived_in_context']}` | `{not s3['bridge_forget_by_fact_id']['fact_survived_in_context']}` |",
            f"| Bridge `POST /forget` by `record_ids` (`r_forget`) | `facts_erased={s3['bridge_forget_by_record_ids']['response'].get('facts_erased')}`, survived_in_ctx=`{s3['bridge_forget_by_record_ids']['f_only_survived_in_context']}` | `{not s3['bridge_forget_by_record_ids']['f_only_survived_in_context']}` |",
            f"| Direct `forget_source()` bumps `facts_version` | `{s3['direct_forget_source']['facts_version_before']} -> {s3['direct_forget_source']['facts_version_after']}` | `{s3['direct_forget_source']['facts_version_bumped']}` |",
            f"| In-flight leased job fenced | rejected=`{s3['direct_forget_source']['inflight_job_rejected']}` (`{s3['direct_forget_source']['inflight_reasons']}`) | `{s3['direct_forget_source']['inflight_job_rejected']}` |",
            f"| Warm `context_pack` cache after Forget | f_only survived=`{surv['warm_context_f_only']}` | `{not surv['warm_context_f_only']}` |",
            f"| `entities` / `entity_aliases` / `links` / `subjects.fact_count` | ent_in_vault=`{surv['entity_tariq_in_vault_people']}`, aliases=`{surv['aliases_tariq_count']}`, link_active=`{surv['link_tariq_active_in_db']}`, count_stale=`{surv['subjects_fact_count_stale']}` (`{surv['subjects_fact_count_db']}` vs `{surv['subjects_fact_count_true']}`) | `{not surv['entity_tariq_in_vault_people'] and surv['aliases_tariq_count']==0 and not surv['link_tariq_active_in_db'] and not surv['subjects_fact_count_stale']}` |",
        ])

    if s4:
        lines.extend([
            "",
            "## S4 — Bridge on Live Postgres",
            "",
            f"Raw file: {_rel_link(result_dir / 's4_bridge_pg.json', result_dir)}",
            "",
        ])
        if s4.get("http_client_against_postgres"):
            lines.extend([
                "| Operation (`HttpTemporalMemoryClient`) | OK? | Detail / Error |",
                "|---|---|---|",
            ])
            for k, v in s4["http_client_against_postgres"].items():
                det = v.get("error") or ("ok" if v.get("ok") else str(v))
                lines.append(f"| `{k}` | `{v.get('ok')}` | `{str(det)[:120]}` |")
            lines.append(f"\n- `contest-shared` fake-client reference suite: `{s4['contest_shared_fake_suite_reference'].get('summary', '')}` (`FakeTemporalMemoryClient` only).")
        else:
            lines.append(f"- **Status:** `{s4.get('status')}` — {s4.get('reason', 'not run')}")

    if s5:
        c5a = s5["case_5a_quarantined_fact_leaks"]
        c5b = s5["case_5b_autopromoted_place_provenance"]
        c5c = s5["case_5c_sensitive_surfaces"]
        lines.extend([
            "",
            "## S5 — Rule 9 Surfaces",
            "",
            f"Raw file: {_rel_link(result_dir / 's5_rule9.json', result_dir)}",
            "",
            f"- **5A Quarantined fact (`diabetes`) → entity/link leak:** `Zeta Relative` in `/vault/people`=`{c5a['zeta_in_vault_people']}`, `Rashidiya Clinic` in places=`{c5a['rashidiya_in_vault_places']}`, orphan links=`{c5a['orphan_links_count']}`, in MCP vault=`{c5a['zeta_in_mcp_vault']}`, in export=`{c5a['zeta_in_export_md']}`.",
            f"- **5B Auto-promoted place (`Alserkal Cafe`, no user confirm):** status=`{c5b['alserkal_vault_status']}`, `/vault/people` provenance=`{c5b['alserkal_vault_provenance']}`, `/context` provenance=`{c5b['alserkal_context_provenance']}`; hardcoded envelopes=`{c5b['hardcoded_envelopes']}`.",
            f"- **5C Sensitive categories:** `health` in `/vault/subjects`=`{c5c['health_in_vault_subjects']}`, `faith` in `/vault/subjects`=`{c5c['faith_in_vault_subjects']}`, `faith` in export=`{c5c['faith_in_export_md']}`, `/vault/subjects` omits `sensitive_cat`=`{c5c['vault_subjects_omits_sensitive_cat']}`.",
        ])

    if s6 and "checks" in s6:
        lines.extend([
            "",
            "## S6 — Vault Graph (U1c)",
            "",
            f"Raw file: {_rel_link(result_dir / 's6_graph.json', result_dir)}",
            "",
            "| Check | Pass? |",
            "|---|---|",
        ])
        for k, v in s6["checks"].items():
            lines.append(f"| `{k}` | `{v}` |")

    if s9 and "checks" in s9:
        lines.extend([
            "",
            "## S9 — Why & Story (U5)",
            "",
            f"Raw file: {_rel_link(result_dir / 's9_why_story.json', result_dir)}",
            "",
            "| Check | Pass? |",
            "|---|---|",
        ])
        for k, v in s9["checks"].items():
            lines.append(f"| `{k}` | `{v}` |")

    if s10:
        kw_g = s10["gold_keyword_only"]["context_pack"]["overall"]
        hy_g = s10["gold_hybrid"]["context_pack"]["overall"]
        kw_p = s10["paraphrase_keyword_only"]["context_pack"]["overall"]
        hy_p = s10["paraphrase_hybrid"]["context_pack"]["overall"]
        sc = s10["scale_20k"]
        lines.extend([
            "",
            "## S10 — Hybrid Search Ablation (U4) & 20k Vector Benchmark",
            "",
            f"Raw file: {_rel_link(result_dir / 's10_hybrid_ablation.json', result_dir)}",
            "",
            f"- **Model:** `{s10['model']}` (`dim={s10['dim']}`, `min_sim={s10['min_sim']}`, `weight={s10['weight']}`)",
            f"- **Backfill:** `{s10['backfill']['embedded_facts']}` embedded in `{s10['backfill']['elapsed_ms']} ms` (`quarantine_held={s10['backfill']['quarantine_held']}`, `history_embedded={s10['backfill']['history_embedded']}`)",
            "",
            "| Eval Set | Keyword-only `/context` top8 / top16 (leaks16) | Hybrid `/context` top8 / top16 (leaks16) |",
            "|---|---:|---:|",
            f"| Gold 40 probes (38 non-noise) | `{kw_g['top8_macro_38']} / {kw_g['top16_macro_38']}` (`{kw_g['leaks_or_noise_fail_top16']}` fails) | `{hy_g['top8_macro_38']} / {hy_g['top16_macro_38']}` (`{hy_g['leaks_or_noise_fail_top16']}` fails) |",
            f"| Paraphrase 20 probes (zero shared keywords) | `{kw_p['top8_macro_38']} / {kw_p['top16_macro_38']}` | `{hy_p['top8_macro_38']} / {hy_p['top16_macro_38']}` |",
            "",
            "| 20k Vector Mode | `/context` p50 / p95 / p99 | `/search` p50 / p95 / p99 |",
            "|---|---:|---:|",
        ])
        for mode in ("hnsw_uncached_embed", "hnsw_cached_embed", "exact_uncached_embed", "exact_cached_embed"):
            if mode in sc:
                mc, ms_lat = sc[mode]["context"], sc[mode]["search"]
                lines.append(
                    f"| `{mode}` | {mc['p50_ms']} / {mc['p95_ms']} / {mc['p99_ms']} ms | {ms_lat['p50_ms']} / {ms_lat['p95_ms']} / {ms_lat['p99_ms']} ms |"
                )
        lines.append(f"\n- **20k semantic needle hit (`f_needle`):** `{s10['scale_20k_needle_semantic_hit']}`")

    if commit == "e05371f":
        lines.extend([
            "",
            "## Engine Bugs Hit During Baseline (Unmodified `e05371f`)",
            "",
            "- `privacy/policy.py:44` → `privacy/sensitive.py:231`: `agent-cli` worker kind triggers Layer 2 `screen()` and fails closed (`ScreenUnavailable: TM_CLASSIFIER_MODEL is not set`) when LM Studio is offline.",
            "- `api/bridge.py:111,141,152,174,199,241,278`: `POST /records`, `POST /facts/{id}/resolve`, `POST /forget`, `GET /search` mutate `FakeGraphStore` in-memory attributes (`records`, `facts`, `jobs`, `generations`), returning HTTP 500 or `facts_erased=0` / 0 search hits on `PostgresGraphStore`.",
            "- `privacy/forget.py:75-195`: `forget_source()` never bumps `owners.facts_version`, never recomputes `subjects.fact_count`, and leaves entities/aliases/links active — so warm `context_pack` (`live/context.py:310-316`) serves erased facts.",
            "- `core/applier.py:195-206,399-411` + `api/vault.py:192`: entities and links are persisted even when their only fact is quarantined, and links with `evidence_fact_id=None` are always rendered.",
            "- `api/vault.py:117,177,250` + `live/context.py:504`: `status=='active'` maps to `provenance='user_supplied'` even for auto-promoted places; `/vault/subjects` omits `sensitive_cat` (`api/vault.py:108-121`); `export_md.py:119` gates `health/` only, not `faith/`.",
            "- `live/context.py:406` + `api/vault.py` + `mcp/server.py:485,517`: 10k/1k caps cause >150 ms p95 at 20k facts and miss the 2015 needle on `/context`, `/search`, and MCP `memory_search`.",
        ])

    md_text = "\n".join(lines) + "\n"
    (result_dir / "REPORT.md").write_text(md_text, encoding="utf-8")

    if commit == "e05371f":
        (result_dir / "BASELINE.md").write_text(md_text, encoding="utf-8")
        not_tested = [
            f"# Not Tested in Acceptance Run (`{commit}`)",
            "",
            f"Run folder: [{result_dir.name}](file:///{result_dir.resolve().as_posix()})",
            "",
            "1. **S6 (`/vault/graph?view=subjects|people` & `POST /vault/people/{id}/tier`):** **NOT YET BUILT** on `e05371f` (HTTP 404). Scheduled for U1c.",
            "2. **S7 (Live-triple trap set scoring):** **NOT YET BUILT** on `e05371f` (no instant triple extractor exists). 84-item EN/AR/ARZ dataset is validated in `TRAPS.md` / `traps_dataset.json`; scoring activates in U2.",
            "3. **S8 (R6 topic counter & place type):** **NOT YET BUILT** (`restaurant` type & 2-session topic counter await U2/U3; today's baseline behaviour recorded in `s8_places_topics.json`).",
            "4. **S9 (`why` reason spans & `GET /story`):** **NOT YET BUILT** on `e05371f` (reason span field awaits U3/U5; `GET /story` returns 404 and awaits U5).",
            "5. **Local Qwen / LM Studio Layer 2 screen (`worker_kind='agent-cli'`):** LM Studio (`http://127.0.0.1:1234/v1/models`) was offline, so `agent-cli` jobs fail closed in `privacy/policy.py:44`; S2 submitted Haiku attempts with `worker_kind='internal-cloud'` (Layer 1 regex gate) to complete the 32-job extraction baseline.",
        ]
        (result_dir / "NOT_TESTED.md").write_text("\n".join(not_tested) + "\n", encoding="utf-8")


if __name__ == "__main__":
    rdir = Path(sys.argv[1])
    c = sys.argv[2] if len(sys.argv) > 2 else "HEAD"
    generate(rdir, c)
    print("Generated REPORT.md for", rdir)
