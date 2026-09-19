
from pathlib import Path
import json, time, hashlib, traceback, sys, multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
import pandas as pd

from pcb_world.core.env import PCBWorld
from pcb_world.core.action_schema import (
    ACT_NET_SELECT, ACT_START_ROUTE, ACT_MAKE_LINE, ACT_NET_END,
)
from eval.metrics import compute_metrics_inline

def sha256_file(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def one(task):
    b=task["board"]
    policy=task["policy"]
    requested=list(b["orders"][policy])
    target=set(int(n) for n in b["target_nets"])
    outdir=Path(task["outdir"])
    outdir.mkdir(parents=True,exist_ok=True)
    outpcb=outdir/f"{b['d3_id']}__{policy}.kicad_pcb"

    env=None
    issued_net_order=[]
    action_records=[]
    t0=time.perf_counter()

    try:
        env=PCBWorld(
            board_path=b["guide_path"],
            target_nets=target,
            preserve_nontarget_routing=True,
            max_steps=max(200,4*len(requested)+40),
            engine_seed=77,
            seed=47,
            drc_penalty=0.0,
            emit_drc_tokens=False,
        )
        obs,_=env.reset(seed=47)
        pad_geo={int(k):v for k,v in b["pad_geometry"].items()}

        def do(action, net_id, label):
            nonlocal obs
            obs,reward,terminated,truncated,info=env.step(action)
            action_records.append({
                "net_id":int(net_id),
                "action":label,
                "success":bool(info.get("action_success",False)),
                "action_class":info.get("action_class"),
                "terminated":bool(terminated),
                "truncated":bool(truncated),
            })
            return obs

        # EXACT Phase 8A semantics:
        # always issue the four frozen actions in sequence; do not branch on
        # action_success and do not promote a policy based on these diagnostics.
        for nid in requested:
            p0,p1=pad_geo[int(nid)]

            issued_net_order.append(int(nid))
            do({
                "action_type":ACT_NET_SELECT,
                "net_id":int(nid),
            }, nid, "net_select")

            do({
                "action_type":ACT_START_ROUTE,
                "x_mm":float(p0["x"]),
                "y_mm":float(p0["y"]),
                "layer":int(p0["layer"]),
            }, nid, "start_route")

            do({
                "action_type":ACT_MAKE_LINE,
                "x_mm":float(p1["x"]),
                "y_mm":float(p1["y"]),
                "routing_mode":2,
            }, nid, "make_line")

            do({
                "action_type":ACT_NET_END,
            }, nid, "net_end")

        # Make evaluation quiescent if the last action left a route session open.
        routing_session_open_before_eval = bool(env._engine.is_routing())
        if routing_session_open_before_eval:
            env._engine.cancel_route()

        env._engine.build_connectivity()

        # Canonical target-scoped live metrics.
        target_metrics=compute_metrics_inline(
            env,
            reward_config_name="pcbworld_reward",
            check_angle=45,
        )
        target_routability=float(target_metrics["routability"])
        target_success=bool(target_metrics["success"])
        target_drc_errors=int(env._engine.drc_helper.get_error_count())

        # Whole-board DRC: disable Python target filter and rerun complete DRC.
        env._engine.drc_helper.set_target_net_names(None)
        env._engine.clear_drc_cache()
        env._engine.run_drc()
        full_drc_errors=int(env._engine.drc_helper.get_error_count())
        full_drc_all=int(env._engine.drc_helper.get_violation_count())

        snap=env._engine.get_reward_snapshot(run_drc=False)
        env._engine.save(str(outpcb))

        action_successes=sum(int(x["success"]) for x in action_records)
        return {
            "difficulty":b["difficulty"],
            "d3_id":b["d3_id"],
            "sample":b["sample"],
            "policy":policy,
            "input_guide_sha256":b["guide_sha256"],
            "requested_order":json.dumps(requested),
            "issued_net_order":json.dumps(issued_net_order),
            "issued_order_exact":issued_net_order==requested,
            "target_count":len(requested),
            "target_routability":target_routability,
            "target_success":target_success,
            "target_drc_errors":target_drc_errors,
            "target_clean_success":bool(target_success and target_drc_errors==0),
            "full_drc_errors":full_drc_errors,
            "full_drc_all":full_drc_all,
            "full_clean_success":bool(target_success and full_drc_errors==0),
            "wirelength_mm":float(snap.total_wirelength),
            "via_count":int(snap.via_count),
            "track_count":int(snap.track_count),
            "action_count":len(action_records),
            "action_success_count":action_successes,
            "action_failure_count":len(action_records)-action_successes,
            "action_records":json.dumps(action_records),
            "routing_session_open_before_eval":routing_session_open_before_eval,
            "elapsed_seconds":time.perf_counter()-t0,
            "output_pcb":str(outpcb),
            "output_pcb_sha256":sha256_file(outpcb),
            "api_error":"",
        }

    except Exception as exc:
        return {
            "difficulty":b.get("difficulty"),
            "d3_id":b.get("d3_id"),
            "sample":b.get("sample"),
            "policy":policy,
            "input_guide_sha256":b.get("guide_sha256"),
            "requested_order":json.dumps(requested),
            "issued_net_order":json.dumps(issued_net_order),
            "issued_order_exact":issued_net_order==requested,
            "target_count":len(requested),
            "action_count":len(action_records),
            "action_success_count":sum(int(x["success"]) for x in action_records),
            "action_failure_count":sum(int(not x["success"]) for x in action_records),
            "action_records":json.dumps(action_records),
            "elapsed_seconds":time.perf_counter()-t0,
            "api_error":f"{type(exc).__name__}: {exc}",
            "traceback":traceback.format_exc(),
        }
    finally:
        if env is not None:
            try:
                env.close()
            except Exception:
                pass

def main():
    manifest=json.load(open(sys.argv[1]))
    outcsv=Path(sys.argv[2])
    outdir=Path(sys.argv[3])
    workers=int(sys.argv[4])

    tasks=[
        {"board":b,"policy":p,"outdir":str(outdir)}
        for b in manifest["boards"]
        for p in ["natural","mst_hard_first","mst_easy_first"]
    ]

    rows=[]
    ctx=mp.get_context("spawn")
    with ProcessPoolExecutor(max_workers=workers,mp_context=ctx) as ex:
        futs=[ex.submit(one,t) for t in tasks]
        for i,f in enumerate(as_completed(futs),1):
            row=f.result()
            rows.append(row)
            print(
                f"[{i}/{len(futs)}] {row.get('d3_id')} {row.get('policy')} "
                f"r={row.get('target_routability')} "
                f"drc={row.get('full_drc_errors')} "
                f"action_fail={row.get('action_failure_count')} "
                f"api={row.get('api_error','')[:80]}",
                flush=True,
            )

    df=pd.DataFrame(rows).sort_values(["difficulty","d3_id","policy"])
    df.to_csv(outcsv,index=False)
    print(json.dumps({
        "runs":len(df),
        "boards":int(df["d3_id"].nunique()) if len(df) else 0,
        "api_errors":int(df["api_error"].fillna("").ne("").sum()) if len(df) else 0,
    },indent=2))

if __name__=="__main__":
    main()
