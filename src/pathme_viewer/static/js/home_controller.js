/** This JS controls the main page of PathMe
 **
 * @requires: jquery
 */

$(document).ready(function () {

    // Autocompletion in the first input
    $('#input-1').autocomplete({
        source: function (request, response) {
            $.ajax({
                url: "/api/autocompletion/pathway_name",
                dataType: "json",
                data: {
                    resource: $('#select-1').find(":selected").val(),
                    q: request.term
                },
                success: function (data) {
                    response(data); // functionName
                }
            });
        }, minLength: 2
    });

    // Autocompletion for nodes seeding
    $("#node_selection").select2({
        theme: "bootstrap",
        minimumInputLength: 2,
        multiple: true,
        placeholder: 'Please type any node',
        ajax: {
            url: "/api/node/suggestion/",
            type: "GET",
            contentType: "application/json; charset=utf-8",
            dataType: "json",
            data: function (params) {
                return {
                    q: params.term
                };
            },
            delay: 250,
            processResults: function (data) {
                return {
                    results: data.map(function (item) {
                            return {
                                id: item.id, // node_id
                                text: item.text // bel
                            };
                        }
                    )
                };
            }
        }
    });

});

/**
 * * Dynamically adds/deletes pathways inputs
 */
$(function () {

    var cloneCount = 1; // Avoid duplicate ids

    // Remove button click
    $(document).on(
        'click',
        '[data-role="dynamic-fields"] > .form-inline [data-role="remove"]',
        function (e) {
            e.preventDefault();
            $(this).closest('.form-inline').remove();
        }
    );
    // Add button click
    $(document).on(
        'click',
        '[data-role="dynamic-fields"] > .form-inline [data-role="add"]',
        function (e) {
            e.preventDefault();
            var container = $(this).closest('[data-role="dynamic-fields"]');
            var new_field_group = container.children().filter('.form-inline:first-child').clone();

            pathwayNameInput = $(new_field_group.find('input')[0]); // get input
            resourceSelect = $(new_field_group.find('select')[0]); // get select

            // Increment the counter and save the variable to change the id of the cloned form
            cloneCount++;
            var currentCounter = cloneCount;

            // Empty current value and id to set up auto completion
            pathwayNameInput.attr('id', 'input-' + currentCounter);
            resourceSelect.attr('id', 'select-' + currentCounter);
            pathwayNameInput[0].value = '';
            resourceSelect[0].value = '';

            pathwayNameInput.autocomplete({
                source: function (request, response) {
                    $.ajax({
                        url: "/api/autocompletion/pathway_name",
                        dataType: "json",
                        data: {
                            resource: $('#select-' + currentCounter).find(":selected").val(),
                            q: request.term
                        },
                        success: function (data) {
                            response(data);
                        }
                    });
                }, minLength: 2
            });

            container.append(new_field_group);
        }
    );
});
