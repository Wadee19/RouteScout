
from pathlib import Path
import re, json, math, time, hashlib, argparse
import pandas as pd

from pcb_world.core.env import PCBWorld

def sha256_file(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def safe_json(v):
    if isinstance(v,(str,int,float,bool)) or v is None:
        return v
    if isinstance(v,dict):
        return {str(k):safe_json(x) for k,x in v.items()}
    if isinstance(v,(list,tuple,set)):
        return [safe_json(x) for x in v]
    return repr(v)

def numeric_net_id(key, obj):
    for candidate in (
        obj.get("net_id") if isinstance(obj,dict) else None,
        obj.get("id") if isinstance(obj,dict) else None,
        key,
    ):
        if isinstance(candidate,int):
            return candidate
        m=re.search(r"(\d+)$",str(candidate))
        if m:
            return int(m.group(1))
    raise ValueError(f"Cannot infer numeric net id from {key!r}")

def pads_sorted(net_obj):
    pads=net_obj.get("pads",{})
    if isinstance(pads,dict):
        return [(k,pads[k]) for k in sorted(pads)]
    if isinstance(pads,list):
        return [(str(i),p) for i,p in enumerate(pads)]
    return []

def xy(pad):
    center=pad.get("center",{})
    v=center.get("xy")
    if not (isinstance(v,(list,tuple)) and len(v)>=2):
        raise ValueError(f"Pad has no center.xy: {pad}")
    return float(v[0]),float(v[1])

def layer(pad):
    return pad.get("layer")

def inspect_board(path):
    env=PCBWorld(board_path=str(path),max_steps=50)
    try:
        obs,info=env.reset(seed=47)
        nets=obs.get("board_static",{}).get("nets",{})
        records=[]
        for key,obj in nets.items():
            ps=pads_sorted(obj)
            if len(ps)<2:
                continue
            nid=numeric_net_id(key,obj)
            rec={"net_key":key,"net_id":nid,"pad_count":len(ps)}
            if len(ps)==2:
                (k0,p0),(k1,p1)=ps
                x0,y0=xy(p0); x1,y1=xy(p1)
                rec["mst_mm"]=math.hypot(x1-x0,y1-y0)
            records.append(rec)
        multi=[r for r in records if r["pad_count"]>2]
        two=[r for r in records if r["pad_count"]==2]
        return {
            "board_path":str(path),
            "board_sha256":sha256_file(path),
            "two_pad_nets":two,
            "multi_pad_nets":multi,
            "eligible":len(two)>=2 and len(multi)==0,
            "initial_closed_nets":safe_json(obs.get("closed_nets",[])),
            "initial_drc_count":len(obs.get("drc_violations",[]) or []),
        }
    finally:
        env.close()

def policy_order(records,policy):
    if policy=="natural":
        return [r["net_id"] for r in sorted(records,key=lambda r:r["net_id"])]
    if policy=="mst_hard_first":
        return [r["net_id"] for r in sorted(records,key=lambda r:(-r["mst_mm"],r["net_id"]))]
    if policy=="mst_easy_first":
        return [r["net_id"] for r in sorted(records,key=lambda r:(r["mst_mm"],r["net_id"]))]
    raise ValueError(policy)

def route_board(path, inspection, policy, repeat):
    requested=policy_order(inspection["two_pad_nets"],policy)
    env=PCBWorld(
        board_path=str(path),
        max_steps=max(200,4*len(requested)+40),
    )
    start=time.perf_counter()
    selected=[]
    reward_total=0.0
    api_error=None
    final_obs=None
    try:
        obs,info=env.reset(seed=47)
        nets=obs["board_static"]["nets"]
        by_id={}
        for key,obj in nets.items():
            ps=pads_sorted(obj)
            if len(ps)==2:
                by_id[numeric_net_id(key,obj)]=(key,obj,ps)

        for nid in requested:
            key,obj,ps=by_id[nid]
            (_,p0),(_,p1)=ps
            x0,y0=xy(p0); x1,y1=xy(p1)

            obs,reward,terminated,truncated,info=env.step({"action_type":0,"net_id":nid})
            reward_total+=float(reward)
            selected.append(nid)

            obs,reward,terminated,truncated,info=env.step({
                "action_type":1,
                "x_mm":x0,
                "y_mm":y0,
                "layer":layer(p0),
            })
            reward_total+=float(reward)

            obs,reward,terminated,truncated,info=env.step({
                "action_type":3,
                "x_mm":x1,
                "y_mm":y1,
                "routing_mode":2,
            })
            reward_total+=float(reward)

            obs,reward,terminated,truncated,info=env.step({"action_type":2})
            reward_total+=float(reward)

        final_obs=obs
    except Exception as exc:
        api_error=f"{type(exc).__name__}: {exc}"
        final_obs=locals().get("obs",{})
    finally:
        elapsed=time.perf_counter()-start
        try:
            env.close()
        except Exception:
            pass

    closed=final_obs.get("closed_nets",[]) if isinstance(final_obs,dict) else []
    drc=final_obs.get("drc_violations",[]) if isinstance(final_obs,dict) else []
    geom=final_obs.get("routing_geometry",[]) if isinstance(final_obs,dict) else []

    return {
        "board":Path(path).name,
        "board_sha256":inspection["board_sha256"],
        "policy":policy,
        "repeat":repeat,
        "requested_order":requested,
        "realized_order":selected,
        "order_exact":requested==selected,
        "net_count":len(requested),
        "closed_nets_count":len(closed or []),
        "drc_count":len(drc or []),
        "routing_geometry_count":len(geom or []),
        "reward_total":reward_total,
        "elapsed_seconds":elapsed,
        "api_error":api_error,
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--boards-dir",required=True)
    ap.add_argument("--out-dir",required=True)
    ap.add_argument("--max-boards",type=int,default=3)
    ap.add_argument("--repeats",type=int,default=2)
    args=ap.parse_args()

    boards=sorted(Path(args.boards_dir).glob("*.kicad_pcb"))
    inspections=[]
    for p in boards:
        try:
            inspections.append(inspect_board(p))
        except Exception as exc:
            inspections.append({
                "board_path":str(p),
                "board_sha256":sha256_file(p),
                "eligible":False,
                "inspection_error":f"{type(exc).__name__}: {exc}",
                "two_pad_nets":[],
                "multi_pad_nets":[],
            })

    eligible=[x for x in inspections if x.get("eligible")][:args.max_boards]
    out=Path(args.out_dir); out.mkdir(parents=True,exist_ok=True)
    json.dump(safe_json(inspections),open(out/"board_inspection.json","w"),indent=2)

    rows=[]
    for ins in eligible:
        p=Path(ins["board_path"])
        for policy in ["natural","mst_hard_first","mst_easy_first"]:
            for repeat in range(args.repeats):
                rows.append(route_board(p,ins,policy,repeat))

    df=pd.DataFrame(rows)
    df.to_csv(out/"pilot_runs.csv",index=False)

    summary={
        "boards_scanned":len(inspections),
        "eligible_boards":len(eligible),
        "runs":len(df),
        "api_error_runs":int(df["api_error"].notna().sum()) if len(df) else 0,
        "order_mismatch_runs":int((~df["order_exact"]).sum()) if len(df) else 0,
    }
    json.dump(summary,open(out/"runner_summary.json","w"),indent=2)
    print(json.dumps(summary,indent=2))

if __name__=="__main__":
    main()
