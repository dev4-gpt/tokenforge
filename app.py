"""Offline-first results and research replay: streamlit run app.py."""
from pathlib import Path
import html
import json
import altair as alt
import pandas as pd
import streamlit as st
from tokenforge.reporting import load_bundle, export_candidates

ROOT = Path(__file__).parent
st.set_page_config(page_title='TokenForge', layout='wide', initial_sidebar_state='collapsed')
runs = sorted((ROOT / 'results').glob('r-*.json'), reverse=True)
run_file = st.sidebar.selectbox('Run', [p.name for p in runs])
appearance = st.sidebar.selectbox('Appearance', ['Light', 'Dark'])
if st.sidebar.button('Refresh export from Atlas'):
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env')
    try:
        export_candidates(Path(run_file).stem)
        st.success('Export refreshed')
    except Exception as e:
        st.error(f'Refresh unavailable: {type(e).__name__}')
try:
    data = load_bundle(Path(run_file).stem)
except (ValueError, OSError) as e:
    st.error(str(e))
    st.stop()
st.sidebar.caption('Evidence: local replay. Atlas refresh is optional.')
dark = appearance == 'Dark'
colors = ('#0e1116','#161a21','#eef1f5','#a3acb9','#2a313b') if dark else ('#f4f6f9','#ffffff','#121821','#566070','#dde2e9')
bg, surface, ink, muted, line = colors
st.markdown(f'''<style>
[data-testid="stAppViewContainer"] {{background:{bg};color:{ink};}}
[data-testid="stHeader"] {{background:transparent;}}
[data-testid="stSidebar"] {{background:{surface};}}
.stButton button, [data-baseweb="select"] > div {{background:{surface};color:{ink};border-color:{line};}}
[data-baseweb="tab-highlight"] {{background:#2a78d6;}}
.block-container {{max-width:1120px;padding-top:2rem;padding-bottom:3rem;}}
h1,h2,h3,p,label {{color:{ink};}} h1 {{font-size:2.8rem!important;letter-spacing:-.04em;}}
.hero {{background:{surface};border:1px solid {line};border-radius:12px;padding:24px;margin:16px 0 24px;}}
.hero .big {{color:#2a78d6;font-size:clamp(2.5rem,7vw,4.5rem);font-weight:700;line-height:1.1;}}
.hero p {{color:{muted};margin:8px 0;}}
.facts {{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin-top:20px;}}
.fact {{border-top:1px solid {line};padding-top:12px;min-width:0;}}
.fact strong {{display:block;font-size:1.4rem;}} .fact span {{color:{muted};font-size:.85rem;}}
[data-testid="stTabs"] button p {{font-size:1rem;}}
@media(max-width:600px) {{.block-container{{padding-left:16px;padding-right:16px;}}.facts{{grid-template-columns:1fr;}}h1{{font-size:2rem!important;}}}}
</style>''', unsafe_allow_html=True)
st.caption('C0MPILED-15 · LUMINAL · MONGODB ATLAS · APPLE M3 PRO')
st.title('TokenForge')
st.write('A research team that proposes, tests, and shares evidence to optimize local LLM inference.')
results, experiments, memory, code = st.tabs(['Results', 'Experiments', 'Memory', 'Code'])
candidates = pd.DataFrame(data['candidates'])
rounds = pd.DataFrame(data['rounds'])
held = data['heldout']


def chart_style(chart):
    return chart.configure(background='transparent').configure_axis(labelColor=ink,titleColor=muted,gridColor=line).configure_legend(labelColor=ink,titleColor=ink).configure_view(stroke=None)


def progression():
    rows = [{'round':0,'speedup':1.0,'event':'Baseline','champion':'baseline'}] + [
        {'round':r['round'],'speedup':r['champion_dev_speedup'],'event':'Promotion' if r.get('promoted_id') else 'Remeasurement','champion':r['champion_id'] or 'baseline'} for r in data['rounds']]
    frame = pd.DataFrame(rows)
    base = alt.Chart(frame).encode(x=alt.X('round:Q',axis=alt.Axis(tickMinStep=1),title='Round'),y=alt.Y('speedup:Q',scale=alt.Scale(zero=True),title='Speedup over baseline'),tooltip=['round','speedup','event','champion'])
    return chart_style(base.mark_line(color='#2a78d6') + base.mark_point(size=65).encode(color=alt.Color('event:N',legend=alt.Legend(title=None))))

with results:
    headline = f"{held['speedup_geomean']:.2f}×" if held and held.get('champion_status') == 'ok' else 'Not evaluated'
    correct = sum(c['status']=='ok' for c in data['candidates'])
    promoted = sum(bool(c.get('promoted')) for c in data['candidates'])
    st.markdown(f'''<div class="hero"><div class="big">{headline}</div><p>Fresh-test speedup over the scalar baseline · matching run only</p><div class="facts"><div class="fact"><strong>{len(candidates)}</strong><span>Candidate attempts</span></div><div class="fact"><strong>{correct}</strong><span>Passed generated-text checks</span></div><div class="fact"><strong>{promoted}</strong><span>Recorded promotions</span></div></div></div>''',unsafe_allow_html=True)
    if held:
        values = [{'model':i['model'].replace('.bin',''),'build':build,'tok_s':i[key]} for i in held['items'] for build,key in [('Baseline','baseline_tps'),('OpenMP -O3','omp_tps'),('Champion','champion_tps')]]
        st.subheader('Local inference throughput')
        bars = alt.Chart(pd.DataFrame(values)).mark_bar().encode(x=alt.X('tok_s:Q',title='Tokens / second · shared scale',scale=alt.Scale(domain=[0,max(v['tok_s'] for v in values)*1.1])),y=alt.Y('model:N',title=None),yOffset='build:N',color=alt.Color('build:N',scale=alt.Scale(domain=['Baseline','OpenMP -O3','Champion'],range=['#9aa3af','#eb6834','#2a78d6']),legend=alt.Legend(title=None)),tooltip=['model','build',alt.Tooltip('tok_s:Q',format='.2f')]).properties(height=280)
        st.altair_chart(chart_style(bars),use_container_width=True)
        st.caption('Identical generated text on tested greedy-decoding prompts. This does not imply identical floating-point values.')
    stats = data['champion_stats']
    st.caption(f"Final champion on development: {stats['median']:.2f}× median, {stats['min']:.2f}–{stats['max']:.2f}× across {stats['count']} measurements of that kernel. Validation scores are historical promotion measurements.")
    st.subheader('Performance across rounds')
    st.altair_chart(progression(),use_container_width=True)
    st.caption('Round 0 is the starting baseline. Each point is a measurement; fluctuations alone are not new improvements.')
    lineage = candidates[candidates['promoted']==True] if len(candidates) else candidates
    if len(lineage):
        st.dataframe(lineage[['round','agent','mode','speedup','val','note']].rename(columns={'val':'validation_at_promotion'}),hide_index=True,use_container_width=True,column_config={'speedup':st.column_config.NumberColumn('Dev',format='%.2f×'),'validation_at_promotion':st.column_config.NumberColumn('Validation at promotion',format='%.2f×')})
    if data['comparison']:
        st.subheader('Contemporaneous comparison')
        summary = data['comparison']['summary']
        st.dataframe(pd.DataFrame([{'Kernel':name,'Dev ×':r['dev']['median_speedup'],'Validation ×':r['validation']['median_speedup'],'Later gain distinguished':r.get('vs_previous',{}).get('clears_margin_in_every_block',False)} for name,r in summary.items()]),hide_index=True,use_container_width=True,column_config={'Dev ×':st.column_config.NumberColumn(format='%.2f'),'Validation ×':st.column_config.NumberColumn(format='%.2f')})
        st.caption('Ten randomized blocks confirm the large initial gain. Later promotions did not consistently clear the promotion margin; observed ranges are not confidence intervals.')
        with st.expander('Raw comparison summary'):
            st.json(summary)

with experiments:
    st.subheader('Every experiment')
    if len(candidates):
        dots=alt.Chart(candidates).mark_circle(size=65).encode(x=alt.X('round:Q',axis=alt.Axis(tickMinStep=1)),y=alt.Y('speedup:Q',title='Development speedup'),color='status:N',tooltip=['round','agent','mode','status','speedup','note'])
        st.altair_chart(chart_style(dots),use_container_width=True)
    counts=pd.DataFrame([{'round':r['round'],'outcome':out,'count':count} for r in data['rounds'] for out,count in [('Passed',r['n_ok']),('Failed',r['n_failed'])]])
    if len(counts):
        bars=alt.Chart(counts).mark_bar().encode(x=alt.X('round:O',title='Round'),y=alt.Y('count:Q',title='Attempts',stack='zero'),color=alt.Color('outcome:N',scale=alt.Scale(domain=['Passed','Failed'],range=['#2a78d6','#d03b3b'])),tooltip=['round','outcome','count'])
        st.altair_chart(chart_style(bars),use_container_width=True)
    st.caption('Passed + failed equals actual attempts. No-code/provider failures are distinct from generated-code failures.')
    st.dataframe(candidates[['round','agent','mode','status','speedup','error']] if len(candidates) else candidates,hide_index=True,use_container_width=True)
    if data['study']:
        st.subheader('Exploratory memory study')
        study=data['study']
        st.write(study['interpretation'])
        st.dataframe(pd.DataFrame([{'Condition':r['condition'],'Replicate':r['replicate'],'Passed':f"{r['passed']}/{r['attempts']}",'Fresh ×':r['fresh_speedup'],'Code failures':r['code_failures'],'Repeated failures':r.get('repeated_failures',0),'Tokens recorded':r['tokens']} for r in study['conditions']]),hide_index=True,use_container_width=True,column_config={'Fresh ×':st.column_config.NumberColumn(format='%.2f')})
        st.caption(study.get('token_note','Recorded token usage may be incomplete for timed-out calls.'))
        with st.expander('Study protocol and raw summary'):
            st.json(study)
        st.caption(f"Completed: {study['complete']} · {study['proposals']} proposals · fresh cases evaluated only after freezing winners")

with memory:
    st.subheader('Verified feedback and shared history')
    trace=data['repair']
    if trace:
        st.write('Stored failure → retrieved evidence → new repair → independent evaluation')
        st.success(f"Atlas {trace['retrieval_method']} retrieval · {trace['original_status']} → {trace['repair_status']}")
        st.text(trace['lesson']['rule'])
        st.caption('Verified on development and validation prompts; this trace demonstrates feedback use, not a causal memory advantage.')
        with st.expander('Source IDs and evaluation results'):
            st.json({k:v for k,v in trace.items() if k not in ('original_code','repaired_code','prompt','memory_context')})
        with st.expander('Retrieved evidence and exact prompt'):
            st.json(trace.get('memory_context',[]))
            st.code(trace.get('prompt',''),language='text')
        with st.expander('Failure and repaired implementation'):
            st.code(trace.get('original_code',''),language='c')
            st.code(trace.get('repaired_code',''),language='c')
    else:
        st.info('Historical retrieval context was not recorded. The exported candidates establish storage and lineage, not a causal memory advantage.')
    for agent in range(6):
        with st.expander(f'Agent {agent} · {"fast" if agent%2==0 else "reasoner"}'):
            records=[c for c in data['candidates'] if c['agent']==agent]
            st.write(f'{len(records)} recorded attempts')
            st.json([{'id':c['id'],'round':c['round'],'parent_id':c.get('parent_id'),'retrieved_ids':c.get('retrieved_ids','Not recorded historically'),'status':c['status']} for c in records])

with code:
    st.caption(f"Frozen champion SHA-256: {data['kernel_sha256']}")
    with st.expander('Scalar baseline',expanded=False):
        st.code(data['baseline_code'],language='c')
    with st.expander('Submitted champion',expanded=False):
        st.code(data['champion_code'],language='c')
    st.write('Only matmul is optimized. Results concern the tested models and laptop. Model weights do not change.')
