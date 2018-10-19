/**
 * This JS file controls all network rendering as well as
 *  annotation tree and other filter options and controls
 *  URL for querying the NeuroMMSig API.
 *
 * @summary   Network controller of NeuroMMSig explorer
 *
 * @requires jquery, d3, inspire-tree, blob
 *
 */


// Constants used in the graph controller
var nominalBaseNodeSize = 10; // Default node radius
var edgeStroke = 3.5;  // Edge width
var minZoom = 0.1, maxZoom = 10; // Zoom variables
var opacity = 0.3; //opacity links

//Convex Hull Constants
var curveTypes = ['curveBasisClosed', 'curveCardinalClosed', 'curveCatmullRomClosed', 'curveLinearClosed'];
var scaleFactor = 1.2;
var centroid, polygon, subgraphs, groups;
var color = d3.scaleOrdinal(d3.schemeCategory10);
var simulationAlpha = 0.3; //Alpha simulation convex hulls

var valueline = d3.line()
    .x(function (d) {
        return d[0];
    })
    .y(function (d) {
        return d[1];
    })
    .curve(d3.curveCatmullRomClosed);

/**
 * Return the nodes that are part of a given subgraph.
 * @param {string} subgraphGroup. subgraph name
 * @param {array} links. all links
 * @returns {array} nodes part of the given subgraph
 */
function getNodesInSubgraph(subgraphGroup, links) {

    var groupNodes = [];

    $.each(links, function (key, edge) {
        // Filtering the nodes for each subgraph
        var annotations = getPathwayAnnotations(edge); // Get all the Object with the present subgraph annotations in edge

        for (var annotation in annotations) { // For each annotation checks if the subgraph annotation are the ones for the queried subgraphs
            if (subgraphGroup === annotation) { // If yes, add both nodes in the edge to an object that might contain duplicates
                groupNodes.push(edge.source);
                groupNodes.push(edge.target);
            }
        }
    });

    return groupNodes
}

// select nodes of the group, retrieve its positions
// and return the convex hull of the specified points
// (3 points as minimum, otherwise returns null)
var polygonGenerator = function (subgraphGroup, links) {
    var node_coords = getNodesInSubgraph(subgraphGroup, links)
        .map(function (d) {
            return [d.x, d.y];
        });
    return d3.polygonHull(node_coords);
};


function updateGroups(links, paths) {

    subgraphs.forEach(function (subgraph) {
        var path = paths.filter(function (d) {
            return d === subgraph;
        }).attr('transform', 'scale(1) translate(0,0)')
            .attr('d', function (d) {

                polygon = polygonGenerator(subgraph, links);
                centroid = d3.polygonCentroid(polygon);

                // to scale the shape properly around its points:
                // move the 'g' element to the centroid point, translate
                // all the path around the center of the 'g' and then
                // we can scale the 'g' element properly
                return valueline(
                    polygon.map(function (point) {
                        return [point[0] - centroid[0], point[1] - centroid[1]];
                    })
                );
            });

        // Only when path is defined
        if (path !== undefined) {
            d3.select(path.node().parentNode).attr('transform', 'translate(' + centroid[0] + ',' + (centroid[1]) + ') scale(' + scaleFactor + ')');
        }
    });
}


/**
 * Flatten object returning all its keys and values in array.
 * @param {string} object.
 * @returns {array}
 * @example
 * // returns ['foo','value']
 * flattenObject({foo:'value'})
 */
function flattenObject(object) {
    return Object.keys(object).reduce(function (r, k) {
        return r.concat(k, object[k]);
    }, [])
}


/**
 * Creates an object with all default parameters necessary
 * @param {InspireTree} tree
 * @returns {object} Object with pks, remove, append and selected nodes in the tree
 */
function getDefaultAjaxParameters(tree, firstTry) {

    // Only get the selected nodes in the three if it is not the first time.
    if (firstTry) {
        var args = getSelectedNodesFromTree(tree);
    }
    else {
        var args = {};
    }

    var pathways = [];
    var resources = [];

    $.each(queriedPathways, function (pathwayName, resourceName) {
        pathways.push(pathwayName);
        resources.push(resourceName);
    });

    args["pathways[]"] = pathways;
    args["resources[]"] = resources;

    return args
}

/**
 * Get all annotations needed to build the tree using the pathway default query
 * @returns {object} JSON object coming from the API ready to render the tree
 */
function getAnnotationForTree(tree, firstTry) {
    return doAjaxCall("/api/tree/?" + $.param(getDefaultAjaxParameters(tree, firstTry), true));
}

/**
 * Renders the network given default parameters
 * @param {InspireTree} tree
 */
function renderNetwork(tree) {
    // Store filtering parameters from tree and global variables (pks, expand/delete nodes)

    var args = getDefaultAjaxParameters(tree);

    var renderParameters = $.param(args, true);

    $.getJSON("/api/pathway/?" + renderParameters, function (data) {
        initD3Force(data, tree);
    });
}

/**
 * Gets the best name for a node object
 * @param {object} nodeData object
 * @returns {str} canonical name of the node
 */
function getCanonicalName(nodeData) {
    if (nodeData.cname) {
        return nodeData.cname;
    } else if (nodeData.name) {
        return nodeData.name
    } else if (nodeData.bel) {
        return nodeData.bel
    } else {
        console.log('Undefined node: ' + nodeData);
        return 'UNDEFINED'
    }
}


/**
 * Renders node info table
 * @param {object} node object
 */
function displayNodeInfo(node) {

    var dynamicTable = document.getElementById('info-table');

    while (dynamicTable.rows.length > 0) {
        dynamicTable.deleteRow(0);
    }

    var nodeObject = {};

    nodeObject["Node"] = node.bel;

    if (node.name) {
        nodeObject["Name"] = getCanonicalName(node);
    }
    if (node.function) {
        nodeObject["Function"] = node.function;
    }
    if (node.namespace) {
        nodeObject["Namespace"] = node.namespace;
    }
    if (node.label) {
        nodeObject["Label"] = node.label
    }
    if (node.description) {
        nodeObject["Description"] = node.description
    }

    var row = 0;
    $.each(nodeObject, function (key, value) {
        insertRow(dynamicTable, row, key, value);
        row++
    });
}


/**
 * Renders edge info table
 * @param {object} edge object
 */
function displayEdgeInfo(edge) {

    var edgeObject = {};

    if (edge.contexts) {
        $.each(edge.contexts, function (key, context) {

                edgeObject[key] = '<dl class="dl-horizontal">';
                edgeObject[key] += '<dt>BEL</dt><dd><code>' + context.bel + '</code></dd>';

                if (context.citation) {
                    edgeObject[key] += '<dt>Citation</dt><dd>';
                    if (context.citation.type === "PubMed") {
                        edgeObject[key] += '<a target="_blank" href="https://www.ncbi.nlm.nih.gov/pubmed/' + context.citation.reference + '" style="text-decoration: underline">PMID:' + context.citation.reference + ' <span class="glyphicon glyphicon-new-window"></a> </span></a>';
                    } else if (context.citation.type === "URL") {
                        edgeObject[key] += '<a target="_blank" href=' + context.citation.reference + " target='_blank' " +
                            "style='text-decoration: underline'>" + context.citation.reference + "</a>";
                    } else {
                        edgeObject[key] += context.citation.reference;
                    }

                    edgeObject[key] += '</dd>';
                }

                if (context.evidence) {
                    edgeObject[key] += '<dt>Support</dt><dd>' + context.evidence + "</dd>";
                }

                if (context.annotations && Object.keys(context.annotations).length > 0) {
                    $.each(context.annotations, function (annotation_key, annotation_values) {
                        $.each(annotation_values, function (annotation_value) {
                            edgeObject[key] += '<dt>' + annotation_key + '</dt><dd>' + annotation_value + '</dd>';
                        });
                    });
                }

                edgeObject[key] += '</dl>';
            }
        );
    }

    var dynamicTable = document.getElementById('info-table');

    while (dynamicTable.rows.length > 0) {
        dynamicTable.deleteRow(0);
    }

    var row = 0;
    $.each(edgeObject, function (sk, column1) {
        var row = dynamicTable.insertRow(row);
        var cell1 = row.insertCell(0);
        cell1.innerHTML = column1;
        row++
    });
}


///////////////////////// BEL Commons //////////////////////////////

/**
 * Returns a random integer between min (inclusive) and max (inclusive)
 * Using Math.round() will give you a non-uniform distribution!
 * @param {int} min
 * @param {int} max
 * @return {int}
 */
function getRandomInt(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}


/**
 * Returns object with selected nodes in tree
 * @param {InspireTree} tree
 * @returns {object} selected nodes in the tree
 */
function getSelectedNodesFromTree(tree) {

    var selectedNodes = tree.selected(true);

    var selectionHashMap = {};

    selectedNodes.forEach(function (nodeObject) {

        var key = nodeObject.text.toString();

        selectionHashMap[key] = nodeObject.children.map(function (child) {
            return child.text
        });
    });

    return selectionHashMap;
}


/**
 * Performs an AJAX call given an URL
 * @param {string} url
 */
function doAjaxCall(url) {

    var result = null;
    $.ajax({
        type: "GET",
        url: url,
        dataType: "json",
        success: function (data) {
            result = data;
        },
        data: {},
        async: false
    });

    return result
}


/**
 * Creates a new row in Node/Edge info table
 * @param {object} table: table object
 * @param {int} row: row number
 * @param {string} column1: string for column1
 * @param {string} column2: string for column2
 */
function insertRow(table, row, column1, column2) {

    var row = table.insertRow(row);
    var cell1 = row.insertCell(0);
    var cell2 = row.insertCell(1);
    cell1.innerHTML = column1;
    cell2.innerHTML = column2;
}


$(document).ready(function () {

    //Initialize toggle button
    $('#tree-toggle').bootstrapToggle();

    // Initiate the tree and expands it with the annotations given pks of subgraphs
    var tree = new InspireTree({
        target: "#tree",
        selection: {
            mode: "checkbox",
            multiple: true
        },
        data: getAnnotationForTree(tree, false)
    });

    tree.on("model.loaded", function () {
        tree.expand();
    });

    // Enables tree search
    $('#tree-search').on('keyup', function (ev) {
        tree.search(ev.target.value);
    });

    // render network
    renderNetwork(tree);

    $("#refresh-network").on("click", function () {
        renderNetwork(tree);
    });

    $("#collapse-tree").on("click", function () {
        tree.collapseDeep();
    });

    // // Export network as an image
    d3.select("#save-svg-graph").on("click", function () {
        saveSvgAsPng(d3.select('#graph-svg').nodes()[0], 'MyNetwork.png');
    });

    // Export to BEL
    $("#bel-button").click(function () {
        var args = getDefaultAjaxParameters(tree);
        args["format"] = "bel";

        $.ajax({
            url: "/api/pathway/",
            dataType: "text",
            data: $.param(args, true)
        }).done(function (response) {
            downloadText(response, "pathme_pathway.bel")
        });
    });

    $(".explorer-download").click(function () {
        var args = getDefaultAjaxParameters(tree);
        args["format"] = $(this).data('format');
        window.location.href = "/api/pathway/?" + $.param(args, true);
    });

    // Controls behaviour of clicking in dropdowns
    $('li.dropdown.mega-dropdown a').on('click', function () {
        $(this).parent().toggleClass('open');
    });

    $('body').on('click', function (e) {
        if (!$('li.dropdown.mega-dropdown').is(e.target)
            && $('li.dropdown.mega-dropdown').has(e.target).length === 0
            && $('.open').has(e.target).length === 0
        ) {
            $('li.dropdown.mega-dropdown').removeClass('open');
        }
    });
});


/**
 * Clears used node/edge list and network
 * @example: Used to repopulate the html with a new network
 */
function clearUsedDivs() {
    $("#graph-chart").empty();
    $("#node-list").empty();
    $("#edge-list").empty();
}


///////////////////////////////////////
/// Functions for updating the graph //
///////////////////////////////////////

/**
 * Save previous positions of the nodes in the graph
 * @returns {object} Object with key to previous position
 */
function savePreviousPositions() {
    // Save current positions into prevLoc "object;
    var prevPos = {};

    // __data__ can be accessed also as an attribute (d.__data__)
    d3.selectAll(".node").data().map(function (d) {
        if (d) {
            prevPos[d.id] = [d.x, d.y];
        }

        return d;
    });

    return prevPos
}

/**
 * Update previous node position given new data (if nodes were previously there)
 * @param {object} jsonData: new node data
 * @param {object} prevPos: object created by savePreviousPositions
 * @returns {object}
 */
function updateNodePosition(jsonData, prevPos) {

    var newNodesArray = [];

    // Set old locations back into the original nodes
    $.each(jsonData.nodes, function (index, value) {

        if (prevPos[value.id]) {

            oldX = prevPos[value.id][0];
            oldY = prevPos[value.id][1];
            // value.fx = oldX;
            // value.fy = oldY;
        } else {
            // If no previous coordinate... Start from off screen for a fun zoom-in effect
            oldX = -100;
            oldY = -100;
            newNodesArray.push(value.id);
        }

        value.x = oldX;
        value.y = oldY;

    });

    return {json: jsonData, new_nodes: newNodesArray}
}

/**
 * Find duplicate ID nodes
 * @param {object} data
 * @returns {array} array of duplicates
 * @example: Necessary to node represent the nodes together with their function if they have the same cname
 */
function findDuplicates(data) {

    var hashMap = {};

    data.forEach(function (element, index) {

        if (!(element in hashMap)) {
            hashMap[element] = 0;
        }
        hashMap[element] += 1;
    });

    var duplicates = [];

    $.each(hashMap, function (key, value) {
        if (value > 1) {
            duplicates.push(key);
        }
    });

    return duplicates;
}


function downloadText(response, name) {
    var element = document.createElement("a");
    encoded_response = encodeURIComponent(response);
    element.setAttribute("href", "data:text/plain;charset=utf-8," + encoded_response);
    element.setAttribute("download", name);
    element.style.display = "none";
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
}

/**
 * Gets edge types as a dictionary
 * @param {object} edge json data
 * @return {object}
 */
function getEdgeTypes(edge) {
    var edgeTypes = {};

    $(edge.contexts).each(function (index, context) {
        edgeTypes[context.relation] = true;
    });

    return edgeTypes;
}

/**
 * Gets edge pathway annotations as a dictionary
 * @param {object} edge json data
 * @return {object}
 */
function getPathwayAnnotations(edge) {
    var pathwayAnnotations = {};

    $(edge.contexts).each(function (index, context) {

        if ("annotations" in context && "PathwayID" in context.annotations) {
            for (var pathway in context.annotations["PathwayID"]) {
                pathwayAnnotations[pathway] = true;
            }
        }
    });

    return pathwayAnnotations;
}

/**
 * Gets edge contradiction annotations as a dictionary
 * @param {object} edge json data
 * @return {object}
 */
function getContradictionAnnotations(edge) {
    var contradictionAnnotations = {};

    $(edge.contexts).each(function (index, context) {

        if ("annotations" in context && "Interesting edge" in context.annotations) {
            for (var interesting in context.annotations["Interesting edge"]) {
                contradictionAnnotations[interesting] = true;
            }
        }
    });

    return contradictionAnnotations;
}


/**
 * Checks if there are any causal edges
 * @param {object} edge json data
 * @return {boolean}
 */
function doesEdgeHaveCausal(edge) {

    var edgeTypes = getEdgeTypes(edge);

    var causal_edge_types = ["decreases", "directlyDecreases", "increases", "directlyIncreases"];
    for (var i in causal_edge_types) {
        if (causal_edge_types[i] in edgeTypes) {
            return true;
        }
    }
    return false;
}


/**
 * Initialize d3 Force to plot network from json
 * @param {object} graph json data
 * @param {InspireTree} tree
 */
function initD3Force(graph, tree) {

    //////////////////////////////
    // Main graph visualization //
    //////////////////////////////

    $(".disabled").attr("class", "nav-link ");     // Enable nodes and edges tabs

    var graphDiv = $("#graph-chart"); // Force div

    var nodePanel = $("#node-list"); // Node submit_data div

    var edgePanel = $("#edge-list"); // Edge submit_data div

    clearUsedDivs();

    d = document;
    e = d.documentElement;
    g = d.getElementsByTagName("body")[0];

    var w = graphDiv.width(), h = graphDiv.height();

    // Simulation parameters
    var linkDistance = 100, fCharge = -1700, linkStrength = 0.7, collideStrength = 1;

    // Simulation defined with variables
    var simulation = d3.forceSimulation()
        .force("link", d3.forceLink()
            .distance(linkDistance)
            .strength(linkStrength)
        )
        .force("collide", d3.forceCollide()
            .radius(function (d) {
                return d.r + 10
            })
            .strength(collideStrength)
        )
        .force("charge", d3.forceManyBody()
            .strength(fCharge)
        )
        .force("center", d3.forceCenter(w / 2, h / 2))
        .force("y", d3.forceY(0))
        .force("x", d3.forceX(0));

    // Pin down functionality
    var nodeDrag = d3.drag()
        .on("start", dragStarted)
        .on("drag", dragged)
        .on("end", dragEnded);

    // Methods to drug the groups (convex hulls)
    function groupDragStarted() {
        if (!d3.event.active) simulation.alphaTarget(simulationAlpha).restart();
        d3.select(this).select('path').style('stroke-width', 3);
    }

    function groupDragged(subgraphGroup) {
        $.each(getNodesInSubgraph(subgraphGroup, graph.links), function (index, d) {
            d.x += d3.event.dx;
            d.y += d3.event.dy;
        });
    }

    function groupDragEnded() {
        if (!d3.event.active) simulation.alphaTarget(simulationAlpha).restart();
        d3.select(this).select('path').style('stroke-width', 1);
    }

    function dragStarted(d) {
        if (!d3.event.active) simulation.alphaTarget(simulationAlpha).restart();
        d.fx = d.x;
        d.fy = d.y;
    }

    function dragged(d) {
        d.fx = d3.event.x;
        d.fy = d3.event.y;
    }

    function dragEnded() {
        if (!d3.event.active) simulation.alphaTarget(0);
    }

    function releaseNode(d) {
        d.fx = null;
        d.fy = null;
    }

    //END Pin down functionality

    var svg = d3.select("#graph-chart").append("svg")
        .attr("class", "svg-border")
        .attr("id", "graph-svg")
        .attr("width", w)
        .attr("height", h);

    // // Create definition for arrowhead.
    svg.append("defs").append("marker")
        .attr("id", "arrowhead")
        .attr("viewBox", "0 -5 10 10")
        .attr("refX", 20)
        .attr("refY", 0)
        .attr("markerUnits", "strokeWidth")
        .attr("markerWidth", 6)
        .attr("markerHeight", 6)
        .attr("orient", "auto")
        .attr("opacity", opacity)
        .append("path")
        .attr("d", "M0,-5L10,0L0,5");

    // // Create definition for stub.
    svg.append("defs").append("marker")
        .attr("id", "stub")
        .attr("viewBox", "-1 -5 2 10")
        .attr("refX", 15)
        .attr("refY", 0)
        .attr("markerUnits", "strokeWidth")
        .attr("markerWidth", 6)
        .attr("markerHeight", 6)
        .attr("orient", "auto")
        .attr("opacity", opacity)
        .append("path")
        .attr("d", "M 0,0 m -1,-5 L 1,-5 L 1,5 L -1,5 Z");

    // // Create definition for cross.
    svg.append("defs").append("marker")
        .attr("id", "cross")
        .attr("viewBox", "-1 -5 2 10")
        .attr("refX", 15)
        .attr("refY", 0)
        .attr("markerUnits", "strokeWidth")
        .attr("markerWidth", 2)
        .attr("markerHeight", 6)
        .attr("orient", "auto")
        .attr("opacity", opacity)
        .append("path")
        .attr("d", "M 3,3 L 7,7 M 3,7 L 7,3");


    // Background
    svg.append("rect")
        .attr("width", "100%")
        .attr("height", "100%")
        .attr("fill", "#fcfbfb")
        .style("pointer-events", "all");

    var g = svg.append("g");  // g = svg object where the graph will be appended

    var linkedByIndex = {};
    graph.links.forEach(function (d) {
        linkedByIndex[d.source + "," + d.target] = true;
    });

    function isConnected(a, b) {
        return linkedByIndex[a.index + "," + b.index] || linkedByIndex[b.index + "," + a.index] || a.index === b.index;
    }

    function ticked() {
        link.attr("x1", function (d) {
            return d.source.x;
        })
            .attr("y1", function (d) {
                return d.source.y;
            })
            .attr("x2", function (d) {
                return d.target.x;
            })
            .attr("y2", function (d) {
                return d.target.y;
            });

        node.attr("transform", function (d) {
            return "translate(" + d.x + ", " + d.y + ")";
        });

        updateGroups(graph.links, paths);

    }

    simulation.nodes(graph.nodes)
        .on("tick", ticked);

    simulation.force("link")
        .links(graph.links);

    /////////////////////////////
    // Modify the simulation   //
    /////////////////////////////

    function inputted() {
        simulation.force("link").strength(+this.value);
        simulation.alpha(1).restart();
    }

    d3.select("#link-slider").on("input", inputted);

    ////////////////////////////////////////////////////
    // Definition of links, nodes, text, groups...
    ////////////////////////////////////////////////////

    groups = g.append('g').attr('class', 'groups');

    var link = g.selectAll(".link")
        .data(graph.links)
        .enter().append("line")
        .style("stroke-width", edgeStroke)
        .style("stroke-opacity", 0.4)
        .on("click", displayEdgeInfo)
        .attr("class", function (edge) {

            edgeTypes = getEdgeTypes(edge);

            interestingAnnotations = getContradictionAnnotations(edge);

            // Highlight interesting edges
            if (interestingAnnotations && ("Contradicts" in interestingAnnotations || "May contradict" in interestingAnnotations)) {
                return 'link link_continuous link_red';
            }

            // Highlight causal edge
            if (doesEdgeHaveCausal(edge)) {
                return "link link_continuous";
            }

            // Highlight negative correlations and positive correlations
            if ('negativeCorrelation' in edgeTypes) {
                return 'link link_dashed link_red';
            }

            if ('positiveCorrelation' in edgeTypes) {
                return 'link link_dashed link_blue';
            }

            return "link link_dashed"
        })
        .attr("marker-end", function (edge) {

            edgeTypes = getEdgeTypes(edge);

            if ("increases" in edgeTypes || "directlyIncreases" in edgeTypes) {
                return "url(#arrowhead)"
            } else if ("decreases" in edgeTypes || "directlyDecreases" in edgeTypes) {
                return "url(#stub)"
            } else {
                return ""
            }
        })
        .attr("marker-mid", function (edge) {

            edgeTypes = getEdgeTypes(edge);

            if ("causeNoChange" in edgeTypes) {
                return "url(#cross)"
            } else {
                return ""
            }
        });

    var node = g.selectAll(".nodes")
        .data(graph.nodes)
        .enter().append("g")
        .attr("class", "node")
        // Next two lines -> Pin down functionality
        .on("dblclick", releaseNode)
        // Box info
        .on("click", function (d) {
            displayNodeInfo(d);
        })
        // Dragging
        .call(nodeDrag);

    var circle = node.append("circle")
        .attr("r", nominalBaseNodeSize)
        .attr("class", function (data) {
            return data.function
        });

    var text = node.append("text")
        .attr("class", "node-name")
        .attr("id", function (d) {
            return d.id;
        })
        .attr("fill", "black")
        .attr("dx", 16)
        .attr("dy", ".35em")
        .text(function (d) {
            return getCanonicalName(d);
        });

    // Highlight on mouse-enter and back to normal on mouseout
    node.on("mouseenter", function (data, index) {
        d3.select(this).classed('node_highlighted', true);


        link.classed("link_highlighted", function (o) {
            return o.source.index === index || o.target.index === index;
        });

        node.classed('node_highlighted', function (o) {
            return isConnected(data, o);
        });
    })
        .on("mousedown", function () {
            d3.event.stopPropagation();
        })
        .on("mouseout", function () {
            link.classed("link_highlighted", false);
            node.classed("node_highlighted", false);
        });


    // Highlight links on mouseenter and back to normal on mouseout
    link.on("mouseenter", function (data) {
        d3.select(this).classed('link_highlighted', true);
    })
        .on("mousedown", function () {
            d3.event.stopPropagation();
        })
        .on("mouseout", function () {
            d3.select(this).classed('link_highlighted', false);
        });


    /**
     * Freeze the graph when space is pressed
     */
    function freezeGraph() {
        if (d3.event.keyCode === 32) {
            simulation.stop();
        }
    }

    /**
     * Returns nodes that not pass the filter given a node array/property
     * @param {array} nodeArray
     * @param {string} property
     * @example: nodesNotInArray(['AKT1','APP'], 'cname')
     * @example: nodesNotInArray([1,2], 'id')
     */
    function nodesNotInArray(nodeArray, property) {
        return svg.selectAll(".node").filter(function (el) {
            return nodeArray.indexOf(el[property]) < 0;
        });
    }

    /**
     * Returns nodes that pass the filter given a node array/property (keeps the order of the nodeArray)
     * @param {array} nodeArray
     * @param {string} property
     * @example: nodesNotInArray(['AKT1','APP'], 'cname')
     * @example: nodesNotInArray([1,2], 'id')
     */
    function nodesInArrayKeepOrder(nodeArray, property) {
        return nodeArray.map(function (el) {
            var nodeObject = svg.selectAll(".node").filter(function (node) {
                return el === node[property]
            });
            return nodeObject._groups[0][0]
        });
    }

    /**
     * Resets default styles for nodes/edges/text on double click
     */
    function resetAttributesDoubleClick() {
        // On double click reset attributes (Important disabling the zoom behavior of dbl click because it interferes with this)
        svg.on("dblclick", function () {
            // Remove the overriding stroke so the links default back to the CSS definitions
            link.style("stroke", null);

            // SET default attributes //
            svg.selectAll(".link, .node").style("visibility", "visible")
                .style("opacity", "1");
            // Show node names
            svg.selectAll(".node-name").style("visibility", "visible").style("opacity", "1");
        });

    }

    /**
     * Resets default styles for nodes/edges/text
     */
    function resetAttributes() {
        // Reset visibility and opacity
        svg.selectAll(".link, .node").style("visibility", "visible").style("opacity", "1");
        // Show node names
        svg.selectAll(".node-name").style("visibility", "visible").style("opacity", "1");
        svg.selectAll(".node-name").style("display", "block");
    }

    /**
     * Hides the text of an array of Nodes
     * @param {array} nodeList
     * @param {boolean} visualization. If true: opacity to 0.1, false: 0.0 (hidden)
     * @example hideNodesText([1,34,5,56], false, 'id')
     */
    function hideNodesText(nodeList, visualization) {
        // Filter the text to those not belonging to the list of node names

        var nodesNotInList = g.selectAll(".node-name").filter(function (d) {
            return nodeList.indexOf(d.id) < 0;
        });

        if (visualization !== true) {
            //noinspection JSDuplicatedDeclaration
            var visualizationOption = "opacity", on = "1", off = "0.1";
        } else {
            //noinspection JSDuplicatedDeclaration
            var visualizationOption = "visibility", on = "visible", off = "hidden";
        }

        // Change display property to "none"
        $.each(nodesNotInList._groups[0], function (index, value) {
            value.style.setProperty(visualizationOption, off);
        });
    }

    /**
     * Hides the text of an array of node paths
     * @param {array} data
     * @param {boolean} visualization. If true: opacity to 0.1, false: 0.0 (hidden)
     * @param {string} property
     * @example hideNodesTextInPaths([[1,34,5,56],[123,234,3,4]], false, 'id')
     */
    function hideNodesTextInPaths(data, visualization, property) {
        // Array with all nodes in all paths
        var nodesInPaths = [];

        $.each(data, function (index, value) {
            $.each(value, function (index, value) {
                nodesInPaths.push(value);
            });
        });

        // Filter the text whose innerHTML is not belonging to the list of nodeIDs
        var textNotInPaths = g.selectAll(".node-name").filter(function (d) {
            return nodesInPaths.indexOf(d[property]) < 0;
        });

        if (visualization !== true) {
            //noinspection JSDuplicatedDeclaration
            var visualizationOption = "opacity", on = "1", off = "0.1";
        } else {
            //noinspection JSDuplicatedDeclaration
            var visualizationOption = "visibility", on = "visible", off = "hidden";
        }

        // Change display property to "none"
        $.each(textNotInPaths._groups[0], function (index, value) {
            value.style.setProperty(visualizationOption, off);
        });
    }

    /**
     * Changes the opacity to 0.1 of edges that are not in array
     * @param {array} edgeArray
     * @param {string} property of the edge to filter
     */
    function highlightEdges(edgeArray, property) {
        // Array with names of the nodes in the selected edge
        var nodesInEdges = [];

        // Filtered not selected links
        var edgesNotInArray = g.selectAll(".link").filter(function (edgeObject) {

            if (edgeArray.indexOf(edgeObject.source[property] + "-" + edgeObject.target[property]) >= 0) {
                nodesInEdges.push(edgeObject.source[property]);
                nodesInEdges.push(edgeObject.target[property]);
            }
            else return edgeObject;
        });

        var nodesNotInEdges = node.filter(function (nodeObject) {
            return nodesInEdges.indexOf(nodeObject[property]) < 0;
        });

        nodesNotInEdges.style("opacity", "0.1");
        edgesNotInArray.style("opacity", "0.1");

    }

    /**
     * Highlights nodes from array using property as filter and changes the opacity of the rest of nodes
     * @param {array} nodeArray
     * @param {string} property of the edge to filter
     */
    function highlightNodes(nodeArray, property) {
        // Filter not mapped nodes to change opacity
        var nodesNotInArray = svg.selectAll(".node").filter(function (el) {
            return nodeArray.indexOf(el[property]) < 0;
        });

        // Not mapped links
        var notMappedEdges = g.selectAll(".link").filter(function (el) {
            // Source and target should be present in the edge
            return !(nodeArray.indexOf(el.source[property]) >= 0 || nodeArray.indexOf(el.target[property]) >= 0);
        });

        nodesNotInArray.style("opacity", "0.1");
        notMappedEdges.style("opacity", "0.1");
    }


    /**
     * Highlights nodes which property is equal to condition
     * @param {string} property of the node that is going to checked
     * @param {string} condition property to be asserted
     */
    function highlightNodesByProperty(property, condition) {

        // Filter not mapped nodes to change opacity
        var nodesToHighlight = svg.selectAll(".node").filter(function (node) {
            return node[property] === condition;
        });

        // Set opacity of these nodes to 1
        $.each(nodesToHighlight._groups[0], function (index, node) {
            node.style.setProperty("opacity", "1");
        });
    }

    /**
     * Highlights edges which property is equal to condition
     * @param {string} relation relationship to filter
     */
    function highlightEdgesByRelationship(relation) {

        // Filter not mapped nodes to change opacity
        var edgeToHighlight = svg.selectAll(".link").filter(function (edge) {
            return relation in getEdgeTypes(edge)
        });

        // Set opacity of these edges to 1
        $.each(edgeToHighlight._groups[0], function (index, edge) {
            edge.style.setProperty("opacity", "1");
        });
    }

    /**
     * Colors an array of node paths
     * @param {array} data array of arrays
     * @param {boolean} visualization. If true: opacity to 0.1, false: 0.0 (hidden)
     * @example colorPaths([[1,34,5,56],[123,234,3,4]], false)
     */
    function colorPaths(data, visualization) {

        // data: nested array with all nodes in each path
        // visualization: parameter with visualization info ("hide" || "opaque)

        var link = g.selectAll(".link");

        ///////// Filter the nodes ////////

        // Array with all nodes in all paths
        var nodesInPaths = [];

        $.each(data, function (index, value) {
            $.each(value, function (index, value) {
                nodesInPaths.push(value);
            });
        });

        // Filtering the nodes that are not in any of the paths
        var nodesNotInPaths = svg.selectAll(".node").filter(function (el) {
            return nodesInPaths.indexOf(el.id) < 0;
        });

        if (visualization !== true) {
            //noinspection JSDuplicatedDeclaration
            var visualizationOption = "opacity", on = "1", off = "0.1";
        } else {
            //noinspection JSDuplicatedDeclaration
            var visualizationOption = "visibility", on = "visible", off = "hidden";
        }
        nodesNotInPaths.style(visualizationOption, off);

        ///////// Colour links in each path differently and hide others ////////

        // Colour the links ( Max 21 paths )
        var colorArray = ["#ff2200", " #282040", " #a68d7c", " #332b1a", " #435916", " #00add9", " #bfd0ff", " #f200c2",
            " #990014", " #d97b6c", " #ff8800", " #e5c339", " #5ba629", " #005947", " #005580", " #090040",
            " #8d36d9", " #e5005c", " #733941", " #993d00", " #80ffb2", " #66421a", " #e2f200", " #20f200", " #80fff6",
            " #002b40", " #6e698c", " #802079", " #330014", " #331400", " #ffc480", " #7ca682", " #264a4d", " #0074d9",
            " #220080", " #d9a3d5", " #f279aa"];

        // iter = number of paths ( Max 21 paths )
        if (data.length > colorArray.length) {
            //noinspection JSDuplicatedDeclaration
            var iter = colorArray.length;
        } else {
            //noinspection JSDuplicatedDeclaration
            var iter = data.length;
        }

        // First hide or set to opacity 0.1 all links
        link.style(visualizationOption, off);

        // Make visible again all the edges that are in any of the paths
        var edgesInPaths = [];

        for (var x = 0; x < iter; x++) {

            // Push the array (each path) to a new one where all paths are stored
            var path = link.filter(function (el) {
                // Source and target should be present in the edge and the distance in the array should be one
                return ((data[x].indexOf(el.source.id) >= 0 && data[x].indexOf(el.target.id) >= 0)
                    && (Math.abs(data[x].indexOf(el.source.id) - data[x].indexOf(el.target.id)) === 1));
            });

            edgesInPaths.push(path);
        }

        // Only the links that are in any of the paths are visible
        for (var j = 0, len = edgesInPaths.length; j < len; j++) {
            edgesInPaths[j].style(visualizationOption, on);
        }

        // For each path give a different color
        for (var i = 0; i < iter; i++) {
            var edgesInPath = link.filter(function (el) {
                // Source and target should be present in the edge and the distance in the array should be one
                return ((data[i].indexOf(el.source.id) >= 0 && data[i].indexOf(el.target.id) >= 0)
                    && (Math.abs(data[i].indexOf(el.source.id) - data[i].indexOf(el.target.id)) === 1));
            });

            // Select randomly a color and apply to this path
            edgesInPath.style("stroke", colorArray[getRandomInt(0, 21)]);
        }
    }

    /**
     * Process the response of shortest/all paths and highlight nodes/edges in them
     * @param {array} paths array containing path or paths
     * @param {boolean} checkbox boolean (hide other nodes if true)
     * @param {string} pathMethods if "all" -> all paths else-> shortests
     * @example colorPaths([[1,34,5,56],[123,234,3,4]], ,false)
     */
    function handlePathResponse(paths, checkbox, pathMethods) {
        if (pathMethods === "all") {
            if (paths.length === 0) {
                alert("No paths between the selected nodes");
            }

            resetAttributes();

            // Apply changes in style for select paths
            hideNodesTextInPaths(paths, checkbox, 'id');
            colorPaths(paths, checkbox);
            resetAttributesDoubleClick()
        } else {
            // Change style in force
            resetAttributes();

            var nodesNotInPath = nodesNotInArray(paths, 'id');

            var edgesNotInPath = g.selectAll(".link").filter(function (el) {
                // Source and target should be present in the edge and the distance in the array should be one
                return !((paths.indexOf(el.source.id) >= 0 && paths.indexOf(el.target.id) >= 0)
                    && (Math.abs(paths.indexOf(el.source.id) - paths.indexOf(el.target.id)) === 1));
            });

            // If checkbox is True -> Hide all, Else -> Opacity 0.1
            if (checkbox === true) {
                nodesNotInPath.style("visibility", "hidden");
                edgesNotInPath.style("visibility", "hidden");
            } else {
                nodesNotInPath.style("opacity", "0.1");
                edgesNotInPath.style("opacity", "0.05");
            }
            hideNodesText(paths, checkbox);
            resetAttributesDoubleClick();
        }
    }

    // Call freezeGraph when a key is pressed, freezeGraph checks whether this key is "Space" that triggers the freeze
    d3.select(window).on("keydown", freezeGraph);


    /////////////////////////////////////////////////////////////////////////
    // Build the node selection toggle and creates hashmap nodeNames to IDs /
    /////////////////////////////////////////////////////////////////////////

    // Build the node unordered list
    nodePanel.append("<ul id='node-list-ul' class='list-group checked-list-box not-rounded'></ul>");

    // Variable with all node names
    var nodeNames = [];

    // Create node list and create an array with duplicates
    $.each(graph.nodes, function (key, value) {

        nodeNames.push(getCanonicalName(value));

        $("#node-list-ul").append("<li class='list-group-item'><input class='node-checkbox' type='checkbox'>" +
            "<div class='circle " + value.function + "'>" +
            "</div><span class='node-" + value.id + "'>" + getCanonicalName(value) + "</span></li>");
    });

    var duplicates = findDuplicates(nodeNames);

    var nodeNamesToId = {};

    // Check over duplicate cnames and create hashmap to id
    $.each(graph.nodes, function (key, value) {

        // if the node has no duplicate show it in autocompletion with its cname
        if (duplicates.indexOf(value.cname) < 0) {
            nodeNamesToId[getCanonicalName(value)] = value.id;
        }
        // if it has a duplicate show also the function after the cname
        else {
            nodeNamesToId[getCanonicalName(value) + ' (' + value.function + ')'] = value.id;
        }
    });

    // Highlight only selected nodes in the graph
    $("#get-checked-nodes").on("click", function (event) {
        event.preventDefault();
        var checkedItems = [];
        $(".node-checkbox:checked").each(function (idx, li) {
            // Get the class of the span element (node-ID) Strips "node-" and evaluate the string to integer
            checkedItems.push(li.parentElement.childNodes[2].className.replace("node-", ""))
        });

        resetAttributes();
        highlightNodes(checkedItems, 'id');
        resetAttributesDoubleClick();

    });

    ///////////////////////////////////////
    // Build the edge selection toggle
    ///////////////////////////////////////


    // Build the node unordered list
    edgePanel.append("<ul id='edge-list-ul' class='list-group checked-list-box not-rounded'></ul>");

    /**
     * Creates the edge search functionality and get the nodes in each annotation
     */

    var subgraphsToNodes = {};

    $.each(graph.links, function (key, edge) {

        // Edge Search functionality

        edgeTypes = getEdgeTypes(edge);

        for (edgeType in edgeTypes) {
            $("#edge-list-ul").append("<li class='list-group-item'><input class='edge-checkbox' type='checkbox'><span id="
                + edge.source.id + '-' + edge.target.id + ">" + getCanonicalName(edge.source) + ' <strong><i>' + edgeType +
                '</i></strong> ' + getCanonicalName(edge.target) + "</span></li>");
        }

        // Filtering the nodes for each subgraph
        var annotations = getPathwayAnnotations(edge); // Get all the Object with the present subgraph annotations in edge

        for (var annotation in annotations) { // For each annotation checks if the subgraph annotation are the ones for the queried subgraphs

            if (pathwayIds.includes(annotation)) { // If yes, add both nodes in the edge to an object that might contain duplicates

                if (annotation in subgraphsToNodes) {
                    subgraphsToNodes[annotation].push(edge.source);
                    subgraphsToNodes[annotation].push(edge.target);
                }
                else {
                    subgraphsToNodes[annotation] = [edge.source];
                    subgraphsToNodes[annotation].push(edge.target);
                }
            }
        }
    });

    // Subgraph names array
    subgraphs = Object.keys(subgraphsToNodes);

    // Subgraph to Color Object
    subgraphToColor = {};

    var paths = groups.selectAll('.path_placeholder')
        .data(subgraphs, function (d) {
            return d;
        })
        .enter()
        .append('g')
        .attr('class', 'path_placeholder')
        .append('path')
        .attr('stroke', function (d) {
            // Fill up the subgraphToColor object
            subgraphToColor[d] = color(d);
            return color(d);
        })
        .attr('fill', function (d) {
            return color(d);
        })
        .attr('opacity', 0.2);

    // Color legend
    $.each(subgraphToColor, function (index, value) {
        pathwayIds2Name[""] = '';
    });

    // add interaction to the groups
    groups.selectAll('.path_placeholder')
        .call(d3.drag()
            .on('start', groupDragStarted)
            .on('drag', groupDragged)
            .on('end', groupDragEnded)
        );

    function zoomed() {
        //Transform svg and update convex hull
        g.attr("transform", d3.event.transform);
        updateGroups(graph.links, paths);
    }

    // Zoomming/Panning functionality
    svg.call(d3.zoom()
        .scaleExtent([minZoom, maxZoom])
        .on("zoom", zoomed))
        .on("dblclick.zoom", null);

    /// Convex Hull Specific

    $("#get-checked-edges").on("click", function (event) {
        event.preventDefault();

        var checkedItems = [];
        $(".edge-checkbox:checked").each(function (idx, li) {
            checkedItems.push(li.parentElement.childNodes[1].id);
        });

        resetAttributes();

        highlightEdges(checkedItems, 'id');

        resetAttributesDoubleClick();
    });

    var pathForm = $("#path-form");

    $("#button-paths").on("click", function () {
        if (pathForm.valid()) {

            var checkbox = pathForm.find("input[name='visualization-options']").is(":checked");

            var args = getDefaultAjaxParameters(tree);
            args["source"] = nodeNamesToId[pathForm.find("input[name='source']").val()];
            args["target"] = nodeNamesToId[pathForm.find("input[name='target']").val()];
            args["paths_method"] = $("input[name=paths_method]:checked", pathForm).val();

            var undirected = pathForm.find("input[name='undirectionalize']").is(":checked");

            if (undirected) {
                args["undirected"] = undirected;
            }

            $.ajax({
                url: "/api/pathway/paths",
                type: pathForm.attr("method"),
                dataType: "json",
                data: $.param(args, true),
                success: function (paths) {

                    if (args["paths_method"] === "all") {

                        resetAttributes();

                        // Apply changes in style for select paths
                        hideNodesTextInPaths(paths["paths"], checkbox, 'id');
                        colorPaths(paths["paths"], checkbox);
                        resetAttributesDoubleClick();

                    }
                    else {

                        // Change style in force
                        resetAttributes();

                        var nodesNotInPath = nodesNotInArray(paths, 'id');

                        var edgesNotInPath = g.selectAll(".link").filter(function (el) {
                            // Source and target should be present in the edge and the distance in the array should be one
                            return !((paths.indexOf(el.source.id) >= 0 && paths.indexOf(el.target.id) >= 0)
                                && (Math.abs(paths.indexOf(el.source.id) - paths.indexOf(el.target.id)) === 1));
                        });

                        // If checkbox is True -> Hide all, Else -> Opacity 0.1
                        if (checkbox === true) {
                            nodesNotInPath.style("visibility", "hidden");
                            edgesNotInPath.style("visibility", "hidden");
                        } else {
                            nodesNotInPath.style("opacity", "0.1");
                            edgesNotInPath.style("opacity", "0.05");
                        }
                        hideNodesText(paths, checkbox, 'id');
                        resetAttributesDoubleClick();
                    }
                }, error: function (request) {
                    alert(request.responseText);
                }
            })
        }
    });

    // Path validation form
    pathForm.validate(
        {
            rules: {
                source: {
                    required: true,
                    minlength: 2
                },
                target: {
                    required: true,
                    minlength: 2
                }
            },
            messages: {
                source: "Please enter a valid source",
                target: "Please enter a valid target"
            }
        }
    );


    // Path autocompletion input
    var nodeNamesSorted = Object.keys(nodeNamesToId).sort();

    $("#source-node").autocomplete({
        source: nodeNamesSorted,
        appendTo: "#paths"
    });

    $("#target-node").autocomplete({
        source: nodeNamesSorted,
        appendTo: "#paths"
    });

    // Update Node Dropdown
    $("#node-search").on("keyup", function () {
        // Get value from search form (fixing spaces and case insensitive
        var searchText = $(this).val();
        searchText = searchText.toLowerCase();
        searchText = searchText.replace(/\s+/g, "");

        $.each($("#node-list-ul")[0].childNodes, updateNodeArray);

        function updateNodeArray() {
            var currentLiText = $(this).find("span")[0].innerHTML,
                showCurrentLi = ((currentLiText.toLowerCase()).replace(/\s+/g, "")).indexOf(searchText) !== -1;
            $(this).toggle(showCurrentLi);
        }
    });

    // Update Edge Dropdown
    $("#edge-search").on("keyup", function () {
        // Get value from search form (fixing spaces and case insensitive
        var searchText = $(this).val();
        searchText = searchText.toLowerCase();
        searchText = searchText.replace(/\s+/g, "");

        $.each($("#edge-list-ul")[0].childNodes, updateEdgeArray);

        function updateEdgeArray() {

            var currentLiText = $(this).find("span")[0].innerHTML,
                showCurrentLi = ((currentLiText.toLowerCase()).replace(/\s+/g, "")).indexOf(searchText) !== -1;
            $(this).toggle(showCurrentLi);
        }
    });

    /// Random Paths ////

    var randomPaths = $("#random-paths");

    randomPaths.off("click"); // It will unbind the previous click if multiple graphs has been rendered

    randomPaths.on("click", function () {

            var args = getDefaultAjaxParameters(tree);

            $.ajax({
                url: "/api/pathway/paths/random",
                dataType: "json",
                data: $.param(args, true),
                success: function (paths) {
                    handlePathResponse(paths, false, null);
                },
                error: function (request) {
                    alert(request.responseText);
                }
            })
        }
    );


    var highlightButton = $("#highlight-button");
    highlightButton.off("click"); // It will unbind the previous click if multiple graphs has been rendered

    // Highlight stuffs
    highlightButton.click(function (event) {
        event.preventDefault();

        // Reduce opacity of all nodes/edges to minimum
        svg.selectAll(".node").style("opacity", "0.1");
        svg.selectAll(".link").style("opacity", "0.1");

        $(".highlight-checkbox:checked").each(function (idx, li) {
            var highlightSpan = li.parentElement.parentElement.childNodes[3];

            var spanClass = highlightSpan.className.split("-");

            // If "node" is the first element of the class, call highlight by nodes. Else highlight by edge
            if (spanClass[0] === "node") {
                highlightNodesByProperty(spanClass[1], highlightSpan.id);
            } else {
                highlightEdgesByRelationship(highlightSpan.id);
            }
        });

        resetAttributesDoubleClick()

    });

    var removeConvexHulls = $("#remove-convex-hulls");
    removeConvexHulls.off("click"); // It will unbind the previous click if multiple graphs has been rendered

    // Remove Convex Hulls
    removeConvexHulls.click(function (event) {
        event.preventDefault();
        svg.selectAll('.path_placeholder').remove()
    });

    // Get or show all paths between two nodes via Ajax

    var betwennessForm = $("#betweenness-centrality");

    $("#betweenness-button").on("click", function () {
        if (betwennessForm.valid()) {

            var args = getDefaultAjaxParameters(tree);

            args["node_number"] = betwennessForm.find("input[name='betweenness']").val();

            $.ajax({
                url: "/api/pathway/centrality",
                type: betwennessForm.attr("method"),
                dataType: "json",
                data: $.param(args, true),
                success: function (data) {

                    var nodesToIncrease = nodesInArrayKeepOrder(data, 'id');

                    var nodesToReduce = nodesNotInArray(data, 'id');

                    // Reduce to 7 radius the nodes not in top x
                    $.each(nodesToReduce._groups[0], function (index, value) {
                        value.childNodes[0].setAttribute("r", "7");
                    });

                    // Make bigger by factor scale the nodes in the top x
                    //TODO: change this coefficient
                    var nodeFactor = (nominalBaseNodeSize / 3) / nodesToIncrease.length;
                    var factor = nominalBaseNodeSize + nodeFactor;

                    $.each(nodesToIncrease.reverse(), function (index, value) {
                        value.childNodes[0].setAttribute("r", factor);
                        factor += nodeFactor;
                    });
                },
                error: function (request) {
                    alert(request.responseText);
                }
            })
        }
    });

    betwennessForm.validate(
        {
            rules: {
                betweenness: {
                    required: true,
                    digits: true
                }
            },
            messages: {
                betweenness: "Please enter a number"
            }
        }
    );


    ///////////////////////
    // Tool modal buttons /
    ///////////////////////

    // Hide node names button

    var hideNodeNames = $("#hide-node-names");

    hideNodeNames.off("click"); // It will unbind the previous click if multiple graphs has been rendered

    // Hide text in graph
    hideNodeNames.on("click", function () {
        svg.selectAll(".node-name").style("display", "none");
    });

    var restoreNodeNames = $("#restore-node-names");

    restoreNodeNames.off("click"); // It will unbind the previous click if multiple graphs has been rendered

    // Hide text in graph
    restoreNodeNames.on("click", function () {
        svg.selectAll(".node-name").style("display", "block");
    });

    var restoreAll = $("#restore");

    restoreAll.off("click"); // It will unbind the previous click if multiple graphs has been rendered

    // Restore all
    restoreAll.on("click", function () {
        resetAttributes();
    });

    var removeNodeHighlighting = $("#remove-node-highlighting");

    removeNodeHighlighting.off("click"); // It will unbind the previous click if multiple graphs has been rendered

    // Restore all
    removeNodeHighlighting.on("click", function () {
        removeHighlightNodeBorder();
    });

}
