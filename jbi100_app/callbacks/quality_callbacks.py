"""
Quality Widget Callbacks - Interactive network with predictions
Uses clientside callback for instant visual updates without position reset.
"""

from dash import callback, Output, Input, State, ctx, no_update, clientside_callback, ClientsideFunction, ALL
from dash import html
import plotly.graph_objects as go
from jbi100_app.views.quality import (
    create_network_for_week, 
    compute_staff_impacts_all_weeks,
    create_comparison_bars,
    create_week_slider_marks,
    create_week_context_chart,
    create_config_comparison_chart,
    predict_from_team,
    generate_stylesheet,
    ROLE_COLORS,
    _model_cache
)
from jbi100_app.data import get_services_data, get_staff_schedule_data

_services_df = get_services_data()
_staff_schedule_df = get_staff_schedule_data()
_week_data_cache = {}
ANOMALY_WEEKS = [3, 6, 9, 12, 15, 18, 21, 24, 27, 30, 33, 36, 39, 42, 45, 48, 51]


def register_quality_callbacks():
    """Register quality callbacks."""
    
    # Clientside callback for instant stylesheet updates (preserves positions)
    clientside_callback(
        """
        function(workingIds, roleColors) {
            if (!workingIds || workingIds.length === 0) {
                workingIds = [];
            }
            
            // Base stylesheet
            var stylesheet = [
                {selector: '[node_type = "department"]',
                 style: {
                     'background-color': '#2c3e50', 'label': 'data(label)', 'color': 'white',
                     'font-size': '10px', 'font-weight': 'bold', 'width': '70px', 'height': '26px',
                     'shape': 'round-rectangle', 'text-valign': 'center', 'text-halign': 'center',
                     'border-width': 2, 'border-color': 'white'
                 }},
                {selector: '[node_type = "role"]',
                 style: {
                     'label': 'data(label)', 'color': 'white', 'font-size': '8px', 'font-weight': 'bold',
                     'width': '45px', 'height': '45px', 'shape': 'diamond',
                     'text-valign': 'center', 'text-halign': 'center',
                     'text-wrap': 'wrap', 'text-max-width': '43px',
                     'border-width': 2, 'border-color': 'white'
                 }},
                {selector: '[role_name = "doctor"]', style: {'background-color': '#56C1C1'}},
                {selector: '[role_name = "nurse"]', style: {'background-color': '#B57EDC'}},
                {selector: '[role_name = "nursing_assistant"]', 
                 style: {'background-color': '#FFD166', 'color': '#2c3e50'}},
                {selector: '[node_type = "staff"]',
                 style: {
                     'background-color': 'data(color)', 'label': 'data(label)', 'color': '#2c3e50',
                     'font-size': '6px', 'font-weight': '500',
                     'width': 'data(size)', 'height': 'data(size)', 'shape': 'ellipse',
                     'opacity': 0.3, 'border-width': 1,
                     'border-color': '#999', 'text-valign': 'center', 'text-halign': 'center'
                 }},
                {selector: 'edge[source ^= "role_"]',
                 style: {'width': 1, 'line-color': '#ddd', 'opacity': 0, 'curve-style': 'bezier'}},
                {selector: 'edge[target ^= "role_"]',
                 style: {'width': 1, 'line-color': '#ddd', 'opacity': 0.4, 'curve-style': 'bezier'}},
                {selector: ':active', style: {'overlay-opacity': 0.2, 'overlay-color': '#3498db'}}
            ];
            
            // Add styles for working staff
            for (var i = 0; i < workingIds.length; i++) {
                var staffId = workingIds[i];
                stylesheet.push({
                    selector: '[id = "staff_' + staffId + '"]',
                    style: {'opacity': 1.0, 'border-width': 3, 'border-color': '#2c3e50'}
                });
                stylesheet.push({
                    selector: 'edge[target = "staff_' + staffId + '"]',
                    style: {'opacity': 0.4}
                });
            }
            
            return stylesheet;
        }
        """,
        Output('staff-network-weekly', 'stylesheet'),
        Input('working-ids-store', 'data'),
        State('role-colors-store', 'data')
    )
    
    # Main callback for week/dept changes and node clicks
    @callback(
        [Output('staff-network-weekly', 'elements'),
         Output('quality-week-slider', 'value'),
         Output('quality-week-slider', 'marks'),
         Output('week-context-chart', 'figure'),
         Output('morale-comparison-chart', 'figure'),
         Output('satisfaction-comparison-chart', 'figure'),
         Output('working-count-display', 'children'),
         Output('custom-team-store', 'data'),
         Output('prediction-status', 'children'),
         Output('selected-week-display', 'children'),
         Output('working-ids-store', 'data')],
        [Input('quality-week-slider', 'value'),
         Input('dept-filter', 'value'),
         Input('hide-anomalies-toggle', 'value'),
         Input('staff-network-weekly', 'tapNodeData')],
        [State('custom-team-store', 'data'),
         State('dept-averages-store', 'data'),
         State('current-department-store', 'data'),
         State('staff-network-weekly', 'elements')]
    )
    def update_network_and_charts(selected_week, selected_depts, hide_anomalies_list, 
                                   tap_data, custom_team, dept_averages, stored_dept, current_elements):
        """Handle week changes, department changes, and node clicks."""
        
        hide_anomalies = "hide" in (hide_anomalies_list or [])
        slider_marks = create_week_slider_marks(hide_anomalies)
        
        # Empty defaults
        empty_fig = go.Figure()
        empty_fig.update_layout(margin=dict(l=25, r=5, t=20, b=18), height=120,
                                plot_bgcolor='white', paper_bgcolor='white')
        empty_context = go.Figure()
        empty_context.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=45)
        default_count = html.Div([
            html.Span("# assigned: ", style={'fontSize': '10px', 'color': '#7f8c8d'}),
            html.Span("0", style={'fontSize': '13px', 'color': '#7f8c8d', 'fontWeight': 'bold'})
        ])
        default_store = {'active': False, 'working_ids': []}
        
        if not selected_depts or selected_week is None:
            return [], selected_week or 1, slider_marks, empty_context, empty_fig, empty_fig, default_count, default_store, "", str(selected_week or 1), []
        
        department = selected_depts[0]
        
        # Get what triggered this callback
        triggered_id = ctx.triggered_id
        triggered_prop = ctx.triggered[0]['prop_id'] if ctx.triggered else ''
        
        # Check if department changed
        dept_changed = stored_dept and stored_dept != department
        
        # Handle anomaly weeks
        adjusted_week = selected_week
        if selected_week in ANOMALY_WEEKS:
            if hide_anomalies:
                valid_weeks = [w for w in range(1, 53) if w not in ANOMALY_WEEKS]
                adjusted_week = min(valid_weeks, key=lambda w: abs(w - selected_week))
            else:
                # Can't show anomaly week data - snap to nearest valid
                valid_weeks = [w for w in range(1, 53) if w not in ANOMALY_WEEKS]
                adjusted_week = min(valid_weeks, key=lambda w: abs(w - selected_week))
        
        # Get/compute week data
        cache_key = department
        if cache_key not in _week_data_cache:
            result = compute_staff_impacts_all_weeks(_services_df, _staff_schedule_df, department)
            if result is None or result[0] is None:
                _week_data_cache[cache_key] = None
            else:
                week_data, _ = result
                _week_data_cache[cache_key] = week_data
        
        week_data = _week_data_cache.get(cache_key)
        if week_data is None or adjusted_week not in week_data:
            return [], adjusted_week, slider_marks, empty_context, empty_fig, empty_fig, default_count, default_store, "", str(adjusted_week), []
        
        week_impacts = week_data[adjusted_week]
        
        # Get averages
        if dept_averages and not dept_changed:
            avg_morale = dept_averages['morale']
            avg_satisfaction = dept_averages['satisfaction']
        else:
            dept_services = _services_df[_services_df['service'] == department]
            avg_morale = dept_services['staff_morale'].mean()
            avg_satisfaction = dept_services['patient_satisfaction'].mean()
        
        # Create week context chart (update on week/dept change)
        context_fig = create_week_context_chart(_services_df, department, adjusted_week)
        
        # Determine if we need to regenerate elements
        node_clicked = 'tapNodeData' in triggered_prop and tap_data is not None
        need_new_elements = (triggered_id in ['quality-week-slider', 'dept-filter'] or 
                            dept_changed or 
                            current_elements is None or 
                            len(current_elements) == 0)
        
        # Determine working staff based on what triggered the callback
        if node_clicked and not dept_changed and not need_new_elements:
            # Node was clicked - check if it's a staff node
            node_type = tap_data.get('node_type')
            
            if node_type == 'staff':
                clicked_staff_id = tap_data.get('staff_id_raw')
                
                # Get current working list
                if custom_team and custom_team.get('active'):
                    working_ids = list(custom_team['working_ids'])
                else:
                    working_ids = week_impacts[week_impacts['working_this_week']]['staff_id'].tolist()
                
                # Toggle the clicked staff
                if clicked_staff_id in working_ids:
                    working_ids.remove(clicked_staff_id)
                else:
                    working_ids.append(clicked_staff_id)
                
                custom_team = {'active': True, 'working_ids': working_ids}
                
                # DON'T regenerate elements - keep context chart same
                elements = no_update
                context_fig = no_update
            else:
                # Clicked non-staff node - no change
                if custom_team and custom_team.get('active'):
                    working_ids = list(custom_team['working_ids'])
                else:
                    working_ids = week_impacts[week_impacts['working_this_week']]['staff_id'].tolist()
                    custom_team = {'active': False, 'working_ids': working_ids}
                elements = no_update
                context_fig = no_update
        
        elif need_new_elements:
            # Week or dept changed - reset and regenerate elements
            working_ids = week_impacts[week_impacts['working_this_week']]['staff_id'].tolist()
            custom_team = {'active': False, 'working_ids': working_ids}
            elements = create_network_for_week(week_impacts, department, adjusted_week, 'morale', 
                                               custom_working=None, include_all_edges=True)
        
        else:
            # Initial load or hide-anomalies toggle
            if custom_team and custom_team.get('active'):
                working_ids = list(custom_team['working_ids'])
            else:
                working_ids = week_impacts[week_impacts['working_this_week']]['staff_id'].tolist()
                custom_team = {'active': False, 'working_ids': working_ids}
            elements = no_update
        
        # Compute prediction or get actual values
        if custom_team.get('active'):
            morale_val, sat_val, is_historical, match_week = predict_from_team(department, working_ids)
            
            if morale_val is None:
                morale_val, sat_val = avg_morale, avg_satisfaction
                is_predicted = False
                status_text = ""
            elif is_historical:
                is_predicted = False
                status_text = html.Span(f"✓ Week {match_week} config", 
                                        style={'color': '#27ae60', 'fontSize': '8px'})
            else:
                is_predicted = True
                status_text = html.Span("⚠ Predicted", 
                                        style={'color': '#e67e22', 'fontSize': '8px'})
        else:
            dept_services = _services_df[_services_df['service'] == department]
            week_row = dept_services[dept_services['week'] == adjusted_week]
            if not week_row.empty:
                morale_val = week_row['staff_morale'].values[0]
                sat_val = week_row['patient_satisfaction'].values[0]
            else:
                morale_val, sat_val = avg_morale, avg_satisfaction
            is_predicted = False
            status_text = html.Span(f"W{adjusted_week} actual", style={'color': '#3498db', 'fontSize': '8px'})
        
        # Create bar charts
        morale_fig, sat_fig = create_comparison_bars(department, adjusted_week, morale_val, sat_val,
                                                      is_predicted, avg_morale, avg_satisfaction)
        
        # Working count display
        count_color = '#e67e22' if custom_team.get('active') else '#27ae60'
        count_display = html.Div([
            html.Span("# assigned: ", style={'fontSize': '10px', 'color': '#7f8c8d'}),
            html.Span(f"{len(working_ids)}", style={'fontSize': '13px', 'color': count_color, 'fontWeight': 'bold'}),
            html.Span(" ✎" if custom_team.get('active') else "", 
                      style={'fontSize': '10px', 'color': '#e67e22', 'marginLeft': '3px'})
        ])
        
        return (elements, adjusted_week, slider_marks, context_fig, morale_fig, sat_fig, 
                count_display, custom_team, status_text, str(adjusted_week), working_ids)
    
    # Callback for saving configurations
    @callback(
        [Output('saved-configs-store', 'data'),
         Output('config-name-input', 'value')],
        Input('save-config-btn', 'n_clicks'),
        [State('config-name-input', 'value'),
         State('working-ids-store', 'data'),
         State('saved-configs-store', 'data'),
         State('current-department-store', 'data'),
         State('dept-averages-store', 'data')],
        prevent_initial_call=True
    )
    def save_configuration(n_clicks, config_name, working_ids, saved_configs, department, dept_averages):
        """Save current staff configuration."""
        if not n_clicks or not working_ids:
            return no_update, no_update
        
        # Generate name if not provided
        if not config_name or config_name.strip() == '':
            config_name = f"Config {len(saved_configs) + 1}"
        else:
            config_name = config_name.strip()
        
        # Predict metrics for this configuration
        morale_val, sat_val, is_historical, _ = predict_from_team(department, working_ids)
        
        if morale_val is None:
            morale_val = dept_averages.get('morale', 0)
            sat_val = dept_averages.get('satisfaction', 0)
        
        # Create new config entry
        new_config = {
            'name': config_name,
            'working_ids': working_ids,
            'morale': float(morale_val),
            'satisfaction': float(sat_val),
            'staff_count': len(working_ids),
            'is_predicted': not is_historical
        }
        
        # Add to list (max 5 configs)
        updated_configs = list(saved_configs) if saved_configs else []
        if len(updated_configs) >= 5:
            updated_configs = updated_configs[1:]  # Remove oldest
        updated_configs.append(new_config)
        
        return updated_configs, ''  # Clear input
    
    # Callback for deleting configurations
    @callback(
        Output('saved-configs-store', 'data', allow_duplicate=True),
        Input({'type': 'delete-config-btn', 'index': ALL}, 'n_clicks'),
        State('saved-configs-store', 'data'),
        prevent_initial_call=True
    )
    def delete_configuration(n_clicks_list, saved_configs):
        """Delete a saved configuration."""
        # Check if any button was actually clicked (not just rendered)
        if not n_clicks_list or not any(n for n in n_clicks_list if n) or not saved_configs:
            return no_update
        
        # Find which button was clicked
        triggered = ctx.triggered_id
        if triggered and 'index' in triggered:
            index_to_delete = triggered['index']
            updated_configs = [c for i, c in enumerate(saved_configs) if i != index_to_delete]
            return updated_configs
        
        return no_update
    
    # Callback to update saved configs list display
    @callback(
        Output('saved-configs-list', 'children'),
        Input('saved-configs-store', 'data')
    )
    def update_saved_configs_list(saved_configs):
        """Update the display of saved configurations."""
        if not saved_configs:
            return html.Span("No saved configs", style={'color': '#bdc3c7', 'fontStyle': 'italic'})
        
        config_items = []
        for i, config in enumerate(saved_configs):
            pred_indicator = "⚠" if config.get('is_predicted') else "✓"
            config_items.append(
                html.Div(
                    style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center',
                           'padding': '2px 0', 'borderBottom': '1px solid #f0f0f0'},
                    children=[
                        html.Span([
                            html.Span(f"{pred_indicator} ", style={'fontSize': '8px'}),
                            html.Span(config['name'], style={'fontWeight': '500'}),
                            html.Span(f" ({config['staff_count']})", style={'color': '#95a5a6'})
                        ]),
                        html.Button('✕', id={'type': 'delete-config-btn', 'index': i},
                                    style={'background': 'none', 'border': 'none', 'color': '#e74c3c',
                                           'cursor': 'pointer', 'fontSize': '10px', 'padding': '0 3px'})
                    ]
                )
            )
        
        return config_items
    
    # Callback to update comparison chart
    @callback(
        Output('config-comparison-chart', 'figure'),
        [Input('saved-configs-store', 'data'),
         Input('dept-averages-store', 'data')]
    )
    def update_comparison_chart(saved_configs, dept_averages):
        """Update the comparison chart when configs change."""
        avg_morale = dept_averages.get('morale', 0) if dept_averages else 0
        avg_satisfaction = dept_averages.get('satisfaction', 0) if dept_averages else 0
        
        return create_config_comparison_chart(saved_configs or [], avg_morale, avg_satisfaction)
