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

/**
 * =============================================================================
 * CYTOSCAPE GROUP DRAG
 * =============================================================================
 */
(function() {
    console.log('[GroupDrag] Starting v3...');
    
    var dragState = { active: false, nodeId: null, childOffsets: {} };
    
    function getDescendants(cy, nodeId) {
        var result = [], visited = {}, queue = [nodeId];
        visited[nodeId] = true;
        while (queue.length > 0) {
            var id = queue.shift();
            var edges = cy.edges();
            for (var i = 0; i < edges.length; i++) {
                var src = edges[i].data('source'), tgt = edges[i].data('target');
                if (src === id && !visited[tgt]) {
                    visited[tgt] = true;
                    var n = cy.getElementById(tgt);
                    if (n.length) { result.push(n); queue.push(tgt); }
                }
            }
        }
        return result;
    }
    
    function attachHandlers(cy) {
        if (!cy || cy._gdAttached) return false;
        cy._gdAttached = true;
        console.log('[GroupDrag] ✓✓✓ SUCCESS! Handlers attached! ✓✓✓');
        
        cy.on('grab', 'node', function(e) {
            var node = e.target, type = node.data('node_type');
            if (type !== 'department' && type !== 'role') return;
            dragState.active = true;
            dragState.nodeId = node.id();
            dragState.childOffsets = {};
            var pos = node.position();
            var desc = getDescendants(cy, node.id());
            for (var i = 0; i < desc.length; i++) {
                var c = desc[i];
                dragState.childOffsets[c.id()] = { dx: c.position('x') - pos.x, dy: c.position('y') - pos.y };
            }
            console.log('[GroupDrag] Grabbed ' + type + ' with ' + desc.length + ' children');
        });
        
        cy.on('drag', 'node', function(e) {
            if (!dragState.active || e.target.id() !== dragState.nodeId) return;
            var pos = e.target.position();
            cy.batch(function() {
                for (var id in dragState.childOffsets) {
                    var o = dragState.childOffsets[id];
                    cy.getElementById(id).position({ x: pos.x + o.dx, y: pos.y + o.dy });
                }
            });
        });
        
        cy.on('free', 'node', function() {
            dragState.active = false;
            dragState.nodeId = null;
            dragState.childOffsets = {};
        });
        return true;
    }
    
    // Check if something looks like a cy instance
    function isCyInstance(obj) {
        return obj && typeof obj === 'object' && 
               typeof obj.nodes === 'function' && 
               typeof obj.edges === 'function' && 
               typeof obj.on === 'function' &&
               typeof obj.getElementById === 'function';
    }
    
    // Deep search for cy in an object
    function findCyInObject(obj, depth, visited) {
        if (depth > 8 || !obj || typeof obj !== 'object') return null;
        if (visited.has(obj)) return null;
        visited.add(obj);
        
        if (isCyInstance(obj)) return obj;
        
        // Check common property names
        var names = ['cy', '_cy', 'cytoscape', '_cytoscape', 'state', 'memoizedState', 'stateNode'];
        for (var i = 0; i < names.length; i++) {
            try {
                var val = obj[names[i]];
                if (isCyInstance(val)) return val;
                if (val && typeof val === 'object') {
                    var found = findCyInObject(val, depth + 1, visited);
                    if (found) return found;
                }
            } catch (e) {}
        }
        return null;
    }
    
    function findCy() {
        var container = document.getElementById('staff-network-weekly');
        if (!container) return null;
        
        // Method 1: Check container and children for React fiber
        var elements = [container].concat(Array.from(container.querySelectorAll('*')));
        
        for (var i = 0; i < elements.length; i++) {
            var el = elements[i];
            
            for (var key in el) {
                if (key.indexOf('__reactFiber') !== 0 && key.indexOf('__reactInternalInstance') !== 0) continue;
                
                try {
                    var fiber = el[key];
                    var visited = new Set();
                    var count = 0;
                    
                    while (fiber && count < 150) {
                        count++;
                        if (visited.has(fiber)) break;
                        visited.add(fiber);
                        
                        // Deep search in fiber
                        var cy = findCyInObject(fiber, 0, new Set());
                        if (cy) {
                            console.log('[GroupDrag] Found cy via fiber at depth ' + count);
                            return cy;
                        }
                        
                        fiber = fiber.return;
                    }
                } catch (e) {}
            }
        }
        
        // Method 2: Check canvas element specifically
        var canvas = container.querySelector('canvas');
        if (canvas) {
            for (var key in canvas) {
                if (key.indexOf('__') === 0) {
                    try {
                        var cy = findCyInObject(canvas[key], 0, new Set());
                        if (cy) {
                            console.log('[GroupDrag] Found cy via canvas.' + key);
                            return cy;
                        }
                    } catch (e) {}
                }
            }
        }
        
        return null;
    }
    
    var attempts = 0;
    var maxAttempts = 200;
    
    function poll() {
        attempts++;
        if (attempts > maxAttempts) {
            console.log('[GroupDrag] Gave up after ' + maxAttempts + ' attempts');
            return;
        }
        
        var cy = findCy();
        if (cy) {
            attachHandlers(cy);
            return;
        }
        
        setTimeout(poll, 100);
    }
    
    // Start after a delay
    setTimeout(poll, 1000);
    
    // Also try on DOM changes
    var observer = new MutationObserver(function() {
        if (attempts < maxAttempts) {
            var cy = findCy();
            if (cy) attachHandlers(cy);
        }
    });
    observer.observe(document.body, { childList: true, subtree: true });
    
})();
