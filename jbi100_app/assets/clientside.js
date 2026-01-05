/**
 * Clientside callback: Update highlight rectangle on sparkline when panning Overview.
 * ONLY moves the rectangle - does NOT change x-axis range.
 */
window.dash_clientside = Object.assign({}, window.dash_clientside, {
    clientside: {
        updateHighlightRect: function(relayoutData, currentFig, weekSlider) {
            if (!relayoutData || !currentFig) {
                return window.dash_clientside.no_update;
            }
            
            // Get sidebar week range as fallback
            const sidebarMin = weekSlider ? weekSlider[0] : 1;
            const sidebarMax = weekSlider ? weekSlider[1] : 52;
            
            // Extract x-axis range from relayoutData
            let xMin = null, xMax = null;
            
            if ('xaxis.range[0]' in relayoutData && 'xaxis.range[1]' in relayoutData) {
                xMin = relayoutData['xaxis.range[0]'];
                xMax = relayoutData['xaxis.range[1]'];
            } else if ('xaxis.range' in relayoutData) {
                const rng = relayoutData['xaxis.range'];
                if (Array.isArray(rng) && rng.length === 2) {
                    xMin = rng[0];
                    xMax = rng[1];
                }
            } else if (relayoutData['xaxis.autorange']) {
                // Double-click reset - use sidebar range
                xMin = sidebarMin;
                xMax = sidebarMax;
            }
            
            if (xMin === null || xMax === null) {
                return window.dash_clientside.no_update;
            }
            
            // Clamp to valid weeks
            xMin = Math.max(0.5, xMin);
            xMax = Math.min(52.5, xMax);
            
            // Clone figure and update ONLY the vrect shape
            const newFig = JSON.parse(JSON.stringify(currentFig));
            
            if (newFig.layout && newFig.layout.shapes && newFig.layout.shapes.length > 0) {
                // Update the highlight rectangle (first shape)
                newFig.layout.shapes[0].x0 = xMin;
                newFig.layout.shapes[0].x1 = xMax;
            }
            
            return newFig;
        }
    }
});
