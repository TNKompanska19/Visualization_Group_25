# Developer Guide
## Hospital Operations Dashboard - JBI100 Group 25

---

## Project Structure

```
Visualization_Group_25/
├── app.py                      ← Entry point (run this)
│
└── jbi100_app/
    ├── main.py                 ← Dash app instance
    ├── config.py               ← Colors, labels, constants
    ├── data.py                 ← Data loading & preprocessing
    ├── layout.py               ← Page structure
    │
    ├── callbacks/              ← Interactivity (event handlers)
    │   ├── sidebar_callbacks.py
    │   ├── overview_callbacks.py
    │   └── widget_callbacks.py
    │
    ├── views/                  ← UI components
    │   ├── menu.py             ← Sidebar
    │   ├── overview.py         ← T1 charts
    │   ├── quantity.py         ← T2, T3 charts
    │   └── quality.py          ← T4, T5, T6 charts
    │
    ├── assets/style.css        ← Styling
    └── data/*.csv              ← Datasets
```

---

## What Goes Where

| I need to... | Edit this file |
|--------------|----------------|
| Add/change colors or labels | `config.py` |
| Add derived data columns | `data.py` |
| Change page layout | `layout.py` |
| Add sidebar controls | `views/menu.py` |
| Work on T1 (Overview) | `views/overview.py` |
| Work on T2/T3 (Quantity) | `views/quantity.py` |
| Work on T4/T5/T6 (Quality) | `views/quality.py` |
| Add hover/click interactions | `callbacks/` folder |

---

## Task Assignments

| Task | File | Status |
|------|------|--------|
| T1: Browse trends | `views/overview.py` | Done |
| T2: Bed allocation | `views/quantity.py` | Placeholder |
| T3: Stay duration | `views/quantity.py` | Placeholder |
| T4: Correlations (PCP) | `views/quality.py` | Placeholder |
| T5: Staff impact | `views/quality.py` | Placeholder |
| T6: Extreme performers | `views/quality.py` | Placeholder |

---

## How Callbacks Work

Callbacks connect user actions to UI updates. Example:

```python
@callback(
    Output("tooltip", "children"),    # What to update
    Input("chart", "hoverData")       # What triggers it
)
def update_tooltip(hover_info):
    return f"Week {hover_info['points'][0]['x']}"
```

When the user hovers on the chart, `update_tooltip()` runs and updates the tooltip.

Current callbacks are split by feature:
- `sidebar_callbacks.py` - filter buttons, slider sync, zoom indicator
- `overview_callbacks.py` - T1 hover and tooltip
- `widget_callbacks.py` - rendering and widget swapping

---

## Adding a Chart

**1. Create the chart function in the appropriate view file:**

```python
# views/quantity.py

import plotly.graph_objects as go
from jbi100_app.config import DEPT_COLORS

def create_beds_scatter(df, selected_depts, week_range):
    """T2: Beds vs Refusal Rate scatter plot."""
    week_min, week_max = week_range
    filtered = df[(df["week"] >= week_min) & (df["week"] <= week_max)]
    if selected_depts:
        filtered = filtered[filtered["service"].isin(selected_depts)]
    
    fig = go.Figure()
    for dept in filtered["service"].unique():
        dept_data = filtered[filtered["service"] == dept]
        fig.add_trace(go.Scatter(
            x=dept_data["available_beds"],
            y=dept_data["refusal_rate"],
            mode="markers",
            name=dept,
            marker=dict(color=DEPT_COLORS.get(dept, "#999"))
        ))
    
    fig.update_layout(
        xaxis_title="Available Beds",
        yaxis_title="Refusal Rate (%)",
        plot_bgcolor="white"
    )
    return fig
```

**2. Add it to the expanded widget:**

```python
def create_quantity_expanded(services_df, patients_df, selected_depts, week_range):
    content = html.Div([
        dcc.Graph(
            id="quantity-scatter",
            figure=create_beds_scatter(services_df, selected_depts, week_range),
            config={"displayModeBar": False}
        )
    ])
    return html.Div([header, content])
```

---

## Adding a Callback

**1. Create the callback in the appropriate file:**

```python
# callbacks/quantity_callbacks.py

from dash import callback, Output, Input

def register_quantity_callbacks():
    
    @callback(
        Output("quantity-detail", "children"),
        Input("quantity-scatter", "clickData")
    )
    def on_scatter_click(click_data):
        if click_data:
            return f"Selected: Week {click_data['points'][0]['x']}"
        return "Click a point"
```

**2. Register it in `callbacks/__init__.py`:**

```python
from jbi100_app.callbacks.quantity_callbacks import register_quantity_callbacks

def register_all_callbacks():
    register_sidebar_callbacks()
    register_overview_callbacks()
    register_widget_callbacks()
    register_quantity_callbacks()  # Add this
```

---

## Common Patterns

**Filter data by selection:**
```python
week_min, week_max = week_range
filtered = df[(df["week"] >= week_min) & (df["week"] <= week_max)]
if selected_depts:
    filtered = filtered[filtered["service"].isin(selected_depts)]
```

**Multi-trace chart:**
```python
fig = go.Figure()
for dept in selected_depts:
    dept_data = df[df["service"] == dept]
    fig.add_trace(go.Scatter(
        x=dept_data["week"],
        y=dept_data["some_metric"],
        name=dept,
        line=dict(color=DEPT_COLORS[dept])
    ))
```

**Chart styling:**
```python
fig.update_layout(
    plot_bgcolor="white",
    margin=dict(l=50, r=20, t=30, b=40),
    hovermode="x unified"
)
```

---

## Running the App

```bash
cd D:\TUe\Y2_Q2_Visualization\Repository\Visualization_Group_25
python app.py
```

Open http://localhost:8050. The app auto-reloads when you save files.

---

## Troubleshooting

**Module not found:** Make sure you're in the project root folder before running.

**Chart not updating:** Check that callback Input/Output IDs match the component IDs in the layout.

**Callback ID not found:** The component must exist in the layout before the callback can reference it.
