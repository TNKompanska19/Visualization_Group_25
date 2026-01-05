"""
Quality Widget - Staff Impact Network + Metrics
T5+T6: Interactive network - click to toggle staff, predict outcomes
"""

import pandas as pd
import numpy as np
import math
from sklearn.linear_model import Ridge, Lasso, ElasticNet
from dash import dcc, html
import dash_cytoscape as cyto
import plotly.graph_objects as go

from jbi100_app.config import DEPT_COLORS as CONFIG_DEPT_COLORS, DEPT_LABELS_SHORT

# Optimal hyperparameters from tuning
OPTIMAL_HYPERPARAMS = {
    'emergency': {
        'morale': {'model': 'Lasso', 'alpha': 1.629751},
        'satisfaction': {'model': 'Lasso', 'alpha': 0.849753}
    },
    'surgery': {
        'morale': {'model': 'ElasticNet', 'alpha': 1.519911, 'l1_ratio': 0.65},
        'satisfaction': {'model': 'ElasticNet', 'alpha': 1.747528, 'l1_ratio': 0.35}
    },
    'general_medicine': {
        'morale': {'model': 'Lasso', 'alpha': 1.218593},
        'satisfaction': {'model': 'Ridge', 'alpha': 27.825594}
    },
    'ICU': {
        'morale': {'model': 'Ridge', 'alpha': 27.503878},
        'satisfaction': {'model': 'Lasso', 'alpha': 1.072267}
    }
}

ROLE_COLORS = {
    'doctor': '#56C1C1',
    'nurse': '#B57EDC',
    'nursing_assistant': '#FFD166'
}

ANOMALY_WEEKS = [3, 6, 9, 12, 15, 18, 21, 24, 27, 30, 33, 36, 39, 42, 45, 48, 51]

# Global cache for model data
_model_cache = {}

# Global cache for STABLE node positions per department
# Key: (department, staff_id) -> (x, y)
# This ensures staff nodes stay in the same place across weeks
_position_cache = {}


def compute_staff_impacts_all_weeks(services_df, staff_schedule_df, department):
    """Compute staff impact coefficients and store model for predictions."""
    valid_weeks = [w for w in range(1, 53) if w not in ANOMALY_WEEKS]
    
    full_services = services_df[
        services_df['week'].isin(valid_weeks) & 
        (services_df['service'] == department)
    ].copy().sort_values('week').set_index('week')
    
    full_staff = staff_schedule_df[
        staff_schedule_df['week'].isin(valid_weeks) &
        (staff_schedule_df['service'] == department)
    ].copy()
    
    if full_services.empty or full_staff.empty:
        return None, None
    
    all_staff = full_staff[['staff_id', 'staff_name', 'role']].drop_duplicates()
    
    staff_presence = full_staff.pivot_table(
        index='week', columns='staff_id', values='present',
        aggfunc='max', fill_value=0
    ).reindex(full_services.index, fill_value=0)
    
    staff_variance = staff_presence.var()
    active_staff_ids = staff_variance[staff_variance > 0].index.tolist()
    staff_presence = staff_presence[active_staff_ids]
    n_staff = len(active_staff_ids)
    
    events_encoded = pd.get_dummies(full_services['event'], prefix='event')
    events_encoded = events_encoded.drop(columns=['event_no_event'], errors='ignore')
    
    X = pd.concat([staff_presence, events_encoded], axis=1).values.astype(float)
    y_morale = full_services['staff_morale'].values.astype(float)
    y_satisfaction = full_services['patient_satisfaction'].values.astype(float)
    
    # Fit MORALE model
    mp = OPTIMAL_HYPERPARAMS[department]['morale']
    if mp['model'] == 'Lasso':
        m_model = Lasso(alpha=mp['alpha'], max_iter=10000)
    elif mp['model'] == 'Ridge':
        m_model = Ridge(alpha=mp['alpha'])
    else:
        m_model = ElasticNet(alpha=mp['alpha'], l1_ratio=mp['l1_ratio'], max_iter=10000)
    m_model.fit(X, y_morale)
    
    # Fit SATISFACTION model
    sp = OPTIMAL_HYPERPARAMS[department]['satisfaction']
    if sp['model'] == 'Lasso':
        s_model = Lasso(alpha=sp['alpha'], max_iter=10000)
    elif sp['model'] == 'Ridge':
        s_model = Ridge(alpha=sp['alpha'])
    else:
        s_model = ElasticNet(alpha=sp['alpha'], l1_ratio=sp['l1_ratio'], max_iter=10000)
    s_model.fit(X, y_satisfaction)
    
    impacts_df = pd.DataFrame({
        'staff_id': active_staff_ids,
        'morale_impact': m_model.coef_[:n_staff],
        'satisfaction_impact': s_model.coef_[:n_staff]
    }).merge(all_staff, on='staff_id', how='left')
    
    # Store model info for predictions
    _model_cache[department] = {
        'morale_coefs': dict(zip(active_staff_ids, m_model.coef_[:n_staff])),
        'morale_intercept': m_model.intercept_,
        'satisfaction_coefs': dict(zip(active_staff_ids, s_model.coef_[:n_staff])),
        'satisfaction_intercept': s_model.intercept_,
        'staff_ids': active_staff_ids
    }
    
    # Store historical configurations (which staff worked together each week)
    week_configs = {}
    for week in valid_weeks:
        week_staff = full_staff[full_staff['week'] == week]
        working_ids = frozenset(week_staff[week_staff['present'] == 1]['staff_id'].tolist())
        week_configs[week] = working_ids
    _model_cache[department]['week_configs'] = week_configs
    _model_cache[department]['services_df'] = full_services
    
    # Create per-week data
    week_data = {}
    for week in valid_weeks:
        week_staff = full_staff[full_staff['week'] == week]
        working_ids = week_staff[week_staff['present'] == 1]['staff_id'].tolist()
        week_impacts = impacts_df.copy()
        week_impacts['working_this_week'] = week_impacts['staff_id'].isin(working_ids)
        week_data[week] = week_impacts
    
    return week_data, impacts_df


def predict_from_team(department, active_staff_ids):
    """
    Predict morale and satisfaction for a given team configuration.
    Returns: (morale, satisfaction, is_historical, matching_week)
    """
    if department not in _model_cache:
        return None, None, False, None
    
    cache = _model_cache[department]
    active_set = frozenset(active_staff_ids)
    
    # Check if this configuration exists historically
    for week, config in cache['week_configs'].items():
        if config == active_set:
            # Found matching historical week
            services = cache['services_df']
            if week in services.index:
                row = services.loc[week]
                return row['staff_morale'], row['patient_satisfaction'], True, week
    
    # No match - predict using model
    morale_pred = cache['morale_intercept']
    sat_pred = cache['satisfaction_intercept']
    
    for staff_id in active_staff_ids:
        if staff_id in cache['morale_coefs']:
            morale_pred += cache['morale_coefs'][staff_id]
        if staff_id in cache['satisfaction_coefs']:
            sat_pred += cache['satisfaction_coefs'][staff_id]
    
    # Clamp to 0-100 range
    morale_pred = max(0, min(100, morale_pred))
    sat_pred = max(0, min(100, sat_pred))
    
    return morale_pred, sat_pred, False, None


def fan_positions(count, origin_x, origin_y, angle, base_distance=50, spread_angle=120):
    """Generate fan/tree positions branching from origin.
    
    Args:
        angle: Center angle in degrees (0=right, 90=down, 180=left, 270=up)
        spread_angle: Total angular spread in degrees
    """
    if count == 0:
        return []
    
    center_angle = math.radians(angle)
    
    positions = []
    max_per_ring = 8
    ring = 0
    placed = 0
    
    while placed < count:
        ring_count = min(max_per_ring, count - placed)
        ring_distance = base_distance + ring * 40
        half_spread = math.radians(spread_angle / 2)
        
        if ring_count == 1:
            angles = [center_angle]
        else:
            angles = [
                center_angle - half_spread + (2 * half_spread * i / (ring_count - 1))
                for i in range(ring_count)
            ]
        
        for ang in angles:
            x = origin_x + ring_distance * math.cos(ang)
            y = origin_y + ring_distance * math.sin(ang)
            positions.append((x, y))
            placed += 1
            if placed >= count:
                break
        ring += 1
    
    return positions


def generate_stylesheet(working_ids):
    """
    Generate stylesheet that highlights working staff and dims non-working.
    This approach preserves node positions when toggling.
    """
    base_stylesheet = [
        {'selector': '[node_type = "department"]',
         'style': {
             'background-color': '#2c3e50', 'label': 'data(label)', 'color': 'white',
             'font-size': '10px', 'font-weight': 'bold', 'width': '70px', 'height': '26px',
             'shape': 'round-rectangle', 'text-valign': 'center', 'text-halign': 'center',
             'border-width': 2, 'border-color': 'white'
         }},
        {'selector': '[node_type = "role"]',
         'style': {
             'label': 'data(label)', 'color': 'white', 'font-size': '8px', 'font-weight': 'bold',
             'width': '45px', 'height': '45px', 'shape': 'diamond',
             'text-valign': 'center', 'text-halign': 'center',
             'text-wrap': 'wrap', 'text-max-width': '43px',
             'border-width': 2, 'border-color': 'white'
         }},
        {'selector': '[role_name = "doctor"]', 'style': {'background-color': ROLE_COLORS['doctor']}},
        {'selector': '[role_name = "nurse"]', 'style': {'background-color': ROLE_COLORS['nurse']}},
        {'selector': '[role_name = "nursing_assistant"]', 
         'style': {'background-color': ROLE_COLORS['nursing_assistant'], 'color': '#2c3e50'}},
        # Default staff style (non-working)
        {'selector': '[node_type = "staff"]',
         'style': {
             'background-color': 'data(color)', 'label': 'data(label)', 'color': '#2c3e50',
             'font-size': '6px', 'font-weight': '500',
             'width': 'data(size)', 'height': 'data(size)', 'shape': 'ellipse',
             'opacity': 0.3, 'border-width': 1,
             'border-color': '#999', 'text-valign': 'center', 'text-halign': 'center'
         }},
        # Default edge style (hidden for staff edges)
        {'selector': 'edge[source ^= "role_"]',
         'style': {'width': 1, 'line-color': '#ddd', 'opacity': 0, 'curve-style': 'bezier'}},
        # Role-to-department edges always visible
        {'selector': 'edge[target ^= "role_"]',
         'style': {'width': 1, 'line-color': '#ddd', 'opacity': 0.4, 'curve-style': 'bezier'}},
        {'selector': ':active', 'style': {'overlay-opacity': 0.2, 'overlay-color': '#3498db'}}
    ]
    
    # Add styles for each working staff member
    for staff_id in working_ids:
        # Highlight working staff
        base_stylesheet.append({
            'selector': f'[id = "staff_{staff_id}"]',
            'style': {
                'opacity': 1.0,
                'border-width': 3,
                'border-color': '#2c3e50'
            }
        })
        # Show edge for working staff
        base_stylesheet.append({
            'selector': f'edge[target = "staff_{staff_id}"]',
            'style': {
                'opacity': 0.4
            }
        })
    
    return base_stylesheet


def create_network_for_week(staff_impacts, department, week, metric='morale', custom_working=None, include_all_edges=False):
    """Create network with STABLE positions (nodes stay in same place across weeks).
    
    Key design principle: Positions are computed ONCE per department based on 
    staff_id (stable sort), then cached. This ensures:
    - User can track individual staff across weeks by position
    - Only brightness/size changes, not location
    - Supports Object Constancy (Munzner) - maintain spatial mapping
    
    Args:
        staff_impacts: DataFrame with staff impact data for this week
        department: Department name
        week: Week number
        metric: 'morale' or 'satisfaction' for impact sizing
        custom_working: Optional list of staff_ids to show as working (overrides data)
        include_all_edges: If True, include all edges (visibility via stylesheet)
    """
    global _position_cache
    
    if staff_impacts is None or staff_impacts.empty:
        return []
    
    elements = []
    impact_col = f'{metric}_impact'
    
    max_impact = staff_impacts[impact_col].abs().max()
    if max_impact == 0:
        max_impact = 1
    
    # Narrower canvas
    CENTER_X = 220
    CENTER_Y = 40
    
    dept_id = f"dept_{department}"
    elements.append({
        'data': {
            'id': dept_id,
            'label': department.replace('_', ' ').title(),
            'node_type': 'department'
        },
        'position': {'x': CENTER_X, 'y': CENTER_Y}
    })
    
    ROLE_CONFIG = {
        'doctor': {'x': CENTER_X - 90, 'y': CENTER_Y + 0, 'angle': 200, 'spread': 120},
        'nurse': {'x': CENTER_X, 'y': CENTER_Y + 50, 'angle': 90, 'spread': 120},
        'nursing_assistant': {'x': CENTER_X + 90, 'y': CENTER_Y + 0, 'angle': 30, 'spread': 160}
    }
    
    # Check if we need to compute and cache positions for this department
    cache_key = department
    if cache_key not in _position_cache:
        # First time for this department - compute STABLE positions
        # Sort by staff_id (alphabetically) for consistent ordering across all weeks
        _position_cache[cache_key] = {}
        
        for role, config in ROLE_CONFIG.items():
            role_staff = staff_impacts[staff_impacts['role'] == role].copy()
            if role_staff.empty:
                continue
            
            # STABLE SORT: by staff_id (not by working status or impact)
            role_staff = role_staff.sort_values('staff_id')
            
            role_x, role_y = config['x'], config['y']
            positions = fan_positions(len(role_staff), role_x, role_y, config['angle'],
                                     base_distance=40, spread_angle=config['spread'])
            
            for idx, (_, row) in enumerate(role_staff.iterrows()):
                if idx < len(positions):
                    staff_id = row['staff_id']
                    _position_cache[cache_key][staff_id] = positions[idx]
    
    # Now build elements using cached positions
    for role, config in ROLE_CONFIG.items():
        role_staff = staff_impacts[staff_impacts['role'] == role].copy()
        if role_staff.empty:
            continue
        
        role_x, role_y = config['x'], config['y']
        role_id = f"role_{role}"
        role_label = 'Nursing\nAssistants' if role == 'nursing_assistant' else role.title() + 's'
        
        elements.append({
            'data': {
                'id': role_id,
                'label': role_label,
                'node_type': 'role',
                'role_name': role
            },
            'position': {'x': role_x, 'y': role_y}
        })
        elements.append({'data': {'source': dept_id, 'target': role_id}})
        
        for _, row in role_staff.iterrows():
            staff_id_val = row['staff_id']
            
            # Get cached position (stable across weeks)
            if staff_id_val in _position_cache[cache_key]:
                pos_x, pos_y = _position_cache[cache_key][staff_id_val]
            else:
                # Fallback (shouldn't happen if cache is built correctly)
                pos_x, pos_y = role_x, role_y + 50
            
            # Compute size based on current metric's impact
            abs_impact = abs(row[impact_col])
            normalized_impact = abs_impact / max_impact
            size = 16 + normalized_impact * 24
            
            # Determine working status
            if custom_working is not None:
                is_working = staff_id_val in custom_working
            else:
                is_working = row['working_this_week']
            
            # Visual properties (stylesheet will override based on working status)
            opacity = 1.0 if is_working else 0.3
            border_width = 3 if is_working else 1
            border_color = '#2c3e50' if is_working else '#999'
            
            staff_id = f"staff_{staff_id_val}"
            last_name = row['staff_name'].split()[-1][:6]
            
            elements.append({
                'data': {
                    'id': staff_id,
                    'label': last_name,
                    'full_name': row['staff_name'],
                    'staff_id_raw': staff_id_val,
                    'node_type': 'staff',
                    'size': float(size),
                    'color': ROLE_COLORS[role],
                    'opacity': opacity,
                    'border_width': border_width,
                    'border_color': border_color,
                    'is_working': is_working,
                    'impact': float(row[impact_col])
                },
                'position': {'x': pos_x, 'y': pos_y}
            })
            
            # Add edge: always if include_all_edges, otherwise only if working
            if include_all_edges or is_working:
                elements.append({'data': {'source': role_id, 'target': staff_id}})
    
    return elements


def create_comparison_bars(department, week, morale_val, sat_val, is_predicted=False, 
                           avg_morale=None, avg_satisfaction=None):
    """Create compact comparison bar charts with predicted/actual indicator."""
    
    morale_diff = morale_val - avg_morale if avg_morale else 0
    sat_diff = sat_val - avg_satisfaction if avg_satisfaction else 0
    
    label_suffix = "*" if is_predicted else ""
    week_color_morale = '#27ae60' if morale_diff >= 0 else '#e74c3c'
    week_color_sat = '#27ae60' if sat_diff >= 0 else '#e74c3c'
    
    # Bar positioning: numeric x for precise control
    bar_width = 0.35
    x_positions = [0, 0.45]  # Close together
    
    # MORALE
    morale_fig = go.Figure()
    morale_fig.add_trace(go.Bar(
        x=x_positions,
        y=[avg_morale, morale_val],
        marker_color=['#bdc3c7', week_color_morale],
        marker_line_color=['#bdc3c7', '#e67e22' if is_predicted else week_color_morale],
        marker_line_width=[0, 3 if is_predicted else 0],
        text=[f'{avg_morale:.0f}', f'{morale_val:.0f}'],
        textposition='inside',
        textfont=dict(size=10, color='white'),
        width=bar_width,
        showlegend=False
    ))
    diff_color = '#27ae60' if morale_diff >= 0 else '#e74c3c'
    diff_text = f'+{morale_diff:.0f}' if morale_diff >= 0 else f'{morale_diff:.0f}'
    morale_fig.add_annotation(x=x_positions[1], y=morale_val + 8, text=f"<b>{diff_text}</b>",
                              showarrow=False, font=dict(size=10, color=diff_color))
    morale_fig.update_layout(
        title=dict(text='Morale', font=dict(size=10, color='#2c3e50'), x=0.5, y=0.97),
        yaxis=dict(
            range=[0, 105], 
            showgrid=True, 
            gridcolor='#f0f0f0',
            showticklabels=True,
            tickfont=dict(size=8, color='#7f8c8d'),
            tickvals=[0, 25, 50, 75, 100]
        ),
        xaxis=dict(
            tickmode='array',
            tickvals=x_positions,
            ticktext=['Avg', f'W{week}{label_suffix}'],
            tickfont=dict(size=8),
            range=[-0.3, 0.75]
        ),
        margin=dict(l=25, r=5, t=20, b=18),
        height=120,
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    
    # SATISFACTION
    sat_fig = go.Figure()
    sat_fig.add_trace(go.Bar(
        x=x_positions,
        y=[avg_satisfaction, sat_val],
        marker_color=['#bdc3c7', week_color_sat],
        marker_line_color=['#bdc3c7', '#e67e22' if is_predicted else week_color_sat],
        marker_line_width=[0, 3 if is_predicted else 0],
        text=[f'{avg_satisfaction:.0f}', f'{sat_val:.0f}'],
        textposition='inside',
        textfont=dict(size=10, color='white'),
        width=bar_width,
        showlegend=False
    ))
    diff_color = '#27ae60' if sat_diff >= 0 else '#e74c3c'
    diff_text = f'+{sat_diff:.0f}' if sat_diff >= 0 else f'{sat_diff:.0f}'
    sat_fig.add_annotation(x=x_positions[1], y=sat_val + 8, text=f"<b>{diff_text}</b>",
                           showarrow=False, font=dict(size=10, color=diff_color))
    sat_fig.update_layout(
        title=dict(text='Satisfaction', font=dict(size=10, color='#2c3e50'), x=0.5, y=0.97),
        yaxis=dict(
            range=[0, 105], 
            showgrid=True, 
            gridcolor='#f0f0f0',
            showticklabels=True,
            tickfont=dict(size=8, color='#7f8c8d'),
            tickvals=[0, 25, 50, 75, 100]
        ),
        xaxis=dict(
            tickmode='array',
            tickvals=x_positions,
            ticktext=['Avg', f'W{week}{label_suffix}'],
            tickfont=dict(size=8),
            range=[-0.3, 0.75]
        ),
        margin=dict(l=25, r=5, t=20, b=18),
        height=120,
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    
    return morale_fig, sat_fig


def create_config_comparison_chart(saved_configs, avg_morale, avg_satisfaction):
    """
    Create grouped bar chart comparing saved configurations.
    
    Justification (Munzner M3_03, M4_01, M4_04):
    - Side-by-side bars: "Eyes beat Memory" - low cognitive load comparison
    - Position/length channels: highest accuracy for quantitative comparison
    - Grouped layout: effective for comparing across categories (configs)
    """
    if not saved_configs:
        # Empty state
        fig = go.Figure()
        fig.add_annotation(
            text="Save configurations to compare",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=10, color='#bdc3c7')
        )
        fig.update_layout(
            margin=dict(l=5, r=5, t=5, b=5),
            height=100,
            plot_bgcolor='white',
            paper_bgcolor='white',
            xaxis=dict(visible=False),
            yaxis=dict(visible=False)
        )
        return fig
    
    # Build data
    config_names = ['Avg'] + [c['name'][:8] for c in saved_configs]
    morale_values = [avg_morale] + [c['morale'] for c in saved_configs]
    satisfaction_values = [avg_satisfaction] + [c['satisfaction'] for c in saved_configs]
    n_configs = len(config_names)
    
    # Numeric positioning: smaller bars, tight gaps
    bar_width = 0.15
    inner_gap = 0.05  # Gap between morale and satisfaction bars
    group_gap = 0.25  # Gap between config groups
    
    # Calculate x positions
    morale_x = []
    satisfaction_x = []
    tick_positions = []
    
    current_x = 0
    for i in range(n_configs):
        morale_x.append(current_x)
        satisfaction_x.append(current_x + bar_width + inner_gap)
        tick_positions.append(current_x + bar_width + inner_gap / 2)  # Center of group
        current_x += bar_width * 2 + inner_gap + group_gap
    
    fig = go.Figure()
    
    # Morale bars (blue - consistent with week context chart)
    fig.add_trace(go.Bar(
        name='Morale',
        x=morale_x,
        y=morale_values,
        marker_color='#3498db',
        text=[f'{v:.0f}' for v in morale_values],
        textposition='inside',
        textfont=dict(size=8, color='white'),
        width=bar_width
    ))
    
    # Satisfaction bars (purple - distinct from green/red good/bad indicators)
    fig.add_trace(go.Bar(
        name='Satisf.',
        x=satisfaction_x,
        y=satisfaction_values,
        marker_color='#9b59b6',
        text=[f'{v:.0f}' for v in satisfaction_values],
        textposition='inside',
        textfont=dict(size=8, color='white'),
        width=bar_width
    ))
    
    fig.update_layout(
        barmode='overlay',  # Since we're using explicit x positions
        margin=dict(l=20, r=5, t=25, b=20),
        height=100,
        plot_bgcolor='white',
        paper_bgcolor='white',
        showlegend=True,
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='center',
            x=0.5,
            font=dict(size=7)
        ),
        yaxis=dict(
            range=[0, 105],
            showgrid=True,
            gridcolor='#f0f0f0',
            tickfont=dict(size=7, color='#7f8c8d'),
            tickvals=[0, 50, 100]
        ),
        xaxis=dict(
            tickmode='array',
            tickvals=tick_positions,
            ticktext=config_names,
            tickfont=dict(size=7),
            range=[-0.2, current_x - group_gap + 0.2]
        )
    )
    
    return fig


def create_week_slider_marks(hide_anomalies=False):
    """Create slider marks for all 52 weeks."""
    marks = {}
    for w in range(1, 53):
        if w in ANOMALY_WEEKS:
            if hide_anomalies:
                continue
            marks[w] = {'label': str(w), 'style': {'color': '#bdc3c7', 'fontSize': '7px'}}
        else:
            marks[w] = {'label': str(w), 'style': {'color': '#3498db', 'fontSize': '7px'}}
    return marks


def create_week_context_chart(services_df, department, selected_week, metric='staff_morale'):
    """
    Create a compact bar chart showing metric values across all weeks.
    Highlights selected week and dims anomaly weeks.
    
    Justification (Munzner):
    - Bar chart uses position (most accurate channel) for quantitative comparison
    - Color hue distinguishes selected week (categorical: selected vs not)
    - Aligned with slider below for direct mapping (position → week)
    """
    dept_data = services_df[services_df['service'] == department].copy()
    
    if dept_data.empty:
        fig = go.Figure()
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=40)
        return fig
    
    # Get all weeks 1-52, plus phantom weeks 0 and 53 for edge padding
    weeks = list(range(0, 54))  # 0 to 53
    values = []
    colors = []
    
    # Calculate average for reference line
    valid_data = dept_data[~dept_data['week'].isin(ANOMALY_WEEKS)]
    avg_val = valid_data[metric].mean() if not valid_data.empty else 0
    
    for w in weeks:
        if w == 0 or w == 53:
            # Phantom weeks - invisible padding
            values.append(0)
            colors.append('rgba(0,0,0,0)')  # Transparent
        else:
            week_row = dept_data[dept_data['week'] == w]
            if not week_row.empty:
                val = week_row[metric].values[0]
                values.append(val)
                if w == selected_week:
                    colors.append('#2c3e50')  # Dark - selected
                elif w in ANOMALY_WEEKS:
                    colors.append('#95a5a6')  # Gray - anomaly week (but real data)
                else:
                    colors.append('#3498db')  # Blue - normal
            else:
                # Missing data
                values.append(0)
                colors.append('rgba(0,0,0,0)')
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=weeks,
        y=values,
        marker_color=colors,
        width=0.8,
        cliponaxis=False,  # Prevents clipping edge bars
        hovertemplate='Week %{x}<br>' + metric.replace('_', ' ').title() + ': %{y:.0f}<extra></extra>',
        showlegend=False
    ))
    
    # Add subtle average reference line (no label to allow symmetric margins)
    if avg_val > 0:
        fig.add_hline(y=avg_val, line_dash='dot', line_color='#e74c3c', line_width=1, opacity=0.5)
    
    # Range [0, 53] includes phantom weeks; bars 1-52 align with slider marks
    fig.update_layout(
        margin=dict(l=7, r=7, t=0, b=0),
        height=40,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(
            showgrid=False,
            showticklabels=False,
            zeroline=False,
            range=[0, 53],  # Phantom weeks 0 and 53 provide edge padding
            fixedrange=True
        ),
        yaxis=dict(
            showgrid=False,
            showticklabels=False,
            zeroline=False,
            range=[0, 105],
            fixedrange=True
        ),
        bargap=0.1  # Reduced gap for tighter bar spacing
    )
    
    return fig


def create_quality_mini_sparkline(services_df, selected_depts, week_range, highlighted_week=None, hide_anomalies=False, highlight_color=None):
    """
    Create a compact MORALE-ONLY sparkline showing ALL selected departments.
    
    Justification (Munzner M4_04 - Coordinated Multiple Views):
    - Multiple lines with consistent colors match Overview widget
    - Shaded region shows selected range (filter context)
    - Vertical marker highlights hovered week from Overview (linking)
    - Same color encoding across views reduces cognitive load (M3_03 Eyes beat Memory)
    
    Design changes (Cleveland & McGill accuracy):
    - Dynamic x-axis ticks based on week range for precise position reading
    - More ticks = easier week identification without mental interpolation
    
    Args:
        selected_depts: List of department IDs to display
        hide_anomalies: If True, exclude anomaly weeks from display (Filter - Yi et al.)
        highlight_color: Color for the vertical week highlight line (matches hovered dept)
    """
    from jbi100_app.config import DEPT_COLORS
    
    week_min, week_max = week_range
    
    if not selected_depts:
        fig = go.Figure()
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=100)
        return fig
    
    fig = go.Figure()
    
    # Add shaded region for selected week range
    fig.add_vrect(
        x0=week_min - 0.5, x1=week_max + 0.5,
        fillcolor="rgba(52, 152, 219, 0.1)",
        line_width=0,
        layer="below"
    )
    
    # Add a line for each selected department
    for dept in selected_depts:
        dept_data = services_df[services_df['service'] == dept].sort_values('week')
        
        # Filter out anomaly weeks if requested
        if hide_anomalies:
            dept_data = dept_data[~dept_data['week'].isin(ANOMALY_WEEKS)]
        
        if dept_data.empty:
            continue
        
        color = DEPT_COLORS.get(dept, '#3498db')
        
        fig.add_trace(go.Scatter(
            x=dept_data['week'],
            y=dept_data['staff_morale'],
            mode='lines',
            line=dict(color=color, width=2),
            name=dept.replace('_', ' ').title()[:8],
            hovertemplate='W%{x}: %{y:.0f}<extra></extra>'
        ))
    
    # Add highlighted week marker if provided (Linking & Brushing M4_04)
    if highlighted_week is not None:
        show_highlight = True
        if hide_anomalies and highlighted_week in ANOMALY_WEEKS:
            show_highlight = False
        
        if show_highlight:
            # Use provided color or default to orange
            line_color = highlight_color or "#e67e22"
            
            # Vertical line at hovered week (spans all department lines)
            fig.add_vline(
                x=highlighted_week, 
                line_color=line_color,
                line_width=2,
                line_dash="solid"
            )
    
    # Dynamic x-axis ticks based on week range (Cleveland & McGill: position accuracy)
    # Goal: 5-8 ticks for optimal readability without clutter
    week_span = week_max - week_min + 1
    if week_span <= 12:
        tick_interval = 2   # Every 2 weeks for short ranges (W1-12)
    elif week_span <= 26:
        tick_interval = 4   # Every 4 weeks (~monthly)
    else:
        tick_interval = 8   # Every 8 weeks for full year
    
    # Generate tick values starting from week_min
    tick_vals = list(range(week_min, week_max + 1, tick_interval))
    # Always include last week if not already present
    if week_max not in tick_vals:
        tick_vals.append(week_max)
    tick_text = [f'W{w}' for w in tick_vals]
    
    fig.update_layout(
        margin=dict(l=28, r=8, t=4, b=18),  # Reduced top margin (title moved to widget header)
        height=100,  # Increased from 80 (reclaimed space from bottom hint)
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        showlegend=False,
        # Title removed - now in widget header (Tufte: maximize data-ink ratio)
        xaxis=dict(
            showgrid=False,
            showticklabels=True,
            tickvals=tick_vals,
            ticktext=tick_text,
            tickfont=dict(size=8, color='#64748b'),
            zeroline=False,
            fixedrange=True,
            range=[week_min - 0.5, week_max + 0.5]  # Dynamic range based on selection
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='rgba(0,0,0,0.05)',
            showticklabels=True,
            tickvals=[0, 25, 50, 75, 100],  # Quartiles for better precision
            ticktext=['0', '25', '50', '75', '100'],
            tickfont=dict(size=7, color='#94a3b8'),
            zeroline=False,
            range=[0, 105],  # Full 0-100 range (Tufte: graphical integrity)
            fixedrange=True
        ),
        hovermode='x unified'
    )
    
    return fig


def create_quality_mini(services_df, staff_schedule_df, selected_depts, week_range, hide_anomalies=False):
    """
    Create minimized quality widget - STAFF-FOCUSED (not duplicating Overview).
    
    Design Justification (Munzner):
    - Complementary info: Overview shows satisfaction trends, Quality shows staff/morale
    - Shneiderman's Mantra: "Overview first" - summary without expansion
    - Yi et al. Abstract/Elaborate: Click to expand for network details
    - M4_04 Linking & Brushing: KPIs update on hover from Overview widget
    - Tufte's Data-Ink Ratio: Interaction hint moved to header to maximize chart space
    
    Content (unique to Quality - not in Overview):
    - Staff composition by role
    - Morale metrics (updates on hover - shows week value or avg)
    - Morale sparkline (now larger with more x-axis ticks)
    
    Args:
        hide_anomalies: If True, exclude anomaly weeks from calculations/display (Filter - Yi et al.)
    """
    if not selected_depts:
        return html.Div([
            html.Div("👥 Staff Quality", 
                     style={"fontWeight": "600", "fontSize": "14px", "color": "#2c3e50"}),
            html.Div("Select a department", style={"fontSize": "11px", "color": "#999"})
        ])
    
    # Use first department for reference, but calculate aggregate stats
    department = selected_depts[0]
    week_min, week_max = week_range
    
    # Get data for ALL selected departments in range (for true aggregate)
    all_dept_data = services_df[
        (services_df['service'].isin(selected_depts)) &
        (services_df['week'] >= week_min) &
        (services_df['week'] <= week_max)
    ]
    
    # Filter out anomaly weeks if requested (Yi et al. Filter interaction)
    if hide_anomalies:
        all_dept_data = all_dept_data[~all_dept_data['week'].isin(ANOMALY_WEEKS)]
    
    # Calculate AGGREGATE morale KPIs across all selected departments
    # This gives true overview (Shneiderman's mantra: overview first)
    if not all_dept_data.empty:
        avg_morale = all_dept_data['staff_morale'].mean()  # True average across all
        min_morale = all_dept_data['staff_morale'].min()
        max_morale = all_dept_data['staff_morale'].max()
    else:
        avg_morale = min_morale = max_morale = 0
    
    # Build per-department info for display
    dept_info = []
    total_staff = 0
    for dept in selected_depts:
        dept_staff = staff_schedule_df[staff_schedule_df['service'] == dept]
        dept_count = dept_staff['staff_id'].nunique()
        
        # Get avg morale for this dept in range
        dept_morale_data = services_df[
            (services_df['service'] == dept) &
            (services_df['week'] >= week_min) &
            (services_df['week'] <= week_max)
        ]
        if hide_anomalies:
            dept_morale_data = dept_morale_data[~dept_morale_data['week'].isin(ANOMALY_WEEKS)]
        
        dept_avg_morale = dept_morale_data['staff_morale'].mean() if not dept_morale_data.empty else 0
        
        dept_info.append({
            'dept': dept,
            'staff': dept_count,
            'morale': dept_avg_morale,
            'color': CONFIG_DEPT_COLORS.get(dept, '#3498db'),
            'label': DEPT_LABELS_SHORT.get(dept, dept[:3])
        })
        total_staff += dept_count
    
    # Create sparkline with ALL selected departments
    sparkline_fig = create_quality_mini_sparkline(
        services_df, selected_depts, week_range, 
        highlighted_week=None, hide_anomalies=hide_anomalies
    )
    
    # Format header based on number of departments
    if len(selected_depts) == 1:
        header_subtitle = f"{department.replace('_', ' ').title()} • W{week_min}-{week_max}"
    else:
        header_subtitle = f"{len(selected_depts)} depts • W{week_min}-{week_max}"
    
    return html.Div(
        style={"height": "100%", "display": "flex", "flexDirection": "column"},
        children=[
            # Header row: Title + expand link (Tufte: maximize data-ink by moving hint here)
            html.Div(
                style={
                    "display": "flex", 
                    "justifyContent": "space-between", 
                    "alignItems": "center",
                    "marginBottom": "2px"
                },
                children=[
                    html.Span(
                        "👥 Staff Quality",  # Clearer title (Munzner: meaningful labels)
                        style={"fontWeight": "600", "fontSize": "14px", "color": "#2c3e50"}
                    ),
                    # Expand hint moved here - saves ~15% vertical space (Tufte: data-ink ratio)
                    html.Span(
                        "↗ Network",
                        style={
                            "fontSize": "9px", 
                            "color": "#0ea5e9", 
                            "cursor": "pointer",
                            "fontWeight": "500"
                        }
                    )
                ]
            ),
            html.Div(
                header_subtitle,
                style={"fontSize": "10px", "color": "#64748b", "marginBottom": "4px"}
            ),
            
            # Compact KPI row with per-department breakdown
            html.Div(
                style={
                    "display": "flex",
                    "gap": "4px",
                    "backgroundColor": "#f8f9fa",
                    "borderRadius": "6px",
                    "padding": "4px 6px",
                    "marginBottom": "4px",
                    "alignItems": "center"
                },
                children=[
                    # Staff count section
                    html.Div(
                        id="quality-mini-staff-section",
                        children=[
                            html.Div(
                                id="quality-mini-staff-header",
                                children=[
                                    html.Span(
                                        id="quality-mini-staff-total",
                                        children=f"{total_staff}",
                                        style={"fontSize": "13px", "fontWeight": "700", "color": "#2c3e50"}
                                    ),
                                    html.Span(
                                        id="quality-mini-staff-label",
                                        children=" staff",
                                        style={"fontSize": "8px", "color": "#64748b"}
                                    ),
                                ],
                                style={"marginBottom": "2px"}
                            ),
                            # Per-dept breakdown
                            html.Div(
                                id="quality-mini-staff-breakdown",
                                children=[
                                    html.Span([
                                        html.Span(f"{info['staff']}", style={
                                            "color": info['color'], "fontWeight": "600", "fontSize": "9px"
                                        }),
                                        html.Span(f" {info['label']} ", style={"fontSize": "7px", "color": "#64748b"})
                                    ]) for info in dept_info
                                ] if len(selected_depts) > 1 else [],
                                style={"lineHeight": "1.2"}
                            )
                        ],
                        style={"flex": "1", "textAlign": "center", "borderRight": "1px solid #e2e8f0"}
                    ),
                    
                    # Morale section
                    html.Div(
                        id="quality-mini-morale-section",
                        children=[
                            html.Div(
                                id="quality-mini-morale-header",
                                children=[
                                    html.Span(
                                        id="quality-mini-morale-value",
                                        children=f"{avg_morale:.0f}",
                                        style={"fontSize": "13px", "fontWeight": "700", "color": "#0ea5e9"}
                                    ),
                                    html.Span(
                                        id="quality-mini-morale-label",
                                        children=" avg morale",
                                        style={"fontSize": "8px", "color": "#64748b"}
                                    ),
                                ],
                                style={"marginBottom": "2px"}
                            ),
                            # Per-dept morale breakdown
                            html.Div(
                                id="quality-mini-morale-breakdown",
                                children=[
                                    html.Span([
                                        html.Span(f"{info['morale']:.0f}", style={
                                            "color": info['color'], "fontWeight": "600", "fontSize": "9px"
                                        }),
                                        html.Span(f" {info['label']} ", style={"fontSize": "7px", "color": "#64748b"})
                                    ]) for info in dept_info
                                ] if len(selected_depts) > 1 else [],
                                style={"lineHeight": "1.2"}
                            )
                        ],
                        style={"flex": "1", "textAlign": "center"}
                    ),
                ]
            ),
            
            # Hidden store for department context (used by callback)
            dcc.Store(id="quality-mini-dept-store", data={
                "selected_depts": selected_depts,
                "department": department,
                "avg_morale": avg_morale,
                "min_morale": min_morale,
                "max_morale": max_morale,
                "hide_anomalies": hide_anomalies,
                "total_staff": total_staff,
                "dept_info": dept_info  # Per-dept staff/morale/color
            }),
            
            # Morale sparkline - now uses full remaining space (no bottom hint)
            # Chart title "Morale Trend" added as small label above
            html.Div(
                style={"flex": "1", "minHeight": "60px", "display": "flex", "flexDirection": "column"},
                children=[
                    html.Div(
                        "Morale Trend",  # Clear chart title (Munzner: label what user sees)
                        style={
                            "fontSize": "9px", 
                            "color": "#64748b", 
                            "fontWeight": "500",
                            "marginBottom": "2px",
                            "textAlign": "center"
                        }
                    ),
                    dcc.Graph(
                        id="quality-mini-sparkline",
                        figure=sparkline_fig,
                        config={"displayModeBar": False, "staticPlot": True},
                        style={"flex": "1", "width": "100%", "minHeight": "0"}
                    )
                ]
            )
            # Bottom hint REMOVED - now in header (Tufte: maximize data-ink ratio)
        ]
    )


def create_quality_widget(services_df, staff_schedule_df, selected_depts, week_range):
    """Create quality widget with interactive network."""
    
    if not selected_depts:
        return html.Div(
            style={"height": "100%", "display": "flex", "alignItems": "center", "justifyContent": "center"},
            children=[
                html.Div([
                    html.H4("Staff Configuration", style={'color': '#2c3e50', 'marginBottom': '10px'}),
                    html.P("Select a department to view staff impact network.", style={'color': '#7f8c8d'})
                ], style={'textAlign': 'center'})
            ]
        )
    
    department = selected_depts[0]
    result = compute_staff_impacts_all_weeks(services_df, staff_schedule_df, department)
    
    if result is None or result[0] is None:
        return html.Div(
            style={"height": "100%", "display": "flex", "alignItems": "center", "justifyContent": "center"},
            children=[html.P("No data available.", style={'color': '#e74c3c'})]
        )
    
    week_data, all_impacts = result
    valid_weeks = [w for w in range(1, 53) if w not in ANOMALY_WEEKS]
    first_week = valid_weeks[0]
    
    # Get initial working staff
    initial_working = week_data[first_week][week_data[first_week]['working_this_week']]['staff_id'].tolist()
    
    initial_elements = create_network_for_week(week_data[first_week], department, first_week, 'morale', include_all_edges=True)
    
    # Get averages for comparison
    dept_services = services_df[services_df['service'] == department]
    avg_morale = dept_services['staff_morale'].mean()
    avg_satisfaction = dept_services['patient_satisfaction'].mean()
    
    # Initial values from first week
    first_week_data = dept_services[dept_services['week'] == first_week]
    init_morale = first_week_data['staff_morale'].values[0] if not first_week_data.empty else avg_morale
    init_sat = first_week_data['patient_satisfaction'].values[0] if not first_week_data.empty else avg_satisfaction
    
    morale_fig, sat_fig = create_comparison_bars(department, first_week, init_morale, init_sat, 
                                                  False, avg_morale, avg_satisfaction)
    slider_marks = create_week_slider_marks(hide_anomalies=False)
    
    # Create week context sparkline
    week_context_fig = create_week_context_chart(services_df, department, first_week)
    
    morale_params = OPTIMAL_HYPERPARAMS[department]['morale']
    sat_params = OPTIMAL_HYPERPARAMS[department]['satisfaction']
    working_count = len(initial_working)
    
    # Generate initial stylesheet based on working staff
    stylesheet = generate_stylesheet(initial_working)
    
    # Layout
    header = html.Div(
        style={'flexShrink': '0', 'marginBottom': '4px', 'display': 'flex', 
               'justifyContent': 'space-between', 'alignItems': 'center'},
        children=[
            html.Div([
                html.H4(f"Staff Configuration: {department.replace('_', ' ').title()}", 
                        style={'color': '#2c3e50', 'margin': '0', 'fontSize': '14px'}),
                html.Span(f"{len(all_impacts)} staff | {morale_params['model']} / {sat_params['model']}", 
                          style={'fontSize': '9px', 'color': '#7f8c8d'})
            ]),
            # Working count (toggle moved to legend area)
            html.Div(id='working-count-display', children=[
                html.Span("# assigned: ", style={'fontSize': '10px', 'color': '#7f8c8d'}),
                html.Span(f"{working_count}", style={'fontSize': '13px', 'color': '#27ae60', 'fontWeight': 'bold'})
            ])
        ]
    )
    
    main_content = html.Div(
        style={'flex': '1', 'display': 'flex', 'gap': '8px', 'minHeight': '0'},
        children=[
            # LEFT: Network + Slider (60%)
            html.Div(
                style={'flex': '0.6', 'display': 'flex', 'flexDirection': 'column', 'minWidth': '0'},
                children=[
                    # Week selector with context chart
                    html.Div(style={'flexShrink': '0', 'marginBottom': '5px'}, children=[
                        html.Div(style={'display': 'flex', 'alignItems': 'center', 'gap': '5px', 'marginBottom': '2px'}, children=[
                            html.Label("Week:", style={'fontSize': '9px', 'color': '#7f8c8d'}),
                            html.Span(id='selected-week-display', children=str(first_week),
                                      style={'fontSize': '11px', 'fontWeight': 'bold', 'color': '#2c3e50'})
                        ]),
                        # Context sparkline above slider
                        dcc.Graph(id='week-context-chart', figure=week_context_fig,
                                  config={'displayModeBar': False}, 
                                  style={'height': '40px', 'marginBottom': '-5px'}),
                        # Slider aligned with sparkline
                        dcc.Slider(id='quality-week-slider', min=1, max=52, value=first_week,
                                   marks=slider_marks, step=1, included=False,
                                   tooltip={"placement": "bottom", "always_visible": False})
                    ]),
                    # Network + instructions
                    html.Div(style={'flex': '1', 'display': 'flex', 'flexDirection': 'column', 'minHeight': '0'}, children=[
                        html.Div(style={'fontSize': '8px', 'color': '#7f8c8d', 'textAlign': 'center', 'marginBottom': '3px'},
                                 children="💡 Click staff nodes to toggle assignment"),
                        html.Div(style={'flex': '1', 'border': '1px solid #dee2e6', 'borderRadius': '6px', 
                                        'backgroundColor': 'white', 'minHeight': '0'}, children=[
                            cyto.Cytoscape(
                                id='staff-network-weekly',
                                elements=initial_elements,
                                style={'width': '100%', 'height': '100%'},
                                layout={'name': 'preset'},
                                stylesheet=stylesheet,
                                minZoom=0.4, maxZoom=2.5,
                                autoRefreshLayout=False
                            )
                        ])
                    ]),
                    # Legend + Impact toggle (Gestalt proximity: controls near what they affect)
                    html.Div(style={'flexShrink': '0', 'marginTop': '4px', 'fontSize': '8px', 'textAlign': 'center',
                                    'display': 'flex', 'justifyContent': 'center', 'alignItems': 'center', 'gap': '8px', 'flexWrap': 'wrap'}, children=[
                        # Role legend
                        html.Div(style={'display': 'flex', 'alignItems': 'center', 'gap': '6px'}, children=[
                            html.Span("●", style={'color': ROLE_COLORS['doctor']}),
                            html.Span("Doc", style={'marginRight': '4px'}),
                            html.Span("●", style={'color': ROLE_COLORS['nurse']}),
                            html.Span("Nurse", style={'marginRight': '4px'}),
                            html.Span("●", style={'color': ROLE_COLORS['nursing_assistant']}),
                            html.Span("Asst")
                        ]),
                        # Separator
                        html.Span("|", style={'color': '#ccc'}),
                        # Size encoding explanation + toggle
                        html.Div(style={'display': 'flex', 'alignItems': 'center', 'gap': '4px'}, children=[
                            html.Span("Size=", style={'color': '#7f8c8d'}),
                            html.Button(
                                "Morale",
                                id='impact-morale-btn',
                                n_clicks=0,
                                style={
                                    'padding': '2px 6px', 'fontSize': '8px', 'fontWeight': '600',
                                    'backgroundColor': '#3498db', 'color': 'white',
                                    'border': 'none', 'borderRadius': '3px 0 0 3px', 'cursor': 'pointer'
                                }
                            ),
                            html.Button(
                                "Satisf.",
                                id='impact-satisfaction-btn',
                                n_clicks=0,
                                style={
                                    'padding': '2px 6px', 'fontSize': '8px', 'fontWeight': '500',
                                    'backgroundColor': '#ecf0f1', 'color': '#7f8c8d',
                                    'border': 'none', 'borderRadius': '0 3px 3px 0', 'cursor': 'pointer'
                                }
                            ),
                            html.Span("impact", style={'color': '#7f8c8d', 'marginLeft': '2px'})
                        ]),
                        # Separator
                        html.Span("|", style={'color': '#ccc'}),
                        # Brightness + line encoding
                        html.Span("● Bright + line = Assigned", style={'color': '#7f8c8d'})
                    ])
                ]
            ),
            
            # RIGHT: Bar charts + placeholders (40%)
            html.Div(
                style={'flex': '0.4', 'display': 'flex', 'flexDirection': 'column', 'gap': '5px', 'minWidth': '0'},
                children=[
                    # Top row: Status + Bar charts side by side
                    html.Div(style={'display': 'flex', 'gap': '5px', 'flexShrink': '0'}, children=[
                        # Morale chart
                        html.Div(style={'flex': '1', 'display': 'flex', 'flexDirection': 'column'}, children=[
                            html.Div(style={'textAlign': 'center', 'fontSize': '8px', 'color': '#7f8c8d'},
                                     children="vs Avg"),
                            dcc.Graph(id='morale-comparison-chart', figure=morale_fig,
                                      config={'displayModeBar': False}, style={'height': '120px'})
                        ]),
                        # Satisfaction chart
                        html.Div(style={'flex': '1', 'display': 'flex', 'flexDirection': 'column'}, children=[
                            html.Div(id='prediction-status', 
                                     style={'textAlign': 'center', 'fontSize': '8px', 'minHeight': '14px'}),
                            dcc.Graph(id='satisfaction-comparison-chart', figure=sat_fig,
                                      config={'displayModeBar': False}, style={'height': '120px'})
                        ])
                    ]),
                    # Save configuration section
                    html.Div(style={'flex': '1', 'border': '1px solid #dee2e6', 'borderRadius': '6px',
                                    'padding': '8px', 'minHeight': '60px', 'backgroundColor': 'white',
                                    'display': 'flex', 'flexDirection': 'column', 'gap': '5px'},
                             children=[
                                 html.Div(style={'display': 'flex', 'gap': '5px', 'alignItems': 'center'}, children=[
                                     dcc.Input(id='config-name-input', type='text', placeholder='Config name...',
                                               style={'flex': '1', 'padding': '4px 8px', 'fontSize': '9px',
                                                      'border': '1px solid #dee2e6', 'borderRadius': '4px'}),
                                     html.Button('💾 Save', id='save-config-btn',
                                                 style={'padding': '4px 8px', 'fontSize': '9px',
                                                        'backgroundColor': '#3498db', 'color': 'white',
                                                        'border': 'none', 'borderRadius': '4px', 'cursor': 'pointer'})
                                 ]),
                                 html.Div(id='saved-configs-list', style={'flex': '1', 'overflowY': 'auto',
                                                                           'fontSize': '8px', 'color': '#7f8c8d'})
                             ]),
                    # Comparison chart
                    html.Div(style={'flex': '1', 'border': '1px solid #dee2e6', 'borderRadius': '6px',
                                    'minHeight': '60px', 'backgroundColor': 'white'},
                             children=[
                                 dcc.Graph(id='config-comparison-chart',
                                           figure=create_config_comparison_chart([], avg_morale, avg_satisfaction),
                                           config={'displayModeBar': False},
                                           style={'height': '100%'})
                             ])
                ]
            )
        ]
    )
    
    # Store for tracking custom team selection and clientside callback data
    stores = html.Div([
        dcc.Store(id='custom-team-store', data={'active': False, 'working_ids': initial_working}),
        dcc.Store(id='dept-averages-store', data={'morale': avg_morale, 'satisfaction': avg_satisfaction}),
        dcc.Store(id='current-department-store', data=department),
        dcc.Store(id='working-ids-store', data=initial_working),
        dcc.Store(id='role-colors-store', data=ROLE_COLORS),
        dcc.Store(id='saved-configs-store', data=[])  # List of saved configurations
    ])
    
    return html.Div(
        style={'height': '100%', 'display': 'flex', 'flexDirection': 'column', 'padding': '6px'},
        children=[stores, header, main_content]
    )
