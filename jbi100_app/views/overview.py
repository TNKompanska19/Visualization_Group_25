"""
Overview Widget (T1): Hospital Performance Overview
- Task: Browse trends and outliers in hospital performance
- Expanded: Heatmap (Service × Week) + Timeline + KPIs
- Mini: Problem count + refusals sparkline
"""

from dash import dcc, html
import plotly.graph_objects as go
from jbi100_app.config import COLORS, SEMANTIC, EVENTS


def create_overview_expanded(df, selection):
    """Create expanded overview widget content."""
    
    week_range = selection.get("week_range", [1, 52])
    filtered = df[(df['week'] >= week_range[0]) & (df['week'] <= week_range[1])]
    
    return html.Div(
        className="widget-expanded",
        children=[
            html.Div(className="widget-header", children=[
                html.H5("Hospital Performance Overview", className="widget-title"),
                html.Span("T1: Browse trends and identify outliers", className="widget-subtitle")
            ]),
            html.Div(className="widget-content", children=[
                # KPI Row
                html.Div(className="kpi-row", children=_create_kpis(filtered)),
                # Charts
                html.Div(className="chart-row", children=[
                    html.Div(className="chart-container wide", children=[
                        html.Div("Refusal Rate by Service & Week", className="chart-title"),
                        dcc.Graph(
                            id="overview-heatmap",
                            figure=_create_heatmap(filtered),
                            style={'height': '100%'},
                            config={'displayModeBar': False}
                        )
                    ])
                ]),
                html.Div(style={'height': '140px', 'marginTop': '10px'}, children=[
                    html.Div("Patient Flow Over Time", className="chart-title"),
                    dcc.Graph(
                        id="overview-timeline",
                        figure=_create_timeline(filtered),
                        style={'height': '120px'},
                        config={'displayModeBar': False}
                    )
                ])
            ])
        ]
    )


def create_overview_mini(df, selection):
    """Create mini overview card."""
    
    week_range = selection.get("week_range", [1, 52])
    filtered = df[(df['week'] >= week_range[0]) & (df['week'] <= week_range[1])]
    
    problem_count = (filtered['refusal_rate'] > 20).sum()
    total_refused = filtered['patients_refused'].sum()
    weekly_refused = df.groupby('week')['patients_refused'].sum()
    
    return html.Div([
        html.Div(className="mini-header", children=[
            html.Span("📊 Overview", className="mini-title"),
            html.Span(f"{problem_count}", className="mini-badge") if problem_count > 0 else None
        ]),
        html.Div(className="mini-content", children=[
            html.Div(className="mini-metrics", children=[
                html.Div(className="mini-metric", children=[
                    html.Span(f"{total_refused:,}", className="mini-metric-value"),
                    html.Span("Refused", className="mini-metric-label")
                ]),
                html.Div(className="mini-metric", children=[
                    html.Span(f"{filtered['patient_satisfaction'].mean():.0f}", className="mini-metric-value"),
                    html.Span("Satisfaction", className="mini-metric-label")
                ])
            ]),
            dcc.Graph(figure=_sparkline(weekly_refused, SEMANTIC['bad']), 
                      config={'displayModeBar': False}, style={'height': '40px'})
        ])
    ])


def _create_kpis(df):
    return [
        html.Div(className="kpi-card", children=[
            html.Span(f"{df['patients_admitted'].sum():,}", className="kpi-value"),
            html.Span("Admitted", className="kpi-label")
        ]),
        html.Div(className="kpi-card", children=[
            html.Span(f"{df['patients_refused'].sum():,}", 
                      className=f"kpi-value {'warning' if df['patients_refused'].sum() > 500 else ''}"),
            html.Span("Refused", className="kpi-label")
        ]),
        html.Div(className="kpi-card", children=[
            html.Span(f"{df['patient_satisfaction'].mean():.1f}", 
                      className=f"kpi-value {'good' if df['patient_satisfaction'].mean() >= 70 else ''}"),
            html.Span("Avg Satisfaction", className="kpi-label")
        ]),
        html.Div(className="kpi-card", children=[
            html.Span(f"{df['staff_morale'].mean():.1f}", 
                      className=f"kpi-value {'good' if df['staff_morale'].mean() >= 70 else ''}"),
            html.Span("Avg Morale", className="kpi-label")
        ])
    ]


def _create_heatmap(df):
    pivot = df.pivot_table(index='service', columns='week', values='refusal_rate', aggfunc='mean')
    labels = [s.replace('_', ' ').title() for s in pivot.index]
    
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=pivot.columns.tolist(),
        y=labels,
        colorscale='RdYlGn_r',
        colorbar=dict(title='%', thickness=12),
        zmin=0, zmax=50,
        xgap=1, ygap=2
    ))
    
    fig.update_layout(
        margin=dict(l=110, r=20, t=10, b=40),
        xaxis=dict(title='Week', dtick=4),
        yaxis=dict(autorange='reversed'),
        plot_bgcolor='white'
    )
    return fig


def _create_timeline(df):
    weekly = df.groupby('week').agg({
        'patients_admitted': 'sum',
        'patients_refused': 'sum'
    }).reset_index()
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=weekly['week'], y=weekly['patients_admitted'],
        mode='lines', name='Admitted',
        line=dict(color=SEMANTIC['good'], width=2),
        fill='tozeroy', fillcolor='rgba(39,174,96,0.15)'
    ))
    fig.add_trace(go.Scatter(
        x=weekly['week'], y=weekly['patients_refused'],
        mode='lines', name='Refused',
        line=dict(color=SEMANTIC['bad'], width=2)
    ))
    
    fig.update_layout(
        margin=dict(l=50, r=20, t=5, b=25),
        xaxis=dict(dtick=8),
        yaxis=dict(title='Patients'),
        legend=dict(orientation='h', y=1.1, x=0),
        plot_bgcolor='white',
        hovermode='x unified'
    )
    return fig


def _sparkline(data, color):
    fig = go.Figure(data=go.Scatter(
        x=data.index, y=data.values, mode='lines',
        line=dict(color=color, width=1.5),
        fill='tozeroy', fillcolor=f'rgba{tuple(list(int(color[i:i+2], 16) for i in (1,3,5)) + [0.1])}'
    ))
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        plot_bgcolor='transparent', paper_bgcolor='transparent'
    )
    return fig
