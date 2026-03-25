"""
Palantir (PLTR) 財務モデル シミュレーター — 1ページ縦スクロール
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(
    page_title="PLTR Financial Model",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
.block-container { padding-top: 1rem; padding-bottom: 1rem; }

/* セクションヘッダー */
.sec-hdr {
    background: #1a3a5c; color: white;
    padding: 5px 12px; border-radius: 4px;
    font-size: 0.88rem; font-weight: bold;
    margin: 14px 0 6px 0; letter-spacing: 0.5px;
}

/* KPI カード */
.kpi-box {
    background: #f4f7fb;
    border: 1px solid #c8d8e8;
    border-left: 4px solid #1a3a5c;
    border-radius: 4px;
    padding: 8px 12px;
}
.kpi-lbl { color: #666; font-size: 0.72rem; margin-bottom: 2px; }
.kpi-val { color: #1a3a5c; font-size: 1.15rem; font-weight: bold; line-height: 1.2; }
.kpi-sub { color: #888; font-size: 0.70rem; margin-top: 2px; }
.kpi-bear { border-left-color: #c0392b !important; }
.kpi-bull { border-left-color: #27ae60 !important; }

/* グリッドラベル */
.grid-lbl { font-size: 0.80rem; font-weight: bold; color: #1a3a5c;
            margin-bottom: 2px; padding: 2px 0; }

hr { margin: 6px 0; border-color: #dde3ea; }
</style>
""", unsafe_allow_html=True)

# ─── 定数 ────────────────────────────────────────────────────────────────────
YEARS      = ["FY2025", "FY2026", "FY2027", "FY2028", "FY2029", "FY2030"]
BASE_REV   = 2870.0
HIST_YEARS = ["FY2021", "FY2022", "FY2023", "FY2024"]
HIST = {
    "FY2021": {"revenue": 1541, "gov": 897,  "com": 645,  "gm": 76.7, "opm": 16.7, "fcfm": 18.9, "r40": None},
    "FY2022": {"revenue": 1906, "gov": 1000, "com": 906,  "gm": 73.3, "opm": 19.7, "fcfm": 23.1, "r40": None},
    "FY2023": {"revenue": 2229, "gov": 1222, "com": 1007, "gm": 75.5, "opm": 25.2, "fcfm": 31.2, "r40": 56.4},
    "FY2024": {"revenue": 2870, "gov": 1566, "com": 1304, "gm": 78.9, "opm": 36.0, "fcfm": 30.2, "r40": 66.2},
}
C = {"Bear": "#c0392b", "Base": "#1a3a5c", "Bull": "#27ae60", "実績": "#888"}

# ─── デフォルト ───────────────────────────────────────────────────────────────
_D = {
    "rev_growth":    {"Bear":[25,20,18,15,13,12], "Base":[31,28,25,22,20,18], "Bull":[36,33,30,28,25,22]},
    "gross_margin":  {"Bear":[79,79,80,80,81,81], "Base":[80,81,82,82,83,83], "Bull":[81,82,83,83,84,84]},
    "adj_op_margin": {"Bear":[30,32,34,35,35,36], "Base":[38,40,41,42,42,43], "Bull":[46,48,50,51,52,52]},
    "fcf_margin":    {"Bear":[26,28,30,31,32,33], "Base":[32,34,35,36,37,38], "Bull":[38,40,42,43,44,45]},
    "gov_share":     {"Bear":[54,53,52,51,50,49], "Base":[52,50,48,46,44,42], "Bull":[50,48,46,44,42,40]},
    "nrr":           {"Bear":[118,115,113,112,111,110],"Base":[124,122,120,118,116,115],"Bull":[128,127,125,123,120,118]},
}

def ddf(key): return pd.DataFrame(_D[key], index=YEARS)

def default_val():
    return pd.DataFrame({
        "EV/Rev (x)": [20.0, 38.0, 60.0],
        "WACC (%)":   [10.0, 10.0, 10.0],
        "TGR (%)":    [ 3.0,  3.0,  3.0],
    }, index=["Bear","Base","Bull"])

def default_bal():
    return pd.DataFrame({"Net Cash ($M)":[4600], "Shares (M)":[2200]}, index=["FY2024"])

# ─── 計算 ─────────────────────────────────────────────────────────────────────
def build_model(rg, gm, om, fm, gs, nrr):
    res = {}
    for sc in ["Bear","Base","Bull"]:
        rows, prev = [], BASE_REV
        for yr in YEARS:
            g  = rg.loc[yr,sc]/100;  rev = prev*(1+g)
            _gm=gm.loc[yr,sc]/100; _om=om.loc[yr,sc]/100; _fm=fm.loc[yr,sc]/100
            _gs=gs.loc[yr,sc]/100; _nrr=nrr.loc[yr,sc]/100
            rows.append({"year":yr,"revenue":rev,"yoy":g*100,
                         "gov":rev*_gs,"com":rev*(1-_gs),
                         "gp":rev*_gm,"gm":_gm*100,
                         "op":rev*_om,"om":_om*100,
                         "fcf":rev*_fm,"fm":_fm*100,
                         "r40":g*100+_fm*100,"nrr":_nrr*100})
            prev = rev
        res[sc] = rows
    return res

def build_dcf(rows, wacc_p, tgr_p, net_cash, shares):
    w, g = wacc_p/100, tgr_p/100
    fcfs = [r["fcf"] for r in rows]
    pv1  = sum(f/(1+w)**(i+1) for i,f in enumerate(fcfs))
    tv   = fcfs[-1]*(1+g)/(w-g)
    pvtv = tv/(1+w)**len(fcfs)
    ev   = pv1+pvtv
    eq   = ev+net_cash
    return {"pv1":pv1,"pvtv":pvtv,"tv_pct":pvtv/ev*100,"ev":ev,"eq":eq,"price":eq/shares}

def ev_price(model, sc, mult, nc, sh):
    ev = model[sc][-1]["revenue"]*mult
    return (ev+nc)/sh

# ─── チャート ─────────────────────────────────────────────────────────────────
def fig_rev(model):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=HIST_YEARS, y=[HIST[y]["revenue"] for y in HIST_YEARS],
        mode="lines+markers", name="実績", line=dict(color=C["実績"],dash="dot",width=2), marker=dict(size=5)))
    for sc in ["Bear","Base","Bull"]:
        r = model[sc]
        fig.add_trace(go.Scatter(
            x=["FY2024"]+[x["year"] for x in r], y=[BASE_REV]+[x["revenue"] for x in r],
            mode="lines+markers", name=sc, line=dict(color=C[sc],width=2.5 if sc=="Base" else 1.8), marker=dict(size=5)))
    fig.update_layout(title=dict(text="収益予測 ($M)",font=dict(size=12)),
        height=240, template="plotly_white", margin=dict(t=30,b=15,l=40,r=10),
        legend=dict(orientation="h",y=1.12,x=1,xanchor="right"), yaxis=dict(tickformat="$,.0f"))
    return fig

def fig_seg(model):
    base=model["Base"]
    ay=HIST_YEARS+[r["year"] for r in base]
    ag=[HIST[y]["gov"] for y in HIST_YEARS]+[r["gov"] for r in base]
    ac=[HIST[y]["com"] for y in HIST_YEARS]+[r["com"] for r in base]
    ip=[False]*4+[True]*6
    fig=go.Figure()
    fig.add_trace(go.Bar(x=ay,y=ag,name="Government",marker_color=["#95a5a6" if not p else "#2c6fad" for p in ip]))
    fig.add_trace(go.Bar(x=ay,y=ac,name="Commercial",marker_color=["#bdc3c7" if not p else "#74c0fc" for p in ip]))
    fig.update_layout(barmode="stack",title=dict(text="セグメント収益 (Base)",font=dict(size=12)),
        height=240, template="plotly_white", margin=dict(t=30,b=15,l=40,r=10),
        legend=dict(orientation="h",y=1.12,x=1,xanchor="right"))
    return fig

def fig_margins(model):
    fig=make_subplots(rows=1,cols=3,subplot_titles=["粗利率(%)","調整後OPM(%)","FCFマージン(%)"])
    for col,(k,hk) in enumerate(zip(["gm","om","fm"],["gm","opm","fcfm"]),1):
        fig.add_trace(go.Scatter(x=HIST_YEARS,y=[HIST[y][hk] for y in HIST_YEARS],
            mode="lines+markers",name="実績" if col==1 else "",line=dict(color=C["実績"],dash="dot"),showlegend=(col==1)),row=1,col=col)
        for sc in ["Bear","Base","Bull"]:
            vals=[r[k] for r in model[sc]]
            fig.add_trace(go.Scatter(x=["FY2024"]+[r["year"] for r in model[sc]],
                y=[HIST["FY2024"][hk]]+vals,mode="lines+markers",name=sc if col==1 else "",
                line=dict(color=C[sc]),showlegend=(col==1)),row=1,col=col)
    fig.update_layout(height=230,template="plotly_white",margin=dict(t=35,b=15,l=40,r=10),
        legend=dict(orientation="h",y=1.18,x=1,xanchor="right"))
    return fig

def fig_r40(model):
    fig=go.Figure()
    for sc in ["Bear","Base","Bull"]:
        fig.add_trace(go.Scatter(x=[r["year"] for r in model[sc]],y=[r["r40"] for r in model[sc]],
            mode="lines+markers",name=sc,line=dict(color=C[sc],width=2)))
    hr40={y:HIST[y]["r40"] for y in ["FY2023","FY2024"] if HIST[y]["r40"]}
    fig.add_trace(go.Scatter(x=list(hr40.keys()),y=list(hr40.values()),mode="markers",name="実績",
        marker=dict(size=9,color="#555",symbol="diamond")))
    fig.add_hline(y=40,line_dash="dash",line_color="#e67e22",annotation_text="基準40")
    fig.update_layout(title=dict(text="Rule of 40",font=dict(size=12)),
        height=230,template="plotly_white",margin=dict(t=30,b=15,l=40,r=10))
    return fig

def fig_val_bar(vp):
    fig=go.Figure([go.Bar(x=list(vp.keys()),y=list(vp.values()),
        marker_color=[C[sc] for sc in vp],
        text=[f"${v:,.0f}" for v in vp.values()],textposition="outside")])
    fig.update_layout(title=dict(text="EV/Rev 株価 (FY2030)",font=dict(size=12)),
        height=230,template="plotly_white",margin=dict(t=30,b=15,l=40,r=10),showlegend=False)
    return fig

def fig_dcf_pie(dcf, nc):
    fig=go.Figure(go.Pie(labels=["Phase1 FCF PV","Terminal PV","Net Cash"],
        values=[dcf["pv1"],dcf["pvtv"],nc],hole=0.5,
        marker_colors=["#1a3a5c","#2c6fad","#74c0fc"],textinfo="label+percent"))
    fig.update_layout(title=dict(text=f"DCF 構成 (${dcf['price']:,.0f}/share)",font=dict(size=12)),
        height=230,margin=dict(t=35,b=5,l=5,r=5))
    return fig

def fig_sens():
    nrrs=[110,113,116,120,124,128]; gs=[15,18,22,25,28,33]; bm=38.0
    z=[]
    for n in nrrs:
        row=[]
        for g in gs:
            nb=(n/100-1.15)*50; rs=g+35
            m=bm*(1+(nb+(rs-70))/100)
            row.append(round(max(m,5.0),1))
        z.append(row)
    fig=go.Figure(go.Heatmap(z=z,x=[f"{g}%" for g in gs],y=[f"{n}%" for n in nrrs],
        colorscale="Blues",text=[[f"{v:.1f}x" for v in row] for row in z],
        texttemplate="%{text}",textfont={"size":11},colorbar=dict(title="EV/Rev")))
    fig.update_layout(title=dict(text="センシティビティ: NRR × 成長率 → EV/Revenue",font=dict(size=12)),
        xaxis_title="収益成長率",yaxis_title="NRR",
        height=270,template="plotly_white",margin=dict(t=35,b=25,l=50,r=10))
    return fig

def sec(title):
    st.markdown(f'<div class="sec-hdr">{title}</div>', unsafe_allow_html=True)

def grid_lbl(t):
    st.markdown(f'<div class="grid-lbl">{t}</div>', unsafe_allow_html=True)

# ─── メイン ───────────────────────────────────────────────────────────────────
def main():
    col_t, col_r = st.columns([7,1])
    with col_t:
        st.markdown("## 📊 Palantir (PLTR) 財務モデル シミュレーター")
        st.caption("FY2024 実績ベース | FY2025–FY2030 予測 | 単位: USD Million")
    with col_r:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("↺ リセット", type="secondary"):
            for k in list(st.session_state.keys()): del st.session_state[k]
            st.rerun()

    col_cfg = {c: st.column_config.NumberColumn(c, min_value=0, max_value=200, step=1, format="%d")
               for c in ["Bear","Base","Bull"]}

    # ══════════════════════════════════════════════════════════════════════════
    sec("📐 A. パラメータ入力（セルを直接編集 → 即時再計算）")

    # A-1 収益成長率（全幅）
    grid_lbl("A-1｜収益成長率 (%)")
    rg_df = st.data_editor(ddf("rev_growth"), key="rg",
                            column_config=col_cfg, use_container_width=True, height=255)

    # A-2 利益率 3列
    grid_lbl("A-2｜利益率 (%)")
    ca, cb, cc = st.columns(3)
    with ca:
        st.caption("粗利率")
        gm_df = st.data_editor(ddf("gross_margin"), key="gm",
                                column_config=col_cfg, use_container_width=True, height=255)
    with cb:
        st.caption("調整後 OPM")
        om_df = st.data_editor(ddf("adj_op_margin"), key="om",
                                column_config=col_cfg, use_container_width=True, height=255)
    with cc:
        st.caption("FCF マージン")
        fm_df = st.data_editor(ddf("fcf_margin"), key="fm",
                                column_config=col_cfg, use_container_width=True, height=255)

    # A-3 セグメント / NRR / バリュエーション
    grid_lbl("A-3｜セグメント・NRR・バリュエーション前提")
    cd, ce, cf, cg = st.columns([2,2,3,1.5])
    with cd:
        st.caption("Government 比率 (%)")
        gs_df = st.data_editor(ddf("gov_share"), key="gs",
                                column_config=col_cfg, use_container_width=True, height=255)
    with ce:
        st.caption("NRR (%)")
        nrr_df = st.data_editor(ddf("nrr"), key="nrr",
                                 column_config=col_cfg, use_container_width=True, height=255)
    with cf:
        st.caption("バリュエーション前提")
        val_cfg = {
            "EV/Rev (x)": st.column_config.NumberColumn(min_value=1.0,  max_value=200.0, step=1.0, format="%.1f"),
            "WACC (%)":   st.column_config.NumberColumn(min_value=1.0,  max_value=30.0,  step=0.5, format="%.1f"),
            "TGR (%)":    st.column_config.NumberColumn(min_value=0.0,  max_value=10.0,  step=0.5, format="%.1f"),
        }
        val_df = st.data_editor(default_val(), key="val",
                                 column_config=val_cfg, use_container_width=True, height=160)
    with cg:
        st.caption("BS 前提")
        bal_cfg = {
            "Net Cash ($M)": st.column_config.NumberColumn(min_value=0,   max_value=50000, step=100, format="%d"),
            "Shares (M)":    st.column_config.NumberColumn(min_value=100, max_value=10000, step=50,  format="%d"),
        }
        bal_df = st.data_editor(default_bal(), key="bal",
                                 column_config=bal_cfg, use_container_width=True, height=100)

    # ── 計算 ────────────────────────────────────────────────────────────────
    nc     = float(bal_df.iloc[0]["Net Cash ($M)"])
    sh     = float(bal_df.iloc[0]["Shares (M)"])
    model  = build_model(rg_df, gm_df, om_df, fm_df, gs_df, nrr_df)
    dcf    = build_dcf(model["Base"], val_df.loc["Base","WACC (%)"], val_df.loc["Base","TGR (%)"], nc, sh)
    vp     = {sc: ev_price(model, sc, val_df.loc[sc,"EV/Rev (x)"], nc, sh) for sc in ["Bear","Base","Bull"]}

    # ══════════════════════════════════════════════════════════════════════════
    sec("📌 B. FY2030 サマリー")

    ks = st.columns(6)
    kpis = [
        ("Bear 収益",        f"${model['Bear'][-1]['revenue']:,.0f}M", f"YoY {model['Bear'][-1]['yoy']:.0f}%",  "kpi-bear"),
        ("Base 収益",        f"${model['Base'][-1]['revenue']:,.0f}M", f"YoY {model['Base'][-1]['yoy']:.0f}%",  ""),
        ("Bull 収益",        f"${model['Bull'][-1]['revenue']:,.0f}M", f"YoY {model['Bull'][-1]['yoy']:.0f}%",  "kpi-bull"),
        ("Base OPM / FCF",   f"{model['Base'][-1]['om']:.1f}%",        f"FCF {model['Base'][-1]['fm']:.1f}%",   ""),
        ("Rule of 40 (Base)",f"{model['Base'][-1]['r40']:.1f}",        "目標: 50+",                              ""),
        ("EV/Rev 株価 (Base)",f"${vp['Base']:,.0f}",                   f"Bear ${vp['Bear']:,.0f} – Bull ${vp['Bull']:,.0f}", ""),
    ]
    for col, (lbl, val, sub, cls) in zip(ks, kpis):
        with col:
            st.markdown(
                f'<div class="kpi-box {cls}"><div class="kpi-lbl">{lbl}</div>'
                f'<div class="kpi-val">{val}</div><div class="kpi-sub">{sub}</div></div>',
                unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    sec("📈 C. 収益予測")

    c1, c2 = st.columns(2)
    with c1: st.plotly_chart(fig_rev(model), use_container_width=True)
    with c2: st.plotly_chart(fig_seg(model), use_container_width=True)

    rev_rows = []
    for i, yr in enumerate(YEARS):
        rev_rows.append({
            "FY": yr,
            "Bear 収益": round(model["Bear"][i]["revenue"],0), "Bear YoY%": round(model["Bear"][i]["yoy"],1),
            "Base 収益": round(model["Base"][i]["revenue"],0), "Base YoY%": round(model["Base"][i]["yoy"],1),
            "Bull 収益": round(model["Bull"][i]["revenue"],0), "Bull YoY%": round(model["Bull"][i]["yoy"],1),
            "Gov(Base)": round(model["Base"][i]["gov"],0),
            "Com(Base)": round(model["Base"][i]["com"],0),
            "NRR(Base)%":round(model["Base"][i]["nrr"],1),
        })
    rdf = pd.DataFrame(rev_rows).set_index("FY")
    st.dataframe(
        rdf.style
           .format({c: "${:,.0f}M" for c in ["Bear 収益","Base 収益","Bull 収益","Gov(Base)","Com(Base)"]})
           .format({c: "{:.1f}%" for c in ["Bear YoY%","Base YoY%","Bull YoY%","NRR(Base)%"]})
           .set_properties(**{"font-size":"12px"})
           .set_properties(subset=["Base 収益","Base YoY%"], **{"background-color":"#eaf1fb"}),
        use_container_width=True, height=255)

    # ══════════════════════════════════════════════════════════════════════════
    sec("💰 D. 利益構造（Base シナリオ）")

    c1, c2 = st.columns([3,1])
    with c1: st.plotly_chart(fig_margins(model), use_container_width=True)
    with c2: st.plotly_chart(fig_r40(model), use_container_width=True)

    prof_rows = []
    for i, yr in enumerate(YEARS):
        b = model["Base"][i]
        prof_rows.append({
            "FY": yr,
            "収益($M)": round(b["revenue"],0), "粗利($M)": round(b["gp"],0),
            "粗利率%": round(b["gm"],1),
            "OP($M)": round(b["op"],0), "OPM%": round(b["om"],1),
            "FCF($M)": round(b["fcf"],0), "FCF%": round(b["fm"],1),
            "Rule of 40": round(b["r40"],1),
        })
    pdf = pd.DataFrame(prof_rows).set_index("FY")
    st.dataframe(
        pdf.style
           .format({c: "${:,.0f}M" for c in ["収益($M)","粗利($M)","OP($M)","FCF($M)"]})
           .format({c: "{:.1f}%" for c in ["粗利率%","OPM%","FCF%"]})
           .format({"Rule of 40": "{:.1f}"})
           .set_properties(**{"font-size":"12px"})
           .set_properties(subset=["Rule of 40"], **{"background-color":"#eaf7ee"}),
        use_container_width=True, height=255)

    # ══════════════════════════════════════════════════════════════════════════
    sec("🎯 E. バリュエーション")

    c1, c2, c3 = st.columns([2,2,2])

    with c1:
        st.caption("**EV/Revenue マルチプル法**")
        vrows = []
        for sc in ["Bear","Base","Bull"]:
            fr   = model[sc][-1]["revenue"]
            mult = val_df.loc[sc,"EV/Rev (x)"]
            ev_  = fr*mult
            vrows.append({"シナリオ":sc,"FY2030収益":round(fr,0),"EV/Rev":round(mult,1),
                          "EV":round(ev_,0),"Equity":round(ev_+nc,0),"株価":round(vp[sc],0)})
        vvdf = pd.DataFrame(vrows).set_index("シナリオ")
        st.dataframe(
            vvdf.style
                .format({c: "${:,.0f}M" for c in ["FY2030収益","EV","Equity"]})
                .format({"EV/Rev":"{:.1f}x","株価":"${:,.0f}"})
                .set_properties(**{"font-size":"12px"}),
            use_container_width=True, height=155)
        st.plotly_chart(fig_val_bar(vp), use_container_width=True)

    with c2:
        st.caption("**DCF（Base シナリオ）**")
        dcf_rows = [
            {"項目":"WACC",               "値":f"{val_df.loc['Base','WACC (%)']:.1f}%"},
            {"項目":"ターミナル成長率",     "値":f"{val_df.loc['Base','TGR (%)']:.1f}%"},
            {"項目":"Phase1 PV (FCF)",    "値":f"${dcf['pv1']:,.0f}M"},
            {"項目":"Terminal Value PV",   "値":f"${dcf['pvtv']:,.0f}M"},
            {"項目":"TV / EV 比率",       "値":f"{dcf['tv_pct']:.1f}%"},
            {"項目":"インプライド EV",     "値":f"${dcf['ev']:,.0f}M"},
            {"項目":"Equity Value",        "値":f"${dcf['eq']:,.0f}M"},
            {"項目":"株価 (USD/share)",   "値":f"${dcf['price']:,.0f}"},
        ]
        st.dataframe(pd.DataFrame(dcf_rows).set_index("項目"),
                     use_container_width=True, height=310)
        st.plotly_chart(fig_dcf_pie(dcf, nc), use_container_width=True)

    with c3:
        st.caption("**センシティビティ: NRR × 成長率 → EV/Revenue**")
        st.plotly_chart(fig_sens(), use_container_width=True)
        st.caption("**キー仮定サマリー**")
        st.dataframe(pd.DataFrame([
            {"仮定":"Bootcamp 成約率","Base":"~75%","Bear":"60%台","Bull":"80%+"},
            {"仮定":"US Com 成長",   "Base":"+25-28%","Bear":"+15-18%","Bull":"+33-36%"},
            {"仮定":"NRR",          "Base":"120-122%","Bear":"115-118%","Bull":"125-128%"},
            {"仮定":"EV/Revenue",   "Base":"38x","Bear":"20x","Bull":"60x"},
        ]).set_index("仮定"), use_container_width=True, height=175)

if __name__ == "__main__":
    main()
