"""
Quantity Widget (T2, T3): Capacity & Patient Flow Analysis
- T2: Explore distribution/extremes of bed allocation
- T3: Summarize stay duration distribution
- Expanded: Scatter + Bar + Box plots
- Mini: Refused count + utilization %
"""

from dash import dcc, html
import plotly.graph_objects as go
from jbi100_app.config import COLORS, SEMANTIC


def create_quantity_expanded(services_df, patients_df, selection):
    """Create expanded quantity widget content."""
    
    week_range = selection.get("week_range", [1, 52])
    filtered_svc = services_df[(services_df['week'] >= week_range[0]) & (services_df['week'] <= week_range[1])]
    
    return html.Div(
        className="widget-expanded",
        children=[
            html.Div(className="widget-header", children=[
                html.H5("Capacity & Patient Flow Analysis", className="widget-title"),
                html.Span("T2: Bed allocation | T3: Stay duration", className="widget-subtitle")
            ]),
            html.Div(className="widget-content", children=[
                # Top row: Scatter + Bar
                html.Div(className="chart-row", style={'flex': '1.2'}, children=[
                    html.Div(className="chart-container wide", children=[
                        html.Div("Beds vs Refusal Rate (T2)", className="chart-title"),
                        dcc.Graph(
                            id="quantity-scatter",
                            figure=_create_scatter(filtered_svc),
                            style={'height': '100%'},
                            config={'displayModeBar': False}
                        )
                    ]),
                    html.Div(className="chart-container narrow", children=[
                        html.Div("Refusals by Service", className="chart-title"),
                        dcc.Graph(
                            id="quantity-bar",
                            figure=_create_bar(filtered_svc),
                            style={'height': '100%'},
                            config={'displayModeBar': False}
                        )
                    ])
                ]),
                # Bottom: Box plots
                html.Div(className="chart-row", style={'flex': '0.8', 'marginTop': '10px'}, children=[
                    html.Div(className="chart-container", children=[
                        html.Div("Length of Stay Distribution (T3)", className="chart-title"),
                        dcc.Graph(
                            id="quantity-boxplot",
                            figure=_create_boxplot(patients_df),
                            style={'height': '100%'},
                            config={'displayModeBar': False}
                        )
                    ])
                ])
            ])
        ]
    )


def create_quantity_mini(services_df, selection):
    """Create mini quantity card."""
    
    week_range = selection.get("week_range", [1, 52])
    filtered = services_df[(services_df['week'] >= week_range[0]) & (services_df['week'] <= week_range[1])]
    
    total_refused = filtered['patients_refused'].sum()
    avg_util = filtered['utilization_rate'].mean()
    by_service = services_df.groupby('service')['patients_refused'].sum().sort_values()
    
    return html.Div([
        html.Div(className="mini-header", children=[
            html.Span("📦 Capacity", className="mini-title")
        ]),
        html.Div(className="mini-content", children=[
            html.Div(className="mini-metrics", children=[
                html.Div(className="mini-metric", children=[
                    html.Span(f"{total_refused:,}", className="mini-metric-value"),
                    html.Span("Refused", className="mini-metric-label")
                ]),
                html.Div(className="mini-metric", children=[
                    html.Span(f"{avg_util:.0f}%", className="mini-metric-value"),
                    html.Span("Utilization", className="mini-metric-label")
                ])
            ]),
            dcc.Graph(figure=_mini_bar(by_service), config={'displayModeBar': False}, style={'height': '45px'})
        ])
    ])


def _create_scatter(df):
    fig = go.Figure()
    
    for service in df['service'].unique():
        svc_df = df[df['service'] == service]
        fig.add_trace(go.Scatter(
            x=svc_df['available_beds'],
            y=svc_df['refusal_rate'],
            mode='markers',
            name=service.replace('_', ' ').title(),
            marker=dict(color=COLORS.get(service, '#999'), size=8, line=dict(width=1, color='white')),
            text=svc_df['week'],
            hovertemplate=f"<b>{service.replace('_', ' ').title()}</b><br>Week %{{text}}<br>Beds: %{{x}}<br>Refusal: %{{y:.1f}}%<extra></extra>"
        ))
    
    avg = df['refusal_rate'].mean()
    fig.add_hline(y=avg, line_dash="dash", line_color="gray", annotation_text=f"Avg: {avg:.1f}%")
    
    fig.update_layout(
        margin=dict(l=50, r=20, t=10, b=40),
        xaxis=dict(title='Available Beds'),
        yaxis=dict(title='Refusal Rate (%)'),
        legend=dict(orientation='h', y=-0.15, x=0.5, xanchor='center'),
        plot_bgcolor='white',
        hovermode='closest'
    )
    return fig


def _create_bar(df):
    summary = df.groupby('service')['patients_refused'].sum().reset_index()
    summary['label'] = summary['service'].str.replace('_', ' ').str.title()
    summary = summary.sort_values('patients_refused', ascending=True)
    
    fig = go.Figure(data=go.Bar(
        y=summary['label'],
        x=summary['patients_refused'],
        orientation='h',
        marker=dict(color=[COLORS.get(s, '#999') for s in summary['service']]),
        text=summary['patients_refused'],
        textposition='auto'
    ))
    
    fig.update_layout(
        margin=dict(l=100, r=20, t=10, b=30),
        xaxis=dict(title='Total'),
        yaxis=dict(title=''),
        plot_bgcolor='white'
    )
    return fig


def _create_boxplot(patients_df):
    fig = go.Figure()
    
    for service in patients_df['service'].unique():
        svc_df = patients_df[patients_df['service'] == service]
        fig.add_trace(go.Box(
            y=svc_df['length_of_stay'],
            name=service.replace('_', ' ').title(),
            marker=dict(color=COLORS.get(service, '#999')),
            boxmean='sd'
        ))
    
    fig.update_layout(
        margin=dict(l=50, r=20, t=10, b=30),
        yaxis=dict(title='Days'),
        showlegend=False,
        plot_bgcolor='white'
    )
    return fig


def _mini_bar(data):
    colors = [COLORS.get(s, '#999') for s in data.index]
    labels = [s[:3].upper() for s in data.index]
    
    fig = go.Figure(data=go.Bar(x=labels, y=data.values, marker=dict(color=colors)))
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=15),
        xaxis=dict(tickfont=dict(size=9)),
        yaxis=dict(visible=False),
        plot_bgcolor='transparent', paper_bgcolor='transparent',
        bargap=0.3
    )
    return fig
