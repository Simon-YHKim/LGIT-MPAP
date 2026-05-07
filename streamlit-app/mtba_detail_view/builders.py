# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from typing import Any

import pandas as pd

from .helpers import build_date_cols, popup_key_fol, popup_key_standard, safe_float


INLINE_PATTERN = r'inline|in-line|fol'


def filter_inline_segments(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    return df[
        df['equipment_segment_name'].astype(str).str.contains(INLINE_PATTERN, case=False, regex=True, na=False)
    ].copy()


def build_fol_inline_segment_options(df: pd.DataFrame) -> list[str]:
    if df.empty:
        return []
    vals = sorted(df['equipment_segment_name'].dropna().astype(str).str.strip().unique().tolist())
    return [x for x in vals if x and re.search(INLINE_PATTERN, x, flags=re.I)]


def build_production_maps(base_df: pd.DataFrame):
    if base_df.empty:
        return {}, {}
    prod_daily = base_df.groupby(['equipment_id', 'base_date'], dropna=False)['output_qty'].max().reset_index()
    prod_daily_map = {(r['equipment_id'], r['base_date']): safe_float(r['output_qty']) for _, r in prod_daily.iterrows()}
    eq_total_prod = prod_daily.groupby('equipment_id', dropna=False)['output_qty'].sum().reset_index()
    eq_total_prod_map = {r['equipment_id']: safe_float(r['output_qty']) for _, r in eq_total_prod.iterrows()}
    return prod_daily_map, eq_total_prod_map


def build_daily_mtba_map(base_df: pd.DataFrame):
    if base_df.empty:
        return {}
    mtba_daily = base_df.groupby(['equipment_id', 'base_date'], dropna=False)['daily_mtba'].max().reset_index()
    return {(r['equipment_id'], r['base_date']): safe_float(r['daily_mtba']) for _, r in mtba_daily.iterrows()}


def build_process_mtba_stats(base_df: pd.DataFrame):
    empty = {'mtba_avg': 0.0, 'mtba_min': 0.0, 'mtba_max': 0.0, 'mtba_std': 0.0}
    if base_df.empty or 'mtba' not in base_df.columns:
        return empty
    s = pd.to_numeric(base_df[['equipment_id', 'mtba']].drop_duplicates()['mtba'], errors='coerce').dropna()
    if s.empty:
        return empty
    return {
        'mtba_avg': round(float(s.mean()), 1),
        'mtba_min': round(float(s.min()), 1),
        'mtba_max': round(float(s.max()), 1),
        'mtba_std': round(float(s.std(ddof=0)), 1),
    }


def build_popup_maps(base_df: pd.DataFrame):
    if base_df.empty:
        return {}

    prod_daily_map, _ = build_production_maps(base_df)
    day_total_alarm = (
        base_df.groupby(['equipment_id', 'base_date'], dropna=False)['alarm_count']
        .sum()
        .reset_index()
        .rename(columns={'alarm_count': 'total_alarm_count'})
    )
    day_runtime = (
        base_df.groupby(['equipment_id', 'base_date'], dropna=False)['runtime_minutes']
        .max()
        .reset_index()
        if 'runtime_minutes' in base_df.columns
        else pd.DataFrame(columns=['equipment_id', 'base_date', 'runtime_minutes'])
    )
    day_mtba = (
        base_df.groupby(['equipment_id', 'base_date'], dropna=False)['daily_mtba']
        .max()
        .reset_index()
        .rename(columns={'daily_mtba': 'daily_mtba_max'})
    )
    day_info = (
        base_df.groupby(['equipment_id', 'base_date'], dropna=False)
        .agg(
            equipment_name=('equipment_name', 'first'),
            equipment_no=('equipment_no', 'first'),
            model_name=('model_name', 'first'),
            process_name=('process_name', 'first'),
        )
        .reset_index()
    )
    day_info = day_total_alarm.merge(day_runtime, on=['equipment_id', 'base_date'], how='left') \
                              .merge(day_mtba, on=['equipment_id', 'base_date'], how='left') \
                              .merge(day_info, on=['equipment_id', 'base_date'], how='left')

    day_alarm = (
        base_df.groupby(['equipment_id', 'base_date', 'alarm_code', 'alarm_name'], dropna=False)['alarm_count']
        .sum()
        .reset_index()
        .rename(columns={'alarm_count': 'alarm_count_sum'})
    )

    popup_map = {}
    for _, info in day_info.iterrows():
        eq_id = info['equipment_id']
        base_date = info['base_date']
        total_alarm = safe_float(info.get('total_alarm_count'))
        runtime_min = safe_float(info.get('runtime_minutes'))
        if runtime_min <= 0 and total_alarm > 0:
            runtime_min = safe_float(info.get('daily_mtba_max')) * total_alarm
        output_qty = safe_float(prod_daily_map.get((eq_id, base_date), 0.0))

        sub = (
            day_alarm[(day_alarm['equipment_id'] == eq_id) & (day_alarm['base_date'] == base_date)]
            .copy()
            .sort_values(['alarm_count_sum', 'alarm_name'], ascending=[False, True])
            .head(5)
        )
        rows = []
        for idx, alarm_row in enumerate(sub.itertuples(index=False), start=1):
            cnt = safe_float(getattr(alarm_row, 'alarm_count_sum'))
            rows.append({
                'rank': idx,
                'alarm_name': str(getattr(alarm_row, 'alarm_name')),
                'alarm_code': str(getattr(alarm_row, 'alarm_code')) if pd.notna(getattr(alarm_row, 'alarm_code')) else str(getattr(alarm_row, 'alarm_name')),
                'alarm_count': cnt,
                'alarm_rate_pct': 0.0 if output_qty <= 0 else (cnt / output_qty) * 100.0,
                'share_pct': 0.0 if total_alarm <= 0 else (cnt / total_alarm) * 100.0,
            })

        key = popup_key_standard(eq_id, base_date)
        popup_map[key] = {
            'popup_scope': 'standard',
            'equipment_id': int(eq_id) if pd.notna(eq_id) else None,
            'segment_name': None,
            'base_date': base_date,
            'model_name': info.get('model_name'),
            'process_name': info.get('process_name'),
            'equipment_name': info.get('equipment_name'),
            'equipment_no': info.get('equipment_no'),
            'title': str(info.get('equipment_name') or info.get('equipment_no') or '-'),
            'runtime_min': runtime_min,
            'output_qty': output_qty,
            'total_alarm_count': total_alarm,
            'rows': rows,
        }
    return popup_map


def filter_by_mtba(base_df: pd.DataFrame, mtba_worst: int, mtba_limit: float, only_below: bool):
    if base_df.empty:
        return base_df, pd.DataFrame()

    eq_mtba = base_df[['equipment_id', 'equipment_no', 'equipment_name', 'mtba']].drop_duplicates().copy()
    eq_mtba['mtba_sort'] = pd.to_numeric(eq_mtba['mtba'], errors='coerce').fillna(999999)

    if mtba_worst > 0:
        worst_ids = (
            eq_mtba.sort_values(['mtba_sort', 'equipment_no'], ascending=[True, True])
            .head(mtba_worst)['equipment_id']
            .tolist()
        )
        eq_mtba = eq_mtba[eq_mtba['equipment_id'].isin(worst_ids)].copy()
        base_df = base_df[base_df['equipment_id'].isin(worst_ids)].copy()

    if only_below:
        valid_ids = eq_mtba[eq_mtba['mtba_sort'] <= float(mtba_limit)]['equipment_id'].tolist()
        eq_mtba = eq_mtba[eq_mtba['equipment_id'].isin(valid_ids)].copy()
        base_df = base_df[base_df['equipment_id'].isin(valid_ids)].copy()

    return base_df, eq_mtba


def build_alarm_priority_rows(base_df: pd.DataFrame, top_n: int, result_metric: str, selected_end_date, process_mtba_stats: dict):
    if base_df.empty:
        return []

    prod_daily_map, eq_total_prod_map = build_production_maps(base_df)
    top_alarm_df = (
        base_df.groupby('alarm_name', as_index=False)['alarm_count']
        .sum()
        .rename(columns={'alarm_count': 'total_alarm_count'})
        .sort_values(['total_alarm_count', 'alarm_name'], ascending=[False, True])
        .head(top_n)
        .reset_index(drop=True)
    )

    rows = []
    for idx, alarm_name in enumerate(top_alarm_df['alarm_name'].tolist(), start=1):
        sub = base_df[base_df['alarm_name'] == alarm_name].copy()
        if sub.empty:
            continue
        eq_summary = (
            sub.groupby(['equipment_id', 'equipment_no', 'equipment_name', 'mtba'], dropna=False)
            .agg(total_alarm_count=('alarm_count', 'sum'))
            .reset_index()
            .sort_values(['total_alarm_count', 'equipment_no'], ascending=[False, True])
        )
        for _, eq in eq_summary.iterrows():
            eq_id = eq['equipment_id']
            sub_eq = sub[sub['equipment_id'] == eq_id].copy()
            day_agg = sub_eq.groupby('base_date', as_index=False).agg(alarm_count=('alarm_count', 'sum'))
            day_map, popup_key_map = {}, {}
            for _, drow in day_agg.iterrows():
                base_date = drow['base_date']
                alarm_cnt = safe_float(drow['alarm_count'])
                prod_qty = safe_float(prod_daily_map.get((eq_id, base_date), 0.0))
                if result_metric == '알람율':
                    val = 0.0 if prod_qty <= 0 else (alarm_cnt / prod_qty) * 100.0
                else:
                    val = alarm_cnt
                day_map[base_date] = val
                popup_key_map[base_date] = popup_key_standard(eq_id, base_date)

            rows.append({
                'process_name': sub_eq['process_name'].iloc[0],
                'group_label': f'Worst{idx}',
                'alarm_name': alarm_name,
                'equipment_id': eq_id,
                'equipment_no': str(eq['equipment_no']),
                'equipment_name': str(eq['equipment_name']),
                'mtba': safe_float(eq.get('mtba')),
                'mtba_avg': safe_float(process_mtba_stats.get('mtba_avg')),
                'mtba_min': safe_float(process_mtba_stats.get('mtba_min')),
                'mtba_max': safe_float(process_mtba_stats.get('mtba_max')),
                'mtba_std': safe_float(process_mtba_stats.get('mtba_std')),
                'alarm_count_total': safe_float(eq['total_alarm_count']),
                'output_qty_total': safe_float(eq_total_prod_map.get(eq_id, 0.0)),
                'output_qty_latest': safe_float(prod_daily_map.get((eq_id, selected_end_date), 0.0)),
                'daily_map': day_map,
                'popup_key_map': popup_key_map,
            })
    return rows


def build_equipment_priority_rows(base_df: pd.DataFrame, top_n: int, result_metric: str, selected_end_date, process_mtba_stats: dict):
    if base_df.empty:
        return []

    prod_daily_map, eq_total_prod_map = build_production_maps(base_df)
    mtba_daily_map = build_daily_mtba_map(base_df)
    eq_summary = (
        base_df.groupby(['equipment_id', 'equipment_no', 'equipment_name', 'mtba'], dropna=False)
        .agg(total_alarm_count=('alarm_count', 'sum'))
        .reset_index()
        .sort_values(['total_alarm_count', 'equipment_no'], ascending=[False, True])
    )

    rows = []
    for _, eq in eq_summary.iterrows():
        eq_id = eq['equipment_id']
        sub_eq = base_df[base_df['equipment_id'] == eq_id].copy()
        if sub_eq.empty:
            continue
        top_alarm_df = (
            sub_eq.groupby('alarm_name', as_index=False)['alarm_count']
            .sum()
            .rename(columns={'alarm_count': 'total_alarm_count'})
            .sort_values(['total_alarm_count', 'alarm_name'], ascending=[False, True])
            .head(top_n)
            .reset_index(drop=True)
        )
        eq_dates = sorted(pd.Series(sub_eq['base_date'].dropna().unique()).tolist())
        for idx, alarm_row in top_alarm_df.iterrows():
            alarm_name = alarm_row['alarm_name']
            sub_alarm = sub_eq[sub_eq['alarm_name'] == alarm_name].copy()
            day_alarm_agg = sub_alarm.groupby('base_date', as_index=False).agg(alarm_count=('alarm_count', 'sum'))
            day_map, popup_key_map = {}, {}
            for base_date in eq_dates:
                match = day_alarm_agg[day_alarm_agg['base_date'] == base_date]
                alarm_cnt = safe_float(match['alarm_count'].iloc[0], 0.0) if not match.empty else 0.0
                prod_qty = safe_float(prod_daily_map.get((eq_id, base_date), 0.0))
                day_mtba = safe_float(mtba_daily_map.get((eq_id, base_date), 0.0))
                if result_metric == '알람율':
                    val = 0.0 if prod_qty <= 0 else (alarm_cnt / prod_qty) * 100.0
                elif result_metric == '알람수':
                    val = alarm_cnt
                elif result_metric == 'MTBA':
                    val = day_mtba
                elif result_metric == '생산수량':
                    val = prod_qty
                else:
                    val = alarm_cnt
                day_map[base_date] = val
                popup_key_map[base_date] = popup_key_standard(eq_id, base_date)

            rows.append({
                'process_name': sub_eq['process_name'].iloc[0],
                'equipment_id': eq_id,
                'equipment_no': str(eq['equipment_no']),
                'equipment_name': str(eq['equipment_name']),
                'mtba': safe_float(eq.get('mtba')),
                'mtba_avg': safe_float(process_mtba_stats.get('mtba_avg')),
                'mtba_min': safe_float(process_mtba_stats.get('mtba_min')),
                'mtba_max': safe_float(process_mtba_stats.get('mtba_max')),
                'mtba_std': safe_float(process_mtba_stats.get('mtba_std')),
                'group_label': f'Worst{idx + 1}',
                'alarm_name': str(alarm_name),
                'alarm_count_total': safe_float(alarm_row['total_alarm_count']),
                'output_qty_total': safe_float(eq_total_prod_map.get(eq_id, 0.0)),
                'output_qty_latest': safe_float(prod_daily_map.get((eq_id, selected_end_date), 0.0)),
                'daily_map': day_map,
                'popup_key_map': popup_key_map,
            })
    return rows


def build_grid_dataframe(rows: list[dict], date_cols: list, view_priority: str) -> pd.DataFrame:
    out_rows = []
    last_proc = last_eq = last_group = None
    for row in rows:
        proc = row['process_name']
        eq = row['equipment_no']
        grp = row['group_label']
        show_proc = proc if proc != last_proc else ''
        show_eq = eq if (view_priority == '설비 호기' and eq != last_eq) else (eq if view_priority != '설비 호기' else '')
        show_grp = grp if grp != last_group or proc != last_proc or (view_priority == '설비 호기' and eq != last_eq) else ''
        base = {
            '공정명': show_proc,
            '구분': show_grp,
            '알람명': row['alarm_name'],
            '호기': show_eq if view_priority == '설비 호기' else row['equipment_no'],
            'MTBA': safe_float(row.get('mtba')),
            '알람수': safe_float(row['alarm_count_total']),
            '생산수량': safe_float(row.get('output_qty_latest')),
            'MTBA Avg': safe_float(row.get('mtba_avg')),
            'MTBA Min': safe_float(row.get('mtba_min')),
            'MTBA Max': safe_float(row.get('mtba_max')),
            'MTBA Std': safe_float(row.get('mtba_std')),
        }
        if view_priority != '설비 호기':
            base['호기'] = row['equipment_no']
        for dt in date_cols:
            label = pd.to_datetime(dt).strftime('%Y-%m-%d')
            base[f'd_{label}'] = float(row['daily_map'].get(dt, 0.0))
            base[f'pk_{label}'] = row.get('popup_key_map', {}).get(dt, '')
        out_rows.append(base)
        last_proc, last_eq, last_group = proc, eq, grp
    return pd.DataFrame(out_rows)


def build_standard_bundle(base_df: pd.DataFrame, query: dict):
    if base_df.empty:
        return {
            'base_df': base_df,
            'rows': [],
            'date_cols': build_date_cols(query['start_date'], query['end_date']),
            'popup_map': {},
        }

    stats = build_process_mtba_stats(base_df)
    filtered_df, _ = filter_by_mtba(
        base_df,
        int(query.get('mtba_worst', 0)),
        float(query.get('mtba_limit', 120.0)),
        bool(query.get('only_below', False)),
    )
    popup_map = build_popup_maps(filtered_df)
    if query.get('view_priority') == '알람명':
        rows = build_alarm_priority_rows(
            filtered_df,
            int(query.get('alarm_worst', 5)),
            str(query.get('result_metric', 'MTBA')),
            query.get('end_date'),
            stats,
        )
    else:
        rows = build_equipment_priority_rows(
            filtered_df,
            int(query.get('alarm_worst', 5)),
            str(query.get('result_metric', 'MTBA')),
            query.get('end_date'),
            stats,
        )
    return {
        'base_df': filtered_df,
        'rows': rows,
        'date_cols': build_date_cols(query['start_date'], query['end_date']),
        'popup_map': popup_map,
    }


def build_fol_inline_bundle(base_df: pd.DataFrame, model_name: str, target_date, selected_segments: list[str], prod_process: str | None, result_metric: str, mtba_limit: float, only_below: bool):
    df = filter_inline_segments(base_df)
    if selected_segments:
        df = df[df['equipment_segment_name'].isin(selected_segments)].copy()
    if df.empty:
        return {'grid_df': pd.DataFrame(), 'popup_map': {}, 'process_cols': []}

    proc_agg = (
        df.groupby(['equipment_segment_name', 'process_name'], dropna=False)
        .agg(
            metric_mtba=('daily_mtba', 'mean'),
            metric_prod_qty=('output_qty', 'sum'),
            runtime_minutes=('runtime_minutes', 'sum'),
            total_alarm_count=('alarm_count', 'sum'),
        )
        .reset_index()
    )

    if only_below:
        seg_mtba = proc_agg.groupby('equipment_segment_name', dropna=False)['metric_mtba'].mean().reset_index()
        keep = seg_mtba[seg_mtba['metric_mtba'] <= float(mtba_limit)]['equipment_segment_name'].tolist()
        proc_agg = proc_agg[proc_agg['equipment_segment_name'].isin(keep)].copy()
        df = df[df['equipment_segment_name'].isin(keep)].copy()

    if proc_agg.empty:
        return {'grid_df': pd.DataFrame(), 'popup_map': {}, 'process_cols': []}

    process_cols = sorted(proc_agg['process_name'].dropna().astype(str).unique().tolist())
    if not prod_process or prod_process not in process_cols:
        prod_process = process_cols[0] if process_cols else None

    popup_map = {}
    group_alarm = (
        df.groupby(['equipment_segment_name', 'process_name', 'alarm_code', 'alarm_name'], dropna=False)['alarm_count']
        .sum()
        .reset_index()
        .rename(columns={'alarm_count': 'alarm_count_sum'})
    )
    for _, info in proc_agg.iterrows():
        seg = str(info['equipment_segment_name'])
        proc = str(info['process_name'])
        total_alarm = safe_float(info['total_alarm_count'])
        output_qty = safe_float(info['metric_prod_qty'])
        sub = (
            group_alarm[
                (group_alarm['equipment_segment_name'] == seg)
                & (group_alarm['process_name'] == proc)
            ]
            .copy()
            .sort_values(['alarm_count_sum', 'alarm_name'], ascending=[False, True])
            .head(5)
        )
        rows = []
        for idx, alarm_row in enumerate(sub.itertuples(index=False), start=1):
            cnt = safe_float(getattr(alarm_row, 'alarm_count_sum'))
            rows.append({
                'rank': idx,
                'alarm_name': str(getattr(alarm_row, 'alarm_name')),
                'alarm_code': str(getattr(alarm_row, 'alarm_code')) if pd.notna(getattr(alarm_row, 'alarm_code')) else str(getattr(alarm_row, 'alarm_name')),
                'alarm_count': cnt,
                'alarm_rate_pct': 0.0 if output_qty <= 0 else (cnt / output_qty) * 100.0,
                'share_pct': 0.0 if total_alarm <= 0 else (cnt / total_alarm) * 100.0,
            })
        popup_map[popup_key_fol(seg, proc, target_date)] = {
            'popup_scope': 'fol',
            'equipment_id': None,
            'segment_name': seg,
            'base_date': target_date,
            'model_name': model_name,
            'process_name': proc,
            'equipment_name': None,
            'equipment_no': None,
            'title': f'{seg} / {proc}',
            'runtime_min': safe_float(info.get('runtime_minutes')),
            'output_qty': output_qty,
            'total_alarm_count': total_alarm,
            'rows': rows,
        }

    rows = []
    for seg in sorted(proc_agg['equipment_segment_name'].dropna().astype(str).unique().tolist()):
        sub = proc_agg[proc_agg['equipment_segment_name'] == seg].copy()
        row = {'모델명': model_name, '설비세그먼트명': seg, result_metric: 0.0, '생산수량': 0.0}
        metric_vals = []
        selected_proc_qty = 0.0
        for proc in process_cols:
            match = sub[sub['process_name'] == proc]
            metric_val = 0.0
            prod_qty = 0.0
            if not match.empty:
                metric_val = safe_float(match['metric_mtba'].iloc[0]) if result_metric == 'MTBA' else safe_float(match['metric_prod_qty'].iloc[0])
                prod_qty = safe_float(match['metric_prod_qty'].iloc[0])
            row[f'p_{proc}'] = metric_val
            row[f'pk_{proc}'] = popup_key_fol(seg, proc, target_date)
            metric_vals.append(metric_val)
            if prod_process == proc:
                selected_proc_qty = prod_qty
        row[result_metric] = round(float(pd.Series(metric_vals, dtype='float64').mean()) if result_metric == 'MTBA' and metric_vals else (sum(metric_vals) if metric_vals else 0.0), 1)
        row['생산수량'] = float(selected_proc_qty)
        rows.append(row)

    return {'grid_df': pd.DataFrame(rows), 'popup_map': popup_map, 'process_cols': process_cols}
