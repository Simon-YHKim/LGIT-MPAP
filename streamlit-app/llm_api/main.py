from __future__ import annotations

import time
import pandas as pd
from fastapi import FastAPI, HTTPException

from llm_api.schemas import AnalyzeRequest, ExecuteRequest, ContinueRequest
from llm_api.intent_parser import parse_intent
from llm_api.planner import build_execution_plan
from llm_api.vllm_client import suggest_process_rewrites

from llm_api.uph_llm_queries import (
    load_db_config,
    load_mes_db_config,
    fetch_itas_latest_date,
    fetch_mes_latest_date,
    fetch_itas_uph_day,
    fetch_mes_uph_day,
    fetch_itas_uph_trend,
    fetch_mes_uph_trend,
    fetch_itas_uph_machine_trend,
    fetch_mes_uph_machine_trend,
    fetch_mes_customer_model_stats_by_process,
    fetch_mes_process_name_candidates,
    fetch_itas_process_name_candidates,
    fetch_mes_customer_model_candidates,
    match_best_candidate,
    fetch_mes_ranked_machines,
    fetch_itas_ranked_machines,
    fetch_mes_overall_avg_uph_for_day,
    fetch_itas_overall_avg_uph_for_day,
    fetch_mes_best_worst_ranked_machines,
    fetch_itas_best_worst_ranked_machines,
    resolve_process_candidate,
    resolve_process_candidate_with_rewrites,
)

app = FastAPI(title="UPH LLM API")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat/analyze")
def analyze(req: AnalyzeRequest):
    try:
        t0 = time.time()

        print("=== ANALYZE REQUEST ===")
        print(req)

        intent = parse_intent(req.question)
        print(f"[TIMING] parse_intent: {time.time() - t0:.2f}s")
        print("=== PARSED INTENT (RAW) ===")
        print(intent)

        source_system = intent.get("source_system", "MES")
        process_name = intent.get("process_name")
        customer_model = intent.get("customer_model")

        if source_system == "ITAS":
            db = load_db_config()
            print(f"[TIMING] load_db_config: {time.time() - t0:.2f}s")

            process_candidates = fetch_itas_process_name_candidates(db)
            print(f"[TIMING] fetch_itas_process_name_candidates: {time.time() - t0:.2f}s")

            process_resolution = resolve_process_candidate(process_name, process_candidates)
            print("=== PROCESS RESOLUTION BEFORE REWRITE ===")
            print(process_resolution)
            print(f"[TIMING] resolve_process_candidate: {time.time() - t0:.2f}s")

            if process_resolution["status"] in ["not_found", "need_clarification"] and process_name:
                rewrite_candidates = suggest_process_rewrites(process_name)
                print(f"[TIMING] suggest_process_rewrites (ITAS): {time.time() - t0:.2f}s")
                print("=== PROCESS REWRITE CANDIDATES (ITAS) ===")
                print(rewrite_candidates)

                process_resolution = resolve_process_candidate_with_rewrites(
                    raw_value=process_name,
                    candidates=process_candidates,
                    rewrite_candidates=rewrite_candidates,
                )
                print("=== PROCESS RESOLUTION AFTER REWRITE ===")
                print(process_resolution)
                print(f"[TIMING] resolve_process_candidate_with_rewrites (ITAS): {time.time() - t0:.2f}s")

            if process_resolution["status"] == "resolved":
                process_name = process_resolution["matched_value"]
                intent["process_name"] = process_name

            elif process_resolution["status"] == "need_clarification":
                return {
                    "status": "need_clarification",
                    "message": "입력한 공정명과 유사한 ITAS 공정 후보가 있습니다. 어떤 공정을 의미하셨나요?",
                    "missing_slots": ["process_name"],
                    "candidate_type": "process_name",
                    "candidates": process_resolution["candidates"],
                    "intent": intent,
                }

            elif process_resolution["status"] == "not_found":
                return {
                    "status": "need_clarification",
                    "message": "입력한 공정명과 일치하는 ITAS 공정을 찾지 못했습니다. 아래 후보를 확인해주세요.",
                    "missing_slots": ["process_name"],
                    "candidate_type": "process_name",
                    "candidates": process_resolution["candidates"],
                    "intent": intent,
                }

            latest_date = fetch_itas_latest_date(db)
            print(f"[TIMING] fetch_itas_latest_date: {time.time() - t0:.2f}s")

        else:
            db = load_mes_db_config()
            print(f"[TIMING] load_mes_db_config: {time.time() - t0:.2f}s")

            process_candidates = fetch_mes_process_name_candidates(db)
            print(f"[TIMING] fetch_mes_process_name_candidates: {time.time() - t0:.2f}s")

            process_resolution = resolve_process_candidate(process_name, process_candidates)
            print("=== PROCESS RESOLUTION BEFORE REWRITE ===")
            print(process_resolution)
            print(f"[TIMING] resolve_process_candidate: {time.time() - t0:.2f}s")

            if process_resolution["status"] in ["not_found", "need_clarification"] and process_name:
                rewrite_candidates = suggest_process_rewrites(process_name)
                print(f"[TIMING] suggest_process_rewrites (MES): {time.time() - t0:.2f}s")
                print("=== PROCESS REWRITE CANDIDATES (MES) ===")
                print(rewrite_candidates)

                process_resolution = resolve_process_candidate_with_rewrites(
                    raw_value=process_name,
                    candidates=process_candidates,
                    rewrite_candidates=rewrite_candidates,
                )
                print("=== PROCESS RESOLUTION AFTER REWRITE ===")
                print(process_resolution)
                print(f"[TIMING] resolve_process_candidate_with_rewrites (MES): {time.time() - t0:.2f}s")

            if process_resolution["status"] == "resolved":
                process_name = process_resolution["matched_value"]
                intent["process_name"] = process_name

            elif process_resolution["status"] == "need_clarification":
                return {
                    "status": "need_clarification",
                    "message": "입력한 공정명과 유사한 MES 공정 후보가 있습니다. 어떤 공정을 의미하셨나요?",
                    "missing_slots": ["process_name"],
                    "candidate_type": "process_name",
                    "candidates": process_resolution["candidates"],
                    "intent": intent,
                }

            elif process_resolution["status"] == "not_found":
                return {
                    "status": "need_clarification",
                    "message": "입력한 공정명과 일치하는 MES 공정을 찾지 못했습니다. 아래 후보를 확인해주세요.",
                    "missing_slots": ["process_name"],
                    "candidate_type": "process_name",
                    "candidates": process_resolution["candidates"],
                    "intent": intent,
                }

            if customer_model:
                model_candidates = fetch_mes_customer_model_candidates(db)
                print(f"[TIMING] fetch_mes_customer_model_candidates: {time.time() - t0:.2f}s")

                customer_model = match_best_candidate(customer_model, model_candidates)
                intent["customer_model"] = customer_model
                print(f"[TIMING] customer_model_match: {time.time() - t0:.2f}s")

            latest_date = fetch_mes_latest_date(db)
            print(f"[TIMING] fetch_mes_latest_date: {time.time() - t0:.2f}s")

            if process_name and not intent.get("customer_model"):
                model_candidates = fetch_mes_customer_model_stats_by_process(db, process_name)
                print(f"[TIMING] fetch_mes_customer_model_stats_by_process: {time.time() - t0:.2f}s")
                print("=== MODEL CANDIDATES ===")
                print(model_candidates)

                if len(model_candidates) == 1:
                    auto_model = model_candidates[0]["customer_model"]
                    intent["customer_model"] = auto_model
                    print("=== AUTO SELECTED CUSTOMER MODEL ===")
                    print(auto_model)

                elif len(model_candidates) > 1:
                    return {
                        "status": "need_clarification",
                        "message": f"{process_name} 공정은 여러 customer_model에 존재합니다. 어떤 모델 기준으로 조회할까요?",
                        "missing_slots": ["customer_model"],
                        "candidates": model_candidates,
                        "intent": intent,
                    }

        print("=== PARSED INTENT (NORMALIZED) ===")
        print(intent)

        print("=== LATEST DATE ===")
        print(latest_date)

        plan = build_execution_plan(intent, latest_date=latest_date)
        print(f"[TIMING] build_execution_plan: {time.time() - t0:.2f}s")

        if source_system == "MES" and intent.get("customer_model"):
            msg = plan.get("message", "")
            if "customer_model:" not in msg:
                plan["message"] = f"{msg} (customer_model: {intent['customer_model']})"

        print("=== EXECUTION PLAN ===")
        print(plan)
        print(f"[TIMING] analyze total: {time.time() - t0:.2f}s")

        return plan

    except Exception as e:
        import traceback
        print("=== ANALYZE ERROR ===")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/continue")
def continue_chat(req: ContinueRequest):
    try:
        print("=== CONTINUE REQUEST ===")
        print(req)

        intent = dict(req.intent or {})
        updates = dict(req.updates or {})
        intent.update(updates)

        source_system = intent.get("source_system", "MES")
        process_name = intent.get("process_name")
        customer_model = intent.get("customer_model")

        if source_system == "ITAS":
            db = load_db_config()
            latest_date = fetch_itas_latest_date(db)
        else:
            db = load_mes_db_config()
            latest_date = fetch_mes_latest_date(db)

            if process_name and not customer_model:
                model_candidates = fetch_mes_customer_model_stats_by_process(db, process_name)
                print("=== CONTINUE MODEL CANDIDATES ===")
                print(model_candidates)

                if len(model_candidates) == 1:
                    auto_model = model_candidates[0]["customer_model"]
                    intent["customer_model"] = auto_model

                elif len(model_candidates) > 1:
                    return {
                        "status": "need_clarification",
                        "message": f"{process_name} 공정은 여러 customer_model에 존재합니다. 어떤 모델 기준으로 조회할까요?",
                        "missing_slots": ["customer_model"],
                        "candidates": model_candidates,
                        "intent": intent,
                    }

        plan = build_execution_plan(intent, latest_date=latest_date)

        if source_system == "MES" and intent.get("customer_model"):
            msg = plan.get("message", "")
            if "customer_model:" not in msg:
                plan["message"] = f"{msg} (customer_model: {intent['customer_model']})"

        print("=== CONTINUE PLAN ===")
        print(plan)

        return plan

    except Exception as e:
        import traceback
        print("=== CONTINUE ERROR ===")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/execute")
def execute(req: ExecuteRequest):
    try:
        if not req.approved:
            return {
                "status": "cancelled",
                "message": "사용자가 실행을 승인하지 않았습니다."
            }

        execution_plan = req.execution_plan
        tool_name = execution_plan.get("tool_name")
        args = execution_plan.get("arguments", {})

        print("=== EXECUTE REQUEST ===")
        print(execution_plan)

        source_system = args.get("source_system", "MES")
        customer_model = args.get("customer_model")

        if source_system == "ITAS":
            db = load_db_config()
        else:
            db = load_mes_db_config()

        model_suffix = f", customer_model={customer_model}" if customer_model else ""
        model_text = f" / 모델 {customer_model}" if customer_model else ""

        if tool_name == "get_mes_uph_recent_days":
            df = fetch_mes_uph_trend(
                db=db,
                process_name=args["process_name"],
                start_date=pd.Timestamp(args["start_date"]),
                end_date=pd.Timestamp(args["end_date"]),
                customer_model=customer_model,
            )
            avg_uph = None if df.empty else float(df["uph"].mean())

            return {
                "status": "completed",
                "tool_name": tool_name,
                "result_table": df.to_dict(orient="records"),
                "natural_response": (
                    f"MES 기준 조회 결과가 없습니다. (process_name={args['process_name']}{model_suffix}, start_date={args['start_date']}, end_date={args['end_date']})"
                    if avg_uph is None
                    else f"MES 기준 {args['process_name']}{model_text}의 최근 {args['recent_days']}일 평균 UPH는 {avg_uph:,.2f}입니다."
                ),
            }

        if tool_name == "get_itas_uph_recent_days":
            df = fetch_itas_uph_trend(
                db=db,
                process_name=args["process_name"],
                start_date=pd.Timestamp(args["start_date"]),
                end_date=pd.Timestamp(args["end_date"]),
            )
            avg_uph = None if df.empty else float(df["uph"].mean())

            return {
                "status": "completed",
                "tool_name": tool_name,
                "result_table": df.to_dict(orient="records"),
                "natural_response": (
                    f"ITAS 기준 조회 결과가 없습니다. (process_name={args['process_name']}, start_date={args['start_date']}, end_date={args['end_date']})"
                    if avg_uph is None
                    else f"ITAS 기준 {args['process_name']}의 최근 {args['recent_days']}일 평균 UPH는 {avg_uph:,.2f}입니다."
                ),
            }

        if tool_name == "get_mes_uph_day_by_machine":
            df = fetch_mes_uph_day(
                db=db,
                process_name=args["process_name"],
                selected_date=pd.Timestamp(args["selected_date"]),
                customer_model=customer_model,
            )
            return {
                "status": "completed",
                "tool_name": tool_name,
                "result_table": df.to_dict(orient="records"),
                "natural_response": (
                    f"MES 기준 조회 결과가 없습니다. (process_name={args['process_name']}{model_suffix}, selected_date={args['selected_date']})"
                    if df.empty
                    else f"MES 기준 {args['selected_date']}의 {args['process_name']}{model_text} 호기별 UPH 조회가 완료되었습니다."
                ),
            }

        if tool_name == "get_itas_uph_day_by_machine":
            df = fetch_itas_uph_day(
                db=db,
                process_name=args["process_name"],
                selected_date=pd.Timestamp(args["selected_date"]),
            )
            return {
                "status": "completed",
                "tool_name": tool_name,
                "result_table": df.to_dict(orient="records"),
                "natural_response": (
                    f"ITAS 기준 조회 결과가 없습니다. (process_name={args['process_name']}, selected_date={args['selected_date']})"
                    if df.empty
                    else f"ITAS 기준 {args['selected_date']}의 {args['process_name']} 호기별 UPH 조회가 완료되었습니다."
                ),
            }

        if tool_name == "get_mes_uph_machine_trend":
            df = fetch_mes_uph_machine_trend(
                db=db,
                process_name=args["process_name"],
                machine_no=args["machine_no"],
                start_date=pd.Timestamp(args["start_date"]),
                end_date=pd.Timestamp(args["end_date"]),
                customer_model=customer_model,
            )
            return {
                "status": "completed",
                "tool_name": tool_name,
                "result_table": df.to_dict(orient="records"),
                "natural_response": (
                    f"MES 기준 조회 결과가 없습니다. (process_name={args['process_name']}{model_suffix}, machine_no={args['machine_no']}, start_date={args['start_date']}, end_date={args['end_date']})"
                    if df.empty
                    else f"MES 기준 {args['process_name']}{model_text} {args['machine_no']}호기의 최근 {args['recent_days']}일 UPH 추이 조회가 완료되었습니다."
                ),
            }

        if tool_name == "get_itas_uph_machine_trend":
            df = fetch_itas_uph_machine_trend(
                db=db,
                process_name=args["process_name"],
                machine_no=args["machine_no"],
                start_date=pd.Timestamp(args["start_date"]),
                end_date=pd.Timestamp(args["end_date"]),
            )
            return {
                "status": "completed",
                "tool_name": tool_name,
                "result_table": df.to_dict(orient="records"),
                "natural_response": (
                    f"ITAS 기준 조회 결과가 없습니다. (process_name={args['process_name']}, machine_no={args['machine_no']}, start_date={args['start_date']}, end_date={args['end_date']})"
                    if df.empty
                    else f"ITAS 기준 {args['process_name']} {args['machine_no']}호기의 최근 {args['recent_days']}일 UPH 추이 조회가 완료되었습니다."
                ),
            }

        # --------------------------------------------------
        # ranked best / worst N개
        # --------------------------------------------------
        if tool_name == "get_mes_ranked_machines":
            df = fetch_mes_ranked_machines(
                db=db,
                process_name=args["process_name"],
                selected_date=pd.Timestamp(args["selected_date"]),
                rank_direction=args["rank_direction"],
                top_n=int(args["top_n"]),
                customer_model=customer_model,
            )

            overall_avg_uph = fetch_mes_overall_avg_uph_for_day(
                db=db,
                process_name=args["process_name"],
                selected_date=pd.Timestamp(args["selected_date"]),
                customer_model=customer_model,
            )

            direction_ko = "베스트" if args["rank_direction"] == "best" else "워스트"

            return {
                "status": "completed",
                "tool_name": tool_name,
                "result_table": df.to_dict(orient="records"),
                "summary": {
                    "overall_avg_uph": overall_avg_uph,
                    "rank_direction": args["rank_direction"],
                    "top_n": int(args["top_n"]),
                    "source_system": "MES",
                },
                "natural_response": (
                    f"MES 기준 조회 결과가 없습니다. (process_name={args['process_name']}{model_suffix}, selected_date={args['selected_date']})"
                    if df.empty
                    else f"MES 기준 {args['selected_date']}의 {args['process_name']}{model_text} {direction_ko} 호기 {args['top_n']}개와 UPH 조회가 완료되었습니다."
                ),
            }

        if tool_name == "get_itas_ranked_machines":
            df = fetch_itas_ranked_machines(
                db=db,
                process_name=args["process_name"],
                selected_date=pd.Timestamp(args["selected_date"]),
                rank_direction=args["rank_direction"],
                top_n=int(args["top_n"]),
            )

            overall_avg_uph = fetch_itas_overall_avg_uph_for_day(
                db=db,
                process_name=args["process_name"],
                selected_date=pd.Timestamp(args["selected_date"]),
            )

            direction_ko = "베스트" if args["rank_direction"] == "best" else "워스트"

            return {
                "status": "completed",
                "tool_name": tool_name,
                "result_table": df.to_dict(orient="records"),
                "summary": {
                    "overall_avg_uph": overall_avg_uph,
                    "rank_direction": args["rank_direction"],
                    "top_n": int(args["top_n"]),
                    "source_system": "ITAS",
                },
                "natural_response": (
                    f"ITAS 기준 조회 결과가 없습니다. (process_name={args['process_name']}, selected_date={args['selected_date']})"
                    if df.empty
                    else f"ITAS 기준 {args['selected_date']}의 {args['process_name']} {direction_ko} 호기 {args['top_n']}개와 UPH 조회가 완료되었습니다."
                ),
            }

        # --------------------------------------------------
        # best / worst 각각 N개 (N=1 포함)
        # --------------------------------------------------
        if tool_name == "get_mes_best_worst_ranked_machines":
            df = fetch_mes_best_worst_ranked_machines(
                db=db,
                process_name=args["process_name"],
                selected_date=pd.Timestamp(args["selected_date"]),
                top_n=int(args["top_n"]),
                customer_model=customer_model,
            )

            overall_avg_uph = fetch_mes_overall_avg_uph_for_day(
                db=db,
                process_name=args["process_name"],
                selected_date=pd.Timestamp(args["selected_date"]),
                customer_model=customer_model,
            )

            top_n = int(args["top_n"])

            return {
                "status": "completed",
                "tool_name": tool_name,
                "result_table": df.to_dict(orient="records"),
                "summary": {
                    "overall_avg_uph": overall_avg_uph,
                    "source_system": "MES",
                    "top_n": top_n,
                    "combined_rank": True,
                },
                "natural_response": (
                    f"MES 기준 조회 결과가 없습니다. (process_name={args['process_name']}{model_suffix}, selected_date={args['selected_date']})"
                    if df.empty
                    else (
                        f"MES 기준 {args['selected_date']}의 {args['process_name']}{model_text} Best/Worst 호기와 UPH 조회가 완료되었습니다."
                        if top_n == 1
                        else f"MES 기준 {args['selected_date']}의 {args['process_name']}{model_text} 베스트/워스트 각각 {top_n}개 호기와 UPH 조회가 완료되었습니다."
                    )
                ),
            }

        if tool_name == "get_itas_best_worst_ranked_machines":
            df = fetch_itas_best_worst_ranked_machines(
                db=db,
                process_name=args["process_name"],
                selected_date=pd.Timestamp(args["selected_date"]),
                top_n=int(args["top_n"]),
            )

            overall_avg_uph = fetch_itas_overall_avg_uph_for_day(
                db=db,
                process_name=args["process_name"],
                selected_date=pd.Timestamp(args["selected_date"]),
            )

            top_n = int(args["top_n"])

            return {
                "status": "completed",
                "tool_name": tool_name,
                "result_table": df.to_dict(orient="records"),
                "summary": {
                    "overall_avg_uph": overall_avg_uph,
                    "source_system": "ITAS",
                    "top_n": top_n,
                    "combined_rank": True,
                },
                "natural_response": (
                    f"ITAS 기준 조회 결과가 없습니다. (process_name={args['process_name']}, selected_date={args['selected_date']})"
                    if df.empty
                    else (
                        f"ITAS 기준 {args['selected_date']}의 {args['process_name']} Best/Worst 호기와 UPH 조회가 완료되었습니다."
                        if top_n == 1
                        else f"ITAS 기준 {args['selected_date']}의 {args['process_name']} 베스트/워스트 각각 {top_n}개 호기와 UPH 조회가 완료되었습니다."
                    )
                ),
            }

        return {
            "status": "error",
            "message": f"지원하지 않는 tool_name입니다: {tool_name}"
        }

    except Exception as e:
        import traceback
        print("=== EXECUTE ERROR ===")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))