"""
Quality Widget (T4, T5, T6): Quality & Staff Analysis
- T4: Discover correlations between satisfaction factors
- T5: Explore staff configurations → morale dependency
- T6: Locate extreme staff (best/worst performers)
- Expanded: PCP (Parallel Coordinates) + Correlation matrix + Scatter
- Mini: Satisfaction + Morale

RUBRIC: Advanced multivariate idiom (PCP) required for full marks
"""

from dash import dcc, html
import plotly.graph_objects as go
import numpy as np
from jbi100_app.config import COLORS, SEMANTIC


def create_quality_expanded(services_df, selection):
    """Create expanded quality widget content."""
    
    week_range = selection.get("week_range", [1, 52])
    filtered = services_df[(services_df['week'] >= week_range[0]) & (services_df['week'] <= week_range[1])]
    
    return html.Div(
        className="widget-expanded",
        children=[
            html.Div(className="widget-header", children=[
                html.H5("Quality & Satisfaction Analysis", className="widget-title"),
                html.Span("T4: Correlations | T5: Staff impact | T6: Extremes", className="widget-subtitle")
            ]),
            html.Div(className="widget-content", children=[
                # Top row: PCP + Correlation
                html.Div(className="chart-row", style={'flex': '1.2'}, children=[
                    html.Div(className="chart-container wide", children=[
                        html.Div("Parallel Coordinates - Multivariate Analysis (T4)", className="chart-title"),
                        dcc.Graph(
                            id="quality-pcp",
                            figure=_create_pcp(filtered),
                            style={'height': '100%'},
                            config={'displayModeBar': False}
                        )
                    ]),
                    html.Div(className="chart-container narrow", children=[
                        html.Div("Correlation Matrix (T4)", className="chart-title"),
                        dcc.Graph(
                            id="quality-corr",
                            figure=_create_correlation(filtered),
                            style={'height': '100%'},
                            config={'displayModeBar': False}
                        )
                    ])
                ]),
                # Bottom: Scatter
                html.Div(className="chart-row", style={'flex': '0.8', 'marginTop': '10px'}, children=[
                    html.Div(className="chart-container", children=[
                        html.Div("Satisfaction vs Morale by Service (T5)", className="chart-title"),
                        dcc.Graph(
                            id="quality-scatter",
                            figure=_create_scatter(filtered),
                            style={'height': '100%'},
                            config={'displayModeBar': False}
                        )
                    ])
                ])
            ])
        ]
    )


def create_quality_mini(services_df, selection):
    """Create mini quality card."""
    
    week_range = selection.get("week_range", [1, 52])
    filtered = services_df[(services_df['week'] >= week_range[0]) & (services_df['week'] <= week_range[1])]
    
    avg_sat = filtered['patient_satisfaction'].mean()
    avg_morale = filtered['staff_morale'].mean()
    weekly_sat = services_df.groupby('week')['patient_satisfaction'].mean()
    
    return html.Div([
        html.Div(className="mini-header", children=[
            html.Span("⭐ Quality", className="mini-title")
        ]),
        html.Div(className="mini-content", children=[
            html.Div(className="mini-metrics", children=[
                html.Div(className="mini-metric", children=[
                    html.Span(f"{avg_sat:.0f}", className="mini-metric-value"),
                    html.Span("Satisfaction", className="mini-metric-label")
                ]),
                html.Div(className="mini-metric", children=[
                    html.Span(f"{avg_morale:.0f}", className="mini-metric-value"),
                    html.Span("Morale", className="mini-metric-label")
                ])
            ]),
            dcc.Graph(figure=_sparkline(weekly_sat), config={'displayModeBar': False}, style={'height': '40px'})
        ])
    ])


def _create_pcp(df):
    """
    Parallel Coordinates Plot - MULTIVARIATE IDIOM
    
    Justification (Munzner M5_01):
    - Shows relationships between multiple quantitative attributes
    - Patterns: parallel lines = positive correlation, crossing = negative
    - Supports brushing on axes for filtering
    """
    
    pcp_df = df[['week', 'service', 'available_beds', 'patients_admitted', 
                 'patients_refused', 'patient_satisfaction', 'staff_morale']].copy()
    
    service_map = {s: i for i, s in enumerate(pcp_df['service'].unique())}
    pcp_df['service_num'] = pcp_df['service'].map(service_map)
    
    dimensions = [
        dict(label='Week', values=pcp_df['week'], range=[1, 52]),
        dict(label='Beds', values=pcp_df['available_beds']),
        dict(label='Admitted', values=pcp_df['patients_admitted']),
        dict(label='Refused', values=pcp_df['patients_refused']),
        dict(label='Satisfaction', values=pcp_df['patient_satisfaction'], range=[0, 100]),
        dict(label='Morale', values=pcp_df['staff_morale'], range=[0, 100])
    ]
    
    # Color scale for services
    services = list(pcp_df['service'].unique())
    color_vals = [list(COLORS.values())[i % len(COLORS)] for i in range(len(services))]
    
    fig = go.Figure(data=go.Parcoords(
        line=dict(
            color=pcp_df['service_num'],
            colorscale=[[i/max(1, len(services)-1), color_vals[i]] for i in range(len(services))],
            showscale=False
        ),
        dimensions=dimensions,
        labelangle=-30,
        labelside='top'
    ))
    
    fig.update_layout(
        margin=dict(l=60, r=80, t=30, b=30),
        paper_bgcolor='white'
    )
    
    # Legend
    for i, (service, color) in enumerate(COLORS.items()):
        fig.add_annotation(
            x=1.02, y=0.9 - i*0.12,
            xref='paper', yref='paper',
            text=f"● {service.replace('_', ' ').title()}",
            showarrow=False,
            font=dict(size=10, color=color),
            xanchor='left'
        )
    
    return fig


def _create_correlation(df):
    """Correlation matrix heatmap."""
    
    cols = ['available_beds', 'patients_admitted', 'patients_refused', 
            'patient_satisfaction', 'staff_morale']
    labels = ['Beds', 'Admitted', 'Refused', 'Satisfaction', 'Morale']
    
    corr = df[cols].corr()
    
    fig = go.Figure(data=go.Heatmap(
        z=corr.values,
        x=labels, y=labels,
        colorscale='RdBu_r',
        zmid=0, zmin=-1, zmax=1,
        text=[[f"{v:.2f}" for v in row] for row in corr.values],
        texttemplate="%{text}",
        textfont=dict(size=9),
        colorbar=dict(title='r', thickness=10)
    ))
    
    fig.update_layout(
        margin=dict(l=60, r=20, t=10, b=60),
        xaxis=dict(tickangle=-45),
        yaxis=dict(autorange='reversed'),
        paper_bgcolor='white'
    )
    return fig


def _create_scatter(df):
    """Satisfaction vs Morale scatter."""
    
    fig = go.Figure()
    
    for service in df['service'].unique():
        svc_df = df[df['service'] == service]
        fig.add_trace(go.Scatter(
            x=svc_df['staff_morale'],
            y=svc_df['patient_satisfaction'],
            mode='markers',
            name=service.replace('_', ' ').title(),
            marker=dict(color=COLORS.get(service, '#999'), size=8, line=dict(width=1, color='white')),
            text=svc_df['week'],
            hovertemplate=f"<b>{service.replace('_', ' ').title()}</b><br>Week %{{text}}<br>Morale: %{{x}}<br>Satisfaction: %{{y}}<extra></extra>"
        ))
    
    # Trend line
    z = np.polyfit(df['staff_morale'], df['patient_satisfaction'], 1)
    p = np.poly1d(z)
    x_line = [df['staff_morale'].min(), df['staff_morale'].max()]
    fig.add_trace(go.Scatter(x=x_line, y=p(x_line), mode='lines', 
                             line=dict(color='gray', dash='dash', width=1), showlegend=False))
    
    # Correlation annotation
    corr = df['staff_morale'].corr(df['patient_satisfaction'])
    fig.add_annotation(x=0.02, y=0.98, xref='paper', yref='paper',
                       text=f"r = {corr:.3f}", showarrow=False, font=dict(size=11, color='gray'))
    
    fig.update_layout(
        margin=dict(l=50, r=20, t=10, b=40),
        xaxis=dict(title='Staff Morale'),
        yaxis=dict(title='Patient Satisfaction'),
        legend=dict(orientation='h', y=-0.15, x=0.5, xanchor='center'),
        plot_bgcolor='white',
        hovermode='closest'
    )
    return fig


def _sparkline(data):
    fig = go.Figure(data=go.Scatter(
        x=data.index, y=data.values, mode='lines',
        line=dict(color=SEMANTIC['primary'], width=1.5),
        fill='tozeroy', fillcolor='rgba(44,140,255,0.1)'
    ))
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        plot_bgcolor='transparent', paper_bgcolor='transparent'
    )
    return fig
