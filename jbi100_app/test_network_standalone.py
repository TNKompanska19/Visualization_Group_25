"""Network Tester with POSITION EXPORT"""
import dash
from dash import html, callback, Output, Input, State
import dash_cytoscape as cyto
import pandas as pd
import numpy as np
from sklearn.linear_model import Lasso
import math
import json

services_df = pd.read_csv('jbi100_app/data/services_weekly.csv')
staff_schedule_df = pd.read_csv('jbi100_app/data/staff_schedule.csv')
ANOMALY_WEEKS = [3,6,9,12,15,18,21,24,27,30,33,36,39,42,45,48,51]
ROLE_COLORS = {'doctor': '#56C1C1', 'nurse': '#B57EDC', 'nursing_assistant': '#FFD166'}

valid_weeks = [w for w in range(1,53) if w not in ANOMALY_WEEKS]
full_services = services_df[services_df['week'].isin(valid_weeks) & (services_df['service']=='emergency')].sort_values('week').set_index('week')
full_staff = staff_schedule_df[staff_schedule_df['week'].isin(valid_weeks) & (staff_schedule_df['service']=='emergency')].copy()
all_staff = full_staff[['staff_id','staff_name','role']].drop_duplicates()
staff_presence = full_staff.pivot_table(index='week',columns='staff_id',values='present',aggfunc='max',fill_value=0).reindex(full_services.index,fill_value=0)
staff_variance = staff_presence.var()
active_ids = staff_variance[staff_variance>0].index
staff_presence = staff_presence[active_ids]

model = Lasso(alpha=1.63, max_iter=10000)
model.fit(staff_presence.values.astype(float), full_services['staff_morale'].values.astype(float))

impacts_df = pd.DataFrame({'staff_id': active_ids, 'morale_impact': model.coef_}).merge(all_staff, on='staff_id')
week_staff = full_staff[full_staff['week']==1]
working_ids = week_staff[week_staff['present']==1]['staff_id'].tolist()
impacts_df['working'] = impacts_df['staff_id'].isin(working_ids)
abs_impacts = np.abs(impacts_df['morale_impact'].values)
impacts_df['size'] = 40 + (abs_impacts/abs_impacts.max()*40) if abs_impacts.max()>0 else 50

role_counts = impacts_df.groupby('role').size()
sorted_roles = sorted(role_counts.items(), key=lambda x: x[1], reverse=True)

role_positions = {
    sorted_roles[0][0]: {'x':500,'y':550,'start':0.2*math.pi,'end':0.8*math.pi},
    sorted_roles[1][0]: {'x':250,'y':250,'start':0.9*math.pi,'end':1.6*math.pi},
    sorted_roles[2][0]: {'x':750,'y':250,'start':1.9*math.pi,'end':2.6*math.pi}
}

elements = []
elements.append({'data':{'id':'dept','label':'Emergency','type':'dept'},'position':{'x':500,'y':350}})

for role in impacts_df['role'].unique():
    if role in role_positions:
        rid = f"role_{role}"
        elements.append({'data':{'id':rid,'label':role.replace('_',' ').title(),'type':'role','role_name':role},'position':role_positions[role]})
        elements.append({'data':{'source':'dept','target':rid}})

for role in impacts_df['role'].unique():
    if role not in role_positions:
        continue
    rd = impacts_df[impacts_df['role']==role]
    working = rd[rd['working']==True].reset_index(drop=True)
    not_working = rd[rd['working']==False].reset_index(drop=True)
    rp = role_positions[role]
    
    for idx,row in working.iterrows():
        n = len(working)
        angle = (rp['start']+rp['end'])/2 if n==1 else rp['start']+(rp['end']-rp['start'])*idx/(n-1)
        x = rp['x']+200*math.cos(angle)
        y = rp['y']+200*math.sin(angle)
        sid = f"staff_{row['staff_id']}"
        elements.append({'data':{'id':sid,'label':row['staff_name'],'type':'staff','size':float(row['size']),'color':ROLE_COLORS[role],'opacity':1.0,'border_width':5},'position':{'x':x,'y':y}})
        elements.append({'data':{'source':f"role_{role}",'target':sid}})
    
    for idx,row in not_working.iterrows():
        n = len(not_working)
        angle = (rp['start']+rp['end'])/2 if n==1 else rp['start']+(rp['end']-rp['start'])*idx/(n-1)
        x = rp['x']+280*math.cos(angle)
        y = rp['y']+280*math.sin(angle)
        sid = f"staff_{row['staff_id']}"
        elements.append({'data':{'id':sid,'label':row['staff_name'],'type':'staff','size':float(row['size']),'color':ROLE_COLORS[role],'opacity':0.3,'border_width':2},'position':{'x':x,'y':y}})
        elements.append({'data':{'source':f"role_{role}",'target':sid}})

stylesheet = [
    {'selector':'[type="dept"]','style':{'background-color':'#2c3e50','label':'data(label)','color':'white','font-size':'28px','font-weight':'bold','width':'170px','height':'170px','shape':'round-rectangle','text-valign':'center','text-halign':'center','border-width':5,'border-color':'white'}},
    {'selector':'[role_name="doctor"]','style':{'background-color':ROLE_COLORS['doctor'],'label':'data(label)','color':'white','font-size':'24px','font-weight':'bold','width':'150px','height':'150px','shape':'diamond','text-valign':'center','text-halign':'center','border-width':4,'border-color':'white'}},
    {'selector':'[role_name="nurse"]','style':{'background-color':ROLE_COLORS['nurse'],'label':'data(label)','color':'white','font-size':'24px','font-weight':'bold','width':'150px','height':'150px','shape':'diamond','text-valign':'center','text-halign':'center','border-width':4,'border-color':'white'}},
    {'selector':'[role_name="nursing_assistant"]','style':{'background-color':ROLE_COLORS['nursing_assistant'],'label':'data(label)','color':'#2c3e50','font-size':'22px','font-weight':'bold','width':'150px','height':'150px','shape':'diamond','text-valign':'center','text-halign':'center','border-width':4,'border-color':'white'}},
    {'selector':'[type="staff"]','style':{'background-color':'data(color)','label':'data(label)','color':'#2c3e50','font-size':'15px','font-weight':'600','width':'data(size)','height':'data(size)','shape':'ellipse','opacity':'data(opacity)','border-width':'data(border_width)','border-color':'#2c3e50','text-valign':'center','text-halign':'center'}},
    {'selector':'edge','style':{'width':2,'line-color':'#666','opacity':0.4}},
    {'selector':':selected','style':{'border-width':8,'border-color':'#e74c3c'}}
]

app = dash.Dash(__name__)
app.layout = html.Div([
    html.H1("Network Tester with Position Export", style={'textAlign':'center','color':'#2c3e50'}),
    html.P("✓ Drag nodes to adjust layout, then click EXPORT to print positions!",
           style={'textAlign':'center','color':'#e74c3c','marginBottom':'20px','fontWeight':'bold'}),
    html.Button("📋 EXPORT POSITIONS", id='export-btn', n_clicks=0, 
                style={'display':'block','margin':'0 auto 20px','padding':'12px 24px','fontSize':'16px','fontWeight':'bold','backgroundColor':'#27ae60','color':'white','border':'none','borderRadius':'8px','cursor':'pointer'}),
    cyto.Cytoscape(id='net',elements=elements,style={'width':'100%','height':'700px'},layout={'name':'preset'},stylesheet=stylesheet),
    html.Pre(id='export-output',style={'marginTop':'20px','padding':'15px','backgroundColor':'#f9f9f9','borderRadius':'5px','fontSize':'11px','maxHeight':'200px','overflow':'auto','fontFamily':'monospace'})
],style={'padding':'40px','maxWidth':'1600px','margin':'0 auto'})

@callback(
    Output('export-output','children'),
    Input('export-btn','n_clicks'),
    State('net','elements')
)
def export_positions(n_clicks, current_elements):
    if n_clicks == 0:
        return "Click EXPORT button after arranging nodes to your liking!"
    
    # Extract positions from elements
    positions = {}
    for elem in current_elements:
        if 'position' in elem and 'source' not in elem.get('data', {}):
            node_id = elem['data']['id']
            pos = elem['position']
            positions[node_id] = {'x': round(pos['x'],1), 'y': round(pos['y'],1)}
    
    output = "# Copy this to your code:\\n\\nPOSITIONS = {\\n"
    for node_id, pos in positions.items():
        output += f"    '{node_id}': {pos},\\n"
    output += "}\\n\\n# Then use: elements.append({..., 'position': POSITIONS[node_id]})"
    
    print("\\n" + "="*60)
    print("EXPORTED POSITIONS:")
    print("="*60)
    print(output)
    print("="*60 + "\\n")
    
    return output

if __name__=='__main__':
    print("\\nDrag nodes to adjust, then click EXPORT to get positions!\\n")
    app.run(debug=True,port=8050)